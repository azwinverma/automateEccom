import 'package:flutter/material.dart';

import '../tokens.g.dart';

/// Section label used instead of wrapping sections in cards.
class SectionHeader extends StatelessWidget {
  const SectionHeader(this.title, {super.key, this.trailing});

  final String title;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        AppSpace.s4,
        AppSpace.s6,
        AppSpace.s4,
        AppSpace.s2,
      ),
      child: Row(
        children: [
          Expanded(
            child: Semantics(
              header: true,
              child: Text(title, style: theme.textTheme.titleMedium),
            ),
          ),
          if (trailing != null) trailing!,
        ],
      ),
    );
  }
}
