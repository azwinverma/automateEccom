"use client";

import { isApiError, type Category } from "@commerce-os/api-client";
import { useState, type FormEvent } from "react";
import { EmptyState, QueryError, TableSkeleton } from "@/components/states/States";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog, Drawer } from "@/components/ui/Drawer";
import { SelectField, TextField } from "@/components/ui/Field";
import { InlineAlert, RequestId, SectionHeader, useToast } from "@/components/ui/misc";
import { errorMessage } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import type { AppLocale } from "@/i18n/config";
import { useAction, useApiQuery } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import styles from "./products.module.css";

export function categoryName(c: Category, locale: AppLocale): string {
  return locale === "ne" && c.name_ne ? c.name_ne : c.name;
}

/** Indented label for flat <select>s; categories arrive sorted by path. */
export function categoryOptionLabel(c: Category, locale: AppLocale): string {
  return `${"— ".repeat(c.depth)}${categoryName(c, locale)}`;
}

/** A category can't move under itself or its own subtree (paths are slug paths). */
export function validParents(all: Category[], moving: Category): Category[] {
  return all.filter((c) => c.id !== moving.id && c.path !== moving.path && !c.path.startsWith(`${moving.path}/`));
}

function CategoryEditor({
  category,
  all,
  onSaved,
  onCancel,
}: {
  category: Category;
  all: Category[];
  onSaved: (c: Category) => void;
  onCancel: () => void;
}) {
  const { t, locale } = useI18n();
  const { api } = useAuth();
  const [name, setName] = useState(category.name);
  const [nameNe, setNameNe] = useState(category.name_ne ?? "");
  const [parent, setParent] = useState(category.parent_id ?? "");
  const action = useAction();

  const save = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    const moved = (parent || null) !== (category.parent_id ?? null);
    const c = await action.run(() =>
      api.catalog.updateCategory(category.id, {
        name: name.trim(),
        name_ne: nameNe.trim() || null,
        ...(moved ? { move: true, parent_id: parent || null } : {}),
      }),
    );
    if (c) onSaved(c);
  };

  return (
    <form className={styles.fields} onSubmit={save} noValidate style={{ padding: "var(--space-3) 0", marginTop: 0 }} aria-label={t("products.categoriesDrawer.editTitle", { name: category.name })}>
      {action.error ? (
        <InlineAlert tone="danger">
          {errorMessage(t, action.error)}
          <RequestId id={isApiError(action.error) ? action.error.requestId : null} />
        </InlineAlert>
      ) : null}
      <TextField label={t("products.categoriesDrawer.name")} value={name} onChange={(e) => setName(e.target.value)} autoFocus />
      <TextField label={t("products.categoriesDrawer.nameNe")} optionalLabel={t("common.optional")} value={nameNe} onChange={(e) => setNameNe(e.target.value)} lang="ne" />
      <SelectField label={t("products.categoriesDrawer.move")} value={parent} onChange={(e) => setParent(e.target.value)}>
        <option value="">{t("products.categoriesDrawer.topLevel")}</option>
        {validParents(all, category).map((c) => (
          <option key={c.id} value={c.id}>
            {categoryOptionLabel(c, locale)}
          </option>
        ))}
      </SelectField>
      <div style={{ display: "flex", gap: "var(--space-2)" }}>
        <Button type="submit" variant="primary" size="sm" loading={action.pending}>
          {t("products.categoriesDrawer.save")}
        </Button>
        <Button size="sm" variant="ghost" onClick={onCancel}>
          {t("common.cancel")}
        </Button>
      </div>
    </form>
  );
}

