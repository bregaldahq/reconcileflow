import { ChevronDown } from "lucide-react";

import { statusDescriptions } from "../presentation";
import type { MatchStatus } from "../types";
import { StatusBadge } from "./StatusBadge";

const resultStatuses: MatchStatus[] = [
  "MATCHED",
  "SPLIT_MATCHED",
  "UNMATCHED",
  "AMBIGUOUS",
  "DUPLICATE",
  "MANUAL_REVIEW",
];

export function StatusGuide() {
  return (
    <details className="status-guide">
      <summary>
        O que significa cada etiqueta
        <ChevronDown size={16} aria-hidden="true" />
      </summary>
      <div className="status-guide__grid">
        {resultStatuses.map((status) => (
          <div key={status}>
            <StatusBadge status={status} />
            <p>{statusDescriptions[status]}</p>
          </div>
        ))}
      </div>
    </details>
  );
}
