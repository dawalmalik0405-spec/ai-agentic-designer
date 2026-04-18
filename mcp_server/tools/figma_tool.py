import hashlib
import os
from typing import Any

import requests

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency fallback for local environments
    def load_dotenv():
        return False

load_dotenv()

FIGMA_API_KEY = os.getenv("FIGMA_API_KEY")
FIGMA_FILE_KEY = os.getenv("FIGMA_FILE_KEY")


def get_figma_file(file_key: str | None = None) -> dict[str, Any]:
    target_file_key = file_key or FIGMA_FILE_KEY
    if not target_file_key:
        return {
            "status": "error",
            "file_key": None,
            "file_name": None,
            "errors": [{"code": "missing_file_key", "message": "Figma file key is not configured."}],
        }

    if not FIGMA_API_KEY:
        return {
            "status": "error",
            "file_key": target_file_key,
            "file_name": None,
            "errors": [{"code": "missing_api_key", "message": "Figma API key is not configured."}],
        }

    url = f"https://api.figma.com/v1/files/{target_file_key}"
    headers = {"X-Figma-Token": FIGMA_API_KEY}

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        return {
            "status": "error",
            "file_key": target_file_key,
            "file_name": None,
            "errors": [{"code": "request_failed", "message": str(exc)}],
        }

    payload = response.json()
    return {
        "status": "ok",
        "file_key": target_file_key,
        "file_name": payload.get("name"),
        "document": payload.get("document"),
        "errors": [],
    }


def build_figma_request(site_spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "project": site_spec["project"],
        "design_system": site_spec["design_system"],
        "shared_components": site_spec["shared_components"],
        "pages": site_spec["pages"],
        "sync_strategy": site_spec["figma_sync"]["sync_strategy"],
    }


def _stable_ref(prefix: str, value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{digest}"


def _build_token_refs(design_system: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    token_refs = {}
    for token_group, token_values in design_system.items():
        if not isinstance(token_values, dict):
            continue
        refs = []
        for token_name in token_values.keys():
            token_id = _stable_ref("token", f"{token_group}:{token_name}")
            refs.append({"token_id": token_id, "name": f"{token_group}/{token_name}"})
        token_refs[token_group] = refs
    return token_refs


def _build_component_refs(shared_components: list[dict[str, Any]]) -> list[dict[str, str]]:
    refs = []
    for component in shared_components:
        value = f"{component['component_id']}:{component['section_type']}:{component['variant']}"
        refs.append(
            {
                "component_id": component["component_id"],
                "figma_ref": _stable_ref("component", value),
                "name": component["section_type"],
            }
        )
    return refs


def _build_page_frame_refs(pages: list[dict[str, Any]]) -> list[dict[str, str]]:
    refs = []
    for page in pages:
        refs.append(
            {
                "page_id": page["page_id"],
                "frame_ref": _stable_ref("frame", page["page_id"]),
                "name": page["name"],
            }
        )
    return refs


def _build_section_instance_refs(pages: list[dict[str, Any]]) -> list[dict[str, str]]:
    refs = []
    for page in pages:
        for section in page.get("sections", []):
            refs.append(
                {
                    "page_id": page["page_id"],
                    "instance_id": section["instance_id"],
                    "frame_ref": _stable_ref("section", section["instance_id"]),
                    "section_type": section["section_type"],
                }
            )
    return refs


def sync_site_spec_to_figma(site_spec: dict[str, Any]) -> dict[str, Any]:
    figma_request = build_figma_request(site_spec)
    file_key = site_spec["figma_sync"]["project_file_id"]
    file_name = site_spec["figma_sync"]["file_name"]

    token_refs = _build_token_refs(figma_request["design_system"])
    component_refs = _build_component_refs(figma_request["shared_components"])
    page_frame_refs = _build_page_frame_refs(figma_request["pages"])
    section_instance_refs = _build_section_instance_refs(figma_request["pages"])

    errors = []
    status = "synced"

    if not FIGMA_API_KEY:
        status = "sync_simulated"
        errors.append(
            {
                "code": "missing_api_key",
                "message": "Figma API key is not configured; returning deterministic sync references only.",
            }
        )
    elif FIGMA_FILE_KEY:
        file_lookup = get_figma_file(FIGMA_FILE_KEY)
        if file_lookup["status"] == "error":
            status = "sync_simulated"
            errors.extend(file_lookup["errors"])
        else:
            file_key = file_lookup["file_key"] or file_key
            file_name = file_lookup["file_name"] or file_name

    return {
        "status": status,
        "file_key": file_key,
        "file_name": file_name,
        "figma_request": figma_request,
        "token_refs": token_refs,
        "component_refs": component_refs,
        "page_frame_refs": page_frame_refs,
        "section_instance_refs": section_instance_refs,
        "errors": errors,
    }
