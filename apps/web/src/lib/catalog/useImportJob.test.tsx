import { ApiError, type Api, type ImportJob } from "@commerce-os/api-client";
import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { pollDelay, useImportJob } from "./useImportJob";

const job = (status: ImportJob["status"], extra: Partial<ImportJob> = {}): ImportJob => ({
  id: "imp1",
  status,
  file_name: "kurtas.csv",
  total_rows: 10,
  products_created: 0,
  products_updated: 0,
  rows_failed: 0,
  errors: [],
  created_at: "",
  started_at: null,
  finished_at: null,
  ...extra,
});

function apiWith(fn: () => Promise<ImportJob>) {
  const importJob = vi.fn(fn);
  return { api: { catalog: { importJob } } as unknown as Api, importJob };
}

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

const flush = async (ms: number) => {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
};

describe("import polling", () => {
  it("backs off and caps the delay", () => {
    expect([0, 1, 2, 3, 10].map(pollDelay)).toEqual([1000, 1500, 2250, 3375, 5000]);
  });

  it("polls until a terminal status, then stops", async () => {
    const seq = [job("queued"), job("processing"), job("completed_with_errors", { rows_failed: 2 })];
    const { api, importJob } = apiWith(async () => seq.shift() ?? job("completed"));
    const { result } = renderHook(() => useImportJob(api, "imp1"));
    await flush(0);
    expect(result.current.job?.status).toBe("queued");
    await flush(1000);
    expect(result.current.job?.status).toBe("processing");
    await flush(1500);
    expect(result.current.job?.status).toBe("completed_with_errors");
    expect(result.current.done).toBe(true);
    await flush(30_000);
    expect(importJob).toHaveBeenCalledTimes(3);
  });

  it("does not poll a job that is already finished", async () => {
    const { api, importJob } = apiWith(async () => job("completed"));
    const { result } = renderHook(() => useImportJob(api, "imp1", job("failed")));
    await flush(10_000);
    expect(result.current.job?.status).toBe("failed");
    expect(importJob).not.toHaveBeenCalled();
  });

  it("gives up after repeated failures and can retry", async () => {
    let fail = true;
    const { api, importJob } = apiWith(async () => {
      if (fail) throw new ApiError({ status: 0, code: "network_error", message: "" });
      return job("completed");
    });
    const { result } = renderHook(() => useImportJob(api, "imp1"));
    await flush(0);
    await flush(1000);
    await flush(1500);
    expect(importJob).toHaveBeenCalledTimes(3);
    expect(result.current.error).toBeInstanceOf(ApiError);
    await flush(20_000);
    expect(importJob).toHaveBeenCalledTimes(3);
    fail = false;
    act(() => result.current.retry());
    await flush(0);
    expect(result.current.job?.status).toBe("completed");
    expect(result.current.error).toBeNull();
  });

  it("stops polling on unmount", async () => {
    const { api, importJob } = apiWith(async () => job("processing"));
    const { unmount } = renderHook(() => useImportJob(api, "imp1"));
    await flush(0);
    unmount();
    await flush(30_000);
    expect(importJob).toHaveBeenCalledTimes(1);
  });
});
