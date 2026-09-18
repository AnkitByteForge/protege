import { clerkMiddleware, createRouteMatcher } from "@clerk/nextjs/server";
import { NextResponse } from "next/server";

/**
 * Only the live session flow needs a signed-in parent (roadmap P10's COPPA
 * design: "the child plays under the parent's authenticated session on a
 * shared device" -- there is no independent child identity to protect
 * separately). Everything P12/P13/P14 already shipped (`/world`, `/gallery`,
 * `/(parent)/home`) stays reachable without Clerk configured at all, so
 * those existing routes/tests keep working unmodified.
 */
const isProtectedRoute = createRouteMatcher(["/garden(.*)", "/session(.*)"]);

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
