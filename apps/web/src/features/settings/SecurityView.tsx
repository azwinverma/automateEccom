"use client";

import { isApiError, type Session, type TotpSetup } from "@commerce-os/api-client";
import { useEffect, useState, type FormEvent } from "react";
import { EmptyState, QueryError, TableSkeleton } from "@/components/states/States";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/Drawer";
import { Checkbox, TextField } from "@/components/ui/Field";
import { Icon } from "@/components/ui/Icon";
import { Badge, InlineAlert, PageHeader, RequestId, SectionHeader, useToast } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { errorMessage } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import styles from "./settings.module.css";

function ActionError({ error }: { error: unknown }) {
  const { t } = useI18n();
  if (!error) return null;
  return (
    <InlineAlert tone="danger">
      {errorMessage(t, error)}
      <RequestId id={isApiError(error) ? error.requestId : null} />
    </InlineAlert>
  );
}

function Sessions() {
  const { t, relative, dateTime, date } = useI18n();
  const { api } = useAuth();
  const toast = useToast();
  const sessions = useApiQuery((a) => a.auth.sessions());
  const [confirmAll, setConfirmAll] = useState(false);
  const [revoking, setRevoking] = useState<string | null>(null);
  const revoke = useAction();
  const revokeAll = useAction();

  const revokeOne = async (s: Session) => {
    setRevoking(s.id);
    const ok = await revoke.run(async () => {
      await api.auth.revokeSession(s.id);
      return true;
    });
    setRevoking(null);
    if (ok) {
      sessions.setData((d) => ({ items: d.items.filter((x) => x.id !== s.id) }));
      toast(t("security.sessionRevoked"));
    }
  };

  const doRevokeAll = async () => {
    const ok = await revokeAll.run(async () => {
      await api.auth.revokeOtherSessions();
      return true;
    });
    if (ok) {
      sessions.setData((d) => ({ items: d.items.filter((x) => x.current) }));
      setConfirmAll(false);
      toast(t("security.othersRevoked"));
    }
  };

  const others = sessions.state.status === "success" ? sessions.state.data.items.filter((s) => !s.current).length : 0;

  return (
    <>
      <SectionHeader
        title={t("security.sessionsHeading")}
        id="sessions-heading"
        action={
          others > 0 ? (
            <Button
              size="sm"
              variant="danger"
              onClick={() => {
                revokeAll.clear();
                setConfirmAll(true);
              }}
            >
              {t("security.revokeOthers")}
            </Button>
          ) : null
        }
      />
      <ActionError error={revoke.error} />
      {sessions.state.status === "loading" ? (
        <TableSkeleton columns="2fr 1fr 1fr 1fr 80px" rows={3} label={t("common.loading")} />
      ) : sessions.state.status === "error" ? (
        <QueryError error={sessions.state.error} onRetry={sessions.reload} />
      ) : sessions.state.data.items.length === 0 ? (
        <EmptyState title={t("security.sessionsEmpty")} />
      ) : (
        <div className={table.wrap}>
          <table className={table.table} aria-labelledby="sessions-heading">
            <thead>
              <tr>
                <th scope="col">{t("security.colDevice")}</th>
                <th scope="col" className={table.hideSm}>
                  {t("security.colIp")}
                </th>
                <th scope="col">{t("security.colLastUsed")}</th>
                <th scope="col" className={table.hideSm}>
                  {t("security.colCreated")}
                </th>
                <th scope="col" className={table.actions}>
                  <span className="srOnly">{t("common.actions")}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {[...sessions.state.data.items]
                .sort((a, b) => Number(b.current) - Number(a.current))
                .map((s) => (
                  <tr key={s.id}>
                    <td>
                      <div className={table.primaryCell}>
                        <strong>{s.device_name || t("security.unknownDevice")}</strong>
                        {s.user_agent ? <span title={s.user_agent}>{s.user_agent.slice(0, 60)}</span> : null}
                      </div>
                    </td>
                    <td className={[table.hideSm, table.mono].join(" ")}>{s.ip ?? t("common.none")}</td>
                    <td>
                      {s.current ? (
                        <Badge tone="success">{t("security.thisDevice")}</Badge>
                      ) : s.last_used_at ? (
                        <time dateTime={s.last_used_at} title={dateTime(s.last_used_at)}>
                          {relative(s.last_used_at)}
                        </time>
                      ) : (
                        t("common.none")
                      )}
                    </td>
                    <td className={[table.hideSm, table.muted].join(" ")}>{date(s.created_at)}</td>
                    <td className={table.actions}>
                      {s.current ? null : (
                        <Button
                          size="sm"
                          variant="ghost"
                          loading={revoking === s.id}
                          onClick={() => revokeOne(s)}
                          aria-label={`${t("security.revoke")}: ${s.device_name ?? t("security.unknownDevice")}`}
                        >
                          {t("security.revoke")}
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      )}
      <ConfirmDialog
        open={confirmAll}
        onOpenChange={setConfirmAll}
        title={t("security.revokeOthersTitle")}
        body={t("security.revokeOthersBody")}
        confirmLabel={t("security.revokeOthers")}
        onConfirm={doRevokeAll}
        pending={revokeAll.pending}
        destructive
      >
        <ActionError error={revokeAll.error} />
      </ConfirmDialog>
    </>
  );
}

function RecoveryCodes({ codes, onDone }: { codes: string[]; onDone: () => void }) {
  const { t } = useI18n();
  const [ack, setAck] = useState(false);
  const [copied, setCopied] = useState(false);
  const text = `${t("security.recoveryFileHeader")}\n\n${codes.join("\n")}\n`;

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(codes.join("\n"));
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };
  const download = () => {
    const url = URL.createObjectURL(new Blob([text], { type: "text/plain;charset=utf-8" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "commerce-os-recovery-codes.txt";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className={styles.stack} style={{ padding: "var(--space-5) 0" }}>
      <InlineAlert tone="warning" title={t("security.recoveryTitle")}>
        {t("security.recoveryBody")}
      </InlineAlert>
      <ul className={styles.codes} aria-label={t("security.recoveryTitle")}>
        {codes.map((c) => (
          <li key={c}>{c}</li>
        ))}
      </ul>
      <div className={styles.inlineActions}>
        <Button size="sm" onClick={copy}>
          <Icon name={copied ? "check" : "copy"} />
          {copied ? t("common.copied") : t("security.recoveryCopy")}
        </Button>
        <Button size="sm" onClick={download}>
          <Icon name="download" />
          {t("security.recoveryDownload")}
        </Button>
      </div>
      <Checkbox label={t("security.recoveryAck")} checked={ack} onChange={(e) => setAck(e.target.checked)} />
      <div>
        <Button variant="primary" disabled={!ack} onClick={onDone}>
          {t("security.recoveryDone")}
        </Button>
      </div>
    </div>
  );
}

function Mfa() {
  const { t } = useI18n();
  const { api, me, reloadMe } = useAuth();
  const toast = useToast();
  const [setup, setSetup] = useState<TotpSetup | null>(null);
  const [qr, setQr] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [codes, setCodes] = useState<string[] | null>(null);
  const [disableOpen, setDisableOpen] = useState(false);
  const [disableCode, setDisableCode] = useState("");
  const [password, setPassword] = useState("");
  const start = useAction();
  const enable = useAction();
  const disable = useAction();

  useEffect(() => {
    if (!setup) {
      setQr(null);
      return;
    }
    let cancelled = false;
    import("qrcode")
      .then((QR) => QR.toDataURL(setup.otpauth_uri, { margin: 1, width: 320, color: { dark: "#0F172A", light: "#FFFFFF" } }))
      .then((url) => !cancelled && setQr(url))
      .catch(() => !cancelled && setQr(null));
    return () => {
      cancelled = true;
    };
  }, [setup]);

  if (!me) return null;
  const enabled = me.user.mfa_enabled;

  const begin = async () => {
    const s = await start.run(() => api.auth.totpSetup());
    if (s) setSetup(s);
  };

  const confirm = async (e: FormEvent) => {
    e.preventDefault();
    const clean = code.replace(/\s+/g, "");
    if (!/^\d{6}$/.test(clean)) return;
    const res = await enable.run(() => api.auth.totpEnable(clean));
    if (res) {
      setSetup(null);
      setCode("");
      setCodes(res.recovery_codes);
    }
  };

  const doDisable = async () => {
    const ok = await disable.run(async () => {
      await api.auth.totpDisable(disableCode.replace(/\s+/g, ""), password);
      return true;
    });
    if (ok) {
      setDisableOpen(false);
      setDisableCode("");
      setPassword("");
      await reloadMe();
      toast(t("security.mfaDisabled"));
    }
  };

  return (
    <>
      <SectionHeader title={t("security.mfaHeading")} />
      <div className={styles.mfaRow}>
        <div className={styles.mfaText}>
          <span>
            <Badge tone={enabled ? "success" : "neutral"}>{enabled ? t("security.mfaOn") : t("security.mfaOff")}</Badge>
          </span>
          <p>{enabled ? t("security.mfaOnBody") : t("security.mfaOffBody")}</p>
        </div>
        {codes ? null : enabled ? (
          <Button
            variant="danger"
            onClick={() => {
              disable.clear();
              setDisableOpen(true);
            }}
          >
            {t("security.mfaDisable")}
          </Button>
        ) : setup ? null : (
          <Button variant="primary" onClick={begin} loading={start.pending}>
            {start.pending ? t("security.mfaStarting") : t("security.mfaSetup")}
          </Button>
        )}
      </div>
      <ActionError error={start.error} />

      {setup ? (
        <form className={styles.mfaSetup} onSubmit={confirm} noValidate>
          <div>
            {qr ? (
              // eslint-disable-next-line @next/next/no-img-element -- data URL generated locally
              <img className={styles.qr} src={qr} alt={t("security.mfaQrAlt")} width={176} height={176} />
            ) : (
              <div className={styles.qr} aria-hidden="true" />
            )}
          </div>
          <div className={styles.stack}>
            <p>{t("security.mfaScan")}</p>
            <div>
              <p style={{ color: "var(--text-secondary)", fontSize: "var(--font-size-sm)", marginBottom: "var(--space-1)" }}>
                {t("security.mfaManual")}
              </p>
              <code className={styles.secret}>{setup.secret}</code>
            </div>
            <ActionError error={enable.error} />
            <TextField
              label={t("security.mfaCode")}
              value={code}
              onChange={(e) => setCode(e.target.value)}
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              mono
              style={{ maxWidth: 180 }}
            />
            <div className={styles.inlineActions}>
              <Button type="submit" variant="primary" loading={enable.pending} disabled={!/^\d{6}$/.test(code.replace(/\s+/g, ""))}>
                {enable.pending ? t("security.mfaConfirming") : t("security.mfaConfirm")}
              </Button>
              <Button
                variant="ghost"
                onClick={() => {
                  setSetup(null);
                  setCode("");
                  enable.clear();
                }}
              >
                {t("security.mfaCancel")}
              </Button>
            </div>
          </div>
        </form>
      ) : null}

      {codes ? (
        <RecoveryCodes
          codes={codes}
          onDone={async () => {
            setCodes(null);
            await reloadMe();
            toast(t("security.mfaEnabled"));
          }}
        />
      ) : null}

      <ConfirmDialog
        open={disableOpen}
        onOpenChange={setDisableOpen}
        title={t("security.mfaDisableTitle")}
        body={t("security.mfaDisableBody")}
        confirmLabel={t("security.mfaDisable")}
        onConfirm={doDisable}
        pending={disable.pending}
        destructive
      >
        <ActionError error={disable.error} />
        <TextField
          label={t("security.mfaCode")}
          value={disableCode}
          onChange={(e) => setDisableCode(e.target.value)}
          inputMode="numeric"
          autoComplete="one-time-code"
          mono
        />
        <TextField
          label={t("security.password")}
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </ConfirmDialog>
    </>
  );
}

export function SecurityView() {
  const { t } = useI18n();
  return (
    <>
      <PageHeader level={2} title={t("security.title")} subtitle={t("security.subtitle")} />
      <Mfa />
      <Sessions />
    </>
  );
}
