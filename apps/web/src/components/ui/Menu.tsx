"use client";

import * as DM from "@radix-ui/react-dropdown-menu";
import type { ComponentProps, ReactNode } from "react";
import styles from "./Menu.module.css";

export const MenuRoot = DM.Root;
export const MenuTrigger = DM.Trigger;

export function MenuContent({ children, align = "start", ...rest }: ComponentProps<typeof DM.Content>) {
  return (
    <DM.Portal>
      <DM.Content className={styles.content} align={align} sideOffset={4} collisionPadding={8} {...rest}>
        {children}
      </DM.Content>
    </DM.Portal>
  );
}

export function MenuItem({ danger, children, ...rest }: { danger?: boolean; children: ReactNode } & ComponentProps<typeof DM.Item>) {
  return (
    <DM.Item className={[styles.item, danger && styles.danger].filter(Boolean).join(" ")} {...rest}>
      {children}
    </DM.Item>
  );
}

export function MenuLabel({ children }: { children: ReactNode }) {
  return <DM.Label className={styles.label}>{children}</DM.Label>;
}

export function MenuSeparator() {
  return <DM.Separator className={styles.separator} />;
}

export function MenuRadioGroup(props: ComponentProps<typeof DM.RadioGroup>) {
  return <DM.RadioGroup {...props} />;
}

export function MenuRadioItem({ children, ...rest }: { children: ReactNode } & ComponentProps<typeof DM.RadioItem>) {
  return (
    <DM.RadioItem className={styles.item} {...rest}>
      {children}
      <DM.ItemIndicator className={styles.indicator}>✓</DM.ItemIndicator>
    </DM.RadioItem>
  );
}
