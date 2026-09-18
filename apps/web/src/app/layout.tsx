import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Baloo_2, Nunito } from "next/font/google";
import { ClerkProvider } from "@clerk/nextjs";
import { MotionProvider } from "@/components/motion/MotionProvider";
import { SoundProvider } from "@/hooks/useSound";
import "./globals.css";

/**
 * `<ClerkProvider>` throws if it renders without a publishable key -- and
 * every P12/P13/P14 route (`/world`, `/gallery`, `/(parent)/home`) must
 * keep working in a checkout with no Clerk keys configured at all (the
 * state of this repo before P15). So the provider is opt-in on whether the
 * key is actually present, not unconditional; `middleware.ts` makes the
 * same check for the same reason.
 */
function AuthProvider({ children }: { children: ReactNode }) {
  if (!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) {
    return <>{children}</>;
  }
  return <ClerkProvider>{children}</ClerkProvider>;
}

const bodyFont = Nunito({
  subsets: ["latin"],
  variable: "--font-body",
  display: "swap",
});

const displayFont = Baloo_2({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

export const metadata: Metadata = {
  title: "PROTÉGÉ",
  description: "A warm little world that happens to teach fractions.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${bodyFont.variable} ${displayFont.variable}`}>
      <body>
        <a href="#main" className="skip-link">
          Skip to content
        </a>
        <AuthProvider>
          <MotionProvider>
            <SoundProvider enabled={false}>{children}</SoundProvider>
          </MotionProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
