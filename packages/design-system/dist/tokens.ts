// Generated from packages/design-system/design-tokens.json. Do not edit.
export const tokens = {
  "colors": {
    "brand-blue": "#2563EB",
    "brand-blue-soft": "#DBEAFE",
    "brand-indigo": "#4F46E5",
    "brand-indigo-soft": "#E0E7FF",
    "brand-teal": "#14B8A6",
    "brand-teal-soft": "#CCFBF1",
    "brand-coral": "#FF6B6B",
    "brand-coral-soft": "#FFE4E1",
    "brand-sun": "#FBBF24",
    "brand-sun-soft": "#FEF3C7",
    "neutral-ink": "#0F172A",
    "neutral-slate": "#475569",
    "neutral-slate-muted": "#64748B",
    "neutral-line": "#E2E8F0",
    "neutral-line-strong": "#CBD5E1",
    "neutral-cloud": "#F8FAFC",
    "neutral-paper": "#F1F5F9",
    "neutral-white": "#FFFFFF",
    "semantic-success": "#15803D",
    "semantic-success-soft": "#DCFCE7",
    "semantic-warning": "#B45309",
    "semantic-warning-soft": "#FEF3C7",
    "semantic-danger": "#B91C1C",
    "semantic-danger-soft": "#FEE2E2",
    "semantic-info": "#1D4ED8",
    "semantic-info-soft": "#DBEAFE"
  },
  "dark": {
    "surface": "#0B1220",
    "surface-raised": "#111A2E",
    "line": "#1E293B",
    "text": "#E2E8F0",
    "text-muted": "#94A3B8",
    "brand-blue": "#60A5FA",
    "success": "#4ADE80",
    "warning": "#FBBF24",
    "danger": "#F87171",
    "info": "#93C5FD"
  },
  "space": {
    "0": 0,
    "1": 4,
    "2": 8,
    "3": 12,
    "4": 16,
    "5": 20,
    "6": 24,
    "8": 32,
    "10": 40,
    "12": 48,
    "16": 64
  },
  "radius": {
    "sm": 4,
    "md": 6,
    "lg": 10,
    "full": 9999
  },
  "fontSize": {
    "xs": 12,
    "sm": 13,
    "base": 14,
    "md": 16,
    "lg": 18,
    "xl": 22,
    "2xl": 28,
    "3xl": 36
  },
  "weight": {
    "regular": 400,
    "medium": 500,
    "semibold": 600,
    "bold": 700
  },
  "lineHeight": {
    "tight": 1.2,
    "normal": 1.5,
    "devanagari": 1.7
  },
  "family": {
    "latin": "Inter, ui-sans-serif, system-ui, -apple-system, 'Segoe UI', sans-serif",
    "devanagari": "'Noto Sans Devanagari', Inter, ui-sans-serif, sans-serif",
    "mono": "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, monospace"
  },
  "duration": {
    "fast": 150,
    "standard": 220,
    "large": 320
  },
  "easing": {
    "standard": "cubic-bezier(0.2, 0, 0, 1)",
    "exit": "cubic-bezier(0.3, 0, 1, 1)"
  },
  "elevation": {
    "none": "none",
    "raised": "0 1px 2px rgba(15, 23, 42, 0.06), 0 1px 1px rgba(15, 23, 42, 0.04)",
    "overlay": "0 12px 32px rgba(15, 23, 42, 0.14), 0 2px 6px rgba(15, 23, 42, 0.08)"
  },
  "status": {
    "$description": "Semantic mapping for lifecycle states used by signature components (Channel Sync Rail, Order Journey, Autopilot Strip). Values reference color tokens.",
    "healthy": "color.brand.teal",
    "automated": "color.brand.indigo",
    "needsAttention": "color.semantic.warning",
    "failed": "color.semantic.danger",
    "pending": "color.neutral.slateMuted",
    "celebrate": "color.brand.coral"
  }
} as const;
export type ColorToken = keyof typeof tokens.colors;
