import { X } from "lucide-react";
import { useEffect } from "react";
import { useTranslation } from "react-i18next";

/** Older readers need time; never hide a message sooner than this (docs/03 §5). */
export const MIN_TOAST_MS = 6000;

export interface ToastProps {
  message: string;
  /** e.g. "Made a mistake? Reverse it" after a money action (docs/03 §1.9). */
  actionLabel?: string;
  onAction?: () => void;
  onClose: () => void;
  durationMs?: number;
}

export function Toast({ message, actionLabel, onAction, onClose, durationMs = 8000 }: ToastProps) {
  const { t } = useTranslation();
  const duration = Math.max(durationMs, MIN_TOAST_MS);

  useEffect(() => {
    const timer = window.setTimeout(onClose, duration);
    return () => window.clearTimeout(timer);
  }, [duration, onClose]);

  return (
    <div
      role="status"
      className="fixed inset-x-3 bottom-3 z-40 mx-auto flex max-w-lg flex-wrap items-center gap-3 rounded-card bg-ink p-4 text-surface sm:inset-x-auto sm:right-6 sm:bottom-6"
    >
      <p className="flex-1 text-body">{message}</p>
      {actionLabel && onAction ? (
        <button
          type="button"
          onClick={onAction}
          className="min-h-[48px] rounded-lg border-2 border-mint px-4 font-semibold text-mint focus-visible:outline-3 focus-visible:outline-mint"
        >
          {actionLabel}
        </button>
      ) : null}
      <button
        type="button"
        onClick={onClose}
        aria-label={t("toast.close")}
        className="flex min-h-[48px] min-w-[48px] items-center justify-center rounded-lg focus-visible:outline-3 focus-visible:outline-mint"
      >
        <X size={22} aria-hidden="true" />
      </button>
    </div>
  );
}
