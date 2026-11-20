import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/l10n/formatters.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/state_views.dart';
import '../../fulfillment/presentation/fulfillment_labels.dart';
import '../data/procurement_api.dart';
import 'procurement_labels.dart';

/// Purchase orders with status filter chips (PRO-003). Plan without procurement → upsell view.
class PurchaseOrdersScreen extends ConsumerStatefulWidget {
  const PurchaseOrdersScreen({super.key, this.initialStatus});

  final String? initialStatus;

  @override
  ConsumerState<PurchaseOrdersScreen> createState() =>
      _PurchaseOrdersScreenState();
}

class _PurchaseOrdersScreenState extends ConsumerState<PurchaseOrdersScreen> {
  late String? _status = widget.initialStatus;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final palette = AppPalette.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    final value = ref.watch(purchaseOrdersProvider(_status));
    return Scaffold(
      appBar: AppBar(title: Text(l.poTitle)),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(purchaseOrdersProvider(_status));
          await ref.read(purchaseOrdersProvider(_status).future);
        },
        child: ListView(
          children: [
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpace.s4,
                vertical: AppSpace.s2,
              ),
              child: Row(
                children: [
                  for (final f in poFilters)
                    Padding(
                      padding: const EdgeInsets.only(right: AppSpace.s2),
                      child: ChoiceChip(
                        key: Key('po-filter-${f ?? 'all'}'),
                        label: Text(
                          f == null ? l.poFilterAll : poStatusLabel(l, f),
                        ),
                        selected: _status == f,
                        onSelected: (_) => setState(() => _status = f),
                      ),
                    ),
                ],
              ),
            ),
            AsyncValueView<List<PurchaseOrder>>(
              value: value,
              onRetry: () => ref.invalidate(purchaseOrdersProvider(_status)),
              loading: const SkeletonList(rows: 4),
              isEmpty: (items) => items.isEmpty,
              empty: Padding(
                padding: const EdgeInsets.all(AppSpace.s4),
                child: Text(
                  l.poEmpty,
                  key: const Key('po-empty'),
                  style: TextStyle(color: palette.muted),
                ),
              ),
              data:
                  (items) => Column(
                    children: [
                      for (final po in items)
                        ListTile(
                          key: Key('po-row-${po.id}'),
                          onTap:
                              () => context.push('/purchase-orders/${po.id}'),
                          title: Text(
                            l.poListItem(po.number, po.supplierName),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          subtitle: Text(
                            [
                              l.poTotal(
                                Formatters.money(
                                  po.totalMinor,
                                  po.currency,
                                  lang,
                                ),
                              ),
                              l.poItems(po.lines.length.toString()),
                              if (po.source == 'recommendation')
                                l.poFromSuggestion,
                            ].join(' · '),
                          ),
                          trailing: StatusChip(
                            label: poStatusLabel(l, po.status),
                            colors: poStatusColors(context, po.status),
                          ),
                        ),
                    ],
                  ),
            ),
          ],
        ),
      ),
    );
  }
}
