import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/errors/api_error.dart';
import '../../../core/l10n/formatters.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../core/l10n/money_input.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/section_header.dart';
import '../../../design/widgets/state_views.dart';
import '../../channels/data/channels_api.dart';
import '../../channels/presentation/reconnect_sheet.dart';
import '../../content/data/content_api.dart';
import '../../studio/data/studio_api.dart';
import '../../studio/presentation/review_view.dart'
    show priceErrorText, variantLabel;
import '../../studio/presentation/widgets/attribute_review_row.dart'
    show humaniseKey;
import '../data/catalog_api.dart';

final productProvider = FutureProvider.autoDispose
    .family<ProductDetail, String>(
      (ref, id) => ref.watch(catalogApiProvider).product(id),
    );

final listingPollDelayProvider = Provider<Duration>(
  (ref) => const Duration(seconds: 3),
);

/// Listings, re-polled while any channel is still pending/publishing.
final listingsProvider = StreamProvider.autoDispose
    .family<List<ChannelListing>, String>((ref, id) async* {
      final api = ref.watch(catalogApiProvider);
      final every = ref.watch(listingPollDelayProvider);
      for (var i = 0; i < 40; i++) {
        final items = await api.listings(id);
        yield items;
        if (!items.any((l) => l.inFlight)) return;
        await Future<void>.delayed(every);
      }
    });

/// The Studio job a product came from (needed to create posts). Uses the
/// `?job=` hint when present, else looks through applied jobs.
final productJobIdProvider = FutureProvider.autoDispose
    .family<String?, (String, String?)>((ref, args) async {
      final (productId, hint) = args;
      if (hint != null && hint.isNotEmpty) return hint;
      final jobs = await ref
          .watch(studioApiProvider)
          .listJobs(status: 'applied', limit: 100);
      return jobs.where((j) => j.productId == productId).firstOrNull?.id;
    });

/// After create: confirm AI details → go live → publish → posts.
class ProductScreen extends ConsumerStatefulWidget {
  const ProductScreen({super.key, required this.productId, this.jobId});

  final String productId;
  final String? jobId;

  @override
  ConsumerState<ProductScreen> createState() => _ProductScreenState();
}

class _ProductScreenState extends ConsumerState<ProductScreen> {
  ProductDetail? _local;
  bool _busy = false;
  ApiError? _error;
  final _attributesKey = GlobalKey();
  final Set<String> _publishTo = {};
  final Set<String> _postTo = {};

  ProductDetail? get _p =>
      _local ?? ref.watch(productProvider(widget.productId)).valueOrNull;

