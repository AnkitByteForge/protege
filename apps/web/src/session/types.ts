/**
 * The 21 canonical session states (roadmap P7: `protege.contracts.SessionState`,
 * `packages/contracts/src/protege/contracts/enums.py`). P10's wire schema
 * types `SessionOut.state`/`SessionEventOut.state` as a plain `string`
 * (`services/session/src/protege/session_service/schemas.py`), so
 * `make api-types`/openapi-typescript has no enum to generate here -- this
 * union is P15's own, hand-kept copy of that one closed vocabulary, not a
 * second copy of a shape the generated schema already types more strongly.
 * Values are UPPERCASE, verbatim from the Python `StrEnum` member values
 * (confirmed against a live `POST /v1/sessions` response: `"state":
 * "DIAGNOSTIC"`) -- keep in sync with `enums.py`'s `SessionState` if a
 * state is ever added there.
 */
export const SESSION_STATES = [
  "ARRIVAL",
  "SPROUT_TEASE",
  "DIAGNOSTIC",
  "DISCOVERY",
  "GUIDED_LEARNING",
  "PRACTICE",
  "EXPLANATION",
  "SPROUT_SETUP",
  "SPROUT_SETUP_HARD",
  "TEACH_BACK",
  "COACH_ASSIST",
  "REFLECTION",
  "INDEPENDENT_VERIFY",
  "TRANSFER",
  "MASTERY_DECISION",
  "REWARD",
  "SUMMARY",
  "RETRIEVAL_SCHEDULE",
  "ESCALATE_TO_HUMAN",
  "COMPLETE",
  "ABANDONED",
] as const;

export type SessionStateName = (typeof SESSION_STATES)[number];

/**
 * States that are always synchronous/instantaneous on the server (roadmap
 * P10 `engine/runtime.py` docstring: "States the roadmap marks as
 * synchronous/instantaneous ... are advanced through automatically within
 * the same request"; plus `SPROUT_TEASE`, which `create_session` also
 * advances through synchronously before ever returning). The client mirror
 * holds the rendered scene here for a deliberate minimum beat (roadmap P15:
 * "deliberate beats, no instant jumps; the child always sees *why*
 * something changed") rather than flashing straight through to whatever the
 * server has already reached by the time its SSE events arrive -- it never
 * invents a state the server didn't actually pass through.
 */
export const BEAT_STATES: ReadonlySet<SessionStateName> = new Set([
  "ARRIVAL",
  "SPROUT_TEASE",
  "DISCOVERY",
  "GUIDED_LEARNING",
  "SPROUT_SETUP",
  "SPROUT_SETUP_HARD",
  "MASTERY_DECISION",
  "RETRIEVAL_SCHEDULE",
]);

export const TERMINAL_STATES: ReadonlySet<SessionStateName> = new Set(["COMPLETE", "ABANDONED"]);

/**
 * States whose own resulting content must be held on screen for a
 * deliberate beat *before* advancing, even though the state itself is a
 * real, interactive dwell (not a `BEAT_STATES` pass-through). `COACH_ASSIST`
 * is the one member today: `hint_requested`'s response already carries the
 * server's auto-cascaded `state: "TEACH_BACK"` (`engine/runtime.py`
 * advances `COACH_ASSIST` -> `TEACH_BACK` in the same request once a hint
 * is delivered), so the SSE confirmation of that same transition can arrive
 * within the same poll cycle the hint text itself did. Without holding here,
 * the scene would flip to `teach_back` before the hint -- the entire point
 * of asking for one -- was ever visible on screen.
 */
export const HOLD_BEFORE_ADVANCING_STATES: ReadonlySet<SessionStateName> = new Set([
  "COACH_ASSIST",
]);
