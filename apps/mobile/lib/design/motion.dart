import 'package:flutter/material.dart';

import 'tokens.g.dart';

/// Motion durations from tokens, collapsed to zero when the OS asks for
/// reduced motion.
abstract final class Motion {
  static Duration of(BuildContext context, Duration base) =>
      MediaQuery.maybeDisableAnimationsOf(context) ?? false
          ? Duration.zero
          : base;

  static Duration fast(BuildContext c) => of(c, AppMotion.fast);
  static Duration standard(BuildContext c) => of(c, AppMotion.standard);
  static Duration large(BuildContext c) => of(c, AppMotion.large);
}

/// Page transitions that become instant when animations are disabled.
class ReducedMotionPageTransitionsBuilder extends PageTransitionsBuilder {
  const ReducedMotionPageTransitionsBuilder(this.inner);

  final PageTransitionsBuilder inner;

  @override
  Widget buildTransitions<T>(
    PageRoute<T> route,
    BuildContext context,
    Animation<double> animation,
    Animation<double> secondaryAnimation,
    Widget child,
  ) {
    if (MediaQuery.maybeDisableAnimationsOf(context) ?? false) return child;
    return inner.buildTransitions(
      route,
      context,
      animation,
      secondaryAnimation,
      child,
    );
  }
}
