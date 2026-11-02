import 'package:flutter/material.dart';

import '../brand_geometry.g.dart';

/// Nivaro N-loop mark (specs/26 §4). Geometry is generated from
/// packages/design-system/brand/geometry.mjs; never redraw it by hand.
class NivaroMark extends StatelessWidget {
  const NivaroMark({
    super.key,
    this.size = 24,
    this.monoColor,
    this.semanticLabel,
  });

  final double size;

  /// Single-colour mark (e.g. white on navy). Null = brand gradient.
  final Color? monoColor;
  final String? semanticLabel;

  @override
  Widget build(BuildContext context) {
    final mark = CustomPaint(
      size: Size.square(size),
      painter: _MarkPainter(monoColor),
    );
    return semanticLabel == null
        ? ExcludeSemantics(child: mark)
        : Semantics(label: semanticLabel, image: true, child: mark);
  }
}

class _MarkPainter extends CustomPainter {
  _MarkPainter(this.mono);

  final Color? mono;

  static Offset _p(List<num> s, int i) =>
      Offset(s[i].toDouble(), s[i + 1].toDouble());

  @override
  void paint(Canvas canvas, Size size) {
    canvas.scale(size.width / NivaroMarkGeometry.box);
    Paint stroke(Shader? shader, [Color? color]) =>
        Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = NivaroMarkGeometry.ribbon
          ..strokeCap = StrokeCap.round
          ..shader = shader
          ..color = color ?? const Color(0xFF000000);
    Shader grad(List<num> s, Color a, Color b) => LinearGradient(
      colors: [a, b],
    ).createShader(Rect.fromPoints(_p(s, 0), _p(s, 2)));
    void seg(List<num> s, Paint p) => canvas.drawLine(_p(s, 0), _p(s, 2), p);

    const d = NivaroMarkGeometry.diagonal;
    if (mono != null) {
      // Diagonal first, then a thin fold gap, then the stems (same reading as the SVG mono mark).
      canvas.saveLayer(Offset.zero & const Size(64, 64), Paint());
      seg(d, stroke(null, mono));
      final gap =
          Paint()
            ..blendMode = BlendMode.clear
            ..strokeWidth = 2.2
            ..strokeCap = StrokeCap.round;
      canvas.drawLine(const Offset(30.4, 17.2), const Offset(28.6, 23.4), gap);
      canvas.drawLine(const Offset(33.6, 46.8), const Offset(35.4, 40.6), gap);
      canvas.restore();
      seg(NivaroMarkGeometry.left, stroke(null, mono));
      seg(NivaroMarkGeometry.right, stroke(null, mono));
      return;
    }
    seg(
      d,
      stroke(grad(d, NivaroMarkGeometry.flowMid1, NivaroMarkGeometry.flowMid2)),
    );
    seg(
      d,
      stroke(
        LinearGradient(
          colors: [
            NivaroMarkGeometry.fold.withValues(alpha: 0.34),
            NivaroMarkGeometry.fold.withValues(alpha: 0),
            NivaroMarkGeometry.fold.withValues(alpha: 0),
            NivaroMarkGeometry.fold.withValues(alpha: 0.22),
          ],
          stops: const [0.08, 0.34, 0.66, 0.92],
        ).createShader(Rect.fromPoints(_p(d, 0), _p(d, 2))),
      ),
    );
    seg(
      NivaroMarkGeometry.left,
      stroke(
        grad(
          NivaroMarkGeometry.left,
          NivaroMarkGeometry.flowStart,
          NivaroMarkGeometry.flowMid1,
        ),
      ),
    );
    seg(
      NivaroMarkGeometry.right,
      stroke(
        grad(
          NivaroMarkGeometry.right,
          NivaroMarkGeometry.flowMid2,
          NivaroMarkGeometry.flowEnd,
        ),
      ),
    );
  }

  @override
  bool shouldRepaint(_MarkPainter old) => old.mono != mono;
}

/// Mark + "nivaro" wordmark. The wordmark follows [color] (ink on light, white on navy).
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
    final wordH = height * 0.72;
    return Semantics(
      label: semanticLabel,
      image: true,
      child: ExcludeSemantics(
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            NivaroMark(size: height),
            SizedBox(width: height * 0.42),
            CustomPaint(
              size: Size(
                wordH *
                    NivaroWordmarkGeometry.width /
                    NivaroWordmarkGeometry.height,
                wordH,
              ),
              painter: _WordmarkPainter(c),
            ),
          ],
        ),
      ),
    );
  }
}

/// Mirrors WORDMARK.paths in geometry.mjs (lines, one arc, one curve); circles come from the generated file.
class _WordmarkPainter extends CustomPainter {
  _WordmarkPainter(this.color);

  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    canvas.scale(size.height / NivaroWordmarkGeometry.height);
    final p =
        Paint()
          ..color = color
          ..style = PaintingStyle.stroke
          ..strokeWidth = NivaroWordmarkGeometry.stroke
          ..strokeCap = StrokeCap.round
          ..strokeJoin = StrokeJoin.round;
    final path =
        Path()
          // n
          ..moveTo(4, 17)
          ..lineTo(4, 40)
          ..moveTo(4, 26.5)
          ..arcToPoint(const Offset(22, 26.5), radius: const Radius.circular(9))
          ..lineTo(22, 40)
          // i
          ..moveTo(32, 17)
          ..lineTo(32, 40)
          // v
          ..moveTo(41.5, 17)
          ..lineTo(51.5, 40)
          ..lineTo(61.5, 17)
          // a (stem)
          ..moveTo(92.3, 17)
          ..lineTo(92.3, 40)
          // r
          ..moveTo(103.5, 17)
          ..lineTo(103.5, 40)
          ..moveTo(103.5, 29)
          ..cubicTo(103.5, 21, 108.5, 17, 116, 17);
    canvas.drawPath(path, p);
    for (final c in NivaroWordmarkGeometry.circles) {
      canvas.drawCircle(
        Offset(c[0].toDouble(), c[1].toDouble()),
        c[2].toDouble(),
        p,
      );
    }
    const dot = NivaroWordmarkGeometry.dot;
    canvas.drawCircle(
      Offset(dot[0].toDouble(), dot[1].toDouble()),
      dot[2].toDouble(),
      Paint()..color = color,
    );
  }

  @override
  bool shouldRepaint(_WordmarkPainter old) => old.color != color;
}
