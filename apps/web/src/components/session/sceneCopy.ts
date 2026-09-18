import type { SessionStateName } from "@/session/types";

/**
 * Child-facing copy for the states that render as a passive, timed beat
 * (roadmap P15: "deliberate beats, no instant jumps"). Every word here is
 * pre-authored, plain-English narration of *why* the world is about to
 * change -- never a technical label, never the state name itself.
 */
export const BEAT_COPY: Partial<Record<SessionStateName, { title: string; body: string }>> = {
  ARRIVAL: {
    title: "Walking into the garden…",
    body: "Getting everything ready for you.",
  },
  SPROUT_TEASE: {
    title: "Someone's excited to see you!",
    body: "Sprout has been waiting to show you something.",
  },
  DISCOVERY: {
    title: "Let's look around first.",
    body: "Take a moment to notice what's here before we dig in.",
  },
  SPROUT_SETUP: {
    title: "Sprout is thinking of what to say…",
    body: "One moment while Sprout gets ready to tell you what he thinks he knows.",
  },
  SPROUT_SETUP_HARD: {
    title: "Sprout has a trickier idea this time…",
    body: "This one's a little sneakier — get ready.",
  },
  MASTERY_DECISION: {
    title: "Let's see how that went…",
    body: "Thinking it over.",
  },
  RETRIEVAL_SCHEDULE: {
    title: "Remembering this for next time…",
    body: "Sprout is tucking this away so we can talk about it again soon.",
  },
};

export const ANSWER_SCENE_COPY: Partial<
  Record<SessionStateName, { eyebrow: string; hintAvailable: boolean }>
> = {
  DIAGNOSTIC: { eyebrow: "Let's see what you already know", hintAvailable: false },
  PRACTICE: { eyebrow: "Your turn to try", hintAvailable: true },
  INDEPENDENT_VERIFY: { eyebrow: "Show me on your own", hintAvailable: false },
  TRANSFER: { eyebrow: "One more, a little different", hintAvailable: false },
};
