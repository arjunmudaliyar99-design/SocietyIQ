import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from "react";

export type ButtonVariant = "primary" | "secondary" | "danger";

const VARIANT: Record<ButtonVariant, string> = {
  primary: "bg-teal text-surface shadow-card hover:bg-teal-dark hover:shadow-raised active:bg-teal-dark border-2 border-teal",
  secondary: "bg-surface text-teal border-2 border-teal hover:bg-paper",
  danger: "bg-red text-surface border-2 border-red hover:brightness-90",
};

const BASE =
  "inline-flex items-center justify-center gap-2 rounded-lg px-5 font-semibold text-body " +
  "transition-[background-color,box-shadow,transform] duration-150 active:scale-[0.98] " +
  "focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-ink " +
  "disabled:cursor-not-allowed disabled:opacity-60 disabled:active:scale-100";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  icon?: ReactNode;
}

/** Min height 48 px (docs/03 §5). Icons always come with a label (docs/03 §1.3). */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = "primary", icon, className = "", children, type = "button", ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={`${BASE} min-h-[48px] py-2 ${VARIANT[variant]} ${className}`}
      {...rest}
    >
      {icon ? <span aria-hidden="true">{icon}</span> : null}
      <span>{children}</span>
    </button>
  );
});

/** Main action of a screen: min height 56 px, full width on phones (docs/03 §5). */
export const BigButton = forwardRef<HTMLButtonElement, ButtonProps>(function BigButton(
  { variant = "primary", icon, className = "", children, type = "button", ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={`${BASE} min-h-[56px] w-full py-3 text-section sm:w-auto sm:min-w-64 ${VARIANT[variant]} ${className}`}
      {...rest}
    >
      {icon ? <span aria-hidden="true">{icon}</span> : null}
      <span>{children}</span>
    </button>
  );
});
