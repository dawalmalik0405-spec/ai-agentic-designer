from typing import TypedDict


class AgentState(TypedDict):
  prompt: str
  pages: dict
  ui: dict
  theme: dict
  assets: dict
  plan: dict

