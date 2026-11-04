import type { SVGProps } from "react";

/** 16px stroke icons drawn for this app. Decorative by default (aria-hidden). */
const PATHS = {
  home: "M2.5 7.5 8 3l5.5 4.5V13a.5.5 0 0 1-.5.5h-3v-4H6v4H3a.5.5 0 0 1-.5-.5z",
  inbox: "M2 9.5h3.2l1 1.8h3.6l1-1.8H14M3.6 3.5h8.8L14 9.5V13H2V9.5z",
  orders: "M4 2.5h8v11l-2-1.2-2 1.2-2-1.2-2 1.2zM6 6h4M6 8.5h4",
  products: "M8 2 13.5 5v6L8 14l-5.5-3V5zM2.5 5 8 8l5.5-3M8 8v6",
  content: "M2.5 3.5h11v9h-11zM2.5 10.5l3-3 2.5 2.5 1.5-1.5 4 3.5M10.5 6.5h.01",
  customers: "M6 7.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5zM1.5 13.5c.4-2.3 2.2-3.8 4.5-3.8s4.1 1.5 4.5 3.8M10.5 2.7a2.5 2.5 0 0 1 0 4.6M12 9.9c1.3.5 2.2 1.8 2.5 3.6",
  inventory: "M2 5.5 8 2.5l6 3-6 3zM2 8.5l6 3 6-3M2 11.5l6 3 6-3",
  fulfillment: "M1.5 4h8v7h-8zM9.5 6.5h3l2 2.5V11h-5M4 13a1.3 1.3 0 1 0 0-2.6A1.3 1.3 0 0 0 4 13zM11.5 13a1.3 1.3 0 1 0 0-2.6 1.3 1.3 0 0 0 0 2.6z",
  returns: "M5.5 3.5 2.5 6.5l3 3M2.5 6.5h7a4 4 0 0 1 0 8H7",
  automation: "M4 4.5h3v3H4zM9 8.5h3v3H9zM5.5 7.5v2.5a.5.5 0 0 0 .5.5h3M10.5 8.5V5a.5.5 0 0 0-.5-.5H7",
  analytics: "M2.5 13.5h11M4 11V8M7 11V4.5M10 11V7M13 11V3",
  settings: "M8 10a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM8 1.5v2M8 12.5v2M1.5 8h2M12.5 8h2M3.4 3.4l1.4 1.4M11.2 11.2l1.4 1.4M3.4 12.6l1.4-1.4M11.2 4.8l1.4-1.4",
  search: "M7 12a5 5 0 1 0 0-10 5 5 0 0 0 0 10zM10.6 10.6 14 14",
  menu: "M2.5 4h11M2.5 8h11M2.5 12h11",
  close: "M3.5 3.5l9 9M12.5 3.5l-9 9",
  chevronDown: "M4 6l4 4 4-4",
  chevronRight: "M6 4l4 4-4 4",
  check: "M3 8.5l3 3 7-7",
  copy: "M5.5 5.5h8v8h-8zM10.5 5.5v-3h-8v8h3",
  download: "M8 2.5v8M4.5 7 8 10.5 11.5 7M2.5 13.5h11",
  alert: "M8 2 14.5 13.5h-13zM8 6.5v3M8 11.5h.01",
  lock: "M4 7.5h8v6H4zM5.5 7.5V5a2.5 2.5 0 0 1 5 0v2.5",
  plus: "M8 3v10M3 8h10",
  more: "M3.5 8h.01M8 8h.01M12.5 8h.01",
  logout: "M6 2.5H3v11h3M10 5l3 3-3 3M13 8H6",
  globe: "M8 14.5a6.5 6.5 0 1 0 0-13 6.5 6.5 0 0 0 0 13zM1.5 8h13M8 1.5c1.8 1.8 2.6 4 2.6 6.5S9.8 12.7 8 14.5C6.2 12.7 5.4 10.5 5.4 8S6.2 3.3 8 1.5z",
  store: "M2.5 6.5V13.5h11V6.5M1.5 3h13l-1 3.5H2.5zM6.5 13.5v-4h3v4",
  refresh: "M13.5 3v3.5H10M2.5 13V9.5H6M3.3 6a5 5 0 0 1 9.4-.5M12.7 10a5 5 0 0 1-9.4.5",
  arrowRight: "M3 8h10M9 4l4 4-4 4",
  shield: "M8 1.5 13.5 3.5v4c0 3.3-2.4 6-5.5 7-3.1-1-5.5-3.7-5.5-7v-4z",
  sun: "M8 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM8 1.5v1.5M8 13v1.5M1.5 8H3M13 8h1.5M3.4 3.4l1 1M11.6 11.6l1 1M3.4 12.6l1-1M11.6 4.4l1-1",
  moon: "M13.5 9.8A5.8 5.8 0 0 1 6.2 2.5 5.8 5.8 0 1 0 13.5 9.8z",
  monitor: "M2 3h12v8H2zM6 14h4M8 11v3",
  clock: "M8 14.5a6.5 6.5 0 1 0 0-13 6.5 6.5 0 0 0 0 13zM8 4.5V8l2.5 1.5",
  print: "M4.5 5.5v-3h7v3M4.5 11H2.5V6h11v5h-2M4.5 9h7v4.5h-7z",
  cash: "M1.5 4.5h13v7h-13zM8 10a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM3.5 6.5v3M12.5 6.5v3",
} as const;

export type IconName = keyof typeof PATHS;

export function Icon({
  name,
  size = 16,
  label,
  ...rest
}: { name: IconName; size?: number; label?: string } & Omit<SVGProps<SVGSVGElement>, "name">) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="none"
      stroke="currentColor"
      strokeWidth={name === "more" ? 2.4 : 1.4}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden={label ? undefined : true}
      role={label ? "img" : undefined}
      aria-label={label}
      focusable="false"
      {...rest}
    >
      <path d={PATHS[name]} />
    </svg>
  );
}
