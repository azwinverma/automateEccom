// Generated from packages/design-system/design-tokens.json. Do not edit. (brand geometry from packages/design-system/brand/geometry.mjs)
// ignore_for_file: constant_identifier_names
import 'package:flutter/painting.dart';

/// N-loop mark in a 64×64 box. Segments are [x1, y1, x2, y2]; ribbon width 12, round caps.
abstract final class NivaroMarkGeometry {
  static const box = 64.0;
  static const ribbon = 12.0;
  static const diagonal = [24, 16, 40, 48];
  static const left = [14, 50, 24, 16];
  static const right = [40, 48, 50, 14];
  static const flowStart = Color(0xFF2563EB);
  static const flowMid1 = Color(0xFF2F7BEF);
  static const flowMid2 = Color(0xFF16A9B8);
  static const flowEnd = Color(0xFF14B8A6);
  static const fold = Color(0xFF0F172A);
}

/// Wordmark "nivaro" (viewBox 150×46, stroke 6.4). Circles are [cx, cy, r].
abstract final class NivaroWordmarkGeometry {
  static const width = 150.0;
  static const height = 46.0;
  static const stroke = 6.4;
  static const circles = [[81, 28.5, 11.3], [134.5, 28.5, 11.3]];
  static const dot = [32, 6.6, 3.9];
}
