import { useId, type SelectHTMLAttributes } from "react";

export interface SelectFieldProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label: string;
  help?: string;
  options: { value: string; label: string }[];
}

/** Native select with the label above, same look as Field (docs/03 §5). */
export function SelectField({ label, help, options, id, className = "", ...rest }: SelectFieldProps) {
  const autoId = useId();
  const selectId = id ?? autoId;
  const helpId = help ? `${selectId}-help` : undefined;
  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <label htmlFor={selectId} className="text-body font-semibold">
        {label}
      </label>
      <select
        id={selectId}
        aria-describedby={helpId}
        className="min-h-[48px] rounded-lg border-2 border-line bg-surface px-3 text-body focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-ink"
        {...rest}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      {help ? (
        <p id={helpId} className="text-small text-muted">
          {help}
        </p>
      ) : null}
    </div>
  );
}
