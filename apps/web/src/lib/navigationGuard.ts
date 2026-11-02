"use client";

import { useEffect } from "react";

/**
 * Unsaved-changes guard. Covers tab close/reload (beforeunload), in-app links
 * (capture-phase click on same-origin anchors, before Next's Link handler runs) and
 * programmatic navigation that opts in via `confirmLeave()` (e.g. the command palette).
 */
let activeMessage: string | null = null;

export function confirmLeave(): boolean {
  return activeMessage === null || window.confirm(activeMessage);
}

export function useUnsavedChangesGuard(dirty: boolean, message: string) {
  useEffect(() => {
    if (!dirty) return;
    activeMessage = message;

    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    const onClick = (e: MouseEvent) => {
      if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      const a = (e.target as Element | null)?.closest?.("a[href]") as HTMLAnchorElement | null;
      if (!a || a.target === "_blank" || a.hasAttribute("download")) return;
      const url = new URL(a.href, window.location.href);
      if (url.origin !== window.location.origin) return;
      if (url.pathname === window.location.pathname && url.search === window.location.search) return; // in-page anchors
      if (!window.confirm(message)) {
        e.preventDefault();
        e.stopPropagation();
      }
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    document.addEventListener("click", onClick, true);
    return () => {
      activeMessage = null;
      window.removeEventListener("beforeunload", onBeforeUnload);
      document.removeEventListener("click", onClick, true);
    };
  }, [dirty, message]);
}
