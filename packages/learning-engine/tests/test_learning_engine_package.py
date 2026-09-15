"""Foundation-only smoke test (feature/phase2-foundation).

Confirms the package is installed and importable inside the uv workspace.
Real learning-engine tests (BKT, Bayes, Elo, validators) land on
feature/p2-learning.
"""

import protege.learning_engine as learning_engine


def test_package_importable() -> None:
    assert learning_engine.__version__ == "0.1.0"
