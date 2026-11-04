import 'package:flutter/material.dart';

import '../../../../core/l10n/gen/app_localizations.dart';
import '../../../../design/tokens.g.dart';

/// Capabilities reachable from Home. Built ones open the real screen; the
/// rest route to an honest "coming soon" explainer until the domain exists.
enum QuickAction {
  addProduct('add-product', Icons.add_box_outlined),
  captureProduct('capture-product', Icons.photo_camera_outlined),
  generateContent('generate-content', Icons.edit_note_outlined),
  createReel('create-reel', Icons.movie_creation_outlined),
  viewOrders('orders', Icons.receipt_long_outlined),
  viewMessages('messages', Icons.chat_bubble_outline);

  const QuickAction(this.slug, this.icon);
  final String slug;
  final IconData icon;

  static QuickAction? fromSlug(String slug) {
    for (final a in values) {
      if (a.slug == slug) return a;
    }
    return null;
  }

  /// Live flows (Phase 1) vs. honest "coming soon" explainers.
  String get route => switch (this) {
    addProduct || captureProduct => '/studio/capture',
    generateContent => '/studio/drafts',
    viewOrders => '/orders',
    viewMessages => '/inbox',
    _ => '/soon/$slug',
  };

  /// Bottom-navigation tabs are switched to (go), not pushed on top.
  bool get isTab => this == viewOrders || this == viewMessages;

  String label(AppLocalizations l) => switch (this) {
    addProduct => l.qaAddProduct,
    captureProduct => l.qaCaptureProduct,
    generateContent => l.qaGenerateContent,
    createReel => l.qaCreateReel,
    viewOrders => l.qaViewOrders,
    viewMessages => l.qaViewMessages,
  };

  String description(AppLocalizations l) => switch (this) {
    addProduct => l.soonAddProductBody,
    captureProduct => l.soonCaptureProductBody,
    generateContent => l.soonGenerateContentBody,
    createReel => l.soonCreateReelBody,
    viewOrders => l.soonViewOrdersBody,
    viewMessages => l.soonViewMessagesBody,
  };
}

/// Three-column grid of large, flat tap targets (≥ 72dp tall), reachable
/// with a thumb. Capture is emphasised: it is the primary mobile job.
class QuickActionsGrid extends StatelessWidget {
  const QuickActionsGrid({super.key, required this.onSelected});

  final ValueChanged<QuickAction> onSelected;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: AppSpace.s4),
      child: LayoutBuilder(
        builder: (context, constraints) {
          const gap = AppSpace.s2;
          final width = (constraints.maxWidth - gap * 2) / 3;
          return Wrap(
            spacing: gap,
            runSpacing: gap,
            children: [
              for (final a in QuickAction.values)
                SizedBox(
                  width: width,
                  child: Material(
                    color:
                        a == QuickAction.captureProduct
                            ? theme.colorScheme.primaryContainer
                            : theme.colorScheme.surface,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(AppRadius.md),
                      side: BorderSide(
                        color:
                            a == QuickAction.captureProduct
                                ? theme.colorScheme.primaryContainer
                                : theme.colorScheme.outlineVariant,
                      ),
                    ),
                    clipBehavior: Clip.antiAlias,
                    child: InkWell(
                      onTap: () => onSelected(a),
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(minHeight: 76),
                        child: Padding(
                          padding: const EdgeInsets.all(AppSpace.s3),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Icon(
                                a.icon,
                                color:
                                    a == QuickAction.captureProduct
                                        ? theme.colorScheme.primary
                                        : theme.colorScheme.onSurface,
                              ),
                              const SizedBox(height: AppSpace.s2),
                              Text(
                                a.label(l),
                                style: theme.textTheme.labelMedium,
                                maxLines: 2,
                                overflow: TextOverflow.ellipsis,
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }
}
