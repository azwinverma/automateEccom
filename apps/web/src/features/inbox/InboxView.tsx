"use client";

import type { ConversationDetail, ConversationSummary, InboxMessage } from "@commerce-os/api-client";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { EmptyState, QueryError } from "@/components/states/States";
import { Button } from "@/components/ui/Button";
import { Badge, InlineAlert, PageHeader, useToast } from "@/components/ui/misc";
import { useI18n } from "@/i18n/I18nProvider";
import { useAction } from "@/lib/api/hooks";
import { useAuth } from "@/lib/auth/AuthProvider";
import { ErrorAlert } from "../orders/shared";
import styles from "./inbox.module.css";

type Filter = "open" | "escalated" | "unassigned" | "closed";
const FILTERS: Filter[] = ["open", "escalated", "unassigned", "closed"];
const FILTER_LABEL = { open: "inbox.filterOpen", escalated: "inbox.filterEscalated", unassigned: "inbox.filterUnassigned", closed: "inbox.filterClosed" } as const;
const LIST_POLL_MS = 10_000;
const THREAD_POLL_MS = 4_000;

/** Re-run `fn` every `ms` while the tab is visible. */
function usePoll(fn: () => void, ms: number, active = true) {
  const ref = useRef(fn);
  ref.current = fn;
  useEffect(() => {
    if (!active) return;
    const id = setInterval(() => {
      if (document.visibilityState === "visible") ref.current();
    }, ms);
    return () => clearInterval(id);
  }, [ms, active]);
}

