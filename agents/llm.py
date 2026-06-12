import logging
import os

from dotenv import load_dotenv
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_groq import ChatGroq


CURRENT_DIR = os.path.dirname(__file__)
PACKAGE_ROOT = os.path.dirname(CURRENT_DIR)
PROJECT_ROOT = os.path.dirname(PACKAGE_ROOT)

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
load_dotenv(os.path.join(PACKAGE_ROOT, ".env"), override=False)
load_dotenv()

logger = logging.getLogger(__name__)

PLANNING_MODEL = os.getenv("PLANNING_MODEL", "meta/llama-3.3-70b-instruct")

RESEARCH_MODEL = os.getenv("RESEARCH_MODEL", "llama-3.3-70b-versatile")
CODE_MODEL = os.getenv("CODE_MODEL", "qwen/qwen3-next-80b-a3b-instruct")


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
        max_completion_tokens=16384,
    )


def deepseek_llm():
    return _build_nvidia_llm(PLANNING_MODEL, temperature=1)


def qwen_llm():
    return _build_nvidia_llm(CODE_MODEL, temperature=0.7)


def research_llm():
    llm = ChatGroq(
        api_key=os.getenv("GROQ_API_KEY"),
        model=os.getenv("RESEARCH_MODEL", "llama-3.3-70b-versatile"),
        temperature=0
    )
    
    return llm