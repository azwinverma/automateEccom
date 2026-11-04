import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/l10n/formatters.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/state_views.dart';
import '../data/orders_api.dart';
import 'order_labels.dart';

final orderFilterProvider = StateProvider.autoDispose<OrderFilter>(
  (ref) => OrderFilter.needsAction,
);

/// Orders, filtered by what the seller has to do next.
class OrdersScreen extends ConsumerWidget {
  const OrdersScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final filter = ref.watch(orderFilterProvider);
    final orders = ref.watch(ordersProvider(filter));
    return Scaffold(
      appBar: AppBar(title: Text(l.ordersTitle)),
      body: RefreshIndicator(
        onRefresh: () => ref.refresh(ordersProvider(filter).future),
        child: ListView(
          padding: const EdgeInsets.only(bottom: AppSpace.s8),
          children: [
            SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpace.s4,
                vertical: AppSpace.s2,
              ),
              child: Row(
                children: [
                  for (final f in OrderFilter.values) ...[
                    ChoiceChip(
                      key: Key('order-filter-${f.name}'),
                      label: Text(switch (f) {
                        OrderFilter.needsAction => l.ordersFilterNeedsAction,
                        OrderFilter.needsReview => l.ordersFilterNeedsReview,
                        OrderFilter.all => l.ordersFilterAll,
                      }),
                      selected: f == filter,
                      onSelected:
                          (_) =>
                              ref.read(orderFilterProvider.notifier).state = f,
                    ),
                    const SizedBox(width: AppSpace.s2),
                  ],
                ],
              ),
            ),
            AsyncValueView<List<OrderSummary>>(
              value: orders,
              onRetry: () => ref.invalidate(ordersProvider(filter)),
              isEmpty: (o) => o.isEmpty,
              empty: EmptyState(
                icon: Icons.receipt_long_outlined,
                title: l.ordersEmpty,
                body: l.ordersEmptyBody,
              ),
              data:
                  (items) => Column(
                    children: [
                      for (final o in items) ...[
                        OrderTile(order: o),
                        const Divider(height: 1),
                      ],
                    ],
                  ),
            ),
          ],
        ),
      ),
    );
  }
}

class OrderTile extends ConsumerWidget {
  const OrderTile({super.key, required this.order});

  final OrderSummary order;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    final review = reviewLabel(l, order.needsReview);
    return ListTile(
      key: Key('order-${order.id}'),
      minVerticalPadding: AppSpace.s3,
      title: Text(
        '${l.orderNumber(order.number)} · ${order.customerName ?? ''}',
        maxLines: 1,
        overflow: TextOverflow.ellipsis,
      ),
      subtitle: Text(
        review ?? orderStatusLabel(l, order.status),
        style: theme.textTheme.bodySmall?.copyWith(
          color: orderStatusColor(context, order),
        ),
      ),
      trailing: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          Text(
            Formatters.money(order.totalMinor, order.currency, lang),
            style: theme.textTheme.titleSmall,
          ),
          Text(
            paymentMethodLabel(l, order.paymentMethod),
            style: theme.textTheme.labelSmall?.copyWith(
              color: AppPalette.of(context).muted,
            ),
          ),
        ],
      ),
      onTap: () async {
        await context.push('/orders/${order.id}');
        ref.invalidate(ordersProvider);
      },
    );
  }
}
