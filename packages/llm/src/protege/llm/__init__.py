"""PROTÉGÉ provider layer & ModelRouter (roadmap P4).

`LLMProvider` protocol, `NvidiaProvider` (openai SDK, NVIDIA base_url),
`FakeProvider` (canned responses for tests), and `ModelRouter` (role
policy, fallback chain, rate limiting, structured-output enforcement).

No concrete `AnthropicProvider` ships here and this package never depends
on the `anthropic` SDK — that SDK is confined to `tools/authoring/`
(docs/DECISIONS.md D7).

This package is a foundation skeleton (feature/phase2-foundation). No
provider/router logic exists yet; it lands on feature/p4-llm.
"""

__version__ = "0.1.0"
