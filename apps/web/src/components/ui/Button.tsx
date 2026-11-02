import Link from "next/link";
import { forwardRef, type ButtonHTMLAttributes, type ComponentProps, type ReactNode } from "react";
import styles from "./Button.module.css";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "dangerSolid";

interface CommonProps {
  variant?: ButtonVariant;
  size?: "sm" | "md";
  iconOnly?: boolean;
}

function cx(variant: ButtonVariant, size: "sm" | "md", iconOnly: boolean, extra?: string) {
  return [styles.button, styles[variant], size === "sm" && styles.sm, iconOnly && styles.iconOnly, extra]
    .filter(Boolean)
    .join(" ");
}

export const Button = forwardRef<
  HTMLButtonElement,
  CommonProps & ButtonHTMLAttributes<HTMLButtonElement> & { loading?: boolean; children?: ReactNode }
>(function Button({ variant = "secondary", size = "md", iconOnly = false, loading, className, children, disabled, type, ...rest }, ref) {
  return (
    <button
      ref={ref}
      type={type ?? "button"}
      className={cx(variant, size, iconOnly, className)}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {loading ? <span className={styles.spinner} aria-hidden="true" /> : null}
      {children}
    </button>
  );
});

export function ButtonLink({
  variant = "secondary",
  size = "md",
  iconOnly = false,
  className,
  ...rest
}: CommonProps & ComponentProps<typeof Link>) {
  return <Link className={cx(variant, size, iconOnly, className)} {...rest} />;
}
