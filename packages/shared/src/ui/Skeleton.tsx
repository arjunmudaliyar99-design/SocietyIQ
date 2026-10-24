import { useTranslation } from "react-i18next";

/** Grey placeholder that shimmers while data loads; screen readers hear "Loading". */
export function Skeleton({ className = "" }: { className?: string }) {
  return <span aria-hidden="true" className={`siq-skeleton block rounded-lg ${className}`} />;
}

/** A few card-shaped placeholders: the page keeps its shape while loading (docs/03: calm UI). */
export function LoadingBlock({ rows = 3 }: { rows?: number }) {
  const { t } = useTranslation();
  return (
    <div role="status" aria-live="polite" className="flex flex-col gap-3">
      <span className="sr-only">{t("loading")}</span>
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="rounded-card border border-line bg-surface p-5 shadow-card">
          <Skeleton className="mb-3 h-5 w-1/3" />
          <Skeleton className="h-4 w-2/3" />
        </div>
      ))}
    </div>
  );
}
