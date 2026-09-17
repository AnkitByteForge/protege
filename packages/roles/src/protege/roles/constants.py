"""Tunable, documented constants for the P6 Diagnostician.

Every value here is cited to the document that fixes it. None is a silent
default invented by this package — where a canonical document does not fix a
number (confidence calibration, evidence-span matching), the constant is
still named and documented here rather than left as a magic literal at the
call site.
"""

ASR_CONFIDENCE_THRESHOLD = 0.65
"""§7.3: "if mean_asr_confidence < 0.65, must return asr_reliable:false and
abstain rather than guess." Applies only to voice explanations — the other
three teach-back modalities (text, manipulative, explanation_card) carry no
ASR signal and are always treated as reliable (roadmap P18: voice is an
enhancement, never a requirement)."""

MAX_TRACKED_LABELS = 8
"""§22 ``diagnoses.labels`` / ``DiagnosisResult.labels`` (packages/contracts):
at most one label per authored misconception (roadmap P3: 8 misconceptions).
Matches the contract's own ``max_length=8``."""

OTHER_OBSERVED_BEHAVIOR = "other"
"""docs/DECISIONS.md D10/D13: the authored ``"other"`` fallback key used
when a diagnosis is not tied to one specific authored distractor-behavior
key in a misconception's ``distractor_likelihood`` table."""
