"use client";

import { isApiError, type ChannelListing, type ProductDetail } from "@commerce-os/api-client";
import { useState } from "react";
import { QueryError, TableSkeleton } from "@/components/states/States";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Badge, InlineAlert, RequestId, useToast, type Tone } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { errorMessage } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { usePolling } from "@/lib/usePolling";
import wf from "../shared/workflow.module.css";

const TONE: Record<string, Tone> = { published: "success", failed: "danger", out_of_sync: "warning", pending: "info", publishing: "info" };
export const LISTING_IN_FLIGHT = new Set(["pending", "publishing"]);

/** Per-channel listing status for one product; polls while anything is queued or publishing. */
export function ListingsPanel({ product, canPublish }: { product: ProductDetail; canPublish: boolean }) {
  const { t, relative } = useI18n();
  const { api } = useAuth();
  const toast = useToast();
  const connections = useApiQuery((a) => a.channels.list());
  const [round, setRound] = useState(0);
  const listings = usePolling(() => api.catalog.listings(product.id), {
    key: `${product.id}:${round}`,
    isDone: (r) => !r.items.some((l) => LISTING_IN_FLIGHT.has(l.status)),
    delay: (n) => Math.min(4000, 1000 + n * 500),
  });
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);

  const listable =
    connections.state.status === "success"
      ? connections.state.data.items.filter((c) => c.capabilities.includes("product_listing"))
      : [];
  const byConn = new Map<string, ChannelListing>((listings.data?.items ?? []).map((l) => [l.connection_id, l]));
  const live = product.status === "active";

  const act = async (key: string, fn: () => Promise<unknown>, done: string) => {
    setBusy(key);
    setError(null);
    try {
      await fn();
      toast(done);
      setRound((r) => r + 1);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(null);
    }
  };

  if (connections.state.status === "loading") return <TableSkeleton columns="1.4fr 1fr 1fr" rows={2} label={t("common.loading")} />;
  if (connections.state.status === "error") return <QueryError error={connections.state.error} onRetry={connections.reload} />;
  if (listable.length === 0) {
    return (
      <div className={wf.stack}>
        <p className={wf.hint}>{t("listings.none")}</p>
        <div>
          <ButtonLink href="/settings/channels" size="sm">
            {t("listings.connectLink")}
          </ButtonLink>
        </div>
      </div>
    );
  }

  const notListed = listable.filter((c) => {
    const s = byConn.get(c.id)?.status;
    return !s || s === "unpublished" || s === "failed";
  });

  return (
    <div className={wf.stack} data-testid="listings">
      {!live ? <InlineAlert tone="info" live={false}>{t("listings.notActive")}</InlineAlert> : null}
      {error ? (
        <InlineAlert tone="danger">
          {errorMessage(t, error)}
          <RequestId id={isApiError(error) ? error.requestId : null} />
        </InlineAlert>
      ) : null}
      {listings.error ? <QueryError error={listings.error} onRetry={listings.retry} /> : null}
      <div className={table.wrap}>
        <table className={table.table}>
          <thead>
            <tr>
              <th scope="col">{t("channels.colChannel")}</th>
              <th scope="col">{t("listings.colListing")}</th>
              <th scope="col" className={table.actions}>
                {canPublish && live && notListed.length > 1 ? (
                  <Button
                    size="sm"
                    loading={busy === "all"}
                    onClick={() => act("all", () => api.catalog.publish(product.id, notListed.map((c) => c.id)), t("listings.queued"))}
                  >
                    {t("listings.publishAll")}
                  </Button>
                ) : (
                  <span className="srOnly">{t("common.actions")}</span>
                )}
              </th>
            </tr>
          </thead>
          <tbody>
            {listable.map((c) => {
              const l = byConn.get(c.id);
              const status = l?.status ?? "none";
              const inFlight = LISTING_IN_FLIGHT.has(status);
              const blocked = !canPublish || !live || c.needs_reconnect || busy !== null;
              return (
                <tr key={c.id} data-connection={c.display_name} data-status={status}>
                  <td>
                    <div className={table.primaryCell}>
                      <strong>{c.display_name}</strong>
                      {c.needs_reconnect ? <span>{t("channels.status.expired")}</span> : null}
                    </div>
                  </td>
                  <td>
                    <Badge tone={TONE[status] ?? "neutral"}>{t(`listings.status.${status as "none"}`)}</Badge>
                    {l?.last_error_code && (status === "failed" || status === "out_of_sync") ? (
                      <div className={table.muted} style={{ fontSize: "var(--font-size-xs)", marginTop: 2 }}>
                        {t("listings.lastError", { message: t.dynamic(`errors.${l.last_error_code}`) ?? l.last_error_code })}
                      </div>
                    ) : l?.last_synced_at && status === "published" ? (
                      <div className={table.muted} style={{ fontSize: "var(--font-size-xs)", marginTop: 2 }}>
                        {relative(l.last_synced_at)}
                      </div>
                    ) : null}
                  </td>
                  <td className={table.actions}>
                    {inFlight || !canPublish ? null : status === "published" || status === "out_of_sync" ? (
                      <div className={wf.rowActions}>
                        <Button size="sm" disabled={blocked} loading={busy === c.id} onClick={() => act(c.id, () => api.catalog.publish(product.id, [c.id]), t("listings.queued"))}>
                          {t("listings.update")}
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={busy !== null}
                          onClick={() => act(`rm-${c.id}`, () => api.catalog.unpublish(product.id, c.id), t("listings.removed"))}
                        >
                          {t("listings.unpublish")}
                        </Button>
                      </div>
                    ) : (
                      <Button
                        size="sm"
                        variant="primary"
                        disabled={blocked}
                        loading={busy === c.id}
                        onClick={() => act(c.id, () => api.catalog.publish(product.id, [c.id]), t("listings.queued"))}
                        aria-label={`${t("listings.publish")}: ${c.display_name}`}
                      >
                        {t("listings.publish")}
                      </Button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
