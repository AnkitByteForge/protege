"""Foundation-only smoke test (feature/phase2-foundation).

Confirms the package is installed and importable inside the uv workspace.
Real provider/router tests land on feature/p4-llm.
"""

import protege.llm as llm


def test_package_importable() -> None:
    assert llm.__version__ == "0.1.0"
