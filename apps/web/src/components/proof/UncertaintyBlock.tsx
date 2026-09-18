import { Subheading, Text } from "@/components/primitives/Typography";

/**
 * "NOT YET CONFIRMED" (roadmap P20: mandatory, never empty — "a report
 * with no uncertainty is a report that is lying"). The API guarantees
 * `caveats` is never an empty array; this component renders nothing only
 * if that contract is somehow violated, rather than inventing a caveat of
 * its own — a UI bug should be visible, not silently patched over.
 */
export function UncertaintyBlock({
  caveats,
  className,
}: {
  caveats: string[];
  className?: string;
}) {
  if (caveats.length === 0) return null;

  return (
    <div className={className}>
      <Subheading as="h3" className="flex items-center gap-2 text-base text-apricot-700">
        <span aria-hidden>⚠</span> Not yet confirmed
      </Subheading>
      <ul className="mt-1.5 flex flex-col gap-1">
        {caveats.map((caveat, i) => (
          <li key={i}>
            <Text className="text-sm text-ink-soft">{caveat}</Text>
          </li>
        ))}
      </ul>
    </div>
  );
}
