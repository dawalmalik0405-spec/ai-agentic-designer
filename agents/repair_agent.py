import logging
import os
from collections import defaultdict
from pathlib import Path

from agents.page_code_agent import OUTPUT_DIR, PageCodeAgent, ProjectShellGenerator
from schema.page_d import PageDesignOutput
from schema.desighn import DesignSystemOutput
from schema.repair import BuildCheckResult, RepairLoopResult

logger = logging.getLogger(__name__)


class RepairAgent:
    """Applies targeted fixes to generated TSX files based on build errors."""

    def __init__(self, output_dir: str | None = None) -> None:
        self.output_dir = output_dir or OUTPUT_DIR
        self.page_code_agent = PageCodeAgent()

    def _normalize_relative_path(self, file_path: str) -> str:
        normalized = file_path.replace("\\", "/")
        if normalized.startswith(f"{Path(self.output_dir).name}/"):
            normalized = normalized.split("/", 1)[1]
        return normalized.lstrip("/")

    def _group_errors_by_file(self, build_result: BuildCheckResult) -> dict[str, list]:
        grouped: dict[str, list] = defaultdict(list)
        for error in build_result.errors:
            relative = self._normalize_relative_path(error.file)
            grouped[relative].append(error)
        return dict(grouped)

    def _page_name_for_file(self, relative_path: str, page_design_output: PageDesignOutput) -> str | None:
        if not relative_path.startswith("src/pages/") or not relative_path.endswith(".tsx"):
            return None

        module_name = Path(relative_path).stem
        for page in page_design_output.pages:
            if ProjectShellGenerator._module_name(page.page_name) == module_name:
                return page.page_name
        return PageCodeAgent.module_name_to_page_name(module_name)

    async def fix(
        self,
        build_result: BuildCheckResult,
        page_design_output: PageDesignOutput,
        design_system_output: DesignSystemOutput | None,
        selected_style: str = "default",
    ) -> list[str]:
        grouped = self._group_errors_by_file(build_result)
        if not grouped:
            return []

        repaired_files: list[str] = []
        state = {
            "page_design_output": page_design_output,
            "design_system_output": design_system_output,
            "selected_style": selected_style,
        }

        page_files = sorted(
            path for path in grouped if path.startswith("src/pages/") and path.endswith(".tsx")
        )
        other_files = sorted(path for path in grouped if path not in page_files)

        for relative_path in page_files + other_files:
            errors = grouped[relative_path]
            absolute_path = os.path.join(self.output_dir, relative_path.replace("/", os.sep))
            if not os.path.exists(absolute_path):
                logger.warning("Repair skipped missing file: %s", relative_path)
                continue

            original_code = Path(absolute_path).read_text(encoding="utf-8")
            backup = original_code

            try:
                page_name = self._page_name_for_file(relative_path, page_design_output)
                if page_name and any(
                    page.page_name == page_name for page in page_design_output.pages
                ):
                    error_text = "\n".join(
                        f"{err.file} ({err.line},{err.column}): {err.code or 'error'} {err.message}"
                        for err in errors
                    )
                    await self.page_code_agent.generate_single_page(
                        state,
                        page_name,
                        instruction=(
                            "Fix these compile errors while preserving the existing design:\n"
                            f"{error_text}"
                        ),
                    )
                else:
                    await self.page_code_agent.repair_file(
                        relative_path,
                        original_code,
                        errors,
                        output_dir=self.output_dir,
                    )
                repaired_files.append(relative_path)
            except Exception as exc:
                logger.warning("Repair failed for %s: %s", relative_path, exc)
                Path(absolute_path).write_text(backup, encoding="utf-8")

        return repaired_files
