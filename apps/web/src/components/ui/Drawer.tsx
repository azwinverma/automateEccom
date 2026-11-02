"use client";

import * as Dialog from "@radix-ui/react-dialog";
import type { ReactNode } from "react";
import { useI18n } from "@/i18n/I18nProvider";
import { Button } from "./Button";
import { Icon } from "./Icon";
import styles from "./Overlay.module.css";

export function Drawer({
  open,
  onOpenChange,
  title,
  description,
  footer,
  children,
  wide,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: ReactNode;
  description?: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
  wide?: boolean;
}) {
  const { t } = useI18n();
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className={styles.scrim} />
        <Dialog.Content
          className={[styles.drawer, wide && styles.wide].filter(Boolean).join(" ")}
          {...(description ? {} : { "aria-describedby": undefined })}
        >
          <div className={styles.header}>
            <div>
              <Dialog.Title className={styles.title}>{title}</Dialog.Title>
              {description ? <Dialog.Description className={styles.description}>{description}</Dialog.Description> : null}
            </div>
            <Dialog.Close asChild>
              <Button variant="ghost" size="sm" iconOnly aria-label={t("common.close")}>
                <Icon name="close" />
              </Button>
            </Dialog.Close>
          </div>
          <div className={styles.body}>{children}</div>
          {footer ? <div className={styles.footer}>{footer}</div> : null}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  body,
  confirmLabel,
  onConfirm,
  pending,
  destructive,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: ReactNode;
  body?: ReactNode;
  confirmLabel: string;
  onConfirm: () => void;
  pending?: boolean;
  destructive?: boolean;
  children?: ReactNode;
}) {
  const { t } = useI18n();
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className={styles.scrim} />
        <Dialog.Content className={styles.dialog} {...(body ? {} : { "aria-describedby": undefined })}>
          <div className={styles.dialogBody}>
            <Dialog.Title className={styles.title}>{title}</Dialog.Title>
            {body ? <Dialog.Description>{body}</Dialog.Description> : null}
            {children}
          </div>
          <div className={styles.footer}>
            <Dialog.Close asChild>
              <Button variant="ghost">{t("common.cancel")}</Button>
            </Dialog.Close>
            <Button variant={destructive ? "dangerSolid" : "primary"} onClick={onConfirm} loading={pending}>
              {confirmLabel}
            </Button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
