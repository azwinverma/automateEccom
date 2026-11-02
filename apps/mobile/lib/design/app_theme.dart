import 'package:flutter/material.dart';

import 'motion.dart';
import 'tokens.g.dart';

/// Semantic + brand accents that Material's ColorScheme has no slot for.
@immutable
class AppPalette extends ThemeExtension<AppPalette> {
  const AppPalette({
    required this.success,
    required this.successSoft,
    required this.warning,
    required this.warningSoft,
    required this.danger,
    required this.dangerSoft,
    required this.info,
    required this.infoSoft,
    required this.accentSun,
    required this.accentTeal,
    required this.muted,
    required this.line,
    required this.automation,
    required this.automationSoft,
  });

  static const light = AppPalette(
    success: AppColors.semanticSuccess,
    successSoft: AppColors.semanticSuccessSoft,
    warning: AppColors.semanticWarning,
    warningSoft: AppColors.semanticWarningSoft,
    danger: AppColors.semanticDanger,
    dangerSoft: AppColors.semanticDangerSoft,
    info: AppColors.semanticInfo,
    infoSoft: AppColors.semanticInfoSoft,
    accentSun: AppColors.brandSun,
    accentTeal: AppColors.brandTeal,
    muted: AppColors.neutralSlateMuted,
    line: AppColors.neutralLine,
    automation: AppColorsLight.textBrand,
    automationSoft: AppColorsLight.surfaceBrandTint,
  );

  static const dark = AppPalette(
    success: AppColors.darkSuccess,
    successSoft: Color(0x334ADE80),
    warning: AppColors.darkWarning,
    warningSoft: Color(0x33FBBF24),
    danger: AppColors.darkDanger,
    dangerSoft: Color(0x33F87171),
    info: AppColors.darkInfo,
    infoSoft: Color(0x3393C5FD),
    accentSun: AppColors.brandSun,
    accentTeal: AppColors.brandTeal,
    muted: AppColors.darkTextMuted,
    line: AppColors.darkLine,
    automation: AppColorsDark.textBrand,
    automationSoft: AppColorsDark.surfaceBrandTint,
  );

  final Color success;
  final Color successSoft;
  final Color warning;
  final Color warningSoft;
  final Color danger;
  final Color dangerSoft;
  final Color info;
  final Color infoSoft;
  final Color accentSun;
  final Color accentTeal;
  final Color muted;
  final Color line;

  /// Nivaro Blue (strong): marks AI/automation-originated content and decisions.
  final Color automation;
  final Color automationSoft;

  static AppPalette of(BuildContext context) =>
      Theme.of(context).extension<AppPalette>() ?? light;

  @override
  AppPalette copyWith() => this;

  @override
  AppPalette lerp(AppPalette? other, double t) =>
      t < 0.5 ? this : (other ?? this);
}

/// Material 3 restyled to the Nivaro tokens: 6px corners (no pills),
/// neutral-first surfaces, no surface tint, Inter / Noto Sans Devanagari.
abstract final class AppTheme {
  static const latinFamily = 'Inter';
  static const devanagariFamily = 'NotoSansDevanagari';

  static ThemeData light({Locale? locale}) => _build(
    brightness: Brightness.light,
    locale: locale,
    scheme: const ColorScheme(
      brightness: Brightness.light,
      primary: AppColors.brandBlue,
      onPrimary: AppColors.neutralWhite,
      primaryContainer: AppColors.brandBlueSoft,
      onPrimaryContainer: AppColors.neutralInk,
      secondary: AppColors.brandTeal,
      onSecondary: AppColors.neutralInk,
      secondaryContainer: AppColors.brandTealSoft,
      onSecondaryContainer: AppColors.neutralInk,
      tertiary: AppColors.brandCoral,
      onTertiary: AppColors.neutralInk,
      tertiaryContainer: AppColors.brandCoralSoft,
      onTertiaryContainer: AppColors.neutralInk,
      error: AppColors.semanticDanger,
      onError: AppColors.neutralWhite,
      errorContainer: AppColors.semanticDangerSoft,
      onErrorContainer: AppColors.semanticDanger,
      surface: AppColors.neutralWhite,
      onSurface: AppColors.neutralInk,
      onSurfaceVariant: AppColors.neutralSlate,
      surfaceContainerLowest: AppColors.neutralWhite,
      surfaceContainerLow: AppColors.neutralCloud,
      surfaceContainer: AppColors.neutralCloud,
      surfaceContainerHigh: AppColors.neutralPaper,
      surfaceContainerHighest: AppColors.neutralPaper,
      outline: AppColors.neutralLineStrong,
      outlineVariant: AppColors.neutralLine,
      inverseSurface: AppColors.neutralInk,
      onInverseSurface: AppColors.neutralCloud,
      inversePrimary: AppColors.darkBrandBlue,
      shadow: AppColors.neutralInk,
      scrim: AppColors.neutralInk,
      surfaceTint: Colors.transparent,
    ),
    palette: AppPalette.light,
    scaffold: AppColors.neutralCloud,
  );