  Future<void> _run(Future<void> Function() action) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await action();
    } on Object catch (e) {
      final err = asApiError(e);
      if (err.code == 'version_conflict') {
        _local = null;
        ref.invalidate(productProvider(widget.productId));
      }
      if (mounted) setState(() => _error = err);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<String?> _prompt({
    required String title,
    String initial = '',
    bool price = false,
  }) {
    final l = AppLocalizations.of(context);
    final ctl = TextEditingController(text: initial);
    return showDialog<String>(
      context: context,
      builder: (ctx) {
        String? error;
        return StatefulBuilder(
          builder:
              (ctx, setLocal) => AlertDialog(
                title: Text(title),
                content: TextField(
                  controller: ctl,
                  autofocus: true,
                  keyboardType:
                      price
                          ? const TextInputType.numberWithOptions(decimal: true)
                          : TextInputType.text,
                  inputFormatters:
                      price
                          ? [
                            FilteringTextInputFormatter.allow(
                              RegExp(r'[0-9०-९.,\s]'),
                            ),
                          ]
                          : null,
                  decoration: InputDecoration(
                    prefixText:
                        price ? (l.localeName == 'ne' ? 'रू ' : 'Rs ') : null,
                    errorText: error,
                  ),
                ),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.pop(ctx),
                    child: Text(l.actionCancel),
                  ),
                  FilledButton(
                    onPressed: () {
                      if (price) {
                        final r = parseRupeesToPaisa(ctl.text);
                        if (r.error != null) {
                          setLocal(() => error = priceErrorText(l, r.error!));
                          return;
                        }
                      } else if (ctl.text.trim().isEmpty) {
                        setLocal(() => error = l.validationTitleRequired);
                        return;
                      }
                      Navigator.pop(ctx, ctl.text);
                    },
                    child: Text(l.actionSave),
                  ),
                ],
              ),
        );
      },
    ).whenComplete(ctl.dispose);
  }

  Future<void> _editPrice(ProductVariant v) async {
    final l = AppLocalizations.of(context);
    final text = await _prompt(
      title: '${l.productEditPrice} · ${variantLabel(l, v.options)}',
      initial: v.priceMinor > 0 ? paisaToRupeeInput(v.priceMinor) : '',
      price: true,
    );
    if (text == null) return;
    final paisa = parseRupeesToPaisa(text).paisa!;
    await _run(() async {
      final p = await ref
          .read(catalogApiProvider)
          .updateVariantPrice(widget.productId, v.id, paisa);
      setState(() => _local = p);
    });
  }

  Future<void> _editTitle(ProductDetail p) async {
    final l = AppLocalizations.of(context);
    final text = await _prompt(title: l.productEditTitle, initial: p.title);
    if (text == null) return;
    await _run(() async {
      final updated = await ref
          .read(catalogApiProvider)
          .updateTitle(widget.productId, text.trim(), p.version);
      setState(() => _local = updated);
    });
  }

  Future<void> _confirm(List<String> keys) => _run(() async {
    final p = await ref
        .read(catalogApiProvider)
        .confirmAttributes(widget.productId, keys);
    setState(() => _local = p);
  });

  Future<void> _editAttribute(ProductAttribute a) async {
    final l = AppLocalizations.of(context);
    final text = await _prompt(
      title: l.attrEditTitle(humaniseKey(a.key)),
      initial: a.value,
    );
    if (text == null) return;
    await _run(() async {
      final p = await ref.read(catalogApiProvider).setAttributes(
        widget.productId,
        {a.key: text.trim()},
      );
      setState(() => _local = p);
    });
  }

  Future<void> _goLive(ProductDetail p) => _run(() async {
    final updated = await ref
        .read(catalogApiProvider)
        .setStatus(widget.productId, 'active', p.version);
    setState(() => _local = updated);
  });

  Future<void> _publish() => _run(() async {
    await ref
        .read(catalogApiProvider)
        .publish(widget.productId, _publishTo.toList());
    _publishTo.clear();
    ref.invalidate(listingsProvider(widget.productId));
  });

  Future<void> _createPosts(String jobId) => _run(() async {
    final posts = await ref
        .read(contentApiProvider)
        .fromStudio(jobId, _postTo.toList());
    _postTo.clear();
    if (mounted && posts.isNotEmpty) {
      unawaited(context.push('/posts?ids=${posts.map((p) => p.id).join(',')}'));
    }
  });

  void _fixProblem(String problem, ProductDetail p) {
    switch (problem) {
      case 'price_required':
        final v =
            p.activeVariants.where((v) => v.priceMinor <= 0).firstOrNull ??
            p.activeVariants.firstOrNull;
        if (v != null) _editPrice(v);
      case 'title_required':
        _editTitle(p);
      case 'unconfirmed_ai_attributes':
        final ctx = _attributesKey.currentContext;
        if (ctx != null) Scrollable.ensureVisible(ctx);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final async = ref.watch(productProvider(widget.productId));
    final p = _p;
    return Scaffold(
      appBar: AppBar(title: Text(l.productTitle)),
      body:
          p == null
              ? AsyncValueView<ProductDetail>(
                value: async,
                onRetry:
                    () => ref.invalidate(productProvider(widget.productId)),
                data: (_) => const SizedBox.shrink(),
              )
              : RefreshIndicator(
                onRefresh: () async {
                  _local = null;
                  ref
                    ..invalidate(productProvider(widget.productId))
                    ..invalidate(listingsProvider(widget.productId))
                    ..invalidate(channelsProvider);
                  await ref.read(productProvider(widget.productId).future);
                },
                child: _body(context, p),
              ),
    );
  }

  Widget _body(BuildContext context, ProductDetail p) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    final live = p.status == 'active';
    final title =
        lang == 'ne' && (p.titleNe ?? '').isNotEmpty ? p.titleNe! : p.title;
    final problems =
        _error?.code == 'not_publishable'
            ? ((_error!.details['problems'] as List<Object?>?) ?? const [])
                .whereType<String>()
                .toList()
            : const <String>[];
    const pad = EdgeInsets.symmetric(horizontal: AppSpace.s4);

    return ListView(
      padding: const EdgeInsets.only(bottom: AppSpace.s8),
      children: [
        Padding(
          padding: pad,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(title, style: theme.textTheme.headlineSmall),
              const SizedBox(height: AppSpace.s1),
              Text(
                switch (p.status) {
                  'active' => l.productIsLive,
                  'archived' => l.productStatusArchived,
                  _ => l.productSaved,
                },
                key: const Key('product-status'),
                style: theme.textTheme.labelLarge?.copyWith(
                  color:
                      live
                          ? palette.success
                          : theme.colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
        SectionHeader(l.productPrices),
        for (final v in p.activeVariants)
          ListTile(
            tileColor: theme.colorScheme.surface,
            shape: const RoundedRectangleBorder(),
            title: Text(variantLabel(l, v.options)),
            subtitle: v.sku == null ? null : Text(v.sku!),
            trailing: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  v.priceMinor > 0
                      ? Formatters.money(v.priceMinor, v.currency, lang)
                      : l.validationPriceRequired,
                  style: theme.textTheme.titleSmall?.copyWith(
                    color: v.priceMinor > 0 ? null : palette.danger,
                  ),
                ),
                IconButton(
                  tooltip: l.productEditPrice,
                  onPressed: _busy ? null : () => _editPrice(v),
                  icon: const Icon(Icons.edit_outlined),
                ),
              ],
            ),
          ),
        if (p.unconfirmed.isNotEmpty) ...[
          SectionHeader(
            l.productConfirmSection,
            key: _attributesKey,
            trailing: TextButton(
              onPressed:
                  _busy
                      ? null
                      : () => _confirm([for (final a in p.unconfirmed) a.key]),
              child: Text(l.productConfirmAll),
            ),
          ),
          for (final a in p.unconfirmed)
            Container(
              decoration: BoxDecoration(
                color: palette.automationSoft,
                border: Border(
                  left: BorderSide(color: palette.automation, width: 3),
                ),
              ),
              child: ListTile(
                title: Text(a.value),
                subtitle: Text(
                  [
                    humaniseKey(a.key),
                    if (a.confidence != null)
                      l.confidenceLabel(
                        Formatters.percent(a.confidence!, lang),
                      ),
                  ].join(' · '),
                ),
                trailing: Wrap(
                  children: [
                    TextButton(
                      onPressed: _busy ? null : () => _confirm([a.key]),
                      child: Text(l.attrAccept),
                    ),
                    IconButton(
                      tooltip: l.attrEdit,
                      onPressed: _busy ? null : () => _editAttribute(a),
                      icon: const Icon(Icons.edit_outlined),
                    ),
                  ],
                ),
              ),
            ),
        ],
        const SizedBox(height: AppSpace.s4),
        if (_error != null && problems.isEmpty)
          Padding(padding: pad, child: InlineError(error: _error!)),
        if (problems.isNotEmpty)
          Padding(
            padding: pad,
            child: _Problems(
              problems: problems,
              onFix: (pr) => _fixProblem(pr, p),
            ),
          ),
        if (!live)
          Padding(
            padding: const EdgeInsets.all(AppSpace.s4),
            child: FilledButton.icon(
              key: const Key('go-live'),
              style: FilledButton.styleFrom(
                minimumSize: const Size.fromHeight(52),
              ),
              onPressed: _busy ? null : () => _goLive(p),
              icon: const Icon(Icons.storefront_outlined),
              label: Text(l.productGoLive),
            ),
          ),
        _PublishSection(
          productId: widget.productId,
          live: live,
          busy: _busy,
          selected: _publishTo,
          onToggle:
              (id) => setState(
                () =>
                    _publishTo.contains(id)
                        ? _publishTo.remove(id)
                        : _publishTo.add(id),
              ),
          onPublish: _publish,
        ),
        _PostsSection(
          productId: widget.productId,
          jobHint: widget.jobId,
          busy: _busy,
          selected: _postTo,
          onToggle:
              (id) => setState(
                () =>
                    _postTo.contains(id) ? _postTo.remove(id) : _postTo.add(id),
              ),
          onCreate: _createPosts,
        ),
      ],
    );
  }
}

