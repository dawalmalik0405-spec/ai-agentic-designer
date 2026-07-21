from __future__ import annotations

import asyncio
import logging
import os
import random
import time
from dataclasses import dataclass
from enum import Enum
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar


T = TypeVar("T")


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(RuntimeError):
    pass


@dataclass(frozen=True)
class RetryPolicy:
    attempts: int = 3
    base_delay: float = 0.5
    max_delay: float = 8.0
    jitter: float = 0.25
    timeout: float = 180.0


@dataclass(frozen=True)
class CircuitBreakerPolicy:
    failure_threshold: int = 3
    recovery_timeout: float = 60.0
    half_open_success_threshold: int = 1


@dataclass(frozen=True)
class ProviderResilienceConfig:
    provider_name: str
    retry: RetryPolicy = RetryPolicy()
    circuit_breaker: CircuitBreakerPolicy = CircuitBreakerPolicy()


class CircuitBreaker:
    def __init__(
        self,
        policy: CircuitBreakerPolicy,
        provider_name: str,
        logger: logging.Logger | None = None
    ):
        self.policy = policy
        self.provider_name = provider_name
        self.logger = logger or logging.getLogger(__name__)
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.opened_at: float | None = None

    def before_call(self) -> None:
        if self.state != CircuitState.OPEN:
            return

        opened_at = self.opened_at or 0
        elapsed = time.monotonic() - opened_at

        if elapsed >= self.policy.recovery_timeout:
            self.state = CircuitState.HALF_OPEN
            self.success_count = 0
            self.logger.info(
                "Provider circuit half-open",
                extra={
                    "provider": self.provider_name,
                    "state": self.state.value
                }
            )
            return

        raise CircuitOpenError(
            f"Circuit open for provider {self.provider_name}"
        )

    def record_success(self) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count < self.policy.half_open_success_threshold:
                return

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.opened_at = None

    def record_failure(self) -> None:
        self.failure_count += 1
        self.success_count = 0

        if self.failure_count >= self.policy.failure_threshold:
            self.state = CircuitState.OPEN
            self.opened_at = time.monotonic()
            self.logger.warning(
                "Provider circuit opened",
                extra={
                    "provider": self.provider_name,
                    "failure_count": self.failure_count,
                    "state": self.state.value
                }
            )


class ProviderResilience:
    def __init__(
        self,
        config: ProviderResilienceConfig,
        logger: logging.Logger | None = None
    ):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.circuit_breaker = CircuitBreaker(
            policy=config.circuit_breaker,
            provider_name=config.provider_name,
            logger=self.logger
        )

    @classmethod
    def from_env(
        cls,
        provider_name: str,
        logger: logging.Logger | None = None
    ) -> "ProviderResilience":
        prefix = provider_name.upper().replace("-", "_")

        retry = RetryPolicy(
            attempts=int(
                os.getenv(
                    f"{prefix}_RETRY_ATTEMPTS",
                    os.getenv("PROVIDER_RETRY_ATTEMPTS", "3")
                )
            ),
            base_delay=float(
                os.getenv(
                    f"{prefix}_RETRY_BASE_DELAY",
                    os.getenv("PROVIDER_RETRY_BASE_DELAY", "0.5")
                )
            ),
            max_delay=float(
                os.getenv(
                    f"{prefix}_RETRY_MAX_DELAY",
                    os.getenv("PROVIDER_RETRY_MAX_DELAY", "8")
                )
            ),
            jitter=float(
                os.getenv(
                    f"{prefix}_RETRY_JITTER",
                    os.getenv("PROVIDER_RETRY_JITTER", "0.25")
                )
            ),
            timeout=float(
                os.getenv(
                    f"{prefix}_TIMEOUT_SECONDS",
                    os.getenv("PROVIDER_TIMEOUT_SECONDS", "180")
                )
            )
        )

        circuit_breaker = CircuitBreakerPolicy(
            failure_threshold=int(
                os.getenv(
                    f"{prefix}_CIRCUIT_FAILURE_THRESHOLD",
                    os.getenv("PROVIDER_CIRCUIT_FAILURE_THRESHOLD", "3")
                )
            ),
            recovery_timeout=float(
                os.getenv(
                    f"{prefix}_CIRCUIT_RECOVERY_SECONDS",
                    os.getenv("PROVIDER_CIRCUIT_RECOVERY_SECONDS", "60")
                )
            ),
            half_open_success_threshold=int(
                os.getenv(
                    f"{prefix}_CIRCUIT_HALF_OPEN_SUCCESSES",
                    os.getenv("PROVIDER_CIRCUIT_HALF_OPEN_SUCCESSES", "1")
                )
            )
        )

        return cls(
            ProviderResilienceConfig(
                provider_name=provider_name,
                retry=retry,
                circuit_breaker=circuit_breaker
            ),
            logger=logger
        )

    def _delay_for_attempt(self, attempt: int) -> float:
        retry = self.config.retry
        exponential_delay = min(
            retry.base_delay * (2 ** max(attempt - 1, 0)),
            retry.max_delay
        )
        jitter_amount = random.uniform(
            0,
            retry.jitter
        )
        return exponential_delay + jitter_amount

    async def execute(
        self,
        operation_name: str,
        operation: Callable[[], Awaitable[T]]
    ) -> T:
        retry = self.config.retry
        last_error: Exception | None = None

        for attempt in range(1, retry.attempts + 1):
            self.circuit_breaker.before_call()
            started_at = time.monotonic()

            try:
                result = await asyncio.wait_for(
                    operation(),
                    timeout=retry.timeout
                )
                elapsed_ms = int(
                    (time.monotonic() - started_at) * 1000
                )
                self.circuit_breaker.record_success()
                self.logger.info(
                    "Provider call succeeded",
                    extra={
                        "provider": self.config.provider_name,
                        "operation": operation_name,
                        "attempt": attempt,
                        "elapsed_ms": elapsed_ms
                    }
                )
                return result

            except Exception as error:
                last_error = error
                elapsed_ms = int(
                    (time.monotonic() - started_at) * 1000
                )
                self.circuit_breaker.record_failure()

                self.logger.warning(
                    "Provider call failed",
                    extra={
                        "provider": self.config.provider_name,
                        "operation": operation_name,
                        "attempt": attempt,
                        "max_attempts": retry.attempts,
                        "elapsed_ms": elapsed_ms,
                        "error_type": type(error).__name__,
                        "error": str(error)
                    }
                )

                if attempt >= retry.attempts:
                    break

                await asyncio.sleep(
                    self._delay_for_attempt(attempt)
                )

        assert last_error is not None
        raise last_error

    def wrap(
        self,
        operation_name: str
    ) -> Callable[
        [Callable[..., Awaitable[T]]],
        Callable[..., Awaitable[T]]
    ]:
        def decorator(
            func: Callable[..., Awaitable[T]]
        ) -> Callable[..., Awaitable[T]]:
            @wraps(func)
            async def wrapper(
                *args: Any,
                **kwargs: Any
            ) -> T:
                return await self.execute(
                    operation_name,
                    lambda: func(
                        *args,
                        **kwargs
                    )
                )

            return wrapper

        return decorator
