"""Deterministic P3 content validation (roadmap P3 "Testing" + "Validation").

Every rule here is pure and network-free: no LLM judge, no reading-level
formula (that stays in P2 — see ``p2_adapter.py``). Each rule returns the
:class:`~protege.authoring.errors.ContentValidationError` instances it
found; ``validate_content_pack`` runs every rule and returns a single
:class:`ValidationReport` covering counts, representation coverage, and
pass/fail, so a caller sees every problem in one pass rather than stopping
at the first.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from protege.contracts import Intervention, RepresentationType, SproutScript

from .errors import ContentValidationError
from .loader import ContentPack
from .p2_adapter import READING_LEVEL_STATUS_PENDING, NullReadingLevelPort, ReadingLevelPort

REQUIRED_MISCONCEPTION_COUNT = 8
REQUIRED_SPROUT_SCRIPTS_PER_MISCONCEPTION = 6
REQUIRED_INTERVENTIONS_PER_MISCONCEPTION = 3
REQUIRED_DIAGNOSTIC_ITEMS_PER_MISCONCEPTION = 4
REQUIRED_TRANSFER_ITEMS_PER_MISCONCEPTION = 2
REQUIRED_PRACTICE_ITEMS = 40
REQUIRED_GENERAL_TRANSFER_ITEMS = 8
REQUIRED_GENERAL_TRANSFER_REPRESENTATIONS = 2

ALL_REPRESENTATIONS = frozenset(RepresentationType)


def _err(rule: str, message: str) -> ContentValidationError:
    return ContentValidationError(rule, message)


# --- structural: identity and cross-references ------------------------------


def _check_id_uniqueness(pack: ContentPack) -> list[ContentValidationError]:
    errors: list[ContentValidationError] = []

    def _dupes(values: list[str]) -> list[str]:
        counts = Counter(values)
        return sorted(v for v, n in counts.items() if n > 1)

    if dupes := _dupes([s.code for s in pack.skills]):
        errors.append(_err("id_uniqueness", f"duplicate skill codes: {dupes}"))
    if dupes := _dupes([m.code for m in pack.misconceptions]):
        errors.append(_err("id_uniqueness", f"duplicate misconception codes: {dupes}"))
    if dupes := _dupes([s.script_id for s in pack.sprout_scripts]):
        errors.append(_err("id_uniqueness", f"duplicate sprout script ids: {dupes}"))
    if dupes := _dupes([i.intervention_id for i in pack.interventions]):
        errors.append(_err("id_uniqueness", f"duplicate intervention ids: {dupes}"))

    all_item_ids = (
        [i.item_id for i in pack.diagnostic_items]
        + [i.item_id for i in pack.practice_items]
        + [t.item_id for t in pack.transfer_items]
    )
    if dupes := _dupes(all_item_ids):
        errors.append(_err("id_uniqueness", f"duplicate item ids across the item bank: {dupes}"))

    return errors


def _check_misconception_code_validity(pack: ContentPack) -> list[ContentValidationError]:
    errors: list[ContentValidationError] = []
    known = {m.code for m in pack.misconceptions}

    for script in pack.sprout_scripts:
        if script.misconception_code is not None and script.misconception_code not in known:
            errors.append(
                _err(
                    "misconception_code_validity",
                    f"sprout script {script.script_id} references unknown misconception "
                    f"{script.misconception_code!r}",
                )
            )
    for interv in pack.interventions:
        if interv.misconception_code is not None and interv.misconception_code not in known:
            errors.append(
                _err(
                    "misconception_code_validity",
                    f"intervention {interv.intervention_id} references unknown misconception "
                    f"{interv.misconception_code!r}",
                )
            )
    for item in pack.diagnostic_items + pack.practice_items:
        for distractor in item.distractors:
            if distractor.maps_to not in known:
                errors.append(
                    _err(
                        "misconception_code_validity",
                        f"item {item.item_id} distractor {distractor.value!r} maps to unknown "
                        f"misconception {distractor.maps_to!r}",
                    )
                )
    for stem, example in pack.worked_examples.items():
        if example.misconception.code not in known:
            errors.append(
                _err(
                    "misconception_code_validity",
                    f"worked example {stem} misconception {example.misconception.code!r} is not "
                    "in the authored misconception set",
                )
            )
        for label in example.learner_evidence.diagnosis.labels:
            if label.misconception_code not in known:
                errors.append(
                    _err(
                        "misconception_code_validity",
                        f"worked example {stem} diagnosis references unknown misconception "
                        f"{label.misconception_code!r}",
                    )
                )
    return errors


def _check_distractor_mapping(pack: ContentPack) -> list[ContentValidationError]:
    """Diagnostic items must carry at least one distractor mapped to their
    own misconception, with a likelihood consistent with the authored
    ``distractor_likelihood`` table (roadmap P3: "every distractor maps to a
    real misconception code")."""
    errors: list[ContentValidationError] = []
    by_skill = {m.skill_code: m for m in pack.misconceptions if m.skill_code is not None}

    for item in pack.diagnostic_items:
        target = by_skill.get(item.skill_code) if item.skill_code else None
        if target is None:
            errors.append(
                _err(
                    "distractor_mapping",
                    f"diagnostic item {item.item_id} has no resolvable skill_code to check "
                    "its misconception mapping against",
                )
            )
            continue
        if not item.distractors:
            errors.append(
                _err("distractor_mapping", f"diagnostic item {item.item_id} has no distractors")
            )
            continue
        if not any(d.maps_to == target.code for d in item.distractors):
            errors.append(
                _err(
                    "distractor_mapping",
                    f"diagnostic item {item.item_id} has no distractor mapped to its own "
                    f"misconception {target.code!r}",
                )
            )
    for item in pack.practice_items:
        if not item.distractors:
            errors.append(
                _err("distractor_mapping", f"practice item {item.item_id} has no distractors")
            )
    return errors


# --- complement likelihood (D13 independent-Bernoulli Bayes update) ----------

_COMPLEMENT_SUM_TOLERANCE = 0.02
"""Authored probabilities are hand-picked, not solved for; allow small
rounding slack around 1.0 rather than demanding an exact sum."""


def _complement_errors_for(
    code: str,
    primary: dict[str, float],
    complement: dict[str, float] | None,
    *,
    context: str,
) -> list[ContentValidationError]:
    """Check one misconception's ``P(d | not M_k)`` table (D13).

    ``primary`` is the same misconception's ``distractor_likelihood``
    (``P(d | M_k)``) — used only to check the complement is independently
    authored (not a copy, not a reuse of ``"other"``) and shares the same
    behavior-key taxonomy. Nothing here compares the two tables' *meaning*;
    that independence is exactly what D13 requires.
    """
    errors: list[ContentValidationError] = []
    if complement is None:
        errors.append(
            _err(
                "complement_likelihood",
                f"{context}: misconception {code} has no "
                "distractor_likelihood_if_not_misconception — required for v1 content (D13)",
            )
        )
        return errors

    if set(complement) != set(primary):
        errors.append(
            _err(
                "complement_likelihood",
                f"{context}: misconception {code} complement keys {sorted(complement)} must "
                f"match distractor_likelihood keys {sorted(primary)} (D13: same behavior keys, "
                "opposite conditioning)",
            )
        )

    total = sum(complement.values())
    if abs(total - 1.0) > _COMPLEMENT_SUM_TOLERANCE:
        errors.append(
            _err(
                "complement_likelihood",
                f"{context}: misconception {code} complement values sum to {total:.3f}, "
                "expected ~1.0 (it must be a valid conditional distribution)",
            )
        )

    if complement == primary:
        errors.append(
            _err(
                "complement_likelihood",
                f"{context}: misconception {code} complement table is byte-identical to "
                "distractor_likelihood — D13 requires independent authoring, not a copy",
            )
        )

    if "other" in complement and "other" in primary and complement["other"] == primary["other"]:
        errors.append(
            _err(
                "complement_likelihood",
                f"{context}: misconception {code} complement 'other' value "
                f"({complement['other']}) reuses distractor_likelihood's 'other' value "
                "verbatim — D13 forbids reusing distractor_likelihood's residual bucket",
            )
        )

    return errors


def _check_complement_likelihood(pack: ContentPack) -> list[ContentValidationError]:
    """Every v1 misconception must carry an independently-authored,
    well-formed ``P(d | not M_k)`` complement (D13) — checked both on the
    top-level misconception record and on each worked example's embedded
    copy, since the two are authored together but loaded independently."""
    errors: list[ContentValidationError] = []
    for m in pack.misconceptions:
        errors += _complement_errors_for(
            m.code,
            m.distractor_likelihood,
            m.distractor_likelihood_if_not_misconception,
            context="misconceptions.json",
        )
    for stem, example in pack.worked_examples.items():
        m = example.misconception
        errors += _complement_errors_for(
            m.code,
            m.distractor_likelihood,
            m.distractor_likelihood_if_not_misconception,
            context=f"worked example {stem}",
        )
    return errors


# --- prerequisite graph -------------------------------------------------------


def _check_prerequisite_graph(pack: ContentPack) -> list[ContentValidationError]:
    errors: list[ContentValidationError] = []
    skill_codes = {s.code for s in pack.skills}

    for skill in pack.skills:
        for prereq in skill.prerequisites:
            if prereq not in skill_codes:
                errors.append(
                    _err(
                        "prerequisite_graph",
                        f"skill {skill.code} lists unknown prerequisite {prereq!r}",
                    )
                )

    edge_pairs = {(p.skill_code, p.prereq_code) for p in pack.prerequisites}
    authored_pairs = {(s.code, prereq) for s in pack.skills for prereq in s.prerequisites}
    if edge_pairs != authored_pairs:
        only_edges = sorted(edge_pairs - authored_pairs)
        only_skills = sorted(authored_pairs - edge_pairs)
        errors.append(
            _err(
                "prerequisite_graph",
                "prerequisites.json must be exactly the edges implied by skills.json "
                f"(skills.json is the single source of truth); mismatched edges: "
                f"only-in-prerequisites.json={only_edges}, only-in-skills.json={only_skills}",
            )
        )

    graph: dict[str, list[str]] = {s.code: list(s.prerequisites) for s in pack.skills}
    visiting: set[str] = set()
    visited: set[str] = set()

    def _visit(node: str, path: list[str]) -> None:
        if node in visited:
            return
        if node in visiting:
            cycle = " -> ".join([*path, node])
            errors.append(_err("prerequisite_graph", f"prerequisite cycle detected: {cycle}"))
            return
        visiting.add(node)
        for prereq in graph.get(node, []):
            _visit(prereq, [*path, node])
        visiting.discard(node)
        visited.add(node)

    for code in graph:
        _visit(code, [])

    return errors


# --- answer leakage and Sprout constraints ------------------------------------


def _protected_answers(pack: ContentPack) -> dict[str, set[str]]:
    """Per misconception, the correct-answer strings Sprout must never state
    while the misconception is unresolved (§8.4/§17 deterministic leak check).

    Sourced from every diagnostic item whose skill matches the
    misconception's skill — the same item pool the Sprout candidate scripts
    are written against.
    """
    by_skill: dict[str, str] = {
        m.skill_code: m.code for m in pack.misconceptions if m.skill_code is not None
    }
    protected: dict[str, set[str]] = {m.code: set() for m in pack.misconceptions}
    for item in pack.diagnostic_items:
        code = by_skill.get(item.skill_code) if item.skill_code else None
        if code is not None:
            protected[code].add(item.correct_answer.strip().lower())
    return protected


def _contains_answer(utterance: str, answer: str) -> bool:
    return answer.lower() in utterance.lower()


def _check_answer_leakage(pack: ContentPack) -> list[ContentValidationError]:
    """Zero-tolerance deterministic substring check (ARCHITECTURE.md §8.4,
    §17): Sprout must never state the correct answer for its own
    misconception's item family."""
    errors: list[ContentValidationError] = []
    protected = _protected_answers(pack)
    scripts_by_misconception: dict[str, list[SproutScript]] = {}
    for script in pack.sprout_scripts:
        if script.misconception_code is not None:
            scripts_by_misconception.setdefault(script.misconception_code, []).append(script)

    for code, answers in protected.items():
        for script in scripts_by_misconception.get(code, []):
            for answer in answers:
                if answer and _contains_answer(script.utterance, answer):
                    errors.append(
                        _err(
                            "answer_leakage",
                            f"sprout script {script.script_id} (misconception {code}) states "
                            f"the correct answer {answer!r} before resolution",
                        )
                    )
    return errors


_LITERAL_FORBIDDEN_MAX_WORDS = 2
"""``sprout_forbidden`` entries this short are treated as literal vocabulary
to scan for (e.g. "numerator"); longer entries describe a forbidden
*behavior* (e.g. "stating 1/4 > 1/8 before resolution") and are covered by
the answer-leakage and misconception-consistency checks instead, not by a
substring scan."""


def _check_sprout_constraints(pack: ContentPack) -> list[ContentValidationError]:
    errors: list[ContentValidationError] = []
    by_code = {m.code: m for m in pack.misconceptions}

    for script in pack.sprout_scripts:
        if script.misconception_code is None:
            errors.append(
                _err(
                    "sprout_constraints",
                    f"sprout script {script.script_id} has no misconception_code",
                )
            )
            continue
        misconception = by_code.get(script.misconception_code)
        if misconception is None:
            continue  # already reported by _check_misconception_code_validity
        for forbidden in misconception.sprout_forbidden:
            is_literal = len(forbidden.split()) <= _LITERAL_FORBIDDEN_MAX_WORDS
            if is_literal and forbidden.lower() in script.utterance.lower():
                errors.append(
                    _err(
                        "sprout_constraints",
                        f"sprout script {script.script_id} uses forbidden vocabulary "
                        f"{forbidden!r} (misconception {misconception.code})",
                    )
                )
    return errors


def _check_intervention_linkage(pack: ContentPack) -> list[ContentValidationError]:
    errors: list[ContentValidationError] = []
    by_code: dict[str, list[Intervention]] = {m.code: [] for m in pack.misconceptions}
    for interv in pack.interventions:
        if interv.misconception_code in by_code:
            by_code[interv.misconception_code].append(interv)
    for code, interventions in by_code.items():
        if len(interventions) != REQUIRED_INTERVENTIONS_PER_MISCONCEPTION:
            errors.append(
                _err(
                    "intervention_linkage",
                    f"misconception {code} has {len(interventions)} intervention(s), expected "
                    f"{REQUIRED_INTERVENTIONS_PER_MISCONCEPTION}",
                )
            )
    return errors


# --- transfer items ------------------------------------------------------------


def _transfer_pool(record: dict[str, Any]) -> str:
    pool = record.get("pool")
    if pool not in ("misconception", "general"):
        raise KeyError(f"transfer item {record.get('id')!r} missing a valid 'pool' tag")
    return str(pool)


def _check_transfer_items(pack: ContentPack) -> list[ContentValidationError]:
    errors: list[ContentValidationError] = []
    by_skill_diag_representation: dict[str, set[RepresentationType]] = {}
    for item in pack.diagnostic_items:
        if item.skill_code:
            by_skill_diag_representation.setdefault(item.skill_code, set()).add(item.representation)

    per_misconception: dict[str, list[Any]] = {m.code: [] for m in pack.misconceptions}
    general: list[Any] = []
    by_skill_code = {m.skill_code: m.code for m in pack.misconceptions if m.skill_code is not None}

    for raw, item in zip(pack.transfer_items_raw, pack.transfer_items, strict=True):
        try:
            pool = _transfer_pool(raw)
        except KeyError as exc:
            errors.append(_err("transfer_item_correctness", str(exc)))
            continue
        if pool == "general":
            general.append(item)
            continue
        code = by_skill_code.get(item.skill_code) if item.skill_code else None
        if code is None:
            errors.append(
                _err(
                    "transfer_item_correctness",
                    f"transfer item {item.item_id} tagged pool=misconception has no resolvable "
                    "misconception via skill_code",
                )
            )
            continue
        per_misconception[code].append(item)

    for code, items in per_misconception.items():
        if len(items) != REQUIRED_TRANSFER_ITEMS_PER_MISCONCEPTION:
            errors.append(
                _err(
                    "transfer_item_correctness",
                    f"misconception {code} has {len(items)} transfer item(s), expected "
                    f"{REQUIRED_TRANSFER_ITEMS_PER_MISCONCEPTION}",
                )
            )
            continue
        reps = [i.representation for i in items]
        if len(set(reps)) != len(reps):
            errors.append(
                _err(
                    "transfer_item_correctness",
                    f"misconception {code}'s transfer items must use two distinct "
                    f"representations from each other, got {reps}",
                )
            )
        misconception_skill_code = next(
            (m.skill_code for m in pack.misconceptions if m.code == code), None
        )
        diag_reps = (
            by_skill_diag_representation.get(misconception_skill_code, set())
            if misconception_skill_code is not None
            else set()
        )
        for item in items:
            if item.representation in diag_reps:
                errors.append(
                    _err(
                        "transfer_item_correctness",
                        f"transfer item {item.item_id} (misconception {code}) reuses a "
                        f"representation already used by its diagnostic items "
                        f"({item.representation}); transfer requires a NOVEL representation (§1.3)",
                    )
                )

    if len(general) != REQUIRED_GENERAL_TRANSFER_ITEMS:
        errors.append(
            _err(
                "transfer_item_correctness",
                f"general transfer pool has {len(general)} item(s), expected "
                f"{REQUIRED_GENERAL_TRANSFER_ITEMS}",
            )
        )
    general_reps = Counter(i.representation for i in general)
    if len(general_reps) != REQUIRED_GENERAL_TRANSFER_REPRESENTATIONS:
        errors.append(
            _err(
                "transfer_item_correctness",
                f"general transfer pool must span exactly "
                f"{REQUIRED_GENERAL_TRANSFER_REPRESENTATIONS} representations, got "
                f"{dict(general_reps)}",
            )
        )

    return errors


# --- counts and coverage -------------------------------------------------------


def _check_required_counts(pack: ContentPack) -> list[ContentValidationError]:
    errors: list[ContentValidationError] = []
    if len(pack.misconceptions) != REQUIRED_MISCONCEPTION_COUNT:
        errors.append(
            _err(
                "required_counts",
                f"expected {REQUIRED_MISCONCEPTION_COUNT} misconceptions, got "
                f"{len(pack.misconceptions)}",
            )
        )

    scripts_by_code = Counter(
        s.misconception_code for s in pack.sprout_scripts if s.misconception_code is not None
    )
    diagnostics_by_skill = Counter(i.skill_code for i in pack.diagnostic_items if i.skill_code)

    for m in pack.misconceptions:
        n_scripts = scripts_by_code.get(m.code, 0)
        if n_scripts != REQUIRED_SPROUT_SCRIPTS_PER_MISCONCEPTION:
            errors.append(
                _err(
                    "required_counts",
                    f"misconception {m.code} has {n_scripts} sprout script(s), expected "
                    f"{REQUIRED_SPROUT_SCRIPTS_PER_MISCONCEPTION}",
                )
            )
        if not m.sprout_forbidden:
            errors.append(
                _err(
                    "required_counts", f"misconception {m.code} has an empty sprout_forbidden list"
                )
            )
        n_diag = diagnostics_by_skill.get(m.skill_code, 0) if m.skill_code else 0
        if n_diag != REQUIRED_DIAGNOSTIC_ITEMS_PER_MISCONCEPTION:
            errors.append(
                _err(
                    "required_counts",
                    f"misconception {m.code} has {n_diag} diagnostic item(s), expected "
                    f"{REQUIRED_DIAGNOSTIC_ITEMS_PER_MISCONCEPTION}",
                )
            )

    if len(pack.practice_items) != REQUIRED_PRACTICE_ITEMS:
        errors.append(
            _err(
                "required_counts",
                f"expected {REQUIRED_PRACTICE_ITEMS} practice items, got "
                f"{len(pack.practice_items)}",
            )
        )

    if len(pack.worked_examples) != REQUIRED_MISCONCEPTION_COUNT:
        errors.append(
            _err(
                "required_counts",
                f"expected {REQUIRED_MISCONCEPTION_COUNT} worked examples, got "
                f"{len(pack.worked_examples)}",
            )
        )

    return errors


def _representation_counts(pack: ContentPack) -> Counter[RepresentationType]:
    counts: Counter[RepresentationType] = Counter()
    for item in [*pack.diagnostic_items, *pack.practice_items]:
        counts[item.representation] += 1
    for item in pack.transfer_items:
        counts[item.representation] += 1
    return counts


def _check_representation_coverage(pack: ContentPack) -> list[ContentValidationError]:
    counts = _representation_counts(pack)
    missing = ALL_REPRESENTATIONS - set(counts)
    if missing:
        return [
            _err(
                "representation_coverage",
                f"representation type(s) never used anywhere in the content pack: "
                f"{sorted(m.value for m in missing)}",
            )
        ]
    return []


# --- worked examples ------------------------------------------------------------


def _check_worked_examples(pack: ContentPack) -> list[ContentValidationError]:
    errors: list[ContentValidationError] = []
    known_skills = {s.code for s in pack.skills}
    known_misconceptions = {m.code for m in pack.misconceptions}
    known_item_ids = {i.item_id for i in pack.diagnostic_items} | {
        i.item_id for i in pack.practice_items
    }

    for stem, example in pack.worked_examples.items():
        if example.skill.code not in known_skills:
            errors.append(
                _err(
                    "worked_example_validation",
                    f"worked example {stem}: skill {example.skill.code!r} is not in skills.json",
                )
            )
        if example.misconception.code not in known_misconceptions:
            errors.append(
                _err(
                    "worked_example_validation",
                    f"worked example {stem}: misconception "
                    f"{example.misconception.code!r} is not in misconceptions.json",
                )
            )
        for item_id in example.verification.unaided_items:
            if item_id not in known_item_ids:
                errors.append(
                    _err(
                        "worked_example_validation",
                        f"worked example {stem}: verification item {item_id!r} is not in the "
                        "authored item bank",
                    )
                )
        outcome = example.mastery_outcome
        if outcome.p_known_after <= outcome.p_known_before:
            errors.append(
                _err(
                    "worked_example_validation",
                    f"worked example {stem}: mastery_outcome.p_known_after "
                    f"({outcome.p_known_after}) must exceed p_known_before "
                    f"({outcome.p_known_before}) — this is the resolution story the record "
                    "narrates",
                )
            )

    for m in pack.misconceptions:
        if m.code not in pack.worked_examples:
            errors.append(
                _err(
                    "worked_example_validation",
                    f"misconception {m.code} has no corresponding worked example file",
                )
            )

    return errors


# --- top-level report ------------------------------------------------------------


@dataclass(frozen=True)
class ValidationReport:
    """Every rule's findings plus the counts the content manifest reports."""

    errors: list[ContentValidationError]
    misconception_count: int
    sprout_script_count: int
    intervention_count: int
    diagnostic_item_count: int
    practice_item_count: int
    transfer_item_count: int
    worked_example_count: int
    representation_counts: dict[str, int] = field(default_factory=dict)
    reading_level_status: str = READING_LEVEL_STATUS_PENDING

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def errors_by_rule(self) -> dict[str, list[str]]:
        grouped: dict[str, list[str]] = {}
        for e in self.errors:
            grouped.setdefault(e.rule, []).append(e.message)
        return grouped


def _sample_reading_level_texts(pack: ContentPack) -> list[str]:
    texts = [s.utterance for s in pack.sprout_scripts]
    texts += [i.stem for i in pack.diagnostic_items]
    texts += [i.script for i in pack.interventions]
    texts += [i.stem for i in pack.practice_items]
    return texts


def validate_content_pack(
    pack: ContentPack, *, reading_level_port: ReadingLevelPort | None = None
) -> ValidationReport:
    """Run every deterministic P3 rule and return one combined report.

    ``reading_level_port`` defaults to :class:`~protege.authoring.p2_adapter.NullReadingLevelPort`
    — reading level is P2's responsibility (see module docstring there) and
    is reported as not-evaluated rather than skipped silently.
    """
    port = reading_level_port or NullReadingLevelPort()

    errors: list[ContentValidationError] = []
    errors += _check_id_uniqueness(pack)
    errors += _check_misconception_code_validity(pack)
    errors += _check_distractor_mapping(pack)
    errors += _check_complement_likelihood(pack)
    errors += _check_prerequisite_graph(pack)
    errors += _check_answer_leakage(pack)
    errors += _check_sprout_constraints(pack)
    errors += _check_intervention_linkage(pack)
    errors += _check_transfer_items(pack)
    errors += _check_required_counts(pack)
    errors += _check_representation_coverage(pack)
    errors += _check_worked_examples(pack)

    reading_level_status = READING_LEVEL_STATUS_PENDING
    if not isinstance(port, NullReadingLevelPort):
        results = [port.check(text, 3.5) for text in _sample_reading_level_texts(pack)]
        evaluated = [r for r in results if r is not None]
        if evaluated:
            reading_level_status = "pass" if all(evaluated) else "fail"
            if not all(evaluated):
                errors.append(
                    _err(
                        "reading_level",
                        "one or more content strings exceed the P2 grade-level gate",
                    )
                )

    representation_counts = {
        rep.value: count for rep, count in _representation_counts(pack).items()
    }

    return ValidationReport(
        errors=errors,
        misconception_count=len(pack.misconceptions),
        sprout_script_count=len(pack.sprout_scripts),
        intervention_count=len(pack.interventions),
        diagnostic_item_count=len(pack.diagnostic_items),
        practice_item_count=len(pack.practice_items),
        transfer_item_count=len(pack.transfer_items),
        worked_example_count=len(pack.worked_examples),
        representation_counts=representation_counts,
        reading_level_status=reading_level_status,
    )
