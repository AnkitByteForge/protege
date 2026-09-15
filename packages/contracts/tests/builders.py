"""Representative instances of every contract, used by the round-trip,
constraint, and snapshot tests. One builder per exported model."""

from datetime import UTC, datetime

from protege.contracts import (
    CardExplanation,
    CoachHint,
    Concept,
    DiagnosisLabel,
    DiagnosisResult,
    Distractor,
    DomainEvent,
    Evidence,
    Intervention,
    ItemVersion,
    LearnerEvidence,
    LearningItem,
    ManipulativeAction,
    ManipulativeExplanation,
    MasteryEstimate,
    MasteryOutcome,
    Misconception,
    MisconceptionBelief,
    PolicyDecision,
    PolicyDecisionAction,
    PolicyDecisionReward,
    PolicyDecisionState,
    Prerequisite,
    ProofClaim,
    ReportDraft,
    ReportSentence,
    Skill,
    SproutScript,
    SproutTurn,
    TeachingEpisode,
    TextExplanation,
    TransferItem,
    TransferObservation,
    TutorBriefing,
    VerificationRecord,
    VoiceExplanation,
    WorkedExample,
)


def build_skill() -> Skill:
    return Skill(
        code="S004",
        title="Compare unit fractions",
        grade_band="3-4",
        prerequisites=["S001_identify_fraction", "S002_equal_parts"],
        standard="CCSS.3.NF.A.3d",
    )


def build_concept() -> Concept:
    return Concept(
        code="C001",
        title="Fraction magnitude",
        description="Understanding and comparing fraction sizes.",
        skill_codes=["S004"],
    )


def build_prerequisite() -> Prerequisite:
    return Prerequisite(skill_code="S004", prereq_code="S001_identify_fraction")


def build_misconception() -> Misconception:
    return Misconception(
        code="M003",
        title="Larger denominator means larger fraction",
        cognitive_origin="Whole-number bias transferred to the denominator.",
        skill_code="S004",
        distractor_likelihood={"picks_1_8": 0.82, "says_equal": 0.06, "other": 0.12},
        prevalence_prior=0.42,
        citation="Whole-number bias literature; Siegler et al.",
        sprout_forbidden=["stating 1/4 > 1/8 before resolution"],
        content_version="v1",
    )


def build_distractor() -> Distractor:
    return Distractor(value="1/8", maps_to="M003", likelihood=0.82)


def build_learning_item() -> LearningItem:
    return LearningItem(
        id="i_0132",
        stem="Which is more pizza: 1/4 or 1/8?",
        representation="area_model",
        correct="1/4",
        distractors=[build_distractor()],
        elo=1180,
        skill_code="S004",
        content_version="v1",
    )


def build_item_version() -> ItemVersion:
    return ItemVersion(
        item_id="i_0132",
        content_version="v1",
        stem="Which is more pizza: 1/4 or 1/8?",
        correct_answer="1/4",
        distractors=[build_distractor()],
        elo=1180,
        representation="area_model",
    )


def build_intervention() -> Intervention:
    return Intervention(
        id="INT_M003_A",
        type="VISUALIZATION",
        strategy="same_whole_partition_contrast",
        script="Let's cut the SAME pizza two ways and lay them on top of each other.",
        historical_success_rate=0.78,
        misconception_code="M003",
    )


def build_sprout_script() -> SproutScript:
    return SproutScript(
        id="SS_M003_01",
        utterance="I think 1/8 is bigger! Eight is way more than four.",
        emotion="confident",
        misconception_code="M003",
    )


def build_transfer_item() -> TransferItem:
    return TransferItem(
        id="i_0201",
        stem="Mark where 1/4 sits on the line from 0 to 1.",
        representation="number_line",
        correct="1/4",
        skill_code="S004",
        result=True,
    )


