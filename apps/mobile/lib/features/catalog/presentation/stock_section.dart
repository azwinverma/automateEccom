import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/errors/api_error.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/section_header.dart';
import '../../../design/widgets/state_views.dart';
import '../data/stock_api.dart';

/// Per-variant stock from the inventory ledger, with "Receive stock".
/// The server enforces `inventory.adjust`; a refusal shows inline.
class StockSection extends ConsumerStatefulWidget {
  const StockSection({super.key, required this.productId});

  final String productId;

  @override
  ConsumerState<StockSection> createState() => _StockSectionState();
}

class _StockSectionState extends ConsumerState<StockSection> {
  bool _busy = false;
  ApiError? _error;

  Future<void> _receive(VariantStock v) async {
    final qty = await showDialog<int>(
      context: context,
      builder: (_) => _QuantityDialog(title: v.title),
    );
    if (qty == null || !mounted) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref.read(stockApiProvider).receive(v.variantId, qty);
      ref.invalidate(productStockProvider(widget.productId));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(AppLocalizations.of(context).stockReceived)),
        );
      }
    } on Object catch (e) {
      if (mounted) setState(() => _error = asApiError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SectionHeader(l.stockSection),
        AsyncValueView<List<VariantStock>>(
          value: ref.watch(productStockProvider(widget.productId)),
          onRetry: () => ref.invalidate(productStockProvider(widget.productId)),
          loading: const SkeletonList(rows: 2),
          data:
              (items) => Column(
                children: [
                  for (final v in items)
                    ListTile(
                      key: Key('stock-${v.variantId}'),
                      title: Text(
                        v.title == 'Default' ? (v.sku ?? v.title) : v.title,
                      ),
                      subtitle: Text(
                        v.tracked
                            ? l.stockDetail(v.onHand, v.reserved)
                            : l.stockUntracked,
                      ),
                      trailing: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          if (v.tracked)
                            Text(
                              v.low
                                  ? '${l.stockAvailable(v.available)} · ${l.stockLow}'
                                  : l.stockAvailable(v.available),
                              style: theme.textTheme.titleSmall?.copyWith(
                                color:
                                    v.available <= 0 || v.low
                                        ? palette.danger
                                        : null,
                              ),
                            ),
                          IconButton(
                            key: Key('stock-receive-${v.variantId}'),
                            tooltip: l.stockReceive,
                            onPressed: _busy ? null : () => _receive(v),
                            icon: const Icon(Icons.add_box_outlined),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
        ),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpace.s4),
            child: InlineError(error: _error!),
          ),
      ],
    );
  }
}

class _QuantityDialog extends StatefulWidget {
  const _QuantityDialog({required this.title});

  final String title;

  @override
  State<_QuantityDialog> createState() => _QuantityDialogState();
}

class _QuantityDialogState extends State<_QuantityDialog> {
  final _c = TextEditingController();

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  int? get _qty {
    final n = int.tryParse(_c.text.trim());
    return n != null && n > 0 && n <= 1000000 ? n : null;
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return AlertDialog(
      title: Text(l.stockReceive),
      content: TextField(
        key: const Key('stock-qty'),
        controller: _c,
        autofocus: true,
        keyboardType: TextInputType.number,
        inputFormatters: [FilteringTextInputFormatter.digitsOnly],
        decoration: InputDecoration(
          labelText: l.stockQuantity,
          helperText: widget.title,
        ),
        onChanged: (_) => setState(() {}),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text(l.commonCancel),
        ),
        FilledButton(
          key: const Key('stock-qty-save'),
          onPressed:
              _qty == null ? null : () => Navigator.of(context).pop(_qty),
          child: Text(l.stockSave),
        ),
      ],
    );
  }
}
