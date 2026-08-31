import {
  CheckCircle2,
  Clock3,
  Copy,
  GitFork,
  GitMerge,
  LoaderCircle,
  SearchX,
  UserRoundSearch,
  XCircle,
} from "lucide-react";

import type { MatchStatus, RunStatus } from "../types";
import { allStatusLabels, statusDescriptions } from "../presentation";

const icons = {
  MATCHED: CheckCircle2,
  SPLIT_MATCHED: GitMerge,
  UNMATCHED: SearchX,
  AMBIGUOUS: GitFork,
  DUPLICATE: Copy,
  MANUAL_REVIEW: UserRoundSearch,
  PENDING: Clock3,
  QUEUED: Clock3,
  RUNNING: LoaderCircle,
  COMPLETED: CheckCircle2,
  FAILED: XCircle,
};

export function StatusBadge({ status }: { status: MatchStatus | RunStatus }) {
  const Icon = icons[status];
  return (
    <span
      className={`status-badge status-badge--${status.toLowerCase()}`}
      title={statusDescriptions[status]}
      aria-label={`${allStatusLabels[status]}. ${statusDescriptions[status]}`}
    >
      <Icon
        className={status === "RUNNING" ? "spin" : undefined}
        size={13}
        aria-hidden="true"
      />
      <span>{allStatusLabels[status]}</span>
    </span>
  );
}
