"use client";

import type { ProductStatus, ProductSummary } from "@commerce-os/api-client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { EmptyState, ErrorState, QueryError, TableSkeleton } from "@/components/states/States";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Icon } from "@/components/ui/Icon";
import { Badge, PageHeader, type Tone } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { useI18n } from "@/i18n/I18nProvider";
import { useAuth } from "@/lib/auth/AuthProvider";
import { CategoriesDrawer } from "./CategoriesDrawer";
import { ImportDrawer } from "./ImportDrawer";
import styles from "./products.module.css";

type Tab = "all" | ProductStatus;
const TABS: { key: Tab; label: "products.tabAll" | "products.tabActive" | "products.tabDraft" | "products.tabArchived" }[] = [
  { key: "all", label: "products.tabAll" },
  { key: "active", label: "products.tabActive" },
  { key: "draft", label: "products.tabDraft" },
  { key: "archived", label: "products.tabArchived" },
];
const PAGE = 50;

type ListState =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | { status: "ready"; items: ProductSummary[]; next: string | null; loadingMore: boolean; moreError: unknown };

export const STATUS_TONE: Record<ProductStatus, Tone> = { active: "success", draft: "neutral", archived: "neutral" };

export function ProductsList() {
  const { t, money, relative, dateTime, number } = useI18n();
  const { api, merchantId, can } = useAuth();
  const canWrite = can("catalog.write");
  const [tab, setTab] = useState<Tab>("all");
  const [query, setQuery] = useState("");
  const [q, setQ] = useState("");
  const [state, setState] = useState<ListState>({ status: "loading" });
  const [nonce, setNonce] = useState(0);
  const [importOpen, setImportOpen] = useState(false);
  const [categoriesOpen, setCategoriesOpen] = useState(false);

  // Debounce search so typing a SKU doesn't fire a request per keystroke.
  useEffect(() => {
    const id = setTimeout(() => setQ(query.trim()), 300);
    return () => clearTimeout(id);
  }, [query]);

  useEffect(() => {
    let cancelled = false;
    setState({ status: "loading" });
    api.catalog.products({ status: tab === "all" ? undefined : tab, q: q || undefined, limit: PAGE }).then(
      (page) => !cancelled && setState({ status: "ready", items: page.items, next: page.next_cursor, loadingMore: false, moreError: null }),
      (error: unknown) => !cancelled && setState({ status: "error", error }),
    );
    return () => {
      cancelled = true;
    };
  }, [api, merchantId, tab, q, nonce]);

  const loadMore = async () => {
    if (state.status !== "ready" || !state.next || state.loadingMore) return;
    const cursor = state.next;
    setState({ ...state, loadingMore: true, moreError: null });
    try {
      const page = await api.catalog.products({ status: tab === "all" ? undefined : tab, q: q || undefined, limit: PAGE, cursor });
      setState((s) => (s.status === "ready" ? { status: "ready", items: [...s.items, ...page.items], next: page.next_cursor, loadingMore: false, moreError: null } : s));
    } catch (error) {
      setState((s) => (s.status === "ready" ? { ...s, loadingMore: false, moreError: error } : s));
    }
  };

  const price = (p: ProductSummary) => {
    if (!p.price_range) return <span className={table.muted}>{t("products.noPrice")}</span>;
    const { min_minor, max_minor, currency } = p.price_range;
    return min_minor === max_minor
      ? money(min_minor, currency)
      : t("products.priceRange", { min: money(min_minor, currency), max: money(max_minor, currency) });
  };

  const emptyCopy = () => {
    if (q) return <EmptyState title={t("products.emptySearch", { q })} />;
    if (tab === "active") return <EmptyState title={t("products.emptyActive")} />;
    if (tab === "draft") return <EmptyState title={t("products.emptyDraft")} />;
    if (tab === "archived") return <EmptyState title={t("products.emptyArchived")} />;
    return (
      <EmptyState
        title={t("products.emptyTitle")}
        body={canWrite ? t("products.emptyBody") : t("products.readOnly")}
        actions={
          canWrite ? (
            <>
              <ButtonLink href="/products/new" variant="primary">
                <Icon name="plus" />
                {t("products.emptyAdd")}
              </ButtonLink>
              <Button onClick={() => setImportOpen(true)}>{t("products.emptyImport")}</Button>
            </>
          ) : null
        }
      />
    );
  };

  return (
    <>
      <PageHeader
        title={t("products.title")}
        subtitle={t("products.subtitle")}
        actions={
          <div className={styles.headerActions}>
            <Button onClick={() => setCategoriesOpen(true)}>{t("products.categories")}</Button>
            {canWrite ? <Button onClick={() => setImportOpen(true)}>{t("products.importCsv")}</Button> : null}
            {canWrite && can("ai.use") ? (
              <ButtonLink href="/products/studio">
                <Icon name="automation" />
                {t("studio.entry")}
              </ButtonLink>
            ) : null}
            {canWrite ? (
              <ButtonLink href="/products/new" variant="primary">
                <Icon name="plus" />
                {t("products.add")}
              </ButtonLink>
            ) : null}
          </div>
        }
      />

      <div className={styles.toolbar}>
        <div role="tablist" aria-label={t("products.filters")} className={styles.tabs}>
          {TABS.map((tb) => (
            <button
              key={tb.key}
              type="button"
              role="tab"
              aria-selected={tab === tb.key}
              className={styles.tab}
              onClick={() => setTab(tb.key)}
            >
              {t(tb.label)}
            </button>
          ))}
        </div>
        <div className={styles.search} role="search">
          <Icon name="search" />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("products.searchPlaceholder")}
            aria-label={t("products.searchLabel")}
          />
        </div>
      </div>

      <div className={styles.listMeta}>
        {state.status === "loading" ? (
          <TableSkeleton columns="2.4fr 1fr 0.7fr 1.2fr 1fr" rows={8} label={t("common.loading")} />
        ) : state.status === "error" ? (
          <QueryError error={state.error} onRetry={() => setNonce((n) => n + 1)} />
        ) : state.items.length === 0 ? (
          emptyCopy()
        ) : (
          <>
            <div className={table.wrap}>
              <table className={table.table} aria-label={t("products.title")}>
                <thead>
                  <tr>
                    <th scope="col">{t("products.colTitle")}</th>
                    <th scope="col">{t("products.colStatus")}</th>
                    <th scope="col" className={[table.num, table.hideSm].join(" ")}>
                      {t("products.colVariants")}
                    </th>
                    <th scope="col" className={table.num}>
                      {t("products.colPrice")}
                    </th>
                    <th scope="col" className={table.hideSm}>
                      {t("products.colUpdated")}
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {state.items.map((p) => (
                    <tr key={p.id} data-testid="product-row">
                      <td>
                        <div className={table.primaryCell}>
                          <Link href={`/products/${p.id}`} className={styles.titleLink}>
                            {p.title}
                          </Link>
                          <span className="mono">{p.handle}</span>
                        </div>
                      </td>
                      <td>
                        <Badge tone={STATUS_TONE[p.status]}>{t(`products.status.${p.status}`)}</Badge>
                      </td>
                      <td className={[table.num, table.hideSm].join(" ")}>{number(p.variant_count)}</td>
                      <td className={table.num}>{price(p)}</td>
                      <td className={[table.muted, table.hideSm].join(" ")}>
                        <time dateTime={p.updated_at} title={dateTime(p.updated_at)}>
                          {relative(p.updated_at)}
                        </time>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {state.moreError ? <ErrorState error={state.moreError} onRetry={loadMore} /> : null}
            {state.next ? (
              <div style={{ display: "flex", justifyContent: "center", padding: "var(--space-4) 0" }}>
                <Button onClick={loadMore} loading={state.loadingMore}>
                  {t("common.loadMore")}
                </Button>
              </div>
            ) : null}
          </>
        )}
      </div>

      <ImportDrawer open={importOpen} onOpenChange={setImportOpen} onImported={() => setNonce((n) => n + 1)} />
      <CategoriesDrawer open={categoriesOpen} onOpenChange={setCategoriesOpen} />
    </>
  );
}