  static ThemeData dark({Locale? locale}) => _build(
    brightness: Brightness.dark,
    locale: locale,
    scheme: const ColorScheme(
      brightness: Brightness.dark,
      primary: AppColors.darkBrandBlue,
      onPrimary: AppColors.darkSurface,
      primaryContainer: Color(0xFF1E3A8A),
      onPrimaryContainer: AppColors.darkText,
      secondary: AppColors.brandTeal,
      onSecondary: AppColors.darkSurface,
      secondaryContainer: Color(0xFF134E4A),
      onSecondaryContainer: AppColors.darkText,
      tertiary: AppColors.brandCoral,
      onTertiary: AppColors.darkSurface,
      tertiaryContainer: Color(0xFF7F1D1D),
      onTertiaryContainer: AppColors.darkText,
      error: AppColors.darkDanger,
      onError: AppColors.darkSurface,
      errorContainer: Color(0xFF450A0A),
      onErrorContainer: AppColors.darkDanger,
      surface: AppColors.darkSurface,
      onSurface: AppColors.darkText,
      onSurfaceVariant: AppColors.darkTextMuted,
      surfaceContainerLowest: AppColors.darkSurface,
      surfaceContainerLow: AppColors.darkSurface,
      surfaceContainer: AppColors.darkSurfaceRaised,
      surfaceContainerHigh: AppColors.darkSurfaceRaised,
      surfaceContainerHighest: AppColors.darkLine,
      outline: AppColors.darkLine,
      outlineVariant: AppColors.darkLine,
      inverseSurface: AppColors.darkText,
      onInverseSurface: AppColors.darkSurface,
      inversePrimary: AppColors.brandBlue,
      shadow: Colors.black,
      scrim: Colors.black,
      surfaceTint: Colors.transparent,
    ),
    palette: AppPalette.dark,
    scaffold: AppColors.darkSurface,
  );

  static bool isDevanagari(Locale? locale) => locale?.languageCode == 'ne';

  static TextTheme textTheme({required Color ink, required Locale? locale}) {
    final deva = isDevanagari(locale);
    final family = deva ? devanagariFamily : latinFamily;
    final fallback = deva ? const [latinFamily] : const [devanagariFamily];
    final body = deva ? AppLineHeight.devanagari : AppLineHeight.normal;
    final heading = deva ? AppLineHeight.devanagari : AppLineHeight.tight;

    TextStyle s(double size, FontWeight w, double h) => TextStyle(
      fontFamily: family,
      fontFamilyFallback: fallback,
      fontSize: size,
      fontWeight: w,
      height: h,
      color: ink,
      letterSpacing: 0,
    );

    return TextTheme(
      displaySmall: s(AppFontSize.x3xl, FontWeight.w700, heading),
      headlineMedium: s(AppFontSize.x2xl, FontWeight.w700, heading),
      headlineSmall: s(AppFontSize.xl, FontWeight.w600, heading),
      titleLarge: s(AppFontSize.lg, FontWeight.w600, heading),
      titleMedium: s(AppFontSize.md, FontWeight.w600, body),
      titleSmall: s(AppFontSize.base, FontWeight.w600, body),
      bodyLarge: s(AppFontSize.md, FontWeight.w400, body),
      bodyMedium: s(AppFontSize.base, FontWeight.w400, body),
      bodySmall: s(AppFontSize.sm, FontWeight.w400, body),
      labelLarge: s(AppFontSize.base, FontWeight.w600, body),
      labelMedium: s(AppFontSize.sm, FontWeight.w500, body),
      labelSmall: s(AppFontSize.xs, FontWeight.w500, body),
    );
  }

