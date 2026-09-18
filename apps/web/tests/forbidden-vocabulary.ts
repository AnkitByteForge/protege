/**
 * The child-facing world never surfaces internal/technical language
 * (roadmap P15: "Create/retain an automated test scanning rendered
 * user-facing strings for forbidden vocabulary."). Shared by
 * `vocabulary.spec.ts` (the static P12 preview route) and
 * `session/happy-path.spec.ts` (the real, live P15 session flow) -- kept in
 * its own non-test module because Playwright refuses to let one test file
 * import another.
 */
export const forbidden = [
  /\bAI\b/i,
  /\bmodel\b/i,
  /\bmastery\b/i,
  /%/,
  /\bpercent(age)?\b/i,
  /\bscore\b/i,
  /\bprobabilit(y|ies)\b/i,
  /\bstack trace\b/i,
  /\bdebug(ging)?\b/i,
  /\berror code\b/i,
  /\btoken(s)?\b/i,
  /\bstreak\b/i,
  /\bleaderboard\b/i,
  /\bloss\b/i,
];
