import re
import sys

from schema.repair import BuildCheckResult, CompileError

# TypeScript: src/pages/Home.tsx(234,21): error TS2322: message
TSC_ERROR_PATTERN = re.compile(
    r"^(?P<file>[^\s(]+)\((?P<line>\d+),(?P<col>\d+)\):\s+error\s+(?P<code>TS\d+):\s+(?P<message>.+)$"
)

# Vite / rollup style: file.tsx:234:21 - error TS2322: message
ALT_ERROR_PATTERN = re.compile(
    r"^(?P<file>[^\s:]+\.tsx?)\:(?P<line>\d+)\:(?P<col>\d+)\s+-\s+error\s+(?P<code>TS\d+):\s+(?P<message>.+)$"
)

VITE_IMPORT_PATTERN = re.compile(
    r"(Failed to resolve import|Cannot find module)\s+[\"'](?P<target>[^\"']+)[\"']",
    re.IGNORECASE,
)


def parse_compile_errors(log_lines: list[str]) -> list[CompileError]:
    errors: list[CompileError] = []
    seen: set[tuple[str, str]] = set()

    for line in log_lines:
        stripped = line.strip()
        if not stripped:
            continue

        match = TSC_ERROR_PATTERN.match(stripped) or ALT_ERROR_PATTERN.match(stripped)
        if match:
            groups = match.groupdict()
            key = (groups["file"], groups["message"])
            if key in seen:
                continue
            seen.add(key)
            errors.append(
                CompileError(
                    file=groups["file"].replace("\\", "/"),
                    line=int(groups["line"]),
                    column=int(groups["col"]),
                    code=groups["code"],
                    message=groups["message"],
                )
            )
            continue

        import_match = VITE_IMPORT_PATTERN.search(stripped)
        if import_match:
            message = stripped
            key = ("main.tsx", message)
            if key not in seen:
                seen.add(key)
                errors.append(
                    CompileError(
                        file="src/main.tsx",
                        message=message,
                    )
                )

    return errors


class BuildChecker:
    """Runs npm run build and parses TypeScript / Vite errors."""

    async def run(self, output_dir: str) -> BuildCheckResult:
        from agents.page_code_agent import DevServerManager

        dev_server = DevServerManager()
        npm_cmd = "npm.cmd" if sys.platform == "win32" else "npm"
        returncode, lines = await dev_server._run_streamed(
            [npm_cmd, "run", "build"],
            cwd=output_dir,
            label="npm run build",
        )
        errors = parse_compile_errors(lines)
        return BuildCheckResult(
            success=returncode == 0,
            log_tail=lines[-40:],
            errors=errors,
        )
