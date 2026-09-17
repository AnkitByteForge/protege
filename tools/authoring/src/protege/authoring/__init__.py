"""PROTÉGÉ offline authoring tools.

Roadmap P3 (misconception library & item bank): this package loads the
versioned content pack under ``content/math/fractions/v1/`` into the P1
contracts (``packages/contracts``), runs deterministic validation
(``validators.py``), and writes the content manifest (``manifest.py``) that
records validation results without ever marking content as human-ratified.

The offline Fable 5.1 / ``anthropic`` SDK drafting workflow (addendum
§1.3, §9.4-9.5) is a separate, human-invoked step outside this package's
import graph: nothing here calls a network LLM, and this package is never a
runtime dependency of the session service.
"""

__version__ = "0.2.0"
