"""PROTÉGÉ provider layer & ModelRouter (roadmap P4).

``LLMProvider`` protocol, ``NvidiaProvider`` (openai SDK, NVIDIA base_url),
``FakeProvider`` (canned responses for tests), and ``ModelRouter`` (role
policy, fallback chain, rate limiting, structured-output enforcement).

No concrete ``AnthropicProvider`` ships here and this package never depends
on the ``anthropic`` SDK — that SDK is confined to ``tools/authoring/``
(docs/DECISIONS.md D7).
"""

from .base import LLMProvider, LLMResult, Message
from .cache import PromptCache, hash_prompt
from .circuit_breaker import CircuitBreaker
from .errors import (
    AllProvidersExhausted,
    CircuitBreakerOpen,
    FallbackReason,
    ProviderConfigError,
    ProviderError,
    ProviderFailed,
    ProviderRateLimited,
    ProviderTimeout,
    StructuredOutputFailed,
)
from .providers.fake import DEFAULT_CANNED_RESPONSES, FakeOutcome, FakeProvider
from .providers.nvidia import NVIDIA_BASE_URL, NvidiaProvider
from .rate_limit import RateLimitTimeout, TokenBucket
from .router import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_RPM,
    DEFAULT_TEMPERATURE,
    DEFAULT_TIMEOUT_S,
    ROLE_POLICY,
    ROLE_RESPONSE_MODEL,
    HealthCheckResult,
    ModelRouter,
    RolePolicyError,
    StructuredCallOutcome,
)
from .structured import StructuredMode, StructuredParseError, parse_structured
from .telemetry import InMemoryTelemetrySink, ModelRunRecord, TelemetrySink

__version__ = "0.1.0"

__all__ = [  # noqa: RUF022
    "LLMProvider",
    "LLMResult",
    "Message",
    "PromptCache",
    "hash_prompt",
    "CircuitBreaker",
    "AllProvidersExhausted",
    "CircuitBreakerOpen",
    "FallbackReason",
    "ProviderConfigError",
    "ProviderError",
    "ProviderFailed",
    "ProviderRateLimited",
    "ProviderTimeout",
    "StructuredOutputFailed",
    "DEFAULT_CANNED_RESPONSES",
    "FakeOutcome",
    "FakeProvider",
    "NVIDIA_BASE_URL",
    "NvidiaProvider",
    "RateLimitTimeout",
    "TokenBucket",
    "DEFAULT_MAX_TOKENS",
    "DEFAULT_RPM",
    "DEFAULT_TEMPERATURE",
    "DEFAULT_TIMEOUT_S",
    "ROLE_POLICY",
    "ROLE_RESPONSE_MODEL",
    "HealthCheckResult",
    "ModelRouter",
    "RolePolicyError",
    "StructuredCallOutcome",
    "StructuredMode",
    "StructuredParseError",
    "parse_structured",
    "InMemoryTelemetrySink",
    "ModelRunRecord",
    "TelemetrySink",
]
