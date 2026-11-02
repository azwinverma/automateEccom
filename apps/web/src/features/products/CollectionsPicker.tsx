"use client";

import { isApiError } from "@commerce-os/api-client";
import { useState, type FormEvent } from "react";
import { QueryError, TableSkeleton } from "@/components/states/States";
import { Button } from "@/components/ui/Button";
import { Checkbox, TextField } from "@/components/ui/Field";
import { InlineAlert, RequestId, useToast } from "@/components/ui/misc";
import { errorMessage } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import styles from "./products.module.css";

/**
 * Collection membership for one product. Each tick is its own idempotent PUT/DELETE,
 * independent of the main Save (membership has no product version).
 */
export function CollectionsPicker({
  productId,
  memberOf,
  canWrite,
  onChange,
}: {
  productId: string;
  memberOf: string[];
  canWrite: boolean;
  onChange: (ids: string[]) => void;
}) {
  const { t } = useI18n();
  const { api } = useAuth();
  const toast = useToast();
  const collections = useApiQuery((a) => a.catalog.collections());
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [title, setTitle] = useState("");

  const toggle = async (id: string, name: string, on: boolean) => {
    setBusy(id);
    setError(null);
    try {
      if (on) await api.catalog.addToCollection(id, productId);
      else await api.catalog.removeFromCollection(id, productId);
      onChange(on ? [...memberOf, id] : memberOf.filter((x) => x !== id));
      toast(t(on ? "products.editor.collectionAdded" : "products.editor.collectionRemoved", { name }));
    } catch (e) {
      setError(e);
    } finally {
      setBusy(null);
    }
  };

  const create = async (e: FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    setBusy("new");
    setError(null);
    try {
      const c = await api.catalog.createCollection({ title: title.trim() });
      collections.setData((d) => ({ items: [...d.items, c].sort((a, b) => a.title.localeCompare(b.title)) }));
      await api.catalog.addToCollection(c.id, productId);
      onChange([...memberOf, c.id]);
      setTitle("");
      toast(t("products.editor.collectionAdded", { name: c.title }));
    } catch (err) {
      setError(err);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div>
      <span className={styles.fieldLabel}>{t("products.editor.collections")}</span>
      {canWrite ? <p className={styles.sectionHint}>{t("products.editor.collectionsHint")}</p> : null}
      {error ? (
        <InlineAlert tone="danger">
          {errorMessage(t, error)}
          <RequestId id={isApiError(error) ? error.requestId : null} />
        </InlineAlert>
      ) : null}
      {collections.state.status === "loading" ? (
        <TableSkeleton columns="1fr" rows={2} label={t("common.loading")} />
      ) : collections.state.status === "error" ? (
        <QueryError error={collections.state.error} onRetry={collections.reload} />
      ) : collections.state.data.items.length === 0 ? (
        <p className={styles.sectionHint}>{t("products.editor.collectionsEmpty")}</p>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: "var(--space-2)" }} data-testid="collections">
          {collections.state.data.items.map((c) => (
            <Checkbox
              key={c.id}
              label={c.title}
              checked={memberOf.includes(c.id)}
              disabled={!canWrite || busy !== null}
              onChange={(e) => toggle(c.id, c.title, e.target.checked)}
            />
          ))}
        </div>
      )}
      {canWrite ? (
        <form onSubmit={create} style={{ display: "flex", gap: "var(--space-2)", alignItems: "flex-end", marginTop: "var(--space-3)", maxWidth: 480 }}>
          <div style={{ flex: 1 }}>
            <TextField label={t("products.editor.newCollection")} value={title} onChange={(e) => setTitle(e.target.value)} maxLength={160} />
          </div>
          <Button type="submit" size="sm" loading={busy === "new"} disabled={!title.trim()} style={{ marginBottom: 3 }}>
            {t("products.editor.createCollection")}
          </Button>
        </form>
      ) : null}
    </div>
  );
}
