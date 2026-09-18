import type { MouthId } from "@/components/sprout/types";

export interface MouthPartProps {
  id: MouthId;
}

const CX = 120;
const CY = 148;

/** One of the rig's 6 reusable mouth paths. */
export function MouthPart({ id }: MouthPartProps) {
  switch (id) {
    case "worried":
      return <circle cx={CX} cy={CY + 2} r={5.5} fill="#3B2F24" opacity={0.85} />;
    case "flat":
      return (
        <line
          x1={CX - 13}
          y1={CY}
          x2={CX + 13}
          y2={CY}
          stroke="currentColor"
          strokeWidth={3}
          strokeLinecap="round"
        />
      );
    case "frown":
      return (
        <path
          d={`M ${CX - 14} ${CY + 5} Q ${CX} ${CY - 5} ${CX + 14} ${CY + 5}`}
          stroke="currentColor"
          strokeWidth={3}
          strokeLinecap="round"
          fill="none"
        />
      );
    case "smile":
      return (
        <path
          d={`M ${CX - 15} ${CY - 3} Q ${CX} ${CY + 8} ${CX + 15} ${CY - 3}`}
          stroke="currentColor"
          strokeWidth={3}
          strokeLinecap="round"
          fill="none"
        />
      );
    case "open":
      return (
        <path
          d={`M ${CX - 15} ${CY - 4} Q ${CX} ${CY + 12} ${CX + 15} ${CY - 4} Q ${CX} ${CY + 2} ${CX - 15} ${CY - 4} Z`}
          fill="#3B2F24"
          opacity={0.85}
        />
      );
    case "grin":
      return (
        <path
          d={`M ${CX - 20} ${CY - 6} Q ${CX} ${CY + 16} ${CX + 20} ${CY - 6} Q ${CX} ${CY + 2} ${CX - 20} ${CY - 6} Z`}
          fill="#3B2F24"
          opacity={0.85}
        />
      );
  }
}
