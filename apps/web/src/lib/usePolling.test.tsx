import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { backoff, usePolling } from "./usePolling";

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());
const flush = async (ms: number) => act(async () => void (await vi.advanceTimersByTimeAsync(ms)));

describe("usePolling", () => {
  it("backs off", () => expect([0, 1, 2, 9].map((n) => backoff(n))).toEqual([1000, 1500, 2250, 5000]));

  it("polls until done, seeded with the POST response", async () => {
    const seq = ["generating", "post_processing", "ready"];
    const load = vi.fn(async () => ({ status: seq.shift() ?? "ready" }));
    const { result } = renderHook(() => usePolling(load, { key: "v1", isDone: (v) => v.status === "ready", initial: { status: "queued" } }));
    expect(result.current.data?.status).toBe("queued");
    await flush(1000);
    expect(result.current.data?.status).toBe("generating");
    await flush(1500);
    await flush(2250);
    expect(result.current.data?.status).toBe("ready");
    expect(result.current.done).toBe(true);
    await flush(60_000);
    expect(load).toHaveBeenCalledTimes(3);
  });

  it("does not poll a done seed, but refresh() refetches (e.g. expired signed URLs)", async () => {
    const load = vi.fn(async () => ({ status: "ready", url: "fresh" }));
    const { result } = renderHook(() => usePolling(load, { key: "v1", isDone: (v) => v.status === "ready", initial: { status: "ready", url: "stale" } }));
    await flush(10_000);
    expect(load).not.toHaveBeenCalled();
    act(() => result.current.refresh());
    await flush(0);
    expect(result.current.data?.url).toBe("fresh");
  });

  it("restarts when the key changes and stops on unmount", async () => {
    const load = vi.fn(async () => ({ status: "running" }));
    const { rerender, unmount } = renderHook(({ k }) => usePolling(load, { key: k, isDone: () => false }), { initialProps: { k: "a" } });
    await flush(0);
    rerender({ k: "b" });
    await flush(0);
    expect(load).toHaveBeenCalledTimes(2);
    unmount();
    await flush(30_000);
    expect(load).toHaveBeenCalledTimes(2);
  });

  it("surfaces an error after repeated failures", async () => {
    const load = vi.fn(async () => {
      throw new Error("down");
    });
    const { result } = renderHook(() => usePolling(load, { key: "x", isDone: () => false, maxFailures: 2 }));
    await flush(0);
    await flush(1000);
    expect(result.current.error).toBeInstanceOf(Error);
    await flush(30_000);
    expect(load).toHaveBeenCalledTimes(2);
  });
});
