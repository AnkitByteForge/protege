import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Baloo_2, Nunito } from "next/font/google";
import { MotionProvider } from "@/components/motion/MotionProvider";
import { SoundProvider } from "@/hooks/useSound";
import "./globals.css";

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
        <MotionProvider>
          <SoundProvider enabled={false}>{children}</SoundProvider>
        </MotionProvider>
      </body>
    </html>
  );
}