export function InboxView() {
  const { t, relative } = useI18n();
  const { api, merchantId } = useAuth();
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const selected = params.get("c");
  const [filter, setFilter] = useState<Filter>("open");
  const [items, setItems] = useState<ConversationSummary[] | null>(null);
  const [error, setError] = useState<unknown>(null);

  const load = useCallback(async () => {
    try {
      const q =
        filter === "escalated" ? { status: "open" as const, escalated: true } : filter === "unassigned" ? { status: "open" as const, assigned: "unassigned" as const } : { status: filter };
      const p = await api.inbox.conversations({ ...q, limit: 100 });
      setItems(p.items);
      setError(null);
    } catch (e) {
      setError(e);
    }
  }, [api, filter]);

  useEffect(() => {
    setItems(null);
    void load();
  }, [load, merchantId]);
  usePoll(() => void load(), LIST_POLL_MS);

  const open = (id: string | null) => {
    const next = new URLSearchParams(params.toString());
    if (id) next.set("c", id);
    else next.delete("c");
    router.replace(`${pathname}?${next.toString()}`, { scroll: false });
  };

  return (
    <>
      <PageHeader title={t("inbox.title")} subtitle={t("inbox.subtitle")} />
      <div className={styles.layout} data-open={selected ? "true" : "false"}>
        <div className={styles.list}>
          <div className={styles.filters} role="group" aria-label={t("inbox.filters")}>
            {FILTERS.map((f) => (
              <button key={f} type="button" aria-pressed={filter === f} onClick={() => setFilter(f)}>
                {t(FILTER_LABEL[f])}
              </button>
            ))}
          </div>
          {error ? <QueryError error={error} onRetry={() => void load()} /> : null}
          {items === null ? (
            <p className={styles.empty} role="status">
              {t("common.loading")}
            </p>
          ) : items.length === 0 ? (
            <EmptyState title={t("inbox.empty")} body={t("inbox.emptyBody")} />
          ) : (
            <ul className={styles.convs} data-testid="conversations">
              {items.map((c) => (
                <li key={c.id}>
                  <button type="button" className={styles.conv} aria-current={selected === c.id} onClick={() => open(c.id)}>
                    <span className={styles.convTop}>
                      <strong>{c.customer?.display_name ?? "–"}</strong>
                      <span className={styles.meta}>{c.last_message_at ? relative(c.last_message_at) : ""}</span>
                    </span>
                    <span className={styles.preview}>{c.last_message?.text ?? ""}</span>
                    <span className={styles.row}>
                      {c.escalated ? <Badge tone="danger">{t("inbox.filterEscalated")}</Badge> : null}
                      {c.unread_count ? (
                        <span className={styles.unread} aria-label={t("inbox.unread", { n: c.unread_count })}>
                          {c.unread_count}
                        </span>
                      ) : null}
                      <span className={styles.meta}>{c.provider}</span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className={styles.thread}>
          {selected ? (
            <Thread key={selected} id={selected} onBack={() => open(null)} onChanged={() => void load()} />
          ) : (
            <p className={styles.empty}>{t("inbox.pick")}</p>
          )}
        </div>
      </div>
    </>
  );
}

function Thread({ id, onBack, onChanged }: { id: string; onBack: () => void; onChanged: () => void }) {
  const { t, relative, dateTime } = useI18n();
  const { api, can } = useAuth();
  const toast = useToast();
  const action = useAction();
  const [conv, setConv] = useState<ConversationDetail | null>(null);
  const [messages, setMessages] = useState<InboxMessage[] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [text, setText] = useState("");
  const [editing, setEditing] = useState<{ id: string; text: string } | null>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const canReply = can("inbox.reply");

  const load = useCallback(async () => {
    try {
      const [c, m] = await Promise.all([api.inbox.conversation(id), api.inbox.messages(id, { limit: 200 })]);
      setConv(c);
      setMessages((prev) => {
        if (prev && prev.length === m.items.length && prev.every((x, i) => x.id === m.items[i]!.id && x.status === m.items[i]!.status)) return prev;
        return m.items;
      });
      setError(null);
    } catch (e) {
      setError(e);
    }
  }, [api, id]);

  useEffect(() => {
    void load().then(() => api.inbox.markRead(id).then(onChanged, () => undefined));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);
  usePoll(() => void load(), THREAD_POLL_MS);
  useEffect(() => bottom.current?.scrollIntoView({ block: "end" }), [messages?.length]);

  const after = async (fn: () => Promise<unknown>, done?: string) => {
    if ((await action.run(fn)) !== undefined) {
      if (done) toast(done);
      await load();
      onChanged();
    }
  };

  if (error && !conv) return <QueryError error={error} onRetry={() => void load()} />;
  if (!conv || !messages) {
    return (
      <p className={styles.empty} role="status">
        {t("common.loading")}
      </p>
    );
  }
  const draft = conv.order_draft;
  const reason = conv.escalation_reason ? (t.dynamic(`inbox.reason.${conv.escalation_reason}`) ?? conv.escalation_reason) : "";

  return (
    <>
      <div className={styles.threadHead}>
        <div className={styles.row}>
          <Button size="sm" variant="ghost" className={styles.backLink} onClick={onBack}>
            ← {t("inbox.back")}
          </Button>
          <h2>{conv.customer ? <Link href={`/customers/${conv.customer.id}`}>{conv.customer.display_name}</Link> : "–"}</h2>
          {conv.customer?.phone ? <span className={styles.meta}>{conv.customer.phone}</span> : null}
        </div>
        <div className={styles.row}>
          {canReply && conv.human_handoff ? (
            <Button size="sm" onClick={() => void after(() => api.inbox.update(id, { human_handoff: false }), t("inbox.handedBack"))}>
              {t("inbox.handBack")}
            </Button>
          ) : null}
          {canReply ? (
            conv.status === "closed" ? (
              <Button size="sm" variant="ghost" onClick={() => void after(() => api.inbox.update(id, { status: "open" }))}>
                {t("inbox.reopen")}
              </Button>
            ) : (
              <Button size="sm" variant="ghost" onClick={() => void after(() => api.inbox.update(id, { status: "closed" }))}>
                {t("inbox.close")}
              </Button>
            )
          ) : null}
        </div>
      </div>
      <div className={styles.context}>
        {conv.escalated ? (
          <InlineAlert tone="warning" live={false}>
            {t("inbox.escalated", { reason })}
          </InlineAlert>
        ) : (
          <span className={styles.meta}>{conv.human_handoff ? t("inbox.handoff") : t("inbox.aiOn")}</span>
        )}
        {draft && draft.status !== "abandoned" ? (
          <div className={styles.row} data-testid="order-draft">
            <strong>{t("inbox.draft")}:</strong>
            <span>{t(`inbox.draftStatus.${draft.status}`)}</span>
            {draft.awaiting_field ? <span className={styles.meta}>{t("inbox.waitingFor", { field: t.dynamic(`inbox.field.${draft.awaiting_field}`) ?? draft.awaiting_field })}</span> : null}
            {draft.order_id ? <Link href={`/orders/${draft.order_id}`}>{t("inbox.viewOrder")}</Link> : null}
          </div>
        ) : null}
        <div className={styles.row}>
          {conv.ai_summary ? <span>{conv.ai_summary}</span> : null}
          <Button size="sm" variant="ghost" loading={action.pending} onClick={() => void after(() => api.inbox.summary(id))}>
            {conv.ai_summary ? t("inbox.summarize") : t("inbox.summary")}
          </Button>
        </div>
      </div>
      <ErrorAlert error={action.error} />
      <div className={styles.messages} data-testid="messages" role="log" aria-live="polite" aria-label={t("inbox.title")} tabIndex={0}>
        {messages.length === 0 ? <p className={styles.meta}>{t("inbox.noMessages")}</p> : null}
        {messages.map((m) => {
          const cls = [styles.msg, m.direction === "in" ? styles.in : styles.out, m.status === "suggested" ? styles.suggested : "", m.status === "failed" ? styles.failed : ""].join(" ");
          const tools = Object.keys(m.grounding ?? {})
            .map((k) => t.dynamic(`inbox.tool.${k}`))
            .filter(Boolean)
            .join(", ");
          return (
            <div key={m.id} className={cls} data-status={m.status} data-author={m.author_type}>
              {editing?.id === m.id ? (
                <textarea aria-label={t("inbox.edit")} value={editing.text} onChange={(e) => setEditing({ id: m.id, text: e.target.value })} rows={4} style={{ font: "inherit" }} />
              ) : (
                <p>{m.text}</p>
              )}
              <span className={styles.meta}>
                {t(`inbox.author.${m.author_type}`)} ·{" "}
                <time dateTime={m.created_at} title={dateTime(m.created_at)}>
                  {relative(m.created_at)}
                </time>
                {m.status === "suggested" ? ` · ${t("inbox.suggestion")}` : null}
                {m.status === "queued" ? ` · ${t("inbox.queued")}` : null}
                {m.status === "failed" ? ` · ${t("inbox.failed", { reason: t.dynamic(`errors.${m.error_code}`) ?? m.error_code ?? "" })}` : null}
                {m.author_type === "ai" && tools ? ` · ${t("inbox.checked", { facts: tools })}` : null}
              </span>
              {canReply && m.status === "suggested" ? (
                <span className={styles.row}>
                  {editing?.id === m.id ? (
                    <>
                      <Button size="sm" variant="primary" loading={action.pending} onClick={() => void after(() => api.inbox.approve(m.id, editing.text)).then(() => setEditing(null))}>
                        {t("inbox.sendEdited")}
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setEditing(null)}>
                        {t("inbox.cancelEdit")}
                      </Button>
                    </>
                  ) : (
                    <>
                      <Button size="sm" variant="primary" loading={action.pending} onClick={() => void after(() => api.inbox.approve(m.id))}>
                        {t("inbox.approve")}
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => setEditing({ id: m.id, text: m.text })}>
                        {t("inbox.edit")}
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => void after(() => api.inbox.discard(m.id))}>
                        {t("inbox.discard")}
                      </Button>
                    </>
                  )}
                </span>
              ) : null}
              {canReply && m.status === "failed" ? (
                <span className={styles.row}>
                  <Button size="sm" onClick={() => void after(() => api.inbox.retry(m.id))}>
                    {t("inbox.retry")}
                  </Button>
                </span>
              ) : null}
            </div>
          );
        })}
        <div ref={bottom} />
      </div>
      {canReply && conv.status !== "closed" ? (
        <form
          className={styles.composer}
          onSubmit={(e) => {
            e.preventDefault();
            const body = text.trim();
            if (!body) return;
            void after(() => api.inbox.reply(id, body)).then(() => setText(""));
          }}
        >
          <textarea
            aria-label={t("inbox.composer")}
            placeholder={t("inbox.composer")}
            value={text}
            maxLength={4000}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault();
                (e.currentTarget.form as HTMLFormElement).requestSubmit();
              }
            }}
          />
          <Button type="submit" variant="primary" loading={action.pending} disabled={!text.trim()}>
            {t("inbox.send")}
          </Button>
        </form>
      ) : null}
    </>
  );
}
