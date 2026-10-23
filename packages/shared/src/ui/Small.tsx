import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { Button } from "./Button";

export interface EmptyStateProps {
  message: string;
  actionLabel?: string;
  onAction?: () => void;
  icon?: ReactNode;
}

/** Friendly sentence plus one action (docs/03 §5). */
export function EmptyState({ message, actionLabel, onAction, icon }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center gap-4 rounded-card border border-dashed border-line bg-surface p-8 text-center">
      {icon ? (
        <span aria-hidden="true" className="text-muted">
          {icon}
        </span>
      ) : null}
      <p className="text-body">{message}</p>
      {actionLabel && onAction ? <Button onClick={onAction}>{actionLabel}</Button> : null}
    </div>
  );
}

/** "Step 2 of 3" for multi-step forms (docs/03 §5). */
export function StepHeader({ current, total, title }: { current: number; total: number; title: string }) {
  const { t } = useTranslation();
  return (
    <header className="mb-4">
      <p className="text-small font-semibold text-muted">{t("step", { current, total })}</p>
      <h2 className="text-section font-bold">{title}</h2>
    </header>
  );
}
