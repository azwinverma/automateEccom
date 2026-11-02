import 'package:flutter/material.dart';

/// Nivaro logo (owner-approved artwork, specs/26 §4, ADR-032). The PNGs are
/// generated into assets/brand by assets/brand/scripts/render.mjs; never edit them.
abstract final class NivaroAssets {
  static const mark = 'assets/brand/nivaro-mark.png';
  static const markMono = 'assets/brand/nivaro-mark-white.png';
  static const wordmark = 'assets/brand/nivaro-wordmark-ink.png';
  static const markRatio = 384 / 263;
  static const wordRatio = 724 / 201;
}

/// The N-loop mark. [size] is the height; [monoColor] tints the single-colour mark.
class NivaroMark extends StatelessWidget {
  const NivaroMark({
    super.key,
    this.size = 24,
    this.monoColor,
    this.semanticLabel,
  });

  final double size;
  final Color? monoColor;
  final String? semanticLabel;

  @override
  Widget build(BuildContext context) {
    final image = Image.asset(
      monoColor == null ? NivaroAssets.mark : NivaroAssets.markMono,
      height: size,
      width: size * NivaroAssets.markRatio,
      color: monoColor,
      colorBlendMode: monoColor == null ? null : BlendMode.srcIn,
      filterQuality: FilterQuality.medium,
      excludeFromSemantics: true,
    );
    return semanticLabel == null
        ? ExcludeSemantics(child: image)
        : Semantics(label: semanticLabel, image: true, child: image);
  }
}

/// Mark + "nivaro" wordmark. The wordmark is tinted with [color] (ink on light,
/// white on dark) so one asset serves both themes.
class NivaroLogo extends StatelessWidget {
  const NivaroLogo({
    super.key,
    this.height = 24,
    this.color,
    this.semanticLabel = 'Nivaro',
  });

  final double height;
  final Color? color;
  final String semanticLabel;

  @override
  Widget build(BuildContext context) {
    final c = color ?? Theme.of(context).colorScheme.onSurface;
    final wordH = height * 0.6;
    return Semantics(
      label: semanticLabel,
      image: true,
      child: ExcludeSemantics(
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            NivaroMark(size: height),
            SizedBox(width: height * 0.3),
            Image.asset(
              NivaroAssets.wordmark,
              height: wordH,
              width: wordH * NivaroAssets.wordRatio,
              color: c,
              colorBlendMode: BlendMode.srcIn,
              filterQuality: FilterQuality.medium,
            ),
          ],
        ),
      ),
    );
  }
}
