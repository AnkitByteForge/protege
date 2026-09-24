import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

/**
 * Only the authenticated product-entry/live-session flow needs a signed-in
 * parent (roadmap P10's COPPA design: "the child plays under the parent's
 * authenticated session on a shared device" -- there is no independent
 * child identity to protect separately). `/start` is the product-entry
 * bootstrap step (calls `POST /v1/learners/ensure`, which itself requires a
 * verified actor) added by that milestone -- gated here the same way
 * `/garden`/`/session` already are, rather than each page re-checking auth
 * itself. Everything P12/P13/P14 already shipped (`/world`, `/gallery`,
 * `/(parent)/home`) stays reachable without Clerk configured at all, so
 * those existing routes/tests keep working unmodified.
 */
const isProtectedRoute = createRouteMatcher(["/start(.*)", "/garden(.*)", "/session(.*)"]);

const clerkConfigured = Boolean(process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY);

export default clerkConfigured
  ? clerkMiddleware(async (auth, req) => {
      if (isProtectedRoute(req)) {
        await auth.protect();
      }
    })
  : () => NextResponse.next();

export const config = {
  matcher: ["/((?!_next|.*\\..*).*)", "/(api|trpc)(.*)"],
};
