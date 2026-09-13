"""Tests for structured JSON logging."""

import json
import logging

from protege.session_service.logging import JsonFormatter


def test_json_formatter_outputs_parseable_json_with_extras() -> None:
    record = logging.LogRecord(
        name="protege.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello %s",
        args=("world",),
        exc_info=None,
    )
    record.http_status = 200  # type: ignore[attr-defined]

    payload = json.loads(JsonFormatter().format(record))

    assert payload["message"] == "hello world"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "protege.test"
    assert payload["http_status"] == 200