  static ThemeData _build({
    required Brightness brightness,
    required ColorScheme scheme,
    required AppPalette palette,
    required Color scaffold,
    required Locale? locale,
  }) {
    final text = textTheme(ink: scheme.onSurface, locale: locale);
    const md = BorderRadius.all(Radius.circular(AppRadius.md));
    const shape = RoundedRectangleBorder(borderRadius: md);
    const minTap = Size(48, 48);
    const buttonPadding = EdgeInsets.symmetric(
      horizontal: AppSpace.s5,
      vertical: AppSpace.s3,
    );

    OutlineInputBorder border(Color c, [double w = 1]) => OutlineInputBorder(
      borderRadius: md,
      borderSide: BorderSide(color: c, width: w),
    );

    return ThemeData(
      useMaterial3: true,
      brightness: brightness,
      colorScheme: scheme,
      scaffoldBackgroundColor: scaffold,
      textTheme: text,
      fontFamily: text.bodyMedium?.fontFamily,
      extensions: [palette],
      materialTapTargetSize: MaterialTapTargetSize.padded,
      visualDensity: VisualDensity.standard,
      splashFactory: InkRipple.splashFactory,
      dividerTheme: DividerThemeData(
        color: scheme.outlineVariant,
        thickness: 1,
        space: 1,
      ),
      appBarTheme: AppBarTheme(
        backgroundColor: scaffold,
        foregroundColor: scheme.onSurface,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: false,
        surfaceTintColor: Colors.transparent,
        titleTextStyle: text.titleLarge,
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          shape: shape,
          minimumSize: minTap,
          padding: buttonPadding,
          textStyle: text.labelLarge,
          elevation: 0,
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          shape: shape,
          minimumSize: minTap,
          padding: buttonPadding,
          textStyle: text.labelLarge,
          foregroundColor: scheme.onSurface,
          side: BorderSide(color: scheme.outline),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          shape: shape,
          minimumSize: minTap,
          padding: const EdgeInsets.symmetric(horizontal: AppSpace.s3),
          textStyle: text.labelLarge,
        ),
      ),
      iconButtonTheme: IconButtonThemeData(
        style: IconButton.styleFrom(shape: shape, minimumSize: minTap),
      ),
      segmentedButtonTheme: SegmentedButtonThemeData(
        style: SegmentedButton.styleFrom(
          shape: shape,
          minimumSize: minTap,
          textStyle: text.labelLarge,
          selectedBackgroundColor: scheme.primaryContainer,
          selectedForegroundColor: scheme.onPrimaryContainer,
          side: BorderSide(color: scheme.outline),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: scheme.surface,
        contentPadding: const EdgeInsets.symmetric(
          horizontal: AppSpace.s4,
          vertical: AppSpace.s3 + 2,
        ),
        border: border(scheme.outline),
        enabledBorder: border(scheme.outline),
        focusedBorder: border(scheme.primary, 2),
        errorBorder: border(scheme.error),
        focusedErrorBorder: border(scheme.error, 2),
        labelStyle: text.bodyMedium?.copyWith(color: scheme.onSurfaceVariant),
        helperStyle: text.bodySmall?.copyWith(color: scheme.onSurfaceVariant),
        errorStyle: text.bodySmall?.copyWith(color: scheme.error),
        helperMaxLines: 3,
        errorMaxLines: 3,
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        margin: EdgeInsets.zero,
        color: scheme.surface,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: const BorderRadius.all(Radius.circular(AppRadius.lg)),
          side: BorderSide(color: scheme.outlineVariant),
        ),
      ),
      listTileTheme: ListTileThemeData(
        minTileHeight: 56,
        contentPadding: const EdgeInsets.symmetric(horizontal: AppSpace.s4),
        iconColor: scheme.onSurfaceVariant,
        titleTextStyle: text.bodyLarge,
        subtitleTextStyle: text.bodySmall?.copyWith(
          color: scheme.onSurfaceVariant,
        ),
        shape: shape,
      ),
      navigationBarTheme: NavigationBarThemeData(
        height: 64,
        elevation: 0,
        backgroundColor: scheme.surface,
        surfaceTintColor: Colors.transparent,
        indicatorColor: scheme.primaryContainer,
        indicatorShape: shape,
        labelTextStyle: WidgetStatePropertyAll(text.labelMedium),
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        shape: shape,
        backgroundColor: scheme.inverseSurface,
        contentTextStyle: text.bodyMedium?.copyWith(
          color: scheme.onInverseSurface,
        ),
      ),
      dialogTheme: DialogThemeData(
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(AppRadius.lg)),
        ),
        backgroundColor: scheme.surface,
        surfaceTintColor: Colors.transparent,
        titleTextStyle: text.titleLarge,
        contentTextStyle: text.bodyMedium,
      ),
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: scheme.surface,
        surfaceTintColor: Colors.transparent,
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(
            top: Radius.circular(AppRadius.lg),
          ),
        ),
      ),
      chipTheme: ChipThemeData(
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(AppRadius.sm)),
        ),
        labelStyle: text.labelMedium,
        side: BorderSide(color: scheme.outlineVariant),
      ),
      progressIndicatorTheme: ProgressIndicatorThemeData(
        color: scheme.primary,
        linearTrackColor: scheme.surfaceContainerHighest,
      ),
      pageTransitionsTheme: const PageTransitionsTheme(
        builders: {
          TargetPlatform.android: ReducedMotionPageTransitionsBuilder(
            FadeForwardsPageTransitionsBuilder(),
          ),
          TargetPlatform.iOS: ReducedMotionPageTransitionsBuilder(
            CupertinoPageTransitionsBuilder(),
          ),
        },
      ),
    );
  }
}
