from pydantic import BaseModel
from typing import List


class SelectedWebsite(BaseModel):
    name: str
    url: str
    reason: str


class WebsiteSelection(BaseModel):
    websites: List[SelectedWebsite]