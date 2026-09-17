"""Tests for the provider-neutral error hierarchy and `FallbackReason`."""

from protege.llm.errors import (
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


def test_provider_error_carries_provider_and_model() -> None:
    exc = ProviderError("nvidia", "nvidia/nemotron-3-super-120b-a12b")
    assert exc.provider == "nvidia"
    assert exc.model_id == "nvidia/nemotron-3-super-120b-a12b"
    assert "nvidia" in str(exc)


def test_provider_subclasses_are_provider_errors() -> None:
    for cls in (ProviderRateLimited, ProviderTimeout, ProviderConfigError, CircuitBreakerOpen):
        exc = cls("nvidia", "m1")
        assert isinstance(exc, ProviderError)


def test_provider_failed_carries_status_code() -> None:
    exc = ProviderFailed("nvidia", "m1", 503)
    assert exc.status_code == 503
    assert "503" in str(exc)


def test_provider_failed_status_code_optional() -> None:
    exc = ProviderFailed("nvidia", "m1")
    assert exc.status_code is None


def test_structured_output_failed_message_names_role_and_cause() -> None:
    cause = ValueError("bad json")
    exc = StructuredOutputFailed("SPROUT", cause)
    assert exc.role == "SPROUT"
    assert exc.last_error is cause
    assert "SPROUT" in str(exc)
    assert "bad json" in str(exc)


def test_all_providers_exhausted_names_role() -> None:
    exc = AllProvidersExhausted("DIAGNOSTICIAN")
    assert exc.role == "DIAGNOSTICIAN"
    assert "DIAGNOSTICIAN" in str(exc)


def test_fallback_reason_values_match_addendum_2_7() -> None:
    # Addendum §2.7 comment: "rate_limit|timeout|schema|validator" (not
    # exhaustive — see FallbackReason's docstring for the two additions).
    assert FallbackReason.RATE_LIMIT == "rate_limit"
    assert FallbackReason.TIMEOUT == "timeout"
    assert FallbackReason.SCHEMA == "schema"
    assert FallbackReason.VALIDATOR == "validator"
    assert FallbackReason.SERVER_ERROR == "server_error"
    assert FallbackReason.CIRCUIT_OPEN == "circuit_open"
