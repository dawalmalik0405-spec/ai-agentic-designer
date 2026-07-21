import logging
import os

from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_google_genai import ChatGoogleGenerativeAI


CURRENT_DIR = os.path.dirname(__file__)
PACKAGE_ROOT = os.path.dirname(CURRENT_DIR)
PROJECT_ROOT = os.path.dirname(PACKAGE_ROOT)

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
load_dotenv(os.path.join(PACKAGE_ROOT, ".env"), override=False)
load_dotenv()

logger = logging.getLogger(__name__)

PLANNING_MODEL = os.getenv("PLANNING_MODEL", "mistralai/mistral-small-4-119b-2603")
REASONING_MODEL = os.getenv("REASON_MODEL", "minimaxai/minimax-m2.7")
RESEARCH_MODEL = os.getenv("RESEARCH_MODEL", "llama-3.3-70b-versatile")
CODE_MODEL = os.getenv("CODE_MODEL", "deepseek-ai/deepseek-v4-pro")


def _build_nvidia_llm(model_name: str, temperature: float):
    api_key = (
        os.getenv("NVIDIA_API_KEY")
        or os.getenv("NGC_API_KEY")
        or os.getenv("LANGCHAIN_NVIDIA_API_KEY")
    )
    if not api_key:
        raise RuntimeError("NVIDIA_API_KEY is not configured")

    return ChatNVIDIA(
        api_key=api_key,
        model=model_name,
        temperature=temperature,
        top_p=0.95,
        max_completion_tokens=int(os.getenv("NVIDIA_CODE_MAX_TOKENS", "16384")),
    )


GEMINI_MODEL = os.getenv("GEMINI_MODEL","gemini-3.5-flash")
def _build_gemini_llm(model_name: str, temperature: float):
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=temperature,
    )

def gemini_flash_llm():
    return _build_gemini_llm(
        "gemini-3.5-flash",
        temperature=0.3,
    )


def deepseek_llm():
    return _build_nvidia_llm(PLANNING_MODEL, temperature=0.2)


def qwen_llm():
    """Compatibility helper; the configured code model is NVIDIA GLM-5.2."""
    return _build_nvidia_llm(CODE_MODEL, temperature=0.3)


def mcp_code_llm():
    """Return NVIDIA GLM-5.2 for structured MCP tool calling."""
    return _build_nvidia_llm(CODE_MODEL, temperature=0.3)


def reason_llm():
    return _build_nvidia_llm(REASONING_MODEL, temperature=0.7)
