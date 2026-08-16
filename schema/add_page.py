from pydantic import BaseModel


class AddPageRequest(BaseModel):
    page_name: str
    prompt: str
    selected_style: str = "minimalism"


class AddPageOutput(BaseModel):
    page_name: str
    route: str
    file_path: str
    preview_url: str | None = None
    dev_server_status: str | None = None
    log_tail: list[str] = []
