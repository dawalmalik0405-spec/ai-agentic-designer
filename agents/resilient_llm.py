from __future__ import annotations

import logging
from typing import Any

from mcp_tools.resilience import ProviderResilience


logger = logging.getLogger(__name__)


async def resilient_ainvoke(
    model: Any,
    messages: Any,
    operation_name: str
) -> Any:
    model_name = getattr(
        model,
        "model",
        getattr(
            model,
            "model_name",
            model.__class__.__name__
        )
    )
    provider_name = f"llm_{str(model_name).replace('/', '_')}"
    resilience = ProviderResilience.from_env(
        provider_name,
        logger=logger
    )

    return await resilience.execute(
        operation_name,
        lambda: model.ainvoke(
            messages
        )
    )
