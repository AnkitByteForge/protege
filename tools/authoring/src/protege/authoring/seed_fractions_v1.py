"""The authored v1 fractions content pack (roadmap P3).

This module is the human-authored source of ``content/math/fractions/v1/``.
Every stem, cognitive-origin explanation, Sprout line, and intervention
script below was written by hand for this submission; nothing here calls a
model. Regenerating the content files from this module is deterministic and
idempotent (``python -m protege.authoring.seed_fractions_v1``) — the JSON
files it writes are the reviewable artifact; this module is the reviewable
source of that artifact, in one place instead of scattered across eight
hand-edited files.

Eight misconceptions, one per skill:

- M001 (S001_identify_fraction)         — a fraction read as two whole numbers
- M002 (S002_equal_parts)               — unequal partitions still called a fraction
- M003 (S004_compare_unit_fractions)    — larger denominator means larger fraction
                                           (ARCHITECTURE.md §38's own worked example;
                                           reproduced here with its literal IDs, then
                                           extended to the full P3 item counts)
- M004 (S003_equivalent_fractions)      — scaling numerator+denominator "changes" the value
- M005 (S006_compare_unlike_fractions)  — compares denominators only, ignores the numerator
- M006 (S007_improper_fractions)        — a fraction can never exceed one whole
- M007 (S008_fraction_of_a_set)         — divides a set by the numerator, not the denominator
- M008 (S005_add_fractions)             — "add straight across" (adds denominators too)

M005's worked example is deliberately the one with ``transfer_verified=False``
(ARCHITECTURE.md §1.3 correction 3): local mastery is real, the set-model
transfer probe failed, and the claim says so without erasing the mastery.

Each misconception also carries ``distractor_likelihood_if_not_misconception``
— the independently-authored ``P(d | not M_k)`` complement required by
docs/DECISIONS.md D13 (the independent-Bernoulli Bayes update; locked on
``feature/p2-learning``, merged via ``feature/contracts-misconception-complement``).
Per D13 this is a genuinely separate authored judgment, not a transform of
``distractor_likelihood``: it is never ``1 - distractor_likelihood`` per key
(that isn't even guaranteed to be a valid distribution), never a copy of
``distractor_likelihood``, and never a reuse of its ``"other"`` residual.
Each complement was reasoned through per-misconception — see the inline
comment above each one for the specific rationale (e.g., which listed wrong
behavior is a plausible non-diagnostic slip vs. one that is close to
diagnostic of holding the misconception) — and keeps the same behavior keys
as ``distractor_likelihood`` so both tables describe the same distractor
taxonomy under opposite conditioning.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONTENT_VERSION = "v1"

# --- skills -------------------------------------------------------------------

SKILLS: list[dict[str, Any]] = [
    {
        "code": "S001_identify_fraction",
        "title": "Identify a fraction as a part of a whole",
        "grade_band": "1-2",
        "prerequisites": [],
        "standard": "CCSS.1.G.A.3",
    },
    {
        "code": "S002_equal_parts",
        "title": "Partition shapes into equal parts",
        "grade_band": "1-2",
        "prerequisites": ["S001_identify_fraction"],
        "standard": "CCSS.2.G.A.3",
    },
    {
        "code": "S003_equivalent_fractions",
        "title": "Recognize equivalent fractions",
        "grade_band": "3-4",
        "prerequisites": ["S002_equal_parts"],
        "standard": "CCSS.3.NF.A.3",
    },
    {
        "code": "S004_compare_unit_fractions",
        "title": "Compare unit fractions",
        "grade_band": "3-4",
        "prerequisites": ["S001_identify_fraction", "S002_equal_parts"],
        "standard": "CCSS.3.NF.A.3d",
    },
    {
        "code": "S005_add_fractions",
        "title": "Add fractions with like denominators",
        "grade_band": "4-5",
        "prerequisites": ["S003_equivalent_fractions", "S004_compare_unit_fractions"],
        "standard": "CCSS.4.NF.B.3a",
    },
    {
        "code": "S006_compare_unlike_fractions",
        "title": "Compare fractions with unlike numerators and denominators",
        "grade_band": "4-5",
        "prerequisites": ["S004_compare_unit_fractions", "S003_equivalent_fractions"],
        "standard": "CCSS.4.NF.A.2",
    },
    {
        "code": "S007_improper_fractions",
        "title": "Represent fractions greater than one whole",
        "grade_band": "4-5",
        "prerequisites": ["S001_identify_fraction"],
        "standard": "CCSS.4.NF.B.3c",
    },
    {
        "code": "S008_fraction_of_a_set",
        "title": "Find a fraction of a set of objects",
        "grade_band": "3-4",
        "prerequisites": ["S001_identify_fraction", "S002_equal_parts"],
        "standard": "CCSS.3.NF.A.1",
    },
]

# --- misconceptions, each carrying its own sub-content -------------------------
# Every misconception dict carries: code, title, cognitive_origin, skill_code,
# distractor_likelihood, prevalence_prior, citation, sprout_forbidden,
# sprout_scripts (6), interventions (3), diagnostic_items (4),
# transfer_items (2, pool="misconception"), practice_items (5, for its skill).

MISCONCEPTIONS: list[dict[str, Any]] = [
    # ---------------------------------------------------------------- M001 --
    {
        "code": "M001",
        "title": "A fraction is two separate whole numbers, not one quantity",
        "skill_code": "S001_identify_fraction",
        "cognitive_origin": (
            "Whole-number-count bias: before a part-whole scheme develops, children "
            "read '3/4' as two independent counts read top-to-bottom ('a three and a "
            "four') rather than a single quantity describing parts out of a whole."
        ),
        "prevalence_prior": 0.35,
        "distractor_likelihood": {
            "reads_as_two_numbers": 0.68,
            "picks_larger_of_the_two_numbers": 0.17,
            "other": 0.15,
        },
        # P(d | not M001) — independently authored, per D13 (docs/DECISIONS.md,
        # locked on feature/p2-learning). Rationale: a child who has already
        # built a part-whole scheme rarely regresses to reading a fraction as
        # two counts; that reading is a near-diagnostic tell of M001, not a
        # generic slip. Most non-M001 errors are unrelated to this behavior
        # entirely (wrong arithmetic, misread stem, guessing), hence a high
        # "other" residual and low mass on both listed behaviors.
        "distractor_likelihood_if_not_misconception": {
            "reads_as_two_numbers": 0.07,
            "picks_larger_of_the_two_numbers": 0.04,
            "other": 0.89,
        },
        "citation": "Early rational-number concept development literature on the part-whole construct (Behr, Post & Lesh).",
        "sprout_forbidden": [
            "numerator",
            "denominator",
            "stating the fraction names one quantity before resolution",
        ],
        "sprout_scripts": [
            ("Three-fourths? That's easy, it's a three and a four! Two numbers.", "confident"),
            (
                "Wait, is this fraction one thing, or is it really two things, like a 3 and a 4?",
                "curious",
            ),
            ("I don't get how two numbers stuck together make just one amount.", "confused"),
            ("Maybe this fraction means 3 things AND 4 things? I'm not totally sure.", "uncertain"),
            ("I'll just say the top number and the bottom number separately, right?", "confident"),
            ("So which one matters more, the top three or the bottom four?", "curious"),
        ],
        "interventions": [
            (
                "VISUALIZATION",
                "single_shaded_shape",
                "Let's shade ONE shape and count: how many parts did we shade out of how many total? That's our one fraction.",
                0.74,
            ),
            (
                "ANALOGY",
                "team_score_analogy",
                "It's like a score for one team, not two teams — '3 out of 4' is one idea, not a pair of numbers.",
                0.68,
            ),
            (
                "WORKED_EXAMPLE",
                "point_to_the_whole",
                "Watch me point: this whole circle is cut into 4. I shade 3. I say '3 out of 4' as ONE amount.",
                0.71,
            ),
        ],
        "diagnostic_items": [
            (
                "i_1101",
                "This rectangle is cut into 4 equal parts and 3 are shaded. What fraction of the rectangle is shaded?",
                "AREA_MODEL",
                "3/4",
                [("3 and 4, two separate numbers", 0.68), ("4 and 3, two separate numbers", 0.17)],
                1100,
            ),
            (
                "i_1102",
                "A pizza is cut into 5 equal slices and 2 are gone. What fraction of the pizza is left?",
                "AREA_MODEL",
                "3/5",
                [("2 and 5, two separate numbers", 0.68), ("5 and 2, two separate numbers", 0.17)],
                1120,
            ),
            (
                "i_1103",
                "What does the fraction 3/4 mean?",
                "SYMBOLIC",
                "3 equal parts out of 4 total parts",
                [
                    ("A 3 and a 4 — two separate numbers", 0.68),
                    ("The number 3 divided into 4 pieces of its own", 0.17),
                ],
                1140,
            ),
            (
                "i_1104",
                "Which best describes 2/6?",
                "SYMBOLIC",
                "2 out of 6 equal parts, one quantity",
                [("Two numbers, a 2 and a 6", 0.68), ("A 6 split into 2 groups", 0.17)],
                1160,
            ),
        ],
        "transfer_items": [
            (
                "i_1191",
                "Place the point that shows 3/4 on a number line from 0 to 1.",
                "NUMBER_LINE",
                "3/4",
                1300,
            ),
            (
                "i_1192",
                "A basket has 8 apples and 3 are red. What fraction of the basket is red?",
                "SET_MODEL",
                "3/8",
                1320,
            ),
        ],
        "practice_items": [
            (
                "i_2001",
                "A strip is cut into 5 equal parts and 4 are shaded. What fraction is shaded?",
                "AREA_MODEL",
                "4/5",
                [("4 and 5, two separate numbers", 0.68), ("5 and 4, two separate numbers", 0.17)],
                1080,
            ),
            (
                "i_2002",
                "What does 1/3 mean?",
                "SYMBOLIC",
                "1 out of 3 equal parts, one quantity",
                [("A 1 and a 3, two separate numbers", 0.68), ("The number 1 split into 3", 0.17)],
                1090,
            ),
            (
                "i_2003",
                "A garden bed is split into 6 equal plots and 5 are planted. What fraction is planted?",
                "AREA_MODEL",
                "5/6",
                [("5 and 6, two separate numbers", 0.68), ("6 and 5, two separate numbers", 0.17)],
                1100,
            ),
            (
                "i_2004",
                "What does 2/3 mean?",
                "SYMBOLIC",
                "2 out of 3 equal parts, one quantity",
                [("A 2 and a 3, two separate numbers", 0.68), ("The number 2 split into 3", 0.17)],
                1110,
            ),
            (
                "i_2005",
                "A ribbon is cut into 4 equal parts and 1 is used. What fraction is used?",
                "AREA_MODEL",
                "1/4",
                [("1 and 4, two separate numbers", 0.68), ("4 and 1, two separate numbers", 0.17)],
                1120,
            ),
        ],
        "worked_example": {
            "diagnostic_item_id": "i_1101",
            "explanation": "it's 3/4 because I shaded 3 parts and there are 4 parts total, it's one amount not two numbers",
            "asr_confidence": 0.86,
            "manipulative_trace": [
                {"t": 1.6, "action": "drag", "target": "rect_shaded_3"},
                {"t": 3.4, "action": "align", "targets": ["rect_shaded_3", "rect_whole_4"]},
            ],
            "diagnosis_confidence": 0.87,
            "diagnosis_evidence_span": "one amount not two numbers",
            "understanding_signals": ["partitioning_language"],
            "intervention_id": "INT_M001_A",
            "verification_item_indices": [0, 1, 3],
            "transfer_item_index": 0,
            "transfer_result": True,
            "p_known_before": 0.26,
            "p_known_after": 0.88,
            "misconception_after": 0.06,
            "transfer_verified": True,
            "claim": "Ava can identify a fraction as one quantity, not two separate numbers",
            "caveats": [
                "transfer confirmed on a number line only; set-model transfer not yet attempted"
            ],
            "next_review": "2026-09-19",
        },
    },
    # ---------------------------------------------------------------- M002 --
    {
        "code": "M002",
        "title": "Unequal partitions still count as a valid fraction",
        "skill_code": "S002_equal_parts",
        "cognitive_origin": (
            "Children over-attend to the COUNT of pieces and under-attend to their "
            "SIZE, so any shape divided into N regions is labeled '1/N' regardless of "
            "whether the regions are equal — a failure to encode equal partitioning as "
            "a defining feature of a fraction."
        ),
        "prevalence_prior": 0.38,
        "distractor_likelihood": {
            "labels_by_piece_count_only": 0.70,
            "says_uneven_pieces_show_no_fraction": 0.15,
            "other": 0.15,
        },
        # P(d | not M002). Rationale: a child who does hold the equal-parts
        # requirement can still misjudge an unequal partition by eye under
        # time pressure (a performance slip, not a conceptual gap), so
        # "labels_by_piece_count_only" keeps modest but non-trivial mass.
        # The overcorrection ("no fraction at all") is rarer without the
        # underlying miscount, since it requires actively noticing the
        # unequal split and still answering wrong.
        "distractor_likelihood_if_not_misconception": {
            "labels_by_piece_count_only": 0.12,
            "says_uneven_pieces_show_no_fraction": 0.05,
            "other": 0.83,
        },
        "citation": "Research on children's partitioning strategies and the equal-parts requirement in early fraction instruction.",
        "sprout_forbidden": ["equal parts", "unequal pieces don't count"],
        "sprout_scripts": [
            ("I cut it into 4 pieces, so each piece is 1/4 — the sizes don't matter!", "confident"),
            (
                "Does it matter if the pieces are different sizes, as long as there are 4?",
                "curious",
            ),
            (
                "These pieces look really different, but I still called it 1/4. Is that wrong?",
                "confused",
            ),
            ("Maybe the pieces need to match somehow? I'm not sure.", "uncertain"),
            ("Four pieces means fourths, no matter how I cut it, right?", "confident"),
            ("So counting pieces isn't enough — what else do I check?", "curious"),
        ],
        "interventions": [
            (
                "VISUALIZATION",
                "overlay_unequal_pieces",
                "Let's cut out the pieces and stack them on top of each other — see how they're not the same size?",
                0.72,
            ),
            (
                "HINT",
                "same_size_check",
                "Before naming the fraction, ask: are ALL the pieces exactly the same size? If not, it's not a fraction of equal parts yet.",
                0.66,
            ),
            (
                "WORKED_EXAMPLE",
                "fold_to_check_equal",
                "Watch me fold the paper in half twice to make four TRULY equal parts — now every piece matches.",
                0.75,
            ),
        ],
        "diagnostic_items": [
            (
                "i_1201",
                "A square is cut into 4 parts of clearly different sizes and 1 part is shaded. Is the shaded part 1/4 of the square?",
                "AREA_MODEL",
                "No — the parts must be equal size for 1/4 to be correct",
                [
                    ("Yes, 1/4, because 1 out of 4 parts is shaded", 0.70),
                    ("No, uneven pieces can never show a fraction at all", 0.15),
                ],
                1080,
            ),
            (
                "i_1202",
                "A rectangle is split into 3 unequal strips and 2 are shaded. What fraction is shaded?",
                "AREA_MODEL",
                "Cannot say 2/3 — the strips are not equal size",
                [("2/3", 0.70), ("This picture shows no fraction at all", 0.15)],
                1100,
            ),
            (
                "i_1203",
                "6 counters are split into two unequal groups (4 and 2), and one group is circled. Is the circled group 1/2 of the counters?",
                "SET_MODEL",
                "No — the groups must be equal size for 1/2 to apply",
                [
                    ("Yes, 1/2, because one of the two groups is circled", 0.70),
                    ("No, unequal groups can't be described with any fraction", 0.15),
                ],
                1120,
            ),
            (
                "i_1204",
                "A pie is cut into 4 pieces of clearly different sizes and 1 piece is shaded. What fraction is shaded?",
                "SET_MODEL",
                "Cannot say 1/4 — the pieces must be equal size",
                [("1/4", 0.70), ("It shows no fraction since the slices differ", 0.15)],
                1140,
            ),
        ],
        "transfer_items": [
            (
                "i_1291",
                "A number line from 0 to 1 is marked with 4 unevenly spaced ticks. Can the second tick be called 1/4?",
                "NUMBER_LINE",
                "No — the marks must be equally spaced for 1/4 to apply",
                1300,
            ),
            (
                "i_1292",
                "True or false: any shape split into 3 pieces automatically shows thirds.",
                "SYMBOLIC",
                "False — the 3 pieces must be equal size",
                1310,
            ),
        ],
        "practice_items": [
            (
                "i_2006",
                "A circle is cut into 3 clearly unequal pieces and 1 is shaded. Is the shaded piece 1/3?",
                "AREA_MODEL",
                "No — the pieces must be equal size",
                [("Yes, 1/3", 0.70), ("It shows no fraction since the slices differ", 0.15)],
                1090,
            ),
            (
                "i_2007",
                "A rectangle is split into 5 equal strips and 2 are shaded. What fraction is shaded?",
                "AREA_MODEL",
                "2/5",
                [("Cannot tell without checking equal size", 0.70), ("It shows no fraction", 0.15)],
                1100,
            ),
            (
                "i_2008",
                "8 counters split into two unequal groups (5 and 3); one group is circled. Is the circled group of 3 equal to 3/8 of the total?",
                "SET_MODEL",
                "Yes — 3/8 refers to the whole set of 8, and 3 is 3 of those 8 individual counters",
                [
                    ("No, because the two groups aren't equal size", 0.70),
                    ("It shows no fraction", 0.15),
                ],
                1110,
            ),
            (
                "i_2009",
                "A square is cut into 4 equal parts and 3 are shaded. What fraction is shaded?",
                "AREA_MODEL",
                "3/4",
                [("Cannot tell without checking equal size", 0.70), ("It shows no fraction", 0.15)],
                1120,
            ),
            (
                "i_2010",
                "A pie is cut into 6 clearly unequal pieces and 2 are shaded. Is the shaded amount 2/6 of the pie?",
                "AREA_MODEL",
                "No — the pieces must be equal size",
                [("Yes, 2/6", 0.70), ("It shows no fraction since the slices differ", 0.15)],
                1130,
            ),
        ],
        "worked_example": {
            "diagnostic_item_id": "i_1201",
            "explanation": "no, because the parts have to be the same size to call it 1/4, these pieces are all different sizes",
            "asr_confidence": 0.84,
            "manipulative_trace": [
                {"t": 2.1, "action": "drag", "target": "piece_1"},
                {
                    "t": 4.5,
                    "action": "align",
                    "targets": ["piece_1", "piece_2", "piece_3", "piece_4"],
                },
            ],
            "diagnosis_confidence": 0.85,
            "diagnosis_evidence_span": "the parts have to be the same size",
            "understanding_signals": ["partitioning_language"],
            "intervention_id": "INT_M002_C",
            "verification_item_indices": [1, 3, 4],
            "transfer_item_index": 0,
            "transfer_result": True,
            "p_known_before": 0.30,
            "p_known_after": 0.89,
            "misconception_after": 0.05,
            "transfer_verified": True,
            "claim": "Ava can judge whether a partition shows equal parts before naming a fraction",
            "caveats": [
                "transfer confirmed on a number line only; set-model transfer not yet attempted"
            ],
            "next_review": "2026-09-19",
        },
    },
    # ---------------------------------------------------------------- M003 --
    # ARCHITECTURE.md §38's own worked example, reproduced with its literal
    # IDs (S004, M003, i_0132, i_0148/i_0155/i_0161, i_0201, INT_M003_A,
    # SS_M003_01..03) and extended to the full P3 counts (4 diagnostic items,
    # 2 transfer items, 6 sprout scripts, 3 interventions). The §38 second
    # distractor ("equal" -> "M011") is remapped to M003's own authored
    # "says_equal" sub-behavior so the record is self-consistent within this
    # 8-misconception library rather than referencing a misconception this
    # package does not author.
    {
        "code": "M003",
        "title": "Larger denominator means larger fraction",
        "skill_code": "S004_compare_unit_fractions",
        "cognitive_origin": (
            "Whole-number bias — the child transfers whole-number ordering to the "
            "denominator, since 8 > 4."
        ),
        "prevalence_prior": 0.42,
        "distractor_likelihood": {"picks_1_8": 0.82, "says_equal": 0.06, "other": 0.12},
        # P(d | not M003), authored independently per D13 — NOT derived from
        # distractor_likelihood and NOT a reuse of its "other" bucket.
        # Rationale: a child without the whole-number-bias belief rarely
        # picks the smaller-denominator fraction as bigger (that specific
        # wrong pick is close to diagnostic of the bias itself), but "says
        # equal" is a distinct, independent slip — over-generalizing visual
        # similarity between the two shaded regions — that can occur even
        # without whole-number bias, so it gets somewhat more mass than the
        # bias-specific pick.
        #
        # NOTE (flagged in adversarial review): this makes
        # P(says_equal | not M003) = 0.10 exceed P(says_equal | M003) = 0.06.
        # That is intentional, not a transcription error: a child confidently
        # holding the whole-number-bias belief tends to commit to a definite
        # (wrong) comparison rather than hedge with "equal", so "equal" is,
        # if anything, a mild counter-signal for M003 — under the D13 Bayes
        # update, observing it should nudge the M003 posterior down slightly
        # rather than up, which is a legitimate and intended outcome, not a
        # bug in the authored table.
        "distractor_likelihood_if_not_misconception": {
            "picks_1_8": 0.08,
            "says_equal": 0.10,
            "other": 0.82,
        },
        "citation": "Whole-number bias literature; Siegler et al. on fraction magnitude.",
        "sprout_forbidden": ["stating 1/4 > 1/8 before resolution", "numerator", "denominator"],
        "sprout_scripts": [
            ("I think 1/8 is bigger! Eight is way more than four.", "confident"),
            ("Wait, so 1/8 wins because 8 is the bigger number, right?", "curious"),
            ("Hmm, but 8 is more than 4. Doesn't more mean bigger?", "confused"),
            ("Um, maybe 1/8 is bigger? Eight feels like a bigger number to me.", "uncertain"),
            ("Eight pieces has to beat four pieces, so 1/8 wins, right?", "confident"),
            ("If I had 8 friends instead of 4, wouldn't my share be the bigger one?", "curious"),
        ],
        "interventions": [
            (
                "VISUALIZATION",
                "same_whole_partition_contrast",
                "Let's cut the SAME pizza two ways and lay them on top of each other.",
                0.78,
            ),
            (
                "ANALOGY",
                "same_size_pizza_more_friends",
                "Imagine the SAME pizza shared with more friends — more friends means each slice gets smaller, not bigger.",
                0.71,
            ),
            (
                "WORKED_EXAMPLE",
                "stack_the_bars",
                "Watch me stack a 1/4 bar and a 1/8 bar on top of each other — see which one is taller.",
                0.75,
            ),
        ],
        "diagnostic_items": [
            (
                "i_0132",
                "Which is more pizza: 1/4 or 1/8?",
                "AREA_MODEL",
                "1/4",
                [("1/8", 0.82), ("equal", 0.06)],
                1180,
            ),
            (
                "i_0133",
                "Which is more cake: 1/3 or 1/6?",
                "AREA_MODEL",
                "1/3",
                [("1/6", 0.82), ("equal", 0.06)],
                1150,
            ),
            (
                "i_0134",
                "Without drawing a picture, which is larger: 1/5 or 1/10?",
                "SYMBOLIC",
                "1/5",
                [("1/10", 0.82), ("equal", 0.06)],
                1200,
            ),
            (
                "i_0135",
                "Order from smallest to largest: 1/2, 1/6, 1/4.",
                "SYMBOLIC",
                "1/6, 1/4, 1/2",
                [("1/2, 1/4, 1/6", 0.82), ("1/4, 1/6, 1/2", 0.06)],
                1220,
            ),
        ],
        "transfer_items": [
            (
                "i_0201",
                "Place 1/4 and 1/8 on the same number line from 0 to 1. Which point is farther right?",
                "NUMBER_LINE",
                "1/4",
                1300,
            ),
            (
                "i_0202",
                "Two identical trays of 8 cookies each. Tray A gives away 1/4 of its cookies; Tray B gives away 1/8 of its cookies. Which tray gave away more cookies?",
                "SET_MODEL",
                "Tray A (1/4)",
                1320,
            ),
        ],
        # The first three practice items reuse §38's literal verification ids
        # so this worked example's `verification.unaided_items` resolve
        # exactly as the architecture document specifies.
        "practice_items": [
            (
                "i_0148",
                "Which is more juice: 1/3 of a jug or 1/9 of a jug (same size jug)?",
                "AREA_MODEL",
                "1/3",
                [("1/9", 0.82), ("equal", 0.06)],
                1160,
            ),
            (
                "i_0155",
                "A ribbon is cut into 1/4 pieces or 1/7 pieces (same length ribbon). Which piece is longer?",
                "AREA_MODEL",
                "1/4 piece",
                [("1/7 piece", 0.82), ("equal", 0.06)],
                1170,
            ),
            (
                "i_0161",
                "Which is smaller: 1/12 or 1/6 of the same garden bed?",
                "AREA_MODEL",
                "1/12",
                [("1/6", 0.82), ("equal", 0.06)],
                1190,
            ),
            (
                "i_2011",
                "Which is more: 1/2 of a candy bar or 1/5 of the same candy bar?",
                "AREA_MODEL",
                "1/2",
                [("1/5", 0.82), ("equal", 0.06)],
                1150,
            ),
            (
                "i_2012",
                "A rope is split into 1/8 lengths or 1/3 lengths (same rope). Which length is longer?",
                "AREA_MODEL",
                "1/3 length",
                [("1/8 length", 0.82), ("equal", 0.06)],
                1160,
            ),
        ],
        "worked_example": {
            "diagnostic_item_id": "i_0132",
            "explanation": "no because the bottom is how many pieces you cut it so more pieces are littler",
            "asr_confidence": 0.88,
            "manipulative_trace": [
                {"t": 2.1, "action": "drag", "target": "bar_1_4"},
                {"t": 4.8, "action": "align", "targets": ["bar_1_4", "bar_1_8"]},
            ],
            "diagnosis_confidence": 0.91,
            "diagnosis_evidence_span": "more pieces are littler",
            "understanding_signals": ["inverse_denominator_relationship", "partitioning_language"],
            "intervention_id": "INT_M003_A",
            "verification_item_indices": [0, 1, 2],
            "transfer_item_index": 0,
            "transfer_result": True,
            "p_known_before": 0.31,
            "p_known_after": 0.91,
            "misconception_after": 0.04,
            "transfer_verified": True,
            "claim": "Ava can compare unit fractions",
            "caveats": ["transfer confirmed on number line only"],
            "next_review": "2026-09-19",
        },
    },
    # ---------------------------------------------------------------- M004 --
    {
        "code": "M004",
        "title": "Scaling numerator and denominator together changes a fraction's value",
        "skill_code": "S003_equivalent_fractions",
        "cognitive_origin": (
            "Children treat numerator and denominator as independent whole-number "
            "counts, so scaling both by the same factor looks like making a "
            "different, bigger fraction rather than preserving the same part-whole "
            "ratio — a failure to see multiplicative equivalence."
        ),
        "prevalence_prior": 0.33,
        "distractor_likelihood": {
            "says_bigger_numbers_means_different_value": 0.66,
            "says_different_pictures_mean_different_fractions": 0.19,
            "other": 0.15,
        },
        # P(d | not M004). Rationale: "different pictures look different" is
        # a visual slip available to any child regardless of whether they
        # hold the componential (numbers-as-independent-counts) belief — it
        # only requires not looking closely enough to confirm the shaded
        # amounts match. The numeric tell ("bigger numbers means bigger
        # value") is the more diagnostic behavior and is rarer without the
        # belief driving it, so it gets less of the (still small) non-"other"
        # mass than the visual slip does.
        "distractor_likelihood_if_not_misconception": {
            "says_bigger_numbers_means_different_value": 0.06,
            "says_different_pictures_mean_different_fractions": 0.14,
            "other": 0.80,
        },
        "citation": "Literature on componential vs. proportional reasoning in fraction equivalence.",
        "sprout_forbidden": ["equivalent", "stating 1/2 equals 2/4 before resolution"],
        "sprout_scripts": [
            (
                "1/2 and 2/4 can't be the same — 2/4 has bigger numbers, so it must be more!",
                "confident",
            ),
            ("Wait, how can two different-looking fractions be the exact same amount?", "curious"),
            (
                "If the numbers are different, doesn't that mean the fractions are different too?",
                "confused",
            ),
            ("Maybe they're close but not really equal? I'm not sure.", "uncertain"),
            ("Bigger top and bottom numbers always means a bigger fraction, right?", "confident"),
            ("So if I make the numbers bigger, does the fraction always grow?", "curious"),
        ],
        "interventions": [
            (
                "VISUALIZATION",
                "stacked_equal_bars",
                "Let's stack a bar split in halves on top of one split in fourths — see how the shaded amount lines up exactly.",
                0.76,
            ),
            (
                "ANALOGY",
                "same_pizza_cut_differently",
                "It's the same pizza, just sliced differently — cutting it more ways doesn't change how much you have.",
                0.70,
            ),
            (
                "WORKED_EXAMPLE",
                "multiply_top_and_bottom",
                "Watch: multiply the top AND the bottom by the same number — the amount never changes, only how finely it's cut.",
                0.73,
            ),
        ],
        "diagnostic_items": [
            (
                "i_1401",
                "Two identical circles are shaded the same amount, but one is cut into 2 parts (1 shaded) and the other into 4 parts (2 shaded). Are 1/2 and 2/4 the same amount?",
                "AREA_MODEL",
                "Yes — they are equivalent, the same amount",
                [
                    ("No, 2/4 is bigger because the numbers are bigger", 0.66),
                    ("No, they look different so they can't be equal", 0.19),
                ],
                1120,
            ),
            (
                "i_1402",
                "A bar shows 1/3 shaded; an identical bar shows 2/6 shaded the same way. Are these equal?",
                "AREA_MODEL",
                "Yes — 1/3 and 2/6 are equivalent",
                [
                    ("No, 2/6 is bigger because the numbers are bigger", 0.66),
                    ("No, they look different so they can't be equal", 0.19),
                ],
                1140,
            ),
            (
                "i_1403",
                "Is 3/4 equal to 6/8?",
                "SYMBOLIC",
                "Yes, equivalent",
                [("No, 6/8 is bigger", 0.66), ("No, different numbers can't be equal", 0.19)],
                1160,
            ),
            (
                "i_1404",
                "Is 1/5 equal to 2/10?",
                "SYMBOLIC",
                "Yes, equivalent",
                [("No, 2/10 is bigger", 0.66), ("No, different numbers can't be equal", 0.19)],
                1180,
            ),
        ],
        "transfer_items": [
            (
                "i_1491",
                "Do 1/2 and 2/4 land on the exact same point on a number line from 0 to 1?",
                "NUMBER_LINE",
                "Yes, the same point",
                1300,
            ),
            (
                "i_1492",
                "A group of 8 counters: is 'half the group' the same amount as '4 out of 8 counters'?",
                "SET_MODEL",
                "Yes, the same amount",
                1320,
            ),
        ],
        "practice_items": [
            (
                "i_2013",
                "Is 2/3 equal to 4/6?",
                "SYMBOLIC",
                "Yes",
                [
                    ("No, bigger numbers mean bigger value", 0.66),
                    ("No, different-looking fractions can't be equal", 0.19),
                ],
                1110,
            ),
            (
                "i_2014",
                "Is 1/4 equal to 3/12?",
                "SYMBOLIC",
                "Yes",
                [
                    ("No, bigger numbers mean bigger value", 0.66),
                    ("No, different-looking fractions can't be equal", 0.19),
                ],
                1120,
            ),
            (
                "i_2015",
                "Is 2/6 equal to 1/3?",
                "SYMBOLIC",
                "Yes",
                [
                    ("No, bigger numbers mean bigger value", 0.66),
                    ("No, different-looking fractions can't be equal", 0.19),
                ],
                1130,
            ),
            (
                "i_2016",
                "Is 5/10 equal to 1/2?",
                "SYMBOLIC",
                "Yes",
                [
                    ("No, bigger numbers mean bigger value", 0.66),
                    ("No, different-looking fractions can't be equal", 0.19),
                ],
                1140,
            ),
            (
                "i_2017",
                "Is 2/8 equal to 1/4?",
                "SYMBOLIC",
                "Yes",
                [
                    ("No, bigger numbers mean bigger value", 0.66),
                    ("No, different-looking fractions can't be equal", 0.19),
                ],
                1150,
            ),
        ],
        "worked_example": {
            "diagnostic_item_id": "i_1401",
            "explanation": "yes they're the same because you just cut the second one into smaller pieces but it's still the same amount shaded",
            "asr_confidence": 0.85,
            "manipulative_trace": [
                {"t": 1.8, "action": "drag", "target": "bar_1_2"},
                {"t": 3.6, "action": "align", "targets": ["bar_1_2", "bar_2_4"]},
            ],
            "diagnosis_confidence": 0.88,
            "diagnosis_evidence_span": "still the same amount shaded",
            "understanding_signals": ["partitioning_language"],
            "intervention_id": "INT_M004_A",
            "verification_item_indices": [0, 1, 3],
            "transfer_item_index": 0,
            "transfer_result": True,
            "p_known_before": 0.28,
            "p_known_after": 0.89,
            "misconception_after": 0.05,
            "transfer_verified": True,
            "claim": "Ava can recognize equivalent fractions",
            "caveats": [
                "transfer confirmed on a number line only; set-model transfer not yet attempted"
            ],
            "next_review": "2026-09-20",
        },
    },
    # ---------------------------------------------------------------- M005 --
    {
        "code": "M005",
        "title": "Bigger denominator always means a smaller fraction, even across different numerators",
        "skill_code": "S006_compare_unlike_fractions",
        "cognitive_origin": (
            "An overgeneralization of the (correct, unit-fraction-only) rule 'more "
            "pieces means a smaller piece' to fractions whose numerators also "
            "differ: the child compares only denominators and ignores the "
            "numerator entirely (e.g., judging 3/8 < 1/4 because 8 > 4)."
        ),
        "prevalence_prior": 0.30,
        "distractor_likelihood": {
            "compares_denominators_only": 0.68,
            "compares_numerators_only": 0.17,
            "other": 0.15,
        },
        # P(d | not M005). Rationale: denominator-only comparison is a
        # well-documented fast heuristic that even children who understand
        # unlike-fraction comparison sometimes reach for under time
        # pressure — it is a common performance slip, not purely diagnostic
        # of holding the misconception — so it keeps a comparatively higher
        # complement mass than the equivalent behaviors in the other seven
        # misconceptions. Numerator-only comparison (a different, unrelated
        # bug) gets a smaller independent baseline rate.
        "distractor_likelihood_if_not_misconception": {
            "compares_denominators_only": 0.15,
            "compares_numerators_only": 0.10,
            "other": 0.75,
        },
        "citation": "Fraction-comparison strategy literature on componential (part-by-part) reasoning.",
        "sprout_forbidden": ["numerator", "denominator", "comparing only the bottom numbers"],
        "sprout_scripts": [
            (
                "1/4 has to be the biggest — four is such a small bottom number, so the pieces must be huge!",
                "confident",
            ),
            (
                "Isn't a smaller bottom number always the winner, no matter what's on top?",
                "curious",
            ),
            (
                "I only looked at the bottom numbers. Was I supposed to look at the top too?",
                "confused",
            ),
            ("Maybe the top number matters sometimes? I'm not sure when.", "uncertain"),
            ("Smaller bottom number, bigger fraction — that's the rule, right?", "confident"),
            ("So the top number never changes who wins?", "curious"),
        ],
        "interventions": [
            (
                "VISUALIZATION",
                "shade_both_and_compare",
                "Let's shade 3/8 and 1/4 on same-size rectangles and lay them side by side — see which shaded area is bigger.",
                0.72,
            ),
            (
                "HINT",
                "check_the_top_too",
                "Before deciding, check BOTH numbers: how many pieces total, AND how many pieces you actually have.",
                0.65,
            ),
            (
                "WORKED_EXAMPLE",
                "convert_to_common_denominator",
                "Watch: turn 1/4 into 2/8 so both fractions talk about eighths — now compare 3/8 with 2/8 directly.",
                0.79,
            ),
        ],
        "diagnostic_items": [
            (
                "i_1501",
                "Which is bigger: 5/6 or 1/2?",
                "SYMBOLIC",
                "5/6",
                [("1/2", 0.68), ("equal", 0.17)],
                1200,
            ),
            (
                "i_1502",
                "Which is bigger: 7/9 or 1/3?",
                "SYMBOLIC",
                "7/9",
                [("1/3", 0.68), ("equal", 0.17)],
                1220,
            ),
            (
                "i_1503",
                "On a number line, which point is farther right: 3/8 or 1/4?",
                "NUMBER_LINE",
                "3/8",
                [("1/4", 0.68), ("same point", 0.17)],
                1240,
            ),
            (
                "i_1504",
                "On a number line, which point is farther right: 3/10 or 1/4?",
                "NUMBER_LINE",
                "3/10",
                [("1/4", 0.68), ("same point", 0.17)],
                1260,
            ),
        ],
        "transfer_items": [
            (
                "i_1591",
                "Two identical rectangles: one shows 3/8 shaded, the other shows 1/4 shaded. Which rectangle has more shaded?",
                "AREA_MODEL",
                "The 3/8 rectangle",
                1330,
            ),
            (
                "i_1592",
                "Group A has 8 marbles, 3 are blue. Group B has 8 marbles, 2 are blue. Which group has more blue marbles?",
                "SET_MODEL",
                "Group A (3/8)",
                1350,
            ),
        ],
        "practice_items": [
            (
                "i_2018",
                "Which is bigger: 5/8 or 1/3?",
                "SYMBOLIC",
                "5/8",
                [("1/3", 0.68), ("equal", 0.17)],
                1180,
            ),
            (
                "i_2019",
                "Which is bigger: 7/10 or 1/4?",
                "SYMBOLIC",
                "7/10",
                [("1/4", 0.68), ("equal", 0.17)],
                1190,
            ),
            (
                "i_2020",
                "Which is bigger: 4/9 or 1/5?",
                "SYMBOLIC",
                "4/9",
                [("1/5", 0.68), ("equal", 0.17)],
                1200,
            ),
            (
                "i_2021",
                "Which is bigger: 5/9 or 1/6?",
                "SYMBOLIC",
                "5/9",
                [("1/6", 0.68), ("equal", 0.17)],
                1210,
            ),
            (
                "i_2022",
                "Which is bigger: 7/12 or 1/5?",
                "SYMBOLIC",
                "7/12",
                [("1/5", 0.68), ("equal", 0.17)],
                1220,
            ),
        ],
        "worked_example": {
            "diagnostic_item_id": "i_1501",
            "explanation": "5/6 is bigger because I turned 1/2 into 3/6 and 5 is more than 3",
            "asr_confidence": 0.81,
            "manipulative_trace": [
                {"t": 2.4, "action": "drag", "target": "bar_5_6"},
                {"t": 5.0, "action": "align", "targets": ["bar_5_6", "bar_1_2"]},
            ],
            "diagnosis_confidence": 0.86,
            "diagnosis_evidence_span": "turned 1/2 into 3/6",
            "understanding_signals": ["partitioning_language"],
            "intervention_id": "INT_M005_C",
            "verification_item_indices": [0, 1, 3],
            "transfer_item_index": 1,
            "transfer_result": False,
            "p_known_before": 0.29,
            "p_known_after": 0.87,
            "misconception_after": 0.09,
            "transfer_verified": False,
            "claim": "Ava can compare fractions with unlike numerators and denominators",
            "caveats": [
                "transfer to a set/group model not yet confirmed — she solved this with symbols and a "
                "number line but missed the marbles version; we'll check again next session"
            ],
            "next_review": "2026-09-18",
        },
    },
    # ---------------------------------------------------------------- M006 --
    {
        "code": "M006",
        "title": "A fraction can never be greater than one whole",
        "skill_code": "S007_improper_fractions",
        "cognitive_origin": (
            "Early fraction experience is almost entirely parts of a single whole "
            "(pizza slices, pie charts), so 'fraction' gets encoded as inherently "
            "less than one; a numerator larger than the denominator is treated as "
            "an error rather than a quantity greater than one whole."
        ),
        "prevalence_prior": 0.36,
        "distractor_likelihood": {
            "says_impossible_or_invalid": 0.64,
            "rewrites_as_whole_number_only": 0.21,
            "other": 0.15,
        },
        # P(d | not M006). Rationale: a child without the "fractions stop at
        # one whole" belief can still hesitate and call an unfamiliar
        # top-heavy fraction "not allowed" out of unfamiliarity with the
        # item format rather than a genuine belief — a modest rate.
        # "Rewrites as whole number" is closer to a rounding/estimation
        # habit than to this specific belief, so it gets slightly more
        # independent mass than the flat "impossible" claim.
        "distractor_likelihood_if_not_misconception": {
            "says_impossible_or_invalid": 0.09,
            "rewrites_as_whole_number_only": 0.13,
            "other": 0.78,
        },
        "citation": "Literature on the part-whole-only conception of fractions and the transition to fractions greater than one.",
        "sprout_forbidden": [
            "improper",
            "stating a fraction can be greater than one whole before resolution",
        ],
        "sprout_scripts": [
            (
                "That fraction can't be right — the top number can't be bigger than the bottom!",
                "confident",
            ),
            ("Wait, can a fraction ever be bigger than one whole thing?", "curious"),
            ("I thought fractions were always pieces smaller than one whole.", "confused"),
            (
                "Maybe that's just a mistake and should really be a whole number instead?",
                "uncertain",
            ),
            ("Fractions have to stay under 1, so this one must be wrong, right?", "confident"),
            (
                "So what does a fraction like that even mean if it's more than a whole pizza?",
                "curious",
            ),
        ],
        "interventions": [
            (
                "VISUALIZATION",
                "second_whole_plus_extra",
                "Let's shade one WHOLE circle, then start shading a second one — that extra piece is what makes it more than one whole.",
                0.75,
            ),
            (
                "ANALOGY",
                "more_than_one_pizza",
                "It's like ordering more than one whole pizza — you can absolutely have 1 and 1/4 pizzas.",
                0.70,
            ),
            (
                "WORKED_EXAMPLE",
                "count_past_the_whole",
                "Watch me count fourths past 4/4: 4/4 is one whole, 5/4 is one whole plus one more quarter.",
                0.74,
            ),
        ],
        "diagnostic_items": [
            (
                "i_1601",
                "Is 5/4 a real fraction?",
                "SYMBOLIC",
                "Yes — it means one whole and one more quarter",
                [
                    ("No, the top can't be bigger than the bottom", 0.64),
                    ("It just means the number 1", 0.21),
                ],
                1180,
            ),
            (
                "i_1602",
                "Is 7/3 a real number?",
                "SYMBOLIC",
                "Yes — it's more than 2 wholes (2 and 1/3)",
                [("No, that's not allowed", 0.64), ("It just means the number 2", 0.21)],
                1200,
            ),
            (
                "i_1603",
                "These pictures show 1 whole circle fully shaded and one more circle with 1/4 shaded. What fraction is shaded overall?",
                "AREA_MODEL",
                "5/4",
                [
                    ("You can't shade more than one whole circle", 0.64),
                    ("1 (just the whole one counts)", 0.21),
                ],
                1220,
            ),
            (
                "i_1604",
                "Two whole rectangles are shaded plus 1/3 of a third rectangle. What is the total, as a fraction?",
                "AREA_MODEL",
                "7/3",
                [
                    ("That's impossible, fractions stop at 1 whole", 0.64),
                    ("2 (the extra third doesn't count)", 0.21),
                ],
                1240,
            ),
        ],
        "transfer_items": [
            (
                "i_1691",
                "Place 5/4 on a number line that goes from 0 to 2.",
                "NUMBER_LINE",
                "5/4 (between 1 and 2, one quarter past 1)",
                1330,
            ),
            (
                "i_1692",
                "You have 5 quarter-cups of flour. How many cups is that, written as a fraction of a cup?",
                "SET_MODEL",
                "5/4 cups",
                1350,
            ),
        ],
        "practice_items": [
            (
                "i_2023",
                "Is 6/5 more or less than 1 whole?",
                "SYMBOLIC",
                "More than 1 whole",
                [
                    ("That's not a valid fraction", 0.64),
                    ("You just round it down to a whole number", 0.21),
                ],
                1190,
            ),
            (
                "i_2024",
                "Is 9/4 more or less than 2 wholes?",
                "SYMBOLIC",
                "More than 2 wholes",
                [
                    ("That's not a valid fraction", 0.64),
                    ("You just round it down to a whole number", 0.21),
                ],
                1200,
            ),
            (
                "i_2025",
                "What is 8/3 as a mixed number?",
                "SYMBOLIC",
                "2 and 2/3",
                [("That's not a valid fraction", 0.64), ("You just round it down to 2", 0.21)],
                1210,
            ),
            (
                "i_2026",
                "Is 3/3 more, less, or equal to 1 whole?",
                "SYMBOLIC",
                "Equal to 1 whole",
                [("That's not a valid fraction", 0.64), ("It rounds down to 0", 0.21)],
                1180,
            ),
            (
                "i_2027",
                "What is 11/4 as a mixed number?",
                "SYMBOLIC",
                "2 and 3/4",
                [("That's not a valid fraction", 0.64), ("You just round it down to 2", 0.21)],
                1220,
            ),
        ],
        "worked_example": {
            "diagnostic_item_id": "i_1603",
            "explanation": "it's 5/4 because the first circle is a whole one which is 4/4 and then one more piece makes 5/4",
            "asr_confidence": 0.83,
            "manipulative_trace": [
                {"t": 2.0, "action": "drag", "target": "circle_whole"},
                {"t": 4.1, "action": "align", "targets": ["circle_whole", "circle_quarter"]},
            ],
            "diagnosis_confidence": 0.89,
            "diagnosis_evidence_span": "one more piece makes 5/4",
            "understanding_signals": ["partitioning_language"],
            "intervention_id": "INT_M006_A",
            "verification_item_indices": [0, 1, 4],
            "transfer_item_index": 0,
            "transfer_result": True,
            "p_known_before": 0.24,
            "p_known_after": 0.90,
            "misconception_after": 0.06,
            "transfer_verified": True,
            "claim": "Ava can represent fractions greater than one whole",
            "caveats": [
                "transfer confirmed on a number line only; set-model transfer not yet attempted"
            ],
            "next_review": "2026-09-21",
        },
    },
    # ---------------------------------------------------------------- M007 --
    {
        "code": "M007",
        "title": "Fraction of a set means dividing by the numerator, not the denominator",
        "skill_code": "S008_fraction_of_a_set",
        "cognitive_origin": (
            "When asked for a fraction of a GROUP of objects rather than a single "
            "shape, children map the wrong number in the fraction onto the "
            "partitioning step, using the numerator as the divisor instead of the "
            "denominator — a failure to transfer the part-whole model from area to "
            "a set/group model."
        ),
        "prevalence_prior": 0.31,
        "distractor_likelihood": {
            "divides_by_numerator": 0.62,
            "uses_numerator_as_the_answer": 0.23,
            "other": 0.15,
        },
        # P(d | not M007). Rationale: a child who has correctly transferred
        # the part-whole model to sets can still slip and divide by the
        # wrong number of the fraction under time pressure (an arithmetic
        # mix-up, not the procedural misconception), so a modest independent
        # rate. Simply parroting the numerator as a final answer is a
        # lower-effort guessing pattern that is less likely absent the
        # specific procedural confusion.
        "distractor_likelihood_if_not_misconception": {
            "divides_by_numerator": 0.10,
            "uses_numerator_as_the_answer": 0.06,
            "other": 0.84,
        },
        "citation": "Research on children's difficulty transferring fraction understanding from area models to set/group models.",
        "sprout_forbidden": [
            "denominator",
            "stating you divide by the denominator before resolution",
        ],
        "sprout_scripts": [
            ("2/3 of 12? Easy, just divide by the top number: 12 divided by 2 is 6!", "confident"),
            (
                "Wait, which number tells me how many groups to split into, the top or the bottom?",
                "curious",
            ),
            ("I keep mixing up which number I'm supposed to divide by.", "confused"),
            ("Maybe I use the bottom number sometimes? I'm not sure when.", "uncertain"),
            ("The top number is what I divide by, right? That's what I always do.", "confident"),
            ("So the bottom number is just... extra?", "curious"),
        ],
        "interventions": [
            (
                "VISUALIZATION",
                "split_into_denominator_groups",
                "First split all 12 counters into 3 equal groups (that's the bottom number) — THEN count how many groups, 2, you need.",
                0.71,
            ),
            (
                "HINT",
                "bottom_number_is_the_split",
                "The bottom number always tells you how many equal groups to make first. The top number tells you how many of those groups to take.",
                0.68,
            ),
            (
                "WORKED_EXAMPLE",
                "step_by_step_of",
                "Watch: 2/3 of 12 -> Step 1: 12 divided by 3 (the bottom) is 4. Step 2: 4 times 2 (the top) is 8.",
                0.77,
            ),
        ],
        "diagnostic_items": [
            (
                "i_1701",
                "What is 2/3 of 12 counters?",
                "SET_MODEL",
                "8 counters",
                [
                    ("6 counters (12 divided by the top number, 2)", 0.62),
                    ("2 counters (just the top number)", 0.23),
                ],
                1160,
            ),
            (
                "i_1702",
                "What is 3/4 of 16 stickers?",
                "SET_MODEL",
                "12 stickers",
                [
                    ("About 5 stickers (16 divided by the top number, 3)", 0.62),
                    ("3 stickers (just the top number)", 0.23),
                ],
                1180,
            ),
            (
                "i_1703",
                "To find 2/5 of 20, what do you do first?",
                "SYMBOLIC",
                "Divide 20 by 5 (the denominator), then multiply by 2",
                [
                    ("Divide 20 by 2 (the top number)", 0.62),
                    ("Just use the top number, 2, as the answer", 0.23),
                ],
                1200,
            ),
            (
                "i_1704",
                "To find 3/4 of 24, what do you do first?",
                "SYMBOLIC",
                "Divide 24 by 4 (the denominator), then multiply by 3",
                [
                    ("Divide 24 by 3 (the top number)", 0.62),
                    ("Just use the top number, 3, as the answer", 0.23),
                ],
                1220,
            ),
        ],
        "transfer_items": [
            (
                "i_1791",
                "A garden bed has 20 equal square plots, and 2/5 of it grows tomatoes. How many plots grow tomatoes?",
                "AREA_MODEL",
                "8 plots",
                1330,
            ),
            (
                "i_1792",
                "A 25-minute video is divided into fifths. How many minutes is 3/5 of the video?",
                "NUMBER_LINE",
                "15 minutes",
                1350,
            ),
        ],
        "practice_items": [
            (
                "i_2028",
                "What is 1/4 of 20 marbles?",
                "SET_MODEL",
                "5 marbles",
                [("20 marbles (no change)", 0.62), ("1 marble (just the top number)", 0.23)],
                1150,
            ),
            (
                "i_2029",
                "What is 2/5 of 15 stickers?",
                "SET_MODEL",
                "6 stickers",
                [
                    ("About 8 stickers (15 divided by the top number, 2)", 0.62),
                    ("2 stickers", 0.23),
                ],
                1160,
            ),
            (
                "i_2030",
                "What is 3/5 of 20 candies?",
                "SET_MODEL",
                "12 candies",
                [("About 7 candies (20 divided by the top number, 3)", 0.62), ("3 candies", 0.23)],
                1170,
            ),
            (
                "i_2031",
                "What is 1/3 of 18 books?",
                "SET_MODEL",
                "6 books",
                [("18 books (no change)", 0.62), ("1 book", 0.23)],
                1180,
            ),
            (
                "i_2032",
                "What is 2/3 of 21 pencils?",
                "SET_MODEL",
                "14 pencils",
                [("About 11 pencils (21 divided by the top number, 2)", 0.62), ("2 pencils", 0.23)],
                1190,
            ),
        ],
        "worked_example": {
            "diagnostic_item_id": "i_1701",
            "explanation": "you split the 12 into 3 equal groups first, that's 4 each, then you take 2 of the groups so it's 8",
            "asr_confidence": 0.87,
            "manipulative_trace": [
                {"t": 2.5, "action": "drag", "target": "counter_group_1"},
                {"t": 5.2, "action": "align", "targets": ["counter_group_1", "counter_group_2"]},
            ],
            "diagnosis_confidence": 0.90,
            "diagnosis_evidence_span": "split the 12 into 3 equal groups first",
            "understanding_signals": ["partitioning_language"],
            "intervention_id": "INT_M007_C",
            "verification_item_indices": [0, 1, 3],
            "transfer_item_index": 0,
            "transfer_result": True,
            "p_known_before": 0.27,
            "p_known_after": 0.88,
            "misconception_after": 0.07,
            "transfer_verified": True,
            "claim": "Ava can find a fraction of a set of objects",
            "caveats": [
                "transfer confirmed with an area-model garden bed only; a number-line/time version not yet attempted"
            ],
            "next_review": "2026-09-22",
        },
    },
    # ---------------------------------------------------------------- M008 --
    {
        "code": "M008",
        "title": "Adding fractions means adding numerators and denominators separately",
        "skill_code": "S005_add_fractions",
        "cognitive_origin": (
            "The 'add straight across' bug: children apply whole-number addition "
            "procedures directly to both parts of the fraction (1/4 + 1/4 -> 2/8) "
            "because they have not yet encoded that the denominator names the unit "
            "size, which stays fixed when the pieces being combined are already "
            "the same size."
        ),
        "prevalence_prior": 0.45,
        "distractor_likelihood": {
            "adds_across": 0.75,
            "keeps_one_numerator_adds_denominators": 0.10,
            "other": 0.15,
        },
        # P(d | not M008). Rationale: unlike the other seven misconceptions,
        # this citation's own literature explicitly documents "add straight
        # across" as one of the most widely produced fraction-arithmetic
        # slips industry-wide — meaning it shows up even in children who
        # have NOT settled into the persistent misconception, as an early
        # or careless slip on the way to fluency. That documented ubiquity
        # is why this complement gives it noticeably more mass (0.20) than
        # any other misconception's primary behavior gets under its own
        # complement — still well below M008's own P(d|M_k)=0.75, but not
        # negligible the way the other seven's complements are.
        "distractor_likelihood_if_not_misconception": {
            "adds_across": 0.20,
            "keeps_one_numerator_adds_denominators": 0.08,
            "other": 0.72,
        },
        "citation": "The 'add straight across' bug is among the most widely documented fraction-arithmetic errors in mathematics-education research.",
        "sprout_forbidden": [
            "common denominator",
            "stating 1/2 + 1/3 = 2/5 as correct after resolution",
        ],
        "sprout_scripts": [
            ("1/4 plus 1/4 is 2/8 — just add the tops and add the bottoms!", "confident"),
            ("Wait, do I add the bottom numbers together too, or just the top ones?", "curious"),
            (
                "Adding fractions feels just like adding regular numbers, top and bottom both.",
                "confused",
            ),
            ("Maybe the bottom number should stay the same? I'm not totally sure.", "uncertain"),
            ("Adding is adding — tops together, bottoms together, that's the rule!", "confident"),
            ("So why wouldn't the bottom numbers add up too?", "curious"),
        ],
        "interventions": [
            (
                "VISUALIZATION",
                "combine_same_size_pieces",
                "Let's push the shaded pieces from both same-size bars together onto one bar — count how many of the SAME-size pieces you have now.",
                0.80,
            ),
            (
                "HINT",
                "denominator_names_the_piece_size",
                "The bottom number names how big each piece is. If both bars use the same size piece, that number doesn't change when you combine them.",
                0.70,
            ),
            (
                "WORKED_EXAMPLE",
                "same_denominator_addition",
                "Watch: 1/4 + 1/4 — the pieces are already the same size (fourths), so we just add how many pieces: 1 + 1 = 2, giving 2/4.",
                0.82,
            ),
        ],
        "diagnostic_items": [
            (
                "i_1801",
                "What is 1/4 + 1/4?",
                "SYMBOLIC",
                "2/4 (or 1/2)",
                [("2/8", 0.75), ("1/8", 0.10)],
                1150,
            ),
            (
                "i_1802",
                "What is 2/6 + 1/6?",
                "SYMBOLIC",
                "3/6 (or 1/2)",
                [("3/12", 0.75), ("2/12", 0.10)],
                1170,
            ),
            (
                "i_1803",
                "Two bars, each split into 5 equal parts. First bar has 2 parts shaded, second bar has 1 part shaded (same size bars). Combined, what fraction of one bar is that?",
                "AREA_MODEL",
                "3/5",
                [("3/10", 0.75), ("2/10", 0.10)],
                1190,
            ),
            (
                "i_1804",
                "Two circles, each split into 6 slices. First circle: 3 slices shaded. Second circle: 2 slices shaded. Combined, what fraction of one circle is shaded?",
                "AREA_MODEL",
                "5/6",
                [("5/12", 0.75), ("3/12", 0.10)],
                1210,
            ),
        ],
        "transfer_items": [
            (
                "i_1891",
                "Start at 1/5 on a number line and hop forward 2/5. Where do you land?",
                "NUMBER_LINE",
                "3/5",
                1330,
            ),
            (
                "i_1892",
                "A jar of 7 beads has 2/7 red beads and 3/7 blue beads. What fraction of the jar is red or blue combined?",
                "SET_MODEL",
                "5/7",
                1350,
            ),
        ],
        "practice_items": [
            (
                "i_2033",
                "What is 1/6 + 2/6?",
                "SYMBOLIC",
                "3/6 (or 1/2)",
                [("3/12", 0.75), ("1/12", 0.10)],
                1160,
            ),
            (
                "i_2034",
                "What is 2/5 + 1/5?",
                "SYMBOLIC",
                "3/5",
                [("3/10", 0.75), ("2/10", 0.10)],
                1170,
            ),
            (
                "i_2035",
                "What is 3/8 + 2/8?",
                "SYMBOLIC",
                "5/8",
                [("5/16", 0.75), ("3/16", 0.10)],
                1180,
            ),
            (
                "i_2036",
                "What is 1/3 + 1/3?",
                "SYMBOLIC",
                "2/3",
                [("2/6", 0.75), ("1/6", 0.10)],
                1190,
            ),
            (
                "i_2037",
                "What is 4/9 + 3/9?",
                "SYMBOLIC",
                "7/9",
                [("7/18", 0.75), ("4/18", 0.10)],
                1200,
            ),
        ],
        "worked_example": {
            "diagnostic_item_id": "i_1801",
            "explanation": "the pieces are already fourths so the bottom stays 4, you just add 1 plus 1 on top to get 2/4",
            "asr_confidence": 0.90,
            "manipulative_trace": [
                {"t": 1.5, "action": "drag", "target": "bar_1_4_a"},
                {"t": 3.0, "action": "align", "targets": ["bar_1_4_a", "bar_1_4_b"]},
            ],
            "diagnosis_confidence": 0.92,
            "diagnosis_evidence_span": "the bottom stays 4",
            "understanding_signals": ["partitioning_language"],
            "intervention_id": "INT_M008_C",
            "verification_item_indices": [0, 1, 3],
            "transfer_item_index": 0,
            "transfer_result": True,
            "p_known_before": 0.22,
            "p_known_after": 0.93,
            "misconception_after": 0.03,
            "transfer_verified": True,
            "claim": "Ava can add fractions with like denominators",
            "caveats": [
                "transfer confirmed on a number line only; set-model transfer not yet attempted"
            ],
            "next_review": "2026-09-23",
        },
    },
]

# --- general transfer pool: 8 items, 2 representations, not misconception-specific --

GENERAL_TRANSFER_ITEMS: list[dict[str, Any]] = [
    {
        "id": "i_3001",
        "stem": "Place 1/3 and 1/6 on the same number line from 0 to 1. Which is farther right?",
        "representation": "number_line",
        "correct_answer": "1/3",
        "skill_code": "S004_compare_unit_fractions",
        "elo": 1400,
        "pool": "general",
    },
    {
        "id": "i_3002",
        "stem": "On a number line from 0 to 1, place 3/5 and 2/3. Which is farther right?",
        "representation": "number_line",
        "correct_answer": "2/3",
        "skill_code": "S006_compare_unlike_fractions",
        "elo": 1420,
        "pool": "general",
    },
    {
        "id": "i_3003",
        "stem": "Place 7/4 on a number line from 0 to 2.",
        "representation": "number_line",
        "correct_answer": "7/4 (between 1 and 2, one quarter past 1 and a half)",
        "skill_code": "S007_improper_fractions",
        "elo": 1440,
        "pool": "general",
    },
    {
        "id": "i_3004",
        "stem": "Start at 2/7 and hop forward 3/7 on a number line. Where do you land?",
        "representation": "number_line",
        "correct_answer": "5/7",
        "skill_code": "S005_add_fractions",
        "elo": 1460,
        "pool": "general",
    },
    {
        "id": "i_3005",
        "stem": "Without a picture, is 4/10 equal to 2/5?",
        "representation": "symbolic",
        "correct_answer": "Yes",
        "skill_code": "S003_equivalent_fractions",
        "elo": 1400,
        "pool": "general",
    },
    {
        "id": "i_3006",
        "stem": "Without counting objects, what is 3/4 of 40?",
        "representation": "symbolic",
        "correct_answer": "30",
        "skill_code": "S008_fraction_of_a_set",
        "elo": 1420,
        "pool": "general",
    },
    {
        "id": "i_3007",
        "stem": "Without a picture, what does 5/8 mean?",
        "representation": "symbolic",
        "correct_answer": "5 equal parts out of 8 total parts",
        "skill_code": "S001_identify_fraction",
        "elo": 1380,
        "pool": "general",
    },
    {
        "id": "i_3008",
        "stem": "True or false, using words only: a fraction requires equal-size parts.",
        "representation": "symbolic",
        "correct_answer": "True",
        "skill_code": "S002_equal_parts",
        "elo": 1390,
        "pool": "general",
    },
]


# --- assembly -------------------------------------------------------------------


def _distractors(pairs: list[tuple[str, float]], maps_to: str) -> list[dict[str, Any]]:
    return [
        {"value": value, "maps_to": maps_to, "likelihood": likelihood}
        for value, likelihood in pairs
    ]


def build_content() -> dict[str, Any]:
    """Assemble every content file as a ``{relative_path: json_document}`` dict."""
    skills = [dict(s) for s in SKILLS]
    prerequisites = [
        {"skill_code": s["code"], "prereq_code": prereq}
        for s in skills
        for prereq in s["prerequisites"]
    ]

    misconceptions: list[dict[str, Any]] = []
    sprout_scripts: list[dict[str, Any]] = []
    interventions: list[dict[str, Any]] = []
    diagnostic_items: list[dict[str, Any]] = []
    practice_items: list[dict[str, Any]] = []
    misconception_transfer_items: list[dict[str, Any]] = []
    worked_examples: dict[str, dict[str, Any]] = {}

    for m in MISCONCEPTIONS:
        code = m["code"]
        misconceptions.append(
            {
                "code": code,
                "title": m["title"],
                "cognitive_origin": m["cognitive_origin"],
                "skill_code": m["skill_code"],
                "distractor_likelihood": m["distractor_likelihood"],
                "distractor_likelihood_if_not_misconception": m[
                    "distractor_likelihood_if_not_misconception"
                ],
                "prevalence_prior": m["prevalence_prior"],
                "citation": m["citation"],
                "sprout_forbidden": m["sprout_forbidden"],
                "content_version": CONTENT_VERSION,
            }
        )

        for index, (utterance, emotion) in enumerate(m["sprout_scripts"], start=1):
            sprout_scripts.append(
                {
                    "id": f"SS_{code}_{index:02d}",
                    "utterance": utterance,
                    "emotion": emotion,
                    "misconception_code": code,
                }
            )

        for suffix, (itype, strategy, script, rate) in zip("ABC", m["interventions"], strict=True):
            interventions.append(
                {
                    "id": f"INT_{code}_{suffix}",
                    "type": itype,
                    "strategy": strategy,
                    "script": script,
                    "historical_success_rate": rate,
                    "misconception_code": code,
                }
            )

        diag_ids_for_worked: dict[str, dict[str, Any]] = {}
        for item_id, stem, representation, correct, distractor_pairs, elo in m["diagnostic_items"]:
            record = {
                "id": item_id,
                "stem": stem,
                "representation": representation.lower(),
                "correct_answer": correct,
                "distractors": _distractors(distractor_pairs, code),
                "elo": elo,
                "role": "diagnostic",
                "skill_code": m["skill_code"],
                "content_version": CONTENT_VERSION,
            }
            diagnostic_items.append(record)
            diag_ids_for_worked[item_id] = record

        practice_records: list[dict[str, Any]] = []
        for item_id, stem, representation, correct, distractor_pairs, elo in m["practice_items"]:
            record = {
                "id": item_id,
                "stem": stem,
                "representation": representation.lower(),
                "correct_answer": correct,
                "distractors": _distractors(distractor_pairs, code),
                "elo": elo,
                "role": "practice",
                "skill_code": m["skill_code"],
                "content_version": CONTENT_VERSION,
            }
            practice_items.append(record)
            practice_records.append(record)

        transfer_records: list[dict[str, Any]] = []
        for item_id, stem, representation, correct, elo in m["transfer_items"]:
            record = {
                "id": item_id,
                "stem": stem,
                "representation": representation.lower(),
                "correct_answer": correct,
                "elo": elo,
                "skill_code": m["skill_code"],
                "pool": "misconception",
            }
            misconception_transfer_items.append(record)
            transfer_records.append(record)

        we = m["worked_example"]
        skill_record = next(s for s in skills if s["code"] == m["skill_code"])
        misconception_record = misconceptions[-1]
        diagnostic_record = diag_ids_for_worked[we["diagnostic_item_id"]]
        intervention_record = next(i for i in interventions if i["id"] == we["intervention_id"])
        unaided_items = [practice_records[i]["id"] for i in we["verification_item_indices"]]
        transfer_record = transfer_records[we["transfer_item_index"]]

        worked_examples[code] = {
            "skill": skill_record,
            "misconception": misconception_record,
            "sprout_scripts": [s for s in sprout_scripts if s["misconception_code"] == code][:3],
            "sprout_forbidden": m["sprout_forbidden"],
            "diagnostic_item": diagnostic_record,
            "learner_evidence": {
                "explanation": we["explanation"],
                "asr_confidence": we["asr_confidence"],
                "manipulative_trace": we["manipulative_trace"],
                "diagnosis": {
                    "labels": [
                        {
                            "misconception_id": code,
                            "state": "resolved",
                            "confidence": we["diagnosis_confidence"],
                            "evidence_span": we["diagnosis_evidence_span"],
                        }
                    ],
                    "understanding_signals": we["understanding_signals"],
                    "asr_reliable": True,
                },
            },
            "intervention": intervention_record,
            "verification": {
                "unaided_items": unaided_items,
                "results": [True] * len(unaided_items),
                "transfer_item": {
                    "id": transfer_record["id"],
                    "representation": transfer_record["representation"],
                    "result": we["transfer_result"],
                },
            },
            "mastery_outcome": {
                "p_known_before": we["p_known_before"],
                "p_known_after": we["p_known_after"],
                "misconception_posteriors": {code: we["misconception_after"]},
                "transfer_verified": we["transfer_verified"],
                "claim": we["claim"],
                "evidence_ids": [f"e_{code.lower()}_{n}" for n in range(1, 6)],
                "caveats": we["caveats"],
                "next_review": we["next_review"],
            },
        }

    all_transfer_items = misconception_transfer_items + GENERAL_TRANSFER_ITEMS

    return {
        "skills.json": {"skills": skills},
        "prerequisites.json": {"prerequisites": prerequisites},
        "misconceptions.json": {"misconceptions": misconceptions},
        "sprout_scripts.json": {"sprout_scripts": sprout_scripts},
        "interventions.json": {"interventions": interventions},
        "items/diagnostic.json": {"items": diagnostic_items},
        "items/practice.json": {"items": practice_items},
        "items/transfer.json": {"transfer_items": all_transfer_items},
        **{f"worked_examples/{code}.json": doc for code, doc in worked_examples.items()},
    }


def write_content(root: Path) -> list[Path]:
    """Write every file from :func:`build_content` under ``root``. Deterministic:
    sorted keys, stable formatting, so re-running produces byte-identical output."""
    written: list[Path] = []
    for relative_path, document in build_content().items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(document, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        written.append(path)
    return written


def main() -> int:
    from .loader import default_content_root

    for path in write_content(default_content_root()):
        print(path.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
