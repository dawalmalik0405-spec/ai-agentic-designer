from ai_agentic_designer.agents.site_spec import apply_layout_metadata


def generate_ui(site_spec: dict) -> dict:
    return apply_layout_metadata(site_spec)
