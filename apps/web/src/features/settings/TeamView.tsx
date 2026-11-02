"use client";

import { ROLES, isApiError, type Invitation, type Member, type Role } from "@commerce-os/api-client";
import { useState, type FormEvent } from "react";
import { LimitActions } from "@/components/commerce/UsageMeter";
import { DegradedBanner, EmptyState, QueryError, TableSkeleton, isPermissionDenied } from "@/components/states/States";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog, Drawer } from "@/components/ui/Drawer";
import { TextField } from "@/components/ui/Field";
import { Icon } from "@/components/ui/Icon";
import { MenuContent, MenuItem, MenuRoot, MenuTrigger } from "@/components/ui/Menu";
import { Badge, InlineAlert, PageHeader, RequestId, SectionHeader, useToast, type Tone } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { errorMessage, fieldErrorMessages } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction, useApiQuery, useIdempotencyKey } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { parseLimitOptions } from "@/lib/usage";
import { EMAIL_RE } from "@/lib/validation";
import styles from "./settings.module.css";

const INVITABLE: Role[] = ROLES.filter((r) => r !== "owner");

function statusTone(status: string): Tone {
  if (status === "active" || status === "accepted") return "success";
  if (status === "invited" || status === "pending") return "info";
  if (status === "suspended" || status === "revoked" || status === "expired") return "neutral";
  return "neutral";
}

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

function RoleOptions({ value, onChange, roles, name }: { value: Role; onChange: (r: Role) => void; roles: readonly Role[]; name: string }) {
  const { t } = useI18n();
  return (
    <fieldset className={styles.roleOptions}>
      <legend>{t("team.inviteRole")}</legend>
      {roles.map((r) => (
        <label key={r} className={styles.roleOption}>
          <input type="radio" name={name} value={r} checked={value === r} onChange={() => onChange(r)} />
          <strong>{t(`shell.role.${r}`)}</strong>
          <span>{t(`team.roleHelp.${r}`)}</span>
        </label>
      ))}
    </fieldset>
  );
}

function InviteDrawer({ open, onOpenChange, onInvited }: { open: boolean; onOpenChange: (o: boolean) => void; onInvited: (email: string) => void }) {
  const { t, number } = useI18n();
  const { api, membership } = useAuth();
  const { keyFor, reset } = useIdempotencyKey();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Role>("staff");
  const [emailError, setEmailError] = useState<string | null>(null);
  const action = useAction();

  const close = (o: boolean) => {
    if (!o) {
      setEmail("");
      setRole("staff");
      setEmailError(null);
      action.clear();
    }
    onOpenChange(o);
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!EMAIL_RE.test(email.trim())) {
      setEmailError(t("errors.field.email"));
      return;
    }
    setEmailError(null);
    const body = { email: email.trim().toLowerCase(), role };
    const ok = await action.run(async () => {
      await api.team.invite(body, { idempotencyKey: keyFor(body) });
      return true;
    });
    if (ok) {
      reset();
      onInvited(body.email);
      close(false);
    }
  };

  const err = action.error;
  const limit = isApiError(err) && err.code === "usage_limit_reached" ? err.details : null;
  const fieldErr = isApiError(err) && err.code === "validation_error" ? fieldErrorMessages(t, err.fieldErrors()).email : null;

  return (
    <Drawer
      open={open}
      onOpenChange={close}
      title={t("team.inviteTitle", { business: membership?.merchant.name ?? "" })}
      description={t("team.inviteBody")}
      footer={
        <>
          <Button variant="ghost" onClick={() => close(false)}>
            {t("common.cancel")}
          </Button>
          <Button variant="primary" type="submit" form="invite-form" loading={action.pending} disabled={Boolean(limit)}>
            {action.pending ? t("team.inviteSending") : t("team.inviteSubmit")}
          </Button>
        </>
      }
    >
      <form id="invite-form" className={styles.stack} onSubmit={submit} noValidate>
        {limit ? (
          <InlineAlert tone="warning" title={t("team.limitTitle")}>
            {typeof limit.used === "number" && typeof limit.limit === "number" ? (
              <span>{t("team.limitBody", { used: number(limit.used), limit: number(limit.limit) })}</span>
            ) : null}
            {/* Seats are a gauge: no "renews" date; the server's options decide the actions. */}
            <LimitActions
              buyCredits={parseLimitOptions(limit.options).includes("buy_credits")}
              upgrade={parseLimitOptions(limit.options).includes("upgrade")}
            />
            <RequestId id={isApiError(err) ? err.requestId : null} />
          </InlineAlert>
        ) : err && !fieldErr ? (
          <ActionError error={err} />
        ) : null}
        <TextField
          label={t("team.inviteEmail")}
          type="email"
          autoComplete="off"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            if (limit) action.clear();
          }}
          error={emailError ?? fieldErr}
          required
          autoFocus
        />
        <RoleOptions value={role} onChange={setRole} roles={INVITABLE} name="invite-role" />
      </form>
    </Drawer>
  );
}

