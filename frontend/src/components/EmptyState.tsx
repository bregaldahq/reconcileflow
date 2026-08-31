import type { ReactNode } from "react";

export function EmptyState({
  title,
  copy,
  action,
}: {
  title: string;
  copy: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <strong>{title}</strong>
      <p>{copy}</p>
      {action}
    </div>
  );
}