class _Problems extends StatelessWidget {
  const _Problems({required this.problems, required this.onFix});

  final List<String> problems;
  final ValueChanged<String> onFix;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final palette = AppPalette.of(context);
    final theme = Theme.of(context);
    return Container(
      padding: const EdgeInsets.all(AppSpace.s3),
      decoration: BoxDecoration(
        color: palette.dangerSoft,
        borderRadius: BorderRadius.circular(AppRadius.md),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            l.errNotPublishable,
            style: theme.textTheme.titleSmall?.copyWith(color: palette.danger),
          ),
          for (final pr in problems)
            Row(
              children: [
                Expanded(
                  child: Text(switch (pr) {
                    'price_required' => l.productProblemPrice,
                    'unconfirmed_ai_attributes' => l.productProblemAttributes,
                    'active_variant_required' => l.productProblemVariant,
                    'title_required' => l.productProblemTitle,
                    _ => l.errNotPublishable,
                  }, key: Key('problem-$pr')),
                ),
                if (pr != 'active_variant_required')
                  TextButton(
                    onPressed: () => onFix(pr),
                    child: Text(l.productFix),
                  ),
              ],
            ),
        ],
      ),
    );
  }
}

String listingStatusLabel(AppLocalizations l, String status) =>
    switch (status) {
      'pending' => l.listingPending,
      'publishing' => l.listingPublishing,
      'published' => l.listingPublished,
      'failed' => l.listingFailed,
      'out_of_sync' => l.listingOutOfSync,
      'unpublished' => l.listingUnpublished,
      _ => status,
    };

