import Link from "next/link";
import { SoftPanel } from "@/components/primitives/SoftPanel";
import { Display, Eyebrow, Text } from "@/components/primitives/Typography";
import { Stack } from "@/components/primitives/Stack";

const links: { href: string; label: string; note: string }[] = [
  {
    href: "/gallery",
    label: "Design system gallery",
    note: "Every primitive, motion preset, and state in one place.",
  },
  {
    href: "/gallery/manipulatives",
    label: "Manipulatives gallery",
    note: "FractionBar, NumberLine, AreaModel, ExplanationCards — roadmap P13.",
  },
  {
    href: "/world",
    label: "(child) preview — /world",
    note: "SceneFrame + sample scene transitions.",
  },
  { href: "/home", label: "(parent) preview — /home", note: "Parent-register shell, empty state." },
  {
    href: "/briefing",
    label: "(tutor) preview — /briefing",
    note: "Tutor-register shell, empty state.",
  },
];

/**
 * A local developer index, not a product page. The real experience lives
 * behind the (child)/(parent)/(tutor) route groups; this exists only so a
 * reviewer can find them without knowing the URLs.
 */
export default function Home() {
  return (
    <main
      id="main"
      className="mx-auto flex min-h-screen max-w-2xl flex-col justify-center px-6 py-16"
    >
      <Stack gap="lg">
        <div>
          <Eyebrow>Local development index</Eyebrow>
          <Display as="h1">PROTÉGÉ</Display>
          <Text muted className="mt-1">
            Design system & app shell (roadmap P12). Learn → Teach → Prove.
          </Text>
        </div>
        <Stack gap="sm">
          {links.map((l) => (
            <Link key={l.href} href={l.href} className="block">
              <SoftPanel elevation="raised" className="transition-colors hover:border-sky-700">
                <p className="font-sans text-lg font-bold text-ink">{l.label}</p>
                <Text muted className="text-sm">
                  {l.note}
                </Text>
              </SoftPanel>
            </Link>
          ))}
        </Stack>
      </Stack>
    </main>
  );
}
