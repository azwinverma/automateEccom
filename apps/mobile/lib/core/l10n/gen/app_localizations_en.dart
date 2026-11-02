// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appName => 'Commerce OS';

  @override
  String get actionRetry => 'Try again';

  @override
  String get actionContinue => 'Continue';

  @override
  String get actionCancel => 'Cancel';

  @override
  String requestIdLabel(String id) {
    return 'Ref $id';
  }

  @override
  String get loadingLabel => 'Loading';

  @override
  String get splashLoading => 'Opening your shop…';

  @override
  String get offlineBanner => 'You\'re offline. Changes wait until you\'re back.';

  @override
  String get offlineTitle => 'No internet connection';

  @override
  String get offlineBody => 'Check mobile data or Wi-Fi, then try again.';

  @override
  String get errorTitle => 'Couldn\'t load this';

  @override
  String get permissionDeniedTitle => 'You don\'t have access to this';

  @override
  String get permissionDeniedBody => 'Ask the shop owner to give your role access.';

  @override
  String get featureNotInPlanTitle => 'Not in your current plan';

  @override
  String get featureNotInPlanBody => 'Upgrade your plan to use this.';

  @override
  String get errValidation => 'Some details need fixing.';

  @override
  String get errNotAuthenticated => 'Please log in again.';

  @override
  String get errInvalidCredentials => 'Email or password didn\'t match.';

  @override
  String get errMfaInvalidCode => 'That code didn\'t work. Check your authenticator app and try again.';

  @override
  String get errPermissionDenied => 'You don\'t have permission to do this.';

  @override
  String get errFeatureNotInPlan => 'This isn\'t included in your plan.';

  @override
  String get errNotFound => 'We couldn\'t find that.';

  @override
  String get errConflict => 'This changed somewhere else. Refresh and try again.';

  @override
  String get errIdempotencyInProgress => 'Still working on your last request. Give it a moment.';

  @override
  String get errIdempotencyKeyReused => 'This was already sent with different details. Please start again.';

  @override
  String get errSlugTaken => 'That shop link is taken. Try a different name.';

  @override
  String get errEmailTaken => 'An account with this email already exists. Try logging in.';

  @override
  String get errUsageLimitReached => 'You\'ve reached this period\'s limit. Buy credits, upgrade, or wait for renewal.';

  @override
  String get errInvalidStateTransition => 'This can\'t be done at its current stage.';

  @override
  String get errRateLimited => 'Too many tries. Wait a little and try again.';

  @override
  String get errDependencyUnavailable => 'A service we rely on is down. Your data is safe — try again shortly.';

  @override
  String get errSessionEnded => 'For your safety we signed you out. Please log in again.';

  @override
  String get errSessionReused => 'Your login was used on another device, so we signed you out everywhere. Log in again, and change your password if that wasn\'t you.';

  @override
  String get errSessionRevoked => 'This device was logged out from another device. Please log in again.';

  @override
  String get errNetwork => 'No connection. Check your internet and try again.';

  @override
  String get errTimeout => 'The connection is slow and this took too long. Try again.';

  @override
  String get errServer => 'Something went wrong on our side. Try again in a bit.';

  @override
  String get errUnknown => 'Something went wrong. Try again.';

  @override
  String get errFieldInvalid => 'Check this field';

  @override
  String get loginTitle => 'Log in to your shop';

  @override
  String get loginSubtitle => 'Orders, messages and stock in one place.';

  @override
  String get fieldEmail => 'Email';

  @override
  String get fieldPassword => 'Password';

  @override
  String get fieldFullName => 'Your name';

  @override
  String get fieldPhone => 'Mobile number (optional)';

  @override
  String get validationEmailRequired => 'Enter your email';

  @override
  String get validationEmailInvalid => 'That email doesn\'t look right';

  @override
  String get validationPasswordRequired => 'Enter your password';

  @override
  String validationPasswordTooShort(int min) {
    final intl.NumberFormat minNumberFormat = intl.NumberFormat.decimalPattern(localeName);
    final String minString = minNumberFormat.format(min);

    return 'Use at least $minString characters';
  }

  @override
  String get validationPasswordEqualsEmail => 'Password can\'t be the same as your email';

  @override
  String get validationNameRequired => 'Enter your name';

  @override
  String get validationPhoneInvalid => 'Enter a valid mobile number';

  @override
  String passwordHint(int min) {
    final intl.NumberFormat minNumberFormat = intl.NumberFormat.decimalPattern(localeName);
    final String minString = minNumberFormat.format(min);

    return 'At least $minString characters. Avoid common passwords.';
  }

  @override
  String get loginAction => 'Log in';

  @override
  String get loginNoAccount => 'New here? Create an account';

  @override
  String get showPassword => 'Show password';

  @override
  String get hidePassword => 'Hide password';

  @override
  String get mfaTitle => 'Enter your 6-digit code';

  @override
  String get mfaSubtitle => 'Open your authenticator app. A recovery code also works.';

  @override
  String get fieldMfaCode => 'Code';

  @override
  String get validationCodeRequired => 'Enter the code';

  @override
  String get mfaVerifyAction => 'Verify';

  @override
  String get mfaUseDifferentAccount => 'Use a different account';

  @override
  String get registerTitle => 'Create your seller account';

  @override
  String get registerSubtitle => 'Takes about a minute.';

  @override
  String get registerAction => 'Create account';

  @override
  String get registerHaveAccount => 'Already have an account? Log in';

  @override
  String get onboardingTitle => 'Set up your shop';

  @override
  String get onboardingSubtitle => 'You can change these later in Settings.';

  @override
  String get fieldBusinessName => 'Shop or business name';

  @override
  String get fieldBusinessNameHint => 'e.g. Thamel Handloom';

  @override
  String get validationBusinessNameRequired => 'Enter your shop name';

  @override
  String get validationBusinessNameTooShort => 'That name is too short';

  @override
  String get fieldCurrency => 'Currency';

  @override
  String get currencyNpr => 'Nepali Rupee (NPR)';

  @override
  String get fieldTimezone => 'Time zone';

  @override
  String get timezoneKathmandu => 'Kathmandu (UTC+5:45)';

  @override
  String get onboardingFixedNote => 'NPR and Nepal time for now. More options later.';

  @override
  String get fieldDefaultLanguage => 'Language for customers and receipts';

  @override
  String get languageNepali => 'नेपाली';

  @override
  String get languageEnglish => 'English';

  @override
  String get onboardingAction => 'Create shop';

  @override
  String get navHome => 'Home';

  @override
  String get navSettings => 'Settings';

  @override
  String homeGreeting(String name) {
    return 'Namaste, $name';
  }

  @override
  String get homeSectionToday => 'Today';

  @override
  String get metricOrders => 'Orders';

  @override
  String get metricRevenue => 'Revenue';

  @override
  String get metricAiMessages => 'AI-handled messages';

  @override
  String get metricReadyToShip => 'Ready to ship';

  @override
  String get metricNotYet => 'Not counted yet';

  @override
  String get metricNotYetBody => 'These numbers start once orders and messages connect. Until then we show nothing rather than guesses.';

  @override
  String metricUnavailableSemantics(String metric) {
    return '$metric: not available yet';
  }

  @override
  String get homeSectionNeedsYou => 'Needs you';

  @override
  String get exceptionsEmptyTitle => 'Nothing needs you right now';

  @override
  String get exceptionsEmptyBody => 'Payment mismatches, failed deliveries and unsure AI replies will show up here first.';

  @override
  String exceptionsCount(int count) {
    final intl.NumberFormat countNumberFormat = intl.NumberFormat.decimalPattern(localeName);
    final String countString = countNumberFormat.format(count);

    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$countString items',
      one: '1 item',
    );
    return '$_temp0';
  }

  @override
  String get exPaymentMismatch => 'Payment doesn\'t match';

  @override
  String get exLowConfidenceAi => 'AI wasn\'t sure';

  @override
  String get exRefundAboveThreshold => 'Large refund to approve';

  @override
  String get exCourierFailed => 'Delivery failed';

  @override
  String get exChannelExpired => 'Channel disconnected';

  @override
  String get exInventoryMismatch => 'Stock doesn\'t match';

  @override
  String get exPublishFailed => 'Post didn\'t publish';

  @override
  String get exAmbiguousVariant => 'Which size or colour?';

  @override
  String get exCustomerEscalation => 'Customer wants a person';

  @override
  String get exProviderFailure => 'Service problem';

  @override
  String get autopilotTitle => 'Autopilot';

  @override
  String get autopilotModeAssisted => 'Assisted';

  @override
  String get autopilotModeSmart => 'Smart';

  @override
  String get autopilotModeAutopilot => 'Autopilot';

  @override
  String get autopilotModeAssistedHint => 'AI suggests, you approve';

  @override
  String get autopilotModeSmartHint => 'Routine work runs, risky work waits for you';

  @override
  String get autopilotModeAutopilotHint => 'Runs on its own within your rules';

  @override
  String autopilotAutomated(int count) {
    final intl.NumberFormat countNumberFormat = intl.NumberFormat.decimalPattern(localeName);
    final String countString = countNumberFormat.format(count);

    return '$countString handled';
  }

  @override
  String autopilotNeedsAttention(int count) {
    final intl.NumberFormat countNumberFormat = intl.NumberFormat.decimalPattern(localeName);
    final String countString = countNumberFormat.format(count);

    return '$countString need you';
  }

  @override
  String get autopilotNotActive => 'Not active yet. Starts when orders and messages connect.';

  @override
  String get quickActionsTitle => 'Quick actions';

  @override
  String get qaAddProduct => 'Add product';

  @override
  String get qaCaptureProduct => 'Capture product';

  @override
  String get qaGenerateContent => 'Write a post';

  @override
  String get qaCreateReel => 'Create Reel';

  @override
  String get qaViewOrders => 'Orders';

  @override
  String get qaViewMessages => 'Messages';

  @override
  String get comingSoonBadge => 'Coming in the next release';

  @override
  String get comingSoonWhat => 'What it will do';

  @override
  String get comingSoonHonest => 'Until then, nothing here is simulated — no sample orders or made-up numbers.';

  @override
  String get soonAddProductBody => 'Add a product once with price, stock and sizes or colours. We keep it in sync across Instagram, Facebook and TikTok.';

  @override
  String get soonCaptureProductBody => 'Snap a few photos on your phone. We clean up the background and draft the title and details for you to check.';

  @override
  String get soonGenerateContentBody => 'Write captions in Nepali or English from your product details. Nothing is posted until you approve it.';

  @override
  String get soonCreateReelBody => 'Turn your product photos and clips into a short Reel. Uses video credits from your plan.';

  @override
  String get soonViewOrdersBody => 'Follow every order from chat to doorstep: COD, courier status and returns.';

  @override
  String get soonViewMessagesBody => 'All customer messages in one inbox. AI drafts replies from your real stock and prices.';

  @override
  String get settingsTitle => 'Settings';

  @override
  String get settingsProfile => 'Profile';

  @override
  String get settingsShop => 'Shop';

  @override
  String get settingsLanguage => 'App language';

  @override
  String get languageSystem => 'Same as phone';

  @override
  String get settingsSecurity => 'Security & devices';

  @override
  String get settingsPlan => 'Plan & usage';

  @override
  String get settingsLogout => 'Log out';

  @override
  String get logoutConfirmTitle => 'Log out of this phone?';

  @override
  String get emailUnverified => 'Email not verified';

  @override
  String get mfaOn => 'Two-step login is on';

  @override
  String get mfaOff => 'Two-step login is off';

  @override
  String get securityTitle => 'Security & devices';

  @override
  String get sessionsTitle => 'Logged-in devices';

  @override
  String get sessionThisDevice => 'This phone';

  @override
  String sessionLastUsed(String when) {
    return 'Last used $when';
  }

  @override
  String get sessionUnknownDevice => 'Unknown device';

  @override
  String get sessionRevoke => 'Log out';

  @override
  String sessionRevokeConfirm(String device) {
    return 'Log out $device?';
  }

  @override
  String get sessionsRevokeOthers => 'Log out all other devices';

  @override
  String get sessionsRevokeOthersConfirm => 'Every device except this phone will be logged out.';

  @override
  String get sessionsRevokedToast => 'Logged out';

  @override
  String get sessionsOnlyThis => 'Only this phone is logged in.';

  @override
  String get planTitle => 'Plan & usage';

  @override
  String planStatusTrialing(String date) {
    return 'Trial · ends $date';
  }

  @override
  String get planStatusActive => 'Active';

  @override
  String get planStatusPastDue => 'Payment due';

  @override
  String get planStatusCanceled => 'Canceled';

  @override
  String planPeriod(String start, String end) {
    return 'Current period $start – $end';
  }

  @override
  String get usageTitle => 'Usage';

  @override
  String usageUsedOf(String used, String limit) {
    return '$used of $limit';
  }

  @override
  String get usageUnlimited => 'Unlimited';

  @override
  String usageReserved(int count) {
    final intl.NumberFormat countNumberFormat = intl.NumberFormat.decimalPattern(localeName);
    final String countString = countNumberFormat.format(count);

    return '$countString in progress';
  }

  @override
  String get usagePeriodMonth => 'This month';

  @override
  String get usagePeriodDay => 'Today';

  @override
  String get usageLevelNotice => 'Over 70% used';

  @override
  String get usageLevelWarning => 'Almost at the limit';

  @override
  String get usageLevelReached => 'Limit reached. Buy credits or upgrade to keep going.';

  @override
  String get usageEmpty => 'Nothing on your plan is metered yet.';

  @override
  String get creditsTitle => 'Credits';

  @override
  String creditsBalance(String balance) {
    return '$balance credits';
  }

  @override
  String get creditsNoTransactions => 'No credit activity yet';

  @override
  String get videoMeterTitle => 'Video credits';

  @override
  String get videoMeterMonthly => 'This month';

  @override
  String get videoMeterDaily => 'Today';

  @override
  String get videoMeterNoDailyCap => 'No daily cap';

  @override
  String get videoMeterDailyReached => 'Today\'s cap reached. It resets tomorrow.';

  @override
  String get videoMeterHelp => 'A monthly quota plus a daily cap, so one busy day can\'t use up the whole month.';

  @override
  String get resAiTextGenerations => 'AI writing';

  @override
  String get resAiInboxReplies => 'AI replies';

  @override
  String get resAiImages => 'AI images';

  @override
  String get resAutoReels => 'Auto Reels';

  @override
  String get resPremiumVideo => 'Premium video';

  @override
  String get resProducts => 'Products';

  @override
  String get resOrders => 'Orders';

  @override
  String get resChannels => 'Channels';

  @override
  String get resTeamMembers => 'Team members';

  @override
  String get resStores => 'Stores';

  @override
  String get resStorage => 'Storage';

  @override
  String get resAutomationRuns => 'Automation runs';

  @override
  String get resApiCalls => 'API calls';
}