class _PublishSection extends ConsumerWidget {
  const _PublishSection({
    required this.productId,
    required this.live,
    required this.busy,
    required this.selected,
    required this.onToggle,
    required this.onPublish,
  });

  final String productId;
  final bool live;
  final bool busy;
  final Set<String> selected;
  final ValueChanged<String> onToggle;
  final VoidCallback onPublish;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final listings =
        ref.watch(listingsProvider(productId)).valueOrNull ?? const [];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SectionHeader(l.publishSection),
        AsyncValueView<List<ChannelConnection>>(
          value: ref.watch(channelsProvider),
          onRetry: () => ref.invalidate(channelsProvider),
          loading: const SkeletonList(rows: 1),
          data: (all) {
            final eligible =
                all
                    .where(
                      (c) =>
                          c.supports('product_listing') &&
                          (c.isConnected || c.needsReconnect),
                    )
                    .toList();
            if (eligible.isEmpty) return EmptyState(title: l.publishNoChannels);
            return Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                if (!live)
                  Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: AppSpace.s4,
                    ),
                    child: Text(
                      l.publishNeedsLive,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ),
                for (final c in eligible)
                  Builder(
                    builder: (context) {
                      final lst =
                          listings
                              .where((x) => x.connectionId == c.id)
                              .firstOrNull;
                      final statusText =
                          lst == null
                              ? null
                              : [
                                listingStatusLabel(l, lst.status),
                                if (lst.lastErrorCode != null)
                                  l.listingError(lst.lastErrorCode!),
                              ].join(' · ');
                      if (c.needsReconnect) {
                        return ListTile(
                          leading: Icon(Icons.link_off, color: palette.danger),
                          title: Text(c.label),
                          subtitle: Text(l.channelExpiredNote),
                          trailing: TextButton(
                            onPressed:
                                () => showReconnectSheet(
                                  context,
                                  connectionId: c.id,
                                  channelName: c.label,
                                ),
                            child: Text(l.channelReconnect),
                          ),
                        );
                      }
                      return CheckboxListTile(
                        key: Key('publish-${c.id}'),
                        value: selected.contains(c.id),
                        onChanged: live && !busy ? (_) => onToggle(c.id) : null,
                        controlAffinity: ListTileControlAffinity.leading,
                        title: Text(c.label),
                        subtitle:
                            statusText == null
                                ? null
                                : Text(
                                  statusText,
                                  style: TextStyle(
                                    color:
                                        lst!.status == 'failed'
                                            ? palette.danger
                                            : lst.status == 'published'
                                            ? palette.success
                                            : null,
                                  ),
                                ),
                      );
                    },
                  ),
                Padding(
                  padding: const EdgeInsets.all(AppSpace.s4),
                  child: OutlinedButton(
                    style: OutlinedButton.styleFrom(
                      minimumSize: const Size.fromHeight(52),
                    ),
                    onPressed:
                        live && !busy && selected.isNotEmpty ? onPublish : null,
                    child: Text(
                      selected.isEmpty ? l.publishSelectOne : l.publishAction,
                    ),
                  ),
                ),
              ],
            );
          },
        ),
      ],
    );
  }
}

