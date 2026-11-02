export declare const RIBBON: number;
export interface Seg {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}
export declare const FLOW: { start: string; mid1: string; mid2: string; end: string; fold: string };
export interface TrailSeg extends Seg {
  kind: "rise" | "cross";
}
export declare function trailSegments(o: { count: number; height: number; x?: number; y?: number }): {
  segments: TrailSeg[];
  width: number;
  ribbon: number;
};
export declare const LOOP_STAGES: readonly ["create", "sell", "fulfill", "learn"];
