"""Identifier and scalar constraint types.

Codes are strict where the documents are strict (`S004`, `M003`); opaque IDs
are deliberately loose because the persistence layer (P9) assigns UUIDs while
documents and events use prefixed strings.
"""

from typing import Annotated

from pydantic import Field, StringConstraints

SkillCode = Annotated[
    str,
    StringConstraints(pattern=r"^S\d{3}(_[a-z][a-z0-9_]*)?$"),
    Field(examples=["S004", "S001_identify_fraction"]),
]
"""Skill graph node code. `S004` canonical form; the suffix form mirrors the
prerequisite strings used in the §38 worked example."""

MisconceptionCode = Annotated[str, StringConstraints(pattern=r"^M\d{3}$"), Field(examples=["M003"])]
"""Misconception library code (`M003`)."""

ItemId = Annotated[str, StringConstraints(min_length=1, max_length=64)]
"""Learning item identifier (`i_0132` in documents; opaque otherwise)."""

InterventionId = Annotated[str, StringConstraints(min_length=1, max_length=64)]
"""Authored intervention identifier (`INT_M003_A`)."""

SproutScriptId = Annotated[str, StringConstraints(min_length=1, max_length=64)]
"""Authored Sprout utterance identifier (`SS_M003_01`)."""

OpaqueId = Annotated[str, StringConstraints(min_length=1, max_length=128)]
"""Learner/session/trace/event identifiers. Opaque; never a child's name."""

LearnerId = Annotated[OpaqueId, Field(examples=["lrn_01J..."])]
SessionId = Annotated[OpaqueId, Field(examples=["ses_01J..."])]
EventId = Annotated[OpaqueId, Field(examples=["evt_01J..."])]
TraceId = Annotated[OpaqueId, Field(examples=["otel_..."])]
EvidenceId = Annotated[OpaqueId, Field(examples=["e_901"])]
ClaimId = Annotated[OpaqueId, Field(examples=["c_88"])]
ExplanationId = Annotated[OpaqueId, Field(examples=["exp_..."])]
EpisodeId = Annotated[OpaqueId, Field(examples=["te_77"])]
"""Prefixed opaque identifiers from the documents. Same looseness as
OpaqueId; named aliases exist so signatures document what they expect."""

ContentVersion = Annotated[
    str, StringConstraints(pattern=r"^v\d+(-[\w.]+)?$"), Field(examples=["v1"])
]
"""Content package version tag (`v1`); rollback = flipping the pointer."""

GradeBand = Annotated[str, StringConstraints(pattern=r"^[K0-9]+-[K0-9]+$"), Field(examples=["3-4"])]
"""Grade band (`3-4` in the §38 worked example)."""

EloRating = Annotated[int, Field(ge=0, le=3000)]
"""Elo item-difficulty rating. The §38 worked example uses 1180; typical
authored priors land in 800-1800 (ARCHITECTURE.md §10.2)."""

Probability = Annotated[float, Field(ge=0.0, le=1.0)]
"""Any probability in [0, 1]: priors, posteriors, confidences, likelihoods."""

PositiveInt = Annotated[int, Field(ge=0)]
"""Non-negative counter (evidence counts, hint counts, turns)."""

ProbabilityWeight = Annotated[float, Field(ge=0.0, le=3.0)]
"""Evidence weight. 1.0 default, 0.4 after two hints, 3.0 for unaided
verification (ARCHITECTURE.md §10.1 rules 2 and 4)."""