class _PostsSection extends ConsumerWidget {
  const _PostsSection({
    required this.productId,
    required this.jobHint,
    required this.busy,
    required this.selected,
    required this.onToggle,
    required this.onCreate,
  });

  final String productId;
  final String? jobHint;
  final bool busy;
  final Set<String> selected;
  final ValueChanged<String> onToggle;
  final ValueChanged<String> onCreate;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final jobId =
        ref.watch(productJobIdProvider((productId, jobHint))).valueOrNull;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SectionHeader(l.postsSection),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpace.s4),
          child: Text(
            l.postsIntro,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ),
        if (jobId == null)
          EmptyState(title: l.postsNoDraft)
        else
          AsyncValueView<List<ChannelConnection>>(
            value: ref.watch(channelsProvider),
            onRetry: () => ref.invalidate(channelsProvider),
            loading: const SkeletonList(rows: 1),
            data: (all) {
              final eligible =
                  all
                      .where(
                        (c) => c.isConnected && c.supports('content_publish'),
                      )
                      .toList();
              if (eligible.isEmpty) return EmptyState(title: l.postsNoChannels);
              return Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  for (final c in eligible)
                    CheckboxListTile(
                      key: Key('post-${c.id}'),
                      value: selected.contains(c.id),
                      onChanged: busy ? null : (_) => onToggle(c.id),
                      controlAffinity: ListTileControlAffinity.leading,
                      title: Text(c.label),
                    ),
                  Padding(
                    padding: const EdgeInsets.all(AppSpace.s4),
                    child: OutlinedButton(
                      style: OutlinedButton.styleFrom(
                        minimumSize: const Size.fromHeight(52),
                      ),
                      onPressed:
                          !busy && selected.isNotEmpty
                              ? () => onCreate(jobId)
                              : null,
                      child: Text(
                        selected.isEmpty ? l.publishSelectOne : l.postsCreate,
                      ),
                    ),
                  ),
                ],
              );
            },
          ),
      ],
    );
  }
}
