import { CircleAlert } from "lucide-react";
import { useId, type InputHTMLAttributes } from "react";

export interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  help?: string;
  /** Says what to do, e.g. "Phone number needs 10 digits" (docs/03 §1.10). */
  error?: string;
}

/** Label above the input, never placeholder-only; help below; error in red with an icon. */
export function Field({ label, help, error, id, className = "", ...rest }: FieldProps) {
  const autoId = useId();
  const inputId = id ?? autoId;
  const helpId = help ? `${inputId}-help` : undefined;
  const errorId = error ? `${inputId}-error` : undefined;
  const describedBy = [helpId, errorId].filter(Boolean).join(" ") || undefined;

  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <label htmlFor={inputId} className="text-body font-semibold">
        {label}
      </label>
      <input
        id={inputId}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        className={`min-h-[48px] rounded-lg border-2 bg-surface px-3 text-body focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-ink ${
          error ? "border-red" : "border-line"
        }`}
        {...rest}
      />
      {help ? (
        <p id={helpId} className="text-small text-muted">
          {help}
        </p>
      ) : null}
      {error ? (
        <p id={errorId} className="flex items-center gap-1 text-small font-semibold text-red">
          <CircleAlert size={18} aria-hidden="true" />
          {error}
        </p>
      ) : null}
    </div>
  );
}