def build_evidence() -> Evidence:
    return Evidence(
        id="e_901",
        kind="response",
        source_event_id="evt_01J...",
        weight=3.0,
        payload={"item": "i_0148", "correct": True, "unaided": True, "latency": 8.2},
        created_at=datetime(2026, 9, 16, 18, 4, tzinfo=UTC),
    )


def build_mastery_estimate() -> MasteryEstimate:
    return MasteryEstimate(
        learner_id="lrn_01J...",
        skill_code="S004",
        p_known=0.91,
        evidence_count=5,
        unaided_correct=3,
        transfer_verified=True,
        model_version="bkt-v1",
        computed_at=datetime(2026, 9, 16, 18, 4, tzinfo=UTC),
    )


def build_misconception_belief() -> MisconceptionBelief:
    return MisconceptionBelief(
        learner_id="lrn_01J...",
        misconception_code="M003",
        p_holds=0.04,
        state="resolved",
        resolved_at=datetime(2026, 9, 16, 18, 3, tzinfo=UTC),
        resolution_evidence_id="e_904",
    )


def build_teaching_episode() -> TeachingEpisode:
    return TeachingEpisode(
        id="te_77",
        misconception_code="M003",
        turns=4,
        resolved=True,
        resolution_turn=4,
        quality_score=0.9,
        session_id="ses_01J...",
    )


def build_mastery_outcome() -> MasteryOutcome:
    return MasteryOutcome(
        p_known_before=0.31,
        p_known_after=0.91,
        misconception_M003_after=0.04,
        transfer_verified=True,
        claim="Ava can compare unit fractions",
        evidence_ids=["e_901", "e_902", "e_903", "e_904", "e_905"],
        caveats=["transfer confirmed on number line only"],
        next_review="2026-09-19",
    )


def build_manipulative_action() -> ManipulativeAction:
    return ManipulativeAction(t=4.8, action="align", targets=["bar_1_4", "bar_1_8"])


def build_voice_explanation() -> VoiceExplanation:
    return VoiceExplanation(
        text="more pieces means each piece is smaller",
        asr_confidence=0.88,
        skill_code="S004",
    )


def build_text_explanation() -> TextExplanation:
    return TextExplanation(text="the bottom number tells how many pieces", skill_code="S004")


def build_manipulative_explanation() -> ManipulativeExplanation:
    return ManipulativeExplanation(
        manipulative_trace=[build_manipulative_action()],
        skill_code="S004",
    )


def build_card_explanation() -> CardExplanation:
    return CardExplanation(
        card_ids=["card_more_pieces_smaller"],
        skill_code="S004",
    )


def build_diagnosis_label() -> DiagnosisLabel:
    return DiagnosisLabel(
        misconception_id="M003",
        state="resolved",
        confidence=0.91,
        evidence_span="more pieces are littler",
    )


def build_diagnosis_result() -> DiagnosisResult:
    return DiagnosisResult(
        labels=[build_diagnosis_label()],
        understanding_signals=["inverse_denominator_relationship", "partitioning_language"],
        asr_reliable=True,
        model_run_id="mr_01J...",
    )


def build_policy_decision_state() -> PolicyDecisionState:
    return PolicyDecisionState(vector=[0.62, 0.71, 1, 0.25, -0.4, 2, 0, 8.2, 6, 0.7, 0.18, 1, 3, 3])


def build_policy_decision_action() -> PolicyDecisionAction:
    return PolicyDecisionAction(
        type="TEACH_BACK",
        params={"misconception_code": "M003"},
        source="rules",
        shield_overrode=False,
        counterfactual_bandit_choice="PRACTICE",
    )


def build_policy_decision_reward() -> PolicyDecisionReward:
    return PolicyDecisionReward(immediate=0.0, deferred_pending=["retention_d7"])


def build_policy_decision() -> PolicyDecision:
    return PolicyDecision(
        trajectory_id="traj_01J...",
        step=7,
        state=build_policy_decision_state(),
        action=build_policy_decision_action(),
        observation={"resolved": True, "turns": 4, "asr_reliable": True},
        reward=build_policy_decision_reward(),
        next_state_ref="traj_01J...:8",
    )


