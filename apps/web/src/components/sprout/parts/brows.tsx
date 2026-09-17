import type { BrowId } from "@/components/sprout/types";

export interface BrowPartProps {
  id: BrowId;
}

const LEFT_X = 92;
const RIGHT_X = 148;
const CY = 76;

/** One of the rig's 4 reusable brow paths — never the only signal for an expression, but always distinct. */
export function BrowPart({ id }: BrowPartProps) {
  switch (id) {
    case "furrowed":
      return (
        <g stroke="currentColor" strokeWidth={3} strokeLinecap="round">
          <line x1={LEFT_X - 10} y1={CY - 2} x2={LEFT_X + 9} y2={CY + 5} />
          <line x1={RIGHT_X - 9} y1={CY + 5} x2={RIGHT_X + 10} y2={CY - 2} />
        </g>
      );
    case "flat":
      return (
        <g stroke="currentColor" strokeWidth={3} strokeLinecap="round">
          <line x1={LEFT_X - 10} y1={CY} x2={LEFT_X + 10} y2={CY} />
          <line x1={RIGHT_X - 10} y1={CY} x2={RIGHT_X + 10} y2={CY} />
        </g>
      );
    case "quizzical":
      return (
        <g stroke="currentColor" strokeWidth={3} strokeLinecap="round" fill="none">
          <line x1={LEFT_X - 10} y1={CY + 3} x2={LEFT_X + 10} y2={CY + 1} />
          <path d={`M ${RIGHT_X - 10} ${CY} Q ${RIGHT_X} ${CY - 8} ${RIGHT_X + 10} ${CY - 4}`} />
        </g>
      );
    case "raised":
      return (
        <g stroke="currentColor" strokeWidth={3} strokeLinecap="round" fill="none">
          <path d={`M ${LEFT_X - 10} ${CY + 2} Q ${LEFT_X} ${CY - 9} ${LEFT_X + 10} ${CY - 3}`} />
          <path
            d={`M ${RIGHT_X - 10} ${CY - 3} Q ${RIGHT_X} ${CY - 9} ${RIGHT_X + 10} ${CY + 2}`}
          />
        </g>
      );
  }
}
