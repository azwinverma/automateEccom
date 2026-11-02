"use client";

import { isApiError, type ImportJob } from "@commerce-os/api-client";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Button } from "@/components/ui/Button";
import { Drawer } from "@/components/ui/Drawer";
import { Icon } from "@/components/ui/Icon";
import { InlineAlert, RequestId } from "@/components/ui/misc";
import table from "@/components/ui/table.module.css";
import { errorMessage } from "@/i18n/errors";
import { useI18n } from "@/i18n/I18nProvider";
import { useAuth } from "@/lib/auth/AuthProvider";
import { downloadText, errorsCsv, templateCsv } from "@/lib/catalog/csv";
import { useImportJob } from "@/lib/catalog/useImportJob";
import styles from "./products.module.css";

const MAX_BYTES = 5 * 1024 * 1024;

function ImportProgress({ jobId, initial, onFinished }: { jobId: string; initial: ImportJob | null; onFinished: (job: ImportJob) => void }) {
  const { t, number } = useI18n();
  const { api } = useAuth();
  const { job, error, retry, done } = useImportJob(api, jobId, initial);
  const reported = useRef<string | null>(null);

  useEffect(() => {
    if (job && done && reported.current !== job.id) {
      reported.current = job.id;
      onFinished(job);
    }
  }, [job, done, onFinished]);

  const rowMessage = (code: string, message: string) => {
    const known = code !== "invalid_row" ? t.dynamic(`errors.${code}`) : undefined;
    // `invalid_row` messages carry the row-specific detail (e.g. which column); the backend sends them in English.
    return known ?? message ?? t("errors.invalid_row");
  };

  return (
    <div className={styles.fields} data-testid="import-progress">
      <div className={styles.progress} aria-live="polite">
        <strong>{job ? t(`products.import.status.${job.status}`) : t("products.import.status.queued")}</strong>
        {job?.file_name ? <span className={table.muted}>{job.file_name}</span> : null}
        {!done ? (
          <div className={styles.progressTrack} aria-hidden="true">
            <span />
          </div>
        ) : null}
        {job?.total_rows ? <span className={table.muted}>{t("products.import.rows", { count: number(job.total_rows) })}</span> : null}
      </div>

      {error ? (
        <InlineAlert
          tone="warning"
          title={t("products.import.pollError")}
          action={
            <Button size="sm" variant="ghost" onClick={retry}>
              {t("common.retry")}
            </Button>
          }
        >
          <RequestId id={isApiError(error) ? error.requestId : null} />
        </InlineAlert>
      ) : null}

      {job && done ? (
        <>
          <dl className={styles.counts}>
            <div>
              <dt>{t("products.import.created")}</dt>
              <dd>{number(job.products_created)}</dd>
            </div>
            <div>
              <dt>{t("products.import.updated")}</dt>
              <dd>{number(job.products_updated)}</dd>
            </div>
            <div className={job.rows_failed ? styles.countFailed : undefined}>
              <dt>{t("products.import.failedRows")}</dt>
              <dd>{number(job.rows_failed)}</dd>
            </div>
          </dl>
          {job.errors.length > 0 ? (
            <>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "var(--space-3)", flexWrap: "wrap" }}>
                <h3>{t("products.import.errorsHeading")}</h3>
                <Button
                  size="sm"
                  onClick={() =>
                    downloadText(
                      `import-errors-${job.id.slice(0, 8)}.csv`,
                      errorsCsv(job.errors, [t("products.import.colRow"), t("products.import.colHandle"), t("products.import.colCode"), t("products.import.colProblem")]),
                    )
                  }
                >
                  <Icon name="download" />
                  {t("products.import.downloadErrors")}
                </Button>
              </div>
              <div className={table.wrap}>
                <table className={[table.table, table.dense].join(" ")}>
                  <thead>
                    <tr>
                      <th scope="col" className={table.num}>
                        {t("products.import.colRow")}
                      </th>
                      <th scope="col">{t("products.import.colHandle")}</th>
                      <th scope="col">{t("products.import.colProblem")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {job.errors.map((e, i) => (
                      <tr key={`${e.row}-${i}`}>
                        <td className={table.num}>{e.row ?? t("common.none")}</td>
                        <td className={table.mono}>{e.handle ?? t("common.none")}</td>
                        <td>{rowMessage(e.code, e.message)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : null}
        </>
      ) : null}
    </div>
  );
}

export function ImportDrawer({ open, onOpenChange, onImported }: { open: boolean; onOpenChange: (o: boolean) => void; onImported: () => void }) {
  const { t } = useI18n();
  const { api } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [current, setCurrent] = useState<{ id: string; initial: ImportJob | null } | null>(null);
  const [duplicateOf, setDuplicateOf] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const reset = () => {
    setFile(null);
    setFileError(null);
    setError(null);
    setCurrent(null);
    setDuplicateOf(null);
    if (inputRef.current) inputRef.current.value = "";
  };

  const upload = async (e: FormEvent) => {
    e.preventDefault();
    if (!file) {
      setFileError(t("products.import.chooseFirst"));
      return;
    }
    if (file.size > MAX_BYTES) {
      setFileError(t("errors.file_too_large"));
      return;
    }
    setUploading(true);
    setError(null);
    setDuplicateOf(null);
    try {
      const job = await api.catalog.uploadImport(file, file.name);
      setCurrent({ id: job.id, initial: job });
    } catch (err) {
      if (isApiError(err) && err.code === "duplicate_import" && typeof err.details.import_id === "string") {
        setDuplicateOf(err.details.import_id);
      } else {
        setError(err);
      }
    } finally {
      setUploading(false);
    }
  };

  return (
    <Drawer
      open={open}
      onOpenChange={(o) => {
        if (!o) reset();
        onOpenChange(o);
      }}
      title={t("products.import.title")}
      description={t("products.import.body")}
      wide
      footer={
        current ? (
          <Button onClick={reset}>{t("products.import.another")}</Button>
        ) : (
          <Button variant="primary" type="submit" form="import-form" loading={uploading}>
            {uploading ? t("products.import.uploading") : t("products.import.upload")}
          </Button>
        )
      }
    >
      {current ? (
        <ImportProgress
          key={current.id}
          jobId={current.id}
          initial={current.initial}
          onFinished={(job) => {
            if (job.products_created || job.products_updated) onImported();
          }}
        />
      ) : (
        <form id="import-form" className={styles.fields} onSubmit={upload} noValidate>
          <p className={styles.sectionHint}>{t("products.import.howTo")}</p>
          <div>
            <Button size="sm" onClick={() => downloadText("commerce-os-products-template.csv", templateCsv())}>
              <Icon name="download" />
              {t("products.import.template")}
            </Button>
          </div>
          <div className={styles.dropzone}>
            <label htmlFor="import-file" className={styles.fieldLabel}>
              {t("products.import.file")}
            </label>
            <input
              ref={inputRef}
              id="import-file"
              type="file"
              accept=".csv,text/csv"
              onChange={(e) => {
                setFile(e.target.files?.[0] ?? null);
                setFileError(null);
                setDuplicateOf(null);
              }}
              aria-invalid={fileError ? true : undefined}
              aria-describedby={fileError ? "import-file-error" : undefined}
            />
            {fileError ? (
              <p id="import-file-error" className={styles.cellError} style={{ maxWidth: "none" }} role="alert">
                {fileError}
              </p>
            ) : null}
          </div>
          {duplicateOf ? (
            <InlineAlert
              tone="info"
              title={t("products.import.duplicate")}
              action={
                <Button size="sm" onClick={() => setCurrent({ id: duplicateOf, initial: null })}>
                  {t("products.import.viewEarlier")}
                </Button>
              }
            />
          ) : null}
          {error ? (
            <InlineAlert tone="danger">
              {errorMessage(t, error)}
              <RequestId id={isApiError(error) ? error.requestId : null} />
            </InlineAlert>
          ) : null}
        </form>
      )}
    </Drawer>
  );
}