def build_domain_event() -> DomainEvent:
    return DomainEvent(
        id="evt_01J...",
        event_type="MISCONCEPTION_RESOLVED",
        occurred_at=datetime(2026, 9, 16, 18, 3, 22, 481000, tzinfo=UTC),
        learner_id="lrn_01J...",
        session_id="ses_01J...",
        trace_id="otel_01J...",
        payload={
            "misconception_id": "M003",
            "p_holds_before": 0.20,
            "p_holds_after": 0.04,
            "detected_from": "explanation",
            "explanation_id": "exp_01J...",
            "diagnostician_confidence": 0.86,
            "asr_reliable": True,
            "model_run_id": "mr_01J...",
        },
    )


def build_sprout_turn() -> SproutTurn:
    return SproutTurn(
        utterance="Ohhh. More pieces means smaller pieces.",
        exhibits="M003",
        emotion="delighted",
        confidence_shown="low",
    )


def build_coach_hint() -> CoachHint:
    return CoachHint(
        intervention_id="INT_M003_A",
        text="Let's cut the same pizza two ways and compare.",
        persona_note="Ava responded well to pizza analogies.",
    )


def build_report_sentence() -> ReportSentence:
    return ReportSentence(
        text="Ava compared unit fractions correctly on three unseen problems.",
        evidence_ids=["e_901", "e_902", "e_903"],
    )


def build_report_draft() -> ReportDraft:
    return ReportDraft(
        audience="parent",
        claim_key="compares_unit_fractions",
        sentences=[build_report_sentence()],
    )


def build_proof_claim() -> ProofClaim:
    return ProofClaim(
        id="c_88",
        text="Ava can compare unit fractions",
        threshold_id="th_02",
        mastery_estimate_id="me_412",
        evidence_ids=["e_901", "e_902", "e_903", "e_904", "e_905"],
        caveats=["transfer confirmed on number line only"],
    )


def build_tutor_briefing() -> TutorBriefing:
    return TutorBriefing(
        learner_id="lrn_01J...",
        generated_at=datetime(2026, 9, 16, 18, 4, tzinfo=UTC),
        goal="Fraction comparison fluency by Oct 15",
        resolved=[
            {
                "misconception_id": "M003",
                "narrative": "Resolved Tue via teach-back turn 4; verified 3/3 unaided.",
            }
        ],
        still_open=[{"misconception_id": "M007", "p_holds": 0.64, "times_seen": 2}],
        what_worked=["Area model + cut-the-same-pizza analogy"],
        what_we_dont_know=["Equivalence. Never assessed."],
        effort="Strong. 14 min, no abandons.",
        suggested_opener="Show me how you'd explain 2/3 vs 3/4 to Sprout.",
    )


def build_transfer_observation() -> TransferObservation:
    return TransferObservation(id="i_0201", representation="number_line", result=True)


def build_verification_record() -> VerificationRecord:
    return VerificationRecord(
        unaided_items=["i_0148", "i_0155", "i_0161"],
        results=[True, True, True],
        transfer_item=build_transfer_observation(),
    )


def build_learner_evidence() -> LearnerEvidence:
    return LearnerEvidence(
        explanation_text="no because the bottom is how many pieces you cut it",
        asr_confidence=0.88,
        manipulative_trace=[
            build_manipulative_action(),
            ManipulativeAction(t=2.1, action="drag", target="bar_1_4"),
        ],
        diagnosis=build_diagnosis_result(),
    )


def build_worked_example() -> WorkedExample:
    return WorkedExample(
        skill=build_skill(),
        misconception=build_misconception(),
        sprout_scripts=[build_sprout_script()],
        sprout_forbidden=["stating 1/4 > 1/8 before resolution"],
        diagnostic_item=build_learning_item(),
        learner_evidence=build_learner_evidence(),
        intervention=build_intervention(),
        verification=build_verification_record(),
        mastery_outcome=build_mastery_outcome(),
    )
