import type { HTMLAttributes, ReactNode } from "react";

export function Card({ className = "", children, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`rounded-card border border-line bg-surface p-5 ${className}`} {...rest}>
      {children}
    </div>
  );
}

export interface StatCardProps {
  label: string;
  value: ReactNode;
  note?: string;
  onClick?: () => void;
}

/** Label on top, big number, one line of explanation; the whole card is tappable (docs/03 §5). */
export function StatCard({ label, value, note, onClick }: StatCardProps) {
  const body = (
    <>
      <span className="block text-body text-muted">{label}</span>
      <span className="tabular mt-1 block text-stat font-bold">{value}</span>
      {note ? <span className="mt-1 block text-small text-muted">{note}</span> : null}
    </>
  );
  if (!onClick) return <Card>{body}</Card>;
  return (
    <button
      type="button"
      onClick={onClick}
      className="block w-full rounded-card border border-line bg-surface p-5 text-left hover:border-teal focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-ink"
    >
      {body}
    </button>
  );
}
