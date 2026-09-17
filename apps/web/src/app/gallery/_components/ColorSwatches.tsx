import { color } from "@/design/tokens";
import { Text } from "@/components/primitives/Typography";

const swatches: { name: string; hex: string; usage: string }[] = [
  { name: "ink", hex: color.ink, usage: "primary text — 12.1:1 on paper" },
  { name: "ink-soft", hex: color.inkSoft, usage: "secondary text — 6.0:1 on paper" },
  { name: "paper", hex: color.paper, usage: "app background" },
  { name: "surface", hex: color.surface, usage: "panel background" },
  { name: "moss-600", hex: color.moss[600], usage: "primary action fill — 5.1:1 with white text" },
  { name: "moss-200", hex: color.moss[200], usage: "success / selected tint" },
  {
    name: "sky-700",
    hex: color.sky[700],
    usage: "focus ring, secondary action — 5.7:1 with white text",
  },
  { name: "sky-200", hex: color.sky[200], usage: "informational tint" },
  { name: "apricot-700", hex: color.apricot[700], usage: "accent action — 4.6:1 with white text" },
  { name: "apricot-200", hex: color.apricot[200], usage: "warm tint / highlight" },
  {
    name: "clay-700",
    hex: color.clay[700],
    usage: "'not yet' feedback — never red — 5.9:1 with white text",
  },
  { name: "clay-200", hex: color.clay[200], usage: "gentle retry tint" },
  { name: "sand-300", hex: color.sand[300], usage: "borders, choice-button idle" },
];

export function ColorSwatches() {
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
      {swatches.map((s) => (
        <div key={s.name} className="overflow-hidden rounded-xl border border-sand-300">
          <div className="h-16" style={{ backgroundColor: s.hex }} />
          <div className="bg-surface-raised p-3">
            <p className="font-sans text-sm font-bold text-ink">{s.name}</p>
            <p className="font-sans text-xs text-ink-soft">{s.hex}</p>
            <Text muted className="mt-1 text-xs">
              {s.usage}
            </Text>
          </div>
        </div>
      ))}
    </div>
  );
}