export function TeamView() {
  const { t, date } = useI18n();
  const { api, me, membership, can } = useAuth();
  const toast = useToast();
  const members = useApiQuery((a) => a.team.members());
  const invitations = useApiQuery((a) => a.team.invitations());
  const canManage = can("team.manage");
  const business = membership?.merchant.name ?? "";

  const [inviteOpen, setInviteOpen] = useState(false);
  const [roleTarget, setRoleTarget] = useState<Member | null>(null);
  const [newRole, setNewRole] = useState<Role>("staff");
  const [removeTarget, setRemoveTarget] = useState<Member | null>(null);
  const [revokeTarget, setRevokeTarget] = useState<Invitation | null>(null);
  const roleAction = useAction();
  const removeAction = useAction();
  const revokeAction = useAction();

  const displayName = (m: Member) => m.user.full_name || m.user.email;

  const saveRole = async () => {
    if (!roleTarget) return;
    const ok = await roleAction.run(async () => {
      await api.team.changeRole(roleTarget.id, newRole);
      return true;
    });
    if (ok) {
      members.setData((d) => ({ items: d.items.map((m) => (m.id === roleTarget.id ? { ...m, role: newRole } : m)) }));
      setRoleTarget(null);
      toast(t("team.roleSaved"));
    }
  };

  const removeMember = async () => {
    if (!removeTarget) return;
    const ok = await removeAction.run(async () => {
      await api.team.removeMember(removeTarget.id);
      return true;
    });
    if (ok) {
      members.setData((d) => ({ items: d.items.filter((m) => m.id !== removeTarget.id) }));
      toast(t("team.memberRemoved", { name: displayName(removeTarget) }));
      setRemoveTarget(null);
    }
  };

  const revokeInvite = async () => {
    if (!revokeTarget) return;
    const ok = await revokeAction.run(async () => {
      await api.team.revokeInvitation(revokeTarget.id);
      return true;
    });
    if (ok) {
      invitations.setData((d) => ({ items: d.items.filter((i) => i.id !== revokeTarget.id) }));
      toast(t("team.invitationRevoked"));
      setRevokeTarget(null);
    }
  };

  const pendingInvites =
    invitations.state.status === "success"
      ? invitations.state.data.items.filter((i) => !i.status || i.status === "pending")
      : [];

  return (
    <>
      <PageHeader
        level={2}
        title={t("team.title")}
        subtitle={t("team.subtitle", { business })}
        actions={
          canManage ? (
            <Button variant="primary" onClick={() => setInviteOpen(true)}>
              <Icon name="plus" />
              {t("team.invite")}
            </Button>
          ) : null
        }
      />

      <SectionHeader title={t("team.membersHeading")} id="members-heading" />
      {members.state.status === "loading" ? (
        <TableSkeleton columns="2fr 1fr 1fr 1fr 40px" label={t("common.loading")} />
      ) : members.state.status === "error" ? (
        <QueryError error={members.state.error} onRetry={members.reload} />
      ) : members.state.data.items.length === 0 ? (
        <EmptyState title={t("team.membersEmpty")} />
      ) : (
        <div className={table.wrap}>
          <table className={table.table} aria-labelledby="members-heading">
            <thead>
              <tr>
                <th scope="col">{t("team.colName")}</th>
                <th scope="col">{t("team.colRole")}</th>
                <th scope="col" className={table.hideSm}>
                  {t("team.colStatus")}
                </th>
                <th scope="col" className={table.hideSm}>
                  {t("team.colJoined")}
                </th>
                <th scope="col" className={table.actions}>
                  <span className="srOnly">{t("common.actions")}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {members.state.data.items.map((m) => {
                const isMe = m.user.id === me?.user.id;
                return (
                  <tr key={m.id}>
                    <td>
                      <div className={table.primaryCell}>
                        <strong>
                          {displayName(m)}
                          {isMe ? ` · ${t("common.you")}` : ""}
                        </strong>
                        <span>{m.user.email}</span>
                      </div>
                    </td>
                    <td>{t(`shell.role.${m.role}`)}</td>
                    <td className={table.hideSm}>
                      <Badge tone={statusTone(m.status)}>{t.dynamic(`team.status.${m.status}`) ?? m.status}</Badge>
                    </td>
                    <td className={[table.hideSm, table.muted].join(" ")}>{m.joined_at ? date(m.joined_at) : t("common.none")}</td>
                    <td className={table.actions}>
                      {canManage ? (
                        <MenuRoot>
                          <MenuTrigger asChild>
                            <Button variant="ghost" size="sm" iconOnly aria-label={`${t("common.actions")}: ${displayName(m)}`}>
                              <Icon name="more" />
                            </Button>
                          </MenuTrigger>
                          <MenuContent align="end">
                            <MenuItem
                              onSelect={() => {
                                roleAction.clear();
                                setNewRole(m.role);
                                setRoleTarget(m);
                              }}
                            >
                              {t("team.changeRole")}
                            </MenuItem>
                            <MenuItem
                              danger
                              onSelect={() => {
                                removeAction.clear();
                                setRemoveTarget(m);
                              }}
                            >
                              {t("team.removeMember")}
                            </MenuItem>
                          </MenuContent>
                        </MenuRoot>
                      ) : null}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <SectionHeader title={t("team.invitationsHeading")} id="invites-heading" />
      {invitations.state.status === "loading" ? (
        <TableSkeleton columns="2fr 1fr 1fr 1fr 80px" rows={2} label={t("common.loading")} />
      ) : invitations.state.status === "error" ? (
        isPermissionDenied(invitations.state.error) ? (
          <p className={table.empty}>{t("team.invitationsHidden")}</p>
        ) : (
          <DegradedBanner errors={[invitations.state.error]} onRetry={invitations.reload} />
        )
      ) : pendingInvites.length === 0 ? (
        <p className={table.empty}>{t("team.invitationsEmpty")}</p>
      ) : (
        <div className={table.wrap}>
          <table className={table.table} aria-labelledby="invites-heading">
            <thead>
              <tr>
                <th scope="col">{t("team.colEmail")}</th>
                <th scope="col">{t("team.colRole")}</th>
                <th scope="col" className={table.hideSm}>
                  {t("team.colInvited")}
                </th>
                <th scope="col" className={table.hideSm}>
                  {t("team.colExpires")}
                </th>
                <th scope="col" className={table.actions}>
                  <span className="srOnly">{t("common.actions")}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {pendingInvites.map((inv) => (
                <tr key={inv.id}>
                  <td>{inv.email}</td>
                  <td>{t(`shell.role.${inv.role}`)}</td>
                  <td className={[table.hideSm, table.muted].join(" ")}>{inv.created_at ? date(inv.created_at) : t("common.none")}</td>
                  <td className={[table.hideSm, table.muted].join(" ")}>{inv.expires_at ? date(inv.expires_at) : t("common.none")}</td>
                  <td className={table.actions}>
                    {canManage ? (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => {
                          revokeAction.clear();
                          setRevokeTarget(inv);
                        }}
                        aria-label={`${t("team.revokeInvite")}: ${inv.email}`}
                      >
                        {t("team.revokeInvite")}
                      </Button>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <InviteDrawer
        open={inviteOpen}
        onOpenChange={setInviteOpen}
        onInvited={(email) => {
          toast(t("team.inviteSent", { email }));
          invitations.reload();
        }}
      />

      <ConfirmDialog
        open={roleTarget !== null}
        onOpenChange={(o) => !o && setRoleTarget(null)}
        title={roleTarget ? t("team.roleTitle", { name: displayName(roleTarget) }) : ""}
        confirmLabel={t("common.save")}
        onConfirm={saveRole}
        pending={roleAction.pending}
      >
        <ActionError error={roleAction.error} />
        <RoleOptions value={newRole} onChange={setNewRole} roles={ROLES} name="member-role" />
      </ConfirmDialog>

      <ConfirmDialog
        open={removeTarget !== null}
        onOpenChange={(o) => !o && setRemoveTarget(null)}
        title={removeTarget ? t("team.removeTitle", { name: displayName(removeTarget) }) : ""}
        body={t("team.removeBody", { business })}
        confirmLabel={t("common.remove")}
        onConfirm={removeMember}
        pending={removeAction.pending}
        destructive
      >
        <ActionError error={removeAction.error} />
      </ConfirmDialog>

      <ConfirmDialog
        open={revokeTarget !== null}
        onOpenChange={(o) => !o && setRevokeTarget(null)}
        title={revokeTarget ? t("team.revokeTitle", { email: revokeTarget.email }) : ""}
        body={t("team.revokeBody")}
        confirmLabel={t("common.revoke")}
        onConfirm={revokeInvite}
        pending={revokeAction.pending}
        destructive
      >
        <ActionError error={revokeAction.error} />
      </ConfirmDialog>
    </>
  );
}
