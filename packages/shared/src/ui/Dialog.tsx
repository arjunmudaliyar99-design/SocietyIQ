import { X } from "lucide-react";
import { useEffect, useId, useRef, type ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { BigButton, Button } from "./Button";

interface DialogProps {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  /** Element focused when the dialog opens; defaults to the close button. */
  initialFocus?: React.RefObject<HTMLElement | null>;
}

/** Modal panel. Escape and the Close button both close it; focus returns where it was. */
export function Dialog({ open, title, onClose, children, initialFocus }: DialogProps) {
  const { t } = useTranslation();
  const titleId = useId();
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    (initialFocus?.current ?? closeRef.current)?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      previous?.focus();
    };
  }, [open, onClose, initialFocus]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-ink/60 p-3 sm:items-center">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-card bg-surface p-5"
      >
        <div className="mb-4 flex items-start justify-between gap-3">
          <h2 id={titleId} className="text-section font-bold">
            {title}
          </h2>
          <Button ref={closeRef} variant="secondary" icon={<X size={20} />} onClick={onClose}>
            {t("close")}
          </Button>
        </div>
        {children}
      </div>
    </div>
  );
}

export interface ConfirmDialogProps {
  open: boolean;
  /** Plain question, e.g. "Record ₹4,200 cash from Flat B-207?" (docs/03 §1.8). */
  question: string;
  confirmLabel: string;
  cancelLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

/** Two big buttons; the safe choice is on the left and gets focus first (docs/03 §5). */
export function ConfirmDialog({
  open,
  question,
  confirmLabel,
  cancelLabel,
  danger = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const { t } = useTranslation();
  const titleId = useId();
  const safeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    safeRef.current?.focus();
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onCancel();
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      previous?.focus();
    };
  }, [open, onCancel]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-ink/60 p-3 sm:items-center">
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="w-full max-w-lg rounded-card bg-surface p-5"
      >
        <h2 id={titleId} className="mb-5 text-section font-bold">
          {question}
        </h2>
        <div className="flex flex-col gap-3 sm:flex-row">
          <BigButton ref={safeRef} variant="secondary" onClick={onCancel}>
            {cancelLabel ?? t("confirm.no")}
          </BigButton>
          <BigButton variant={danger ? "danger" : "primary"} onClick={onConfirm}>
            {confirmLabel}
          </BigButton>
        </div>
      </div>
    </div>
  );
}
