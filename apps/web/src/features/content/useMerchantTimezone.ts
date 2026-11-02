"use client";

import { useApiQuery } from "@/lib/api/hooks";
import { DEFAULT_TZ } from "@/lib/content/calendar";

/** Merchant's time zone (from GET /merchant); Asia/Kathmandu until it loads or if unset. */
export function useMerchantTimezone(): string {
  const merchant = useApiQuery((a) => a.merchants.current());
  return merchant.state.status === "success" && merchant.state.data.timezone ? merchant.state.data.timezone : DEFAULT_TZ;
}