function CategoriesBody({ onCreated }: { onCreated?: (c: Category) => void }) {
  const { t, locale } = useI18n();
  const { api, can } = useAuth();
  const toast = useToast();
  const categories = useApiQuery((a) => a.catalog.categories());
  const [name, setName] = useState("");
  const [nameNe, setNameNe] = useState("");
  const [parent, setParent] = useState("");
  const [nameError, setNameError] = useState<string | null>(null);
  const action = useAction();
  const remove = useAction();
  const [editing, setEditing] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<Category | null>(null);
  const canWrite = can("catalog.write");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setNameError(t("errors.field.required"));
      return;
    }
    setNameError(null);
    const created = await action.run(() =>
      api.catalog.createCategory({ name: name.trim(), name_ne: nameNe.trim() || undefined, parent_id: parent || null }),
    );
    if (created) {
      categories.setData((d) => ({ items: [...d.items, created].sort((a, b) => a.path.localeCompare(b.path)) }));
      setName("");
      setNameNe("");
      toast(t("products.categoriesDrawer.added"));
      onCreated?.(created);
    }
  };

  return (
    <>
      {categories.state.status === "loading" ? (
        <TableSkeleton columns="1fr" rows={4} label={t("common.loading")} />
      ) : categories.state.status === "error" ? (
        <QueryError error={categories.state.error} onRetry={categories.reload} />
      ) : categories.state.data.items.length === 0 ? (
        <EmptyState title={t("products.categoriesDrawer.empty")} />
      ) : (
        <ul className={styles.tree} aria-label={t("products.categoriesDrawer.tree")}>
          {categories.state.data.items.map((c, _i, all) =>
            editing === c.id ? (
              <li key={c.id} style={{ display: "block", paddingLeft: c.depth * 16 }}>
                <CategoryEditor
                  category={c}
                  all={all}
                  onCancel={() => setEditing(null)}
                  onSaved={() => {
                    setEditing(null);
                    toast(t("products.categoriesDrawer.updated"));
                    categories.reload(); // a move rewrites the whole subtree's paths
                  }}
                />
              </li>
            ) : (
              <li key={c.id} style={{ paddingLeft: c.depth * 16 }}>
                {c.depth > 0 ? <span className={styles.treeIndent} aria-hidden="true" /> : null}
                <span>{c.name}</span>
                {c.name_ne ? <span className={styles.treeNe} lang="ne">{c.name_ne}</span> : null}
                {canWrite ? (
                  <span style={{ marginLeft: "auto", display: "flex", gap: 2 }}>
                    <Button size="sm" variant="ghost" onClick={() => setEditing(c.id)} aria-label={`${t("products.categoriesDrawer.rename")}: ${c.name}`}>
                      {t("products.categoriesDrawer.rename")}
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => {
                        remove.clear();
                        setDeleting(c);
                      }}
                      aria-label={`${t("products.categoriesDrawer.delete")}: ${c.name}`}
                    >
                      {t("products.categoriesDrawer.delete")}
                    </Button>
                  </span>
                ) : null}
              </li>
            ),
          )}
        </ul>
      )}

      {canWrite ? (
        <form className={styles.fields} onSubmit={submit} noValidate>
          <SectionHeader title={t("products.categoriesDrawer.add")} />
          {action.error ? (
            <InlineAlert tone="danger">
              {errorMessage(t, action.error)}
              <RequestId id={isApiError(action.error) ? action.error.requestId : null} />
            </InlineAlert>
          ) : null}
          <TextField label={t("products.categoriesDrawer.name")} value={name} onChange={(e) => setName(e.target.value)} error={nameError} required />
          <TextField
            label={t("products.categoriesDrawer.nameNe")}
            optionalLabel={t("common.optional")}
            value={nameNe}
            onChange={(e) => setNameNe(e.target.value)}
            lang="ne"
          />
          <SelectField label={t("products.categoriesDrawer.parent")} value={parent} onChange={(e) => setParent(e.target.value)}>
            <option value="">{t("products.categoriesDrawer.topLevel")}</option>
            {categories.state.status === "success"
              ? categories.state.data.items.map((c) => (
                  <option key={c.id} value={c.id}>
                    {categoryOptionLabel(c, locale)}
                  </option>
                ))
              : null}
          </SelectField>
          <div>
            <Button type="submit" variant="primary" loading={action.pending}>
              {t("products.categoriesDrawer.add")}
            </Button>
          </div>
        </form>
      ) : (
        <p className={styles.sectionHint}>{t("products.categoriesDrawer.readOnly")}</p>
      )}
      <ConfirmDialog
        open={deleting !== null}
        onOpenChange={(o) => !o && setDeleting(null)}
        title={t("products.categoriesDrawer.deleteTitle", { name: deleting?.name ?? "" })}
        body={t("products.categoriesDrawer.deleteBody")}
        confirmLabel={t("products.categoriesDrawer.delete")}
        pending={remove.pending}
        destructive
        onConfirm={async () => {
          if (!deleting) return;
          const ok = await remove.run(async () => {
            await api.catalog.deleteCategory(deleting.id);
            return true;
          });
          if (ok) {
            categories.setData((d) => ({ items: d.items.filter((x) => x.id !== deleting.id) }));
            setDeleting(null);
            toast(t("products.categoriesDrawer.deleted"));
          }
        }}
      >
        {remove.error ? (
          <InlineAlert tone="danger">
            {errorMessage(t, remove.error)}
            <RequestId id={isApiError(remove.error) ? remove.error.requestId : null} />
          </InlineAlert>
        ) : null}
      </ConfirmDialog>
    </>
  );
}

export function CategoriesDrawer({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  onCreated?: (c: Category) => void;
}) {
  const { t } = useI18n();
  return (
    <Drawer open={open} onOpenChange={onOpenChange} title={t("products.categoriesDrawer.title")} description={t("products.categoriesDrawer.body")}>
      <CategoriesBody onCreated={onCreated} />
    </Drawer>
  );
}
