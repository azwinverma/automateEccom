// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for English (`en`).
class AppLocalizationsEn extends AppLocalizations {
  AppLocalizationsEn([String locale = 'en']) : super(locale);

  @override
  String get appName => 'Nivaro';

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
  String get offlineBanner =>
      'You\'re offline. Changes wait until you\'re back.';

  @override
  String get offlineTitle => 'No internet connection';

  @override
  String get offlineBody => 'Check mobile data or Wi-Fi, then try again.';

  @override
  String get errorTitle => 'Couldn\'t load this';

  @override
  String get permissionDeniedTitle => 'You don\'t have access to this';

  @override
  String get permissionDeniedBody =>
      'Ask the shop owner to give your role access.';

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
  String get errMfaInvalidCode =>
      'That code didn\'t work. Check your authenticator app and try again.';

  @override
  String get errPermissionDenied => 'You don\'t have permission to do this.';

  @override
  String get errFeatureNotInPlan => 'This isn\'t included in your plan.';

  @override
  String get errNotFound => 'We couldn\'t find that.';

  @override
  String get errConflict =>
      'This changed somewhere else. Refresh and try again.';

  @override
  String get errIdempotencyInProgress =>
      'Still working on your last request. Give it a moment.';

  @override
  String get errIdempotencyKeyReused =>
      'This was already sent with different details. Please start again.';

  @override
  String get errSlugTaken => 'That shop link is taken. Try a different name.';

  @override
  String get errEmailTaken =>
      'An account with this email already exists. Try logging in.';

  @override
  String get errUsageLimitReached =>
      'You\'ve reached this period\'s limit. Buy credits, upgrade, or wait for renewal.';

  @override
  String get errInvalidStateTransition =>
      'This can\'t be done at its current stage.';

  @override
  String get errRateLimited => 'Too many tries. Wait a little and try again.';

  @override
  String get errDependencyUnavailable =>
      'A service we rely on is down. Your data is safe — try again shortly.';

  @override
  String get errSessionEnded =>
      'For your safety we signed you out. Please log in again.';

  @override
  String get errSessionReused =>
      'Your login was used on another device, so we signed you out everywhere. Log in again, and change your password if that wasn\'t you.';

  @override
  String get errSessionRevoked =>
      'This device was logged out from another device. Please log in again.';

  @override
  String get errNetwork => 'No connection. Check your internet and try again.';

  @override
  String get errTimeout =>
      'The connection is slow and this took too long. Try again.';

  @override
  String get errServer =>
      'Something went wrong on our side. Try again in a bit.';

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
    final intl.NumberFormat minNumberFormat = intl.NumberFormat.decimalPattern(
      localeName,
    );
    final String minString = minNumberFormat.format(min);

    return 'Use at least $minString characters';
  }

  @override
  String get validationPasswordEqualsEmail =>
      'Password can\'t be the same as your email';

  @override
  String get validationNameRequired => 'Enter your name';

  @override
  String get validationPhoneInvalid => 'Enter a valid mobile number';

  @override
  String passwordHint(int min) {
    final intl.NumberFormat minNumberFormat = intl.NumberFormat.decimalPattern(
      localeName,
    );
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
  String get mfaSubtitle =>
      'Open your authenticator app. A recovery code also works.';

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
  String get onboardingFixedNote =>
      'NPR and Nepal time for now. More options later.';

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
  String get metricNotYetBody =>
      'These numbers start once orders and messages connect. Until then we show nothing rather than guesses.';

  @override
  String metricUnavailableSemantics(String metric) {
    return '$metric: not available yet';
  }

  @override
  String get homeSectionNeedsYou => 'Needs you';

  @override
  String get exceptionsEmptyTitle => 'Nothing needs you right now';

  @override
  String get exceptionsEmptyBody =>
      'Payment mismatches, failed deliveries and unsure AI replies will show up here first.';

  @override
  String exceptionsCount(int count) {
    final intl.NumberFormat countNumberFormat = intl
        .NumberFormat.decimalPattern(localeName);
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
  String get exListingDrift => 'Changed on a channel';

  @override
  String get exActionResolveDrift => 'Choose version';

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
  String get autopilotModeSmartHint =>
      'Routine work runs, risky work waits for you';

  @override
  String get autopilotModeAutopilotHint => 'Runs on its own within your rules';

  @override
  String autopilotAutomated(int count) {
    final intl.NumberFormat countNumberFormat = intl
        .NumberFormat.decimalPattern(localeName);
    final String countString = countNumberFormat.format(count);

    return '$countString handled';
  }

  @override
  String autopilotNeedsAttention(int count) {
    final intl.NumberFormat countNumberFormat = intl
        .NumberFormat.decimalPattern(localeName);
    final String countString = countNumberFormat.format(count);

    return '$countString need you';
  }

  @override
  String get autopilotNotActive =>
      'Not active yet. Starts when orders and messages connect.';

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
  String get comingSoonHonest =>
      'Until then, nothing here is simulated — no sample orders or made-up numbers.';

  @override
  String get soonAddProductBody =>
      'Add a product once with price, stock and sizes or colours. We keep it in sync across Instagram, Facebook and TikTok.';

  @override
  String get soonCaptureProductBody =>
      'Snap a few photos on your phone. We clean up the background and draft the title and details for you to check.';

  @override
  String get soonGenerateContentBody =>
      'Write captions in Nepali or English from your product details. Nothing is posted until you approve it.';

  @override
  String get soonCreateReelBody =>
      'Turn your product photos and clips into a short Reel. Uses video credits from your plan.';

  @override
  String get soonViewOrdersBody =>
      'Follow every order from chat to doorstep: COD, courier status and returns.';

  @override
  String get soonViewMessagesBody =>
      'All customer messages in one inbox. AI drafts replies from your real stock and prices.';

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
  String get sessionsRevokeOthersConfirm =>
      'Every device except this phone will be logged out.';

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
    final intl.NumberFormat countNumberFormat = intl
        .NumberFormat.decimalPattern(localeName);
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
  String get usageLevelReached =>
      'Limit reached. Buy credits or upgrade to keep going.';

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
  String get videoMeterDailyReached =>
      'Today\'s cap reached. It resets tomorrow.';

  @override
  String get videoMeterHelp =>
      'A monthly quota plus a daily cap, so one busy day can\'t use up the whole month.';

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

  @override
  String get captureTitle => 'Capture product';

  @override
  String get captureIntro =>
      'Add up to 6 clear photos. Front, back and a close-up of the fabric or label work best.';

  @override
  String get captureTakePhoto => 'Take photo';

  @override
  String get captureFromGallery => 'Choose from gallery';

  @override
  String capturePhotoCount(int count, int max) {
    final intl.NumberFormat countNumberFormat = intl
        .NumberFormat.decimalPattern(localeName);
    final String countString = countNumberFormat.format(count);
    final intl.NumberFormat maxNumberFormat = intl.NumberFormat.decimalPattern(
      localeName,
    );
    final String maxString = maxNumberFormat.format(max);

    return '$countString of $maxString photos';
  }

  @override
  String get captureLimitReached =>
      'That\'s 6 photos — the most one draft can use.';

  @override
  String captureSkipped(int count) {
    final intl.NumberFormat countNumberFormat = intl
        .NumberFormat.decimalPattern(localeName);
    final String countString = countNumberFormat.format(count);

    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$countString photos weren\'t added',
      one: '1 photo wasn\'t added',
    );
    return '$_temp0 — 6 is the limit.';
  }

  @override
  String get captureNotesLabel => 'Anything we should know? (optional)';

  @override
  String get captureNotesHint => 'e.g. pure cotton, handmade in Bhaktapur';

  @override
  String get captureMakeDraft => 'Write my listing';

  @override
  String get captureWaitForUploads => 'Waiting for photos to finish uploading…';

  @override
  String get captureNeedOneReady => 'Add at least one photo to continue.';

  @override
  String get captureRemovePhoto => 'Remove photo';

  @override
  String get capturePickerError =>
      'Couldn\'t open the camera or gallery. Check photo and camera access in phone Settings.';

  @override
  String get captureResumeAll => 'Resume uploads';

  @override
  String get captureKeepsGoing =>
      'Uploads keep going if you switch apps. If the app closes, they pick up where they left off.';

  @override
  String get uploadQueued => 'Waiting';

  @override
  String uploadUploading(String percent) {
    return 'Uploading $percent';
  }

  @override
  String get uploadProcessing => 'Checking photo';

  @override
  String get uploadReady => 'Ready';

  @override
  String get uploadPaused => 'Paused — no connection';

  @override
  String get uploadRetrying => 'Retrying…';

  @override
  String get uploadRejected => 'Can\'t use this photo';

  @override
  String get uploadFailed => 'Upload failed';

  @override
  String get uploadTapRetry => 'Tap to retry';

  @override
  String get rejectNotAnImage => 'This file isn\'t a photo.';

  @override
  String get rejectTooLarge => 'Photo is too big. Pick one under 20 MB.';

  @override
  String get rejectUnsupported =>
      'This format isn\'t supported. Use JPEG, PNG, WebP or HEIC.';

  @override
  String get rejectMalware => 'This file looked unsafe, so we deleted it.';

  @override
  String get tipLowResolution =>
      'Photo is small. Move closer or use the main camera.';

  @override
  String get tipBlurry => 'Photo looks blurry. Hold steady and tap to focus.';

  @override
  String get tipTooDark => 'Photo looks dark. Try near a window.';

  @override
  String get tipOverexposed => 'Photo is too bright. Move out of direct sun.';

  @override
  String get errFileTooLarge => 'Photo is too big (max 20 MB).';

  @override
  String get errUnsupportedMediaType => 'Use a JPEG, PNG, WebP or HEIC photo.';

  @override
  String get errStorageFull =>
      'Photo storage on your plan is full. Delete old photos or upgrade.';

  @override
  String get errFileUnreadable =>
      'We couldn\'t read this photo from your phone. Pick it again.';

  @override
  String get errUploadMissing =>
      'The photo didn\'t reach us. Retry the upload.';

  @override
  String get errUploadExpired => 'The upload took too long. Start it again.';

  @override
  String get errMediaNotReady =>
      'Some photos are still being checked. Try again in a moment.';

  @override
  String get errMediaNotFound =>
      'Some photos are no longer available. Add them again.';

  @override
  String get errDraftNotReady => 'This draft isn\'t ready yet.';

  @override
  String get errNotPublishable => 'This product isn\'t ready to go live yet.';

  @override
  String get errProductNotActive =>
      'Make the product live first, then publish it to channels.';

  @override
  String get errCapabilityNotSupported => 'This channel can\'t do that.';

  @override
  String get errVersionConflict =>
      'Someone else changed this. We loaded the latest — check and try again.';

  @override
  String get errPostLocked =>
      'Scheduled posts can\'t be edited. Unschedule it first.';

  @override
  String get errReconnectRequired => 'Reconnect this channel first.';

  @override
  String get errScheduleInPast => 'Pick a time in the future.';

  @override
  String get errScheduleTooFar => 'Posts can be scheduled up to 90 days ahead.';

  @override
  String get errCaptionRequired => 'Write a caption.';

  @override
  String get errCaptionTooLong => 'This caption is too long for the channel.';

  @override
  String get errInvalidPhotoCount => 'Choose 1 to 6 photos.';

  @override
  String get errNotFailed => 'Only failed drafts can be retried.';

  @override
  String get errAiUnavailable =>
      'Our writing service is busy. Try again in a few minutes.';

  @override
  String get draftWorkingTitle => 'Writing your listing';

  @override
  String get draftWorkingBody =>
      'Reading your photos and drafting the name, description and captions in Nepali and English. This usually takes under a minute.';

  @override
  String get draftQueued => 'In line';

  @override
  String get draftRunning => 'Working on it';

  @override
  String get draftLeaveOk =>
      'You can leave this screen; we\'ll keep working. Find it later under Drafts.';

  @override
  String get draftFailedTitle => 'We couldn\'t write this draft';

  @override
  String get draftFailedBody =>
      'Our writing service had a problem. Your photos are safe.';

  @override
  String get draftAppliedTitle => 'Already saved as a product';

  @override
  String get draftOpenProduct => 'Open product';

  @override
  String get draftDiscarded => 'This draft was discarded.';

  @override
  String get reviewTitle => 'Check your listing';

  @override
  String get reviewAiNote =>
      'Written by AI from your photos. Change anything that\'s off.';

  @override
  String get reviewSectionText => 'Name and description';

  @override
  String get fieldTitleNe => 'Name (Nepali)';

  @override
  String get fieldTitleEn => 'Name (English)';

  @override
  String get fieldDescriptionNe => 'Description (Nepali)';

  @override
  String get fieldDescriptionEn => 'Description (English)';

  @override
  String get validationTitleRequired => 'Add a name in Nepali or English';

  @override
  String get reviewSectionCategory => 'Category';

  @override
  String get fieldCategoryHint =>
      'Separate levels with /, e.g. Clothing / Kurta';

  @override
  String confidenceLabel(String percent) {
    return '$percent sure';
  }

  @override
  String get reviewSectionDetails => 'Details';

  @override
  String get attrPleaseCheck => 'Please check';

  @override
  String get attrAccept => 'Looks right';

  @override
  String get attrEdit => 'Edit';

  @override
  String get attrAccepted => 'Checked';

  @override
  String get attrEdited => 'Edited by you';

  @override
  String attrEditTitle(String name) {
    return 'Edit $name';
  }

  @override
  String get actionSave => 'Save';

  @override
  String attrUncheckedError(int count) {
    final intl.NumberFormat countNumberFormat = intl
        .NumberFormat.decimalPattern(localeName);
    final String countString = countNumberFormat.format(count);

    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$countString details still need a check',
      one: '1 detail still needs a check',
    );
    return '$_temp0';
  }

  @override
  String get reviewSectionPrice => 'Price and options';

  @override
  String get reviewPriceNote =>
      'Prices always come from you — AI never sets them.';

  @override
  String get fieldPrice => 'Price (Rs)';

  @override
  String fieldPriceFor(String variant) {
    return 'Price for $variant';
  }

  @override
  String get fieldSku => 'SKU (optional)';

  @override
  String get samePriceToggle => 'Same price for all options';

  @override
  String get validationPriceRequired => 'Enter a price';

  @override
  String get validationPriceInvalid => 'Use numbers only, e.g. 1250 or 1250.50';

  @override
  String get validationPriceDecimals => 'Up to 2 decimal places (paisa)';

  @override
  String get validationPriceTooLarge => 'That price is too high';

  @override
  String get optionAdd => 'Add option (e.g. Size)';

  @override
  String get optionName => 'Option name';

  @override
  String get optionValuesHint => 'Values, separated by commas';

  @override
  String get optionRemove => 'Remove option';

  @override
  String get optionValuesRequired => 'Add at least one value for each option';

  @override
  String variantsCount(int count) {
    final intl.NumberFormat countNumberFormat = intl
        .NumberFormat.decimalPattern(localeName);
    final String countString = countNumberFormat.format(count);

    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$countString variants',
      one: '1 variant',
    );
    return '$_temp0';
  }

  @override
  String get tooManyVariants =>
      'That makes more than 100 combinations. Remove some values.';

  @override
  String get reviewSectionChecklist => 'AI couldn\'t tell — please confirm';

  @override
  String get reviewSectionWarnings => 'Things to check';

  @override
  String get issueClaimPrice =>
      'The text mentions a price. Prices come from you; please check.';

  @override
  String get issueClaimDiscount =>
      'The text mentions a discount you didn\'t give us. Remove it or make sure it\'s real.';

  @override
  String get issueClaimStock =>
      'The text talks about stock. Stock comes from your inventory; please check.';

  @override
  String get issueClaimDelivery =>
      'The text promises delivery terms. Make sure they\'re right.';

  @override
  String get issueClaimWarranty =>
      'The text mentions a warranty. Keep it only if you offer one.';

  @override
  String get issueClaimAuthenticity =>
      'The text says it\'s original or genuine. Keep it only if you can back it up.';

  @override
  String get issueClaimOther =>
      'The text makes a claim we couldn\'t verify. Please check.';

  @override
  String get issueNotProductPhoto =>
      'These photos may not show a product. Check them before saving.';

  @override
  String get issueTooLong =>
      'Some text was too long and was shortened. Read it once.';

  @override
  String issueInField(String field) {
    return 'In: $field';
  }

  @override
  String get reviewCreate => 'Save product';

  @override
  String get reviewFixProblems => 'Fix the highlighted items to continue.';

  @override
  String get productTitle => 'Product';

  @override
  String get productStatusDraft => 'Draft';

  @override
  String get productStatusActive => 'Live';

  @override
  String get productStatusArchived => 'Archived';

  @override
  String get productSaved => 'Saved as a draft. Only you can see it.';

  @override
  String get productGoLive => 'Go live';

  @override
  String get productIsLive => 'Live in your catalog';

  @override
  String get productConfirmSection => 'Confirm AI details';

  @override
  String get productConfirmAll => 'Confirm all';

  @override
  String get productProblemPrice => 'Every variant needs a price.';

  @override
  String get productProblemAttributes => 'Confirm the AI details below.';

  @override
  String get productProblemVariant =>
      'Add at least one active variant (from the web dashboard for now).';

  @override
  String get productProblemTitle => 'Add a product name.';

  @override
  String get productFix => 'Fix';

  @override
  String get productEditPrice => 'Edit price';

  @override
  String get productEditTitle => 'Edit name';

  @override
  String get productPrices => 'Prices';

  @override
  String get defaultVariant => 'Default';

  @override
  String get publishSection => 'Publish to channels';

  @override
  String get publishNeedsLive => 'Go live first to publish to channels.';

  @override
  String get publishNoChannels =>
      'No shop channels connected yet. Connect Instagram, Facebook or TikTok from the web dashboard.';

  @override
  String get publishAction => 'Publish';

  @override
  String get publishSelectOne => 'Choose at least one channel';

  @override
  String get channelReconnect => 'Reconnect';

  @override
  String get channelExpiredNote => 'Connection expired';

  @override
  String get listingPending => 'Waiting';

  @override
  String get listingPublishing => 'Publishing…';

  @override
  String get listingPublished => 'Published';

  @override
  String get listingFailed => 'Failed';

  @override
  String get listingOutOfSync => 'Out of sync';

  @override
  String get listingUnpublished => 'Not listed';

  @override
  String listingError(String code) {
    return 'Reason: $code';
  }

  @override
  String reconnectTitle(String channel) {
    return 'Reconnect $channel';
  }

  @override
  String get reconnectChannelGeneric => 'channel';

  @override
  String get reconnectBody =>
      'For now, reconnect channels from the web dashboard in a browser:';

  @override
  String get reconnectCopied => 'Link copied';

  @override
  String get actionCopyLink => 'Copy link';

  @override
  String get postsSection => 'Create posts';

  @override
  String get postsIntro =>
      'Turn the AI captions into posts for each channel. You review before anything goes out.';

  @override
  String get postsCreate => 'Create drafts';

  @override
  String get postsNoChannels => 'No channel that can post is connected yet.';

  @override
  String get postsNoDraft => 'Posts need the AI draft this product came from.';

  @override
  String get postsTitle => 'Posts';

  @override
  String get postStatusDraft => 'Draft';

  @override
  String get postStatusPendingApproval => 'Waiting for approval';

  @override
  String get postStatusApproved => 'Approved';

  @override
  String postStatusScheduled(String when) {
    return 'Scheduled $when';
  }

  @override
  String get postStatusPublishing => 'Publishing…';

  @override
  String get postStatusPublished => 'Published';

  @override
  String get postStatusFailed => 'Failed';

  @override
  String get postStatusCancelled => 'Cancelled';

  @override
  String get fieldCaption => 'Caption';

  @override
  String get postSaveCaption => 'Save caption';

  @override
  String get postSubmit => 'Submit';

  @override
  String get postApprove => 'Approve';

  @override
  String get postPublishNow => 'Publish now';

  @override
  String get postSchedule => 'Schedule';

  @override
  String get postNeedsApprovalNote =>
      'AI-written posts need an approval before they go out.';

  @override
  String get postNoApprovePermission =>
      'Ask the shop owner or a manager to approve this.';

  @override
  String get postCaptionSaved => 'Caption saved';

  @override
  String get postNotFound => 'This post is no longer available.';

  @override
  String get postsEmpty => 'No posts yet.';

  @override
  String get draftsTitle => 'Drafts';

  @override
  String get draftsNew => 'New from photos';

  @override
  String get draftsEmpty =>
      'No drafts yet. Start with a few photos of a product.';

  @override
  String get draftsIntro =>
      'Pick a draft to turn into posts, or start with new photos.';

  @override
  String get draftStatusWorking => 'Writing…';

  @override
  String get draftStatusReady => 'Ready to check';

  @override
  String get draftStatusFailed => 'Failed';

  @override
  String get draftStatusApplied => 'Saved as product';

  @override
  String get draftStatusDiscarded => 'Discarded';

  @override
  String get draftUntitled => 'Untitled draft';

  @override
  String get exSubjectDraft => 'AI draft';

  @override
  String get exSubjectPost => 'Post';

  @override
  String get exSubjectProduct => 'Product';

  @override
  String get exActionReconnect => 'Reconnect';

  @override
  String get exActionRetryPublish => 'Retry publish';

  @override
  String get exActionReschedule => 'Reschedule';

  @override
  String get exActionReviewPost => 'Review post';

  @override
  String get exActionReviewDraft => 'Review draft';

  @override
  String get exActionRetryDraft => 'Retry draft';

  @override
  String get exActionConfirmAttributes => 'Confirm details';

  @override
  String get exActionDismiss => 'Hide';

  @override
  String get homeSectionCatalog => 'Catalog';

  @override
  String get settingsTheme => 'Theme';

  @override
  String get themeLight => 'Light';

  @override
  String get themeDark => 'Dark';

  @override
  String get themeSystem => 'Same as phone';

  @override
  String get loginForgotPassword => 'Forgot password?';

  @override
  String get forgotTitle => 'Reset your password';

  @override
  String get forgotSubtitle =>
      'Enter your account email and we\'ll send you a link to set a new password.';

  @override
  String get forgotAction => 'Send reset link';

  @override
  String get forgotSentTitle => 'Check your email';

  @override
  String get forgotSentBody =>
      'If an account exists for that email, a reset link is on its way. Open it on this phone or a computer. It works once and expires in 30 minutes.';

  @override
  String get forgotBack => 'Back to sign in';

  @override
  String get exUsageLimit => 'Plan limit';

  @override
  String exSubjectUsage(int used, int limit) {
    return '$used of $limit used this month (see Plan on the web)';
  }

  @override
  String get navOrders => 'Orders';

  @override
  String get navInbox => 'Inbox';

  @override
  String get ordersTitle => 'Orders';

  @override
  String get ordersFilterNeedsAction => 'To do';

  @override
  String get ordersFilterNeedsReview => 'Needs review';

  @override
  String get ordersFilterAll => 'All';

  @override
  String get ordersEmpty => 'No orders here';

  @override
  String get ordersEmptyBody =>
      'Orders from chats, your channels and the ones you add appear here.';

  @override
  String orderNumber(int number) {
    return 'Order #$number';
  }

  @override
  String get orderItems => 'Items';

  @override
  String get orderTotals => 'Total';

  @override
  String get orderSubtotal => 'Subtotal';

  @override
  String get orderDelivery => 'Delivery';

  @override
  String get orderDiscount => 'Discount';

  @override
  String get orderTotal => 'Total';

  @override
  String get orderShipTo => 'Deliver to';

  @override
  String get orderPayment => 'Payment';

  @override
  String get orderTimeline => 'Timeline';

  @override
  String get orderNotes => 'Notes';

  @override
  String get orderCancel => 'Cancel order';

  @override
  String get orderCancelTitle => 'Cancel this order?';

  @override
  String get orderCancelBody =>
      'Reserved stock goes back on sale. The customer isn\'t messaged automatically.';

  @override
  String get orderCancelReason => 'Reason';

  @override
  String get orderCancelReasonHint => 'e.g. customer changed their mind';

  @override
  String get orderCancelConfirm => 'Cancel order';

  @override
  String get orderCancelKeep => 'Keep order';

  @override
  String get orderUpdated => 'Order updated';

  @override
  String orderCancelledQty(int count) {
    return '$count cancelled';
  }

  @override
  String get orderUnmatchedItem => 'Not found in your catalog';

  @override
  String get orderViewChat => 'Open chat';

  @override
  String get orderReviewPaymentMismatch =>
      'Paid amount doesn\'t match the total';

  @override
  String get orderReviewPaidAfterCancel => 'Paid after it was cancelled';

  @override
  String get orderReviewStockShort => 'Not enough stock for this order';

  @override
  String get orderReviewUnmatched => 'Some items aren\'t in your catalog';

  @override
  String get orderReviewAddress => 'Address is incomplete';

  @override
  String get orderStatusDraft => 'Draft';

  @override
  String get orderStatusPendingConfirmation => 'Awaiting confirmation';

  @override
  String get orderStatusConfirmed => 'Confirmed';

  @override
  String get orderStatusPaymentPending => 'Awaiting payment';

  @override
  String get orderStatusCodPending => 'To pack (COD)';

  @override
  String get orderStatusReadyToShip => 'Ready to ship';

  @override
  String get orderStatusShipped => 'Shipped';

  @override
  String get orderStatusDelivered => 'Delivered';

  @override
  String get orderStatusCompleted => 'Completed';

  @override
  String get orderStatusCancelled => 'Cancelled';

  @override
  String get orderStatusDeliveryFailed => 'Delivery failed';

  @override
  String get orderStatusReturned => 'Returned';

  @override
  String get orderActionConfirm => 'Confirm order';

  @override
  String get orderActionReadyToShip => 'Mark packed';

  @override
  String get orderActionShipped => 'Mark shipped';

  @override
  String get orderActionDelivered => 'Mark delivered';

  @override
  String get orderActionCompleted => 'Mark completed';

  @override
  String get orderActionDeliveryFailed => 'Delivery failed';

  @override
  String get orderActionReturned => 'Mark returned';

  @override
  String get paymentCod => 'Cash on delivery';

  @override
  String get paymentPrepaid => 'Prepaid';

  @override
  String get payStatusUnpaid => 'Unpaid';

  @override
  String get payStatusPending => 'Waiting for payment';

  @override
  String get payStatusPaid => 'Paid';

  @override
  String get payStatusFailed => 'Payment failed';

  @override
  String get payStatusRefunded => 'Refunded';

  @override
  String get payStatusCodPending => 'To collect on delivery';

  @override
  String get payStatusCodCollected => 'Collected by courier';

  @override
  String get timelineCreated => 'Order created';

  @override
  String timelineImported(String channel) {
    return 'Imported from $channel';
  }

  @override
  String timelineStatus(String status) {
    return 'Now: $status';
  }

  @override
  String get timelineLinesCancelled => 'Some items cancelled';

  @override
  String timelineNote(String note) {
    return 'Note: $note';
  }

  @override
  String get timelinePayment => 'Payment received';

  @override
  String get timelinePaymentFailed => 'Payment failed';

  @override
  String get timelinePaymentMismatch => 'Paid amount didn\'t match';

  @override
  String get timelineOther => 'Update';

  @override
  String get timelineByAi => 'AI Sales Agent';

  @override
  String get timelineAutomatic => 'Automatic';

  @override
  String get inboxTitle => 'Inbox';

  @override
  String get inboxEmpty => 'No open chats';

  @override
  String get inboxEmptyBody =>
      'Customer messages from your connected channels arrive here.';

  @override
  String get inboxNeedsYou => 'Needs you';

  @override
  String inboxYou(String text) {
    return 'You: $text';
  }

  @override
  String get inboxCustomer => 'Customer';

  @override
  String get threadReplyHint => 'Write a reply';

  @override
  String get threadSend => 'Send';

  @override
  String get threadSuggestion => 'AI suggestion, not sent yet';

  @override
  String get threadSuggestionSend => 'Send';

  @override
  String get threadSuggestionEdit => 'Edit';

  @override
  String get threadSuggestionDiscard => 'Discard';

  @override
  String get threadEditTitle => 'Edit before sending';

  @override
  String get threadFailed => 'Not sent';

  @override
  String get threadRetry => 'Retry';

  @override
  String get threadSending => 'Sending…';

  @override
  String get threadByAi => 'AI';

  @override
  String get threadHandBack => 'Hand back to AI';

  @override
  String get threadHandedBack => 'The AI will answer new messages again.';

  @override
  String get threadHumanBanner =>
      'You\'re handling this chat. The AI is paused.';

  @override
  String get threadEscalatedBanner => 'The AI handed this chat to you.';

  @override
  String draftCollecting(String field) {
    return 'Taking an order: waiting for $field';
  }

  @override
  String get draftAwaitingConfirmation =>
      'Order summary sent. Waiting for the customer\'s yes.';

  @override
  String get draftConfirmed => 'Order created from this chat';

  @override
  String get stockSection => 'Stock';

  @override
  String stockAvailable(int count) {
    return '$count available';
  }

  @override
  String stockDetail(int onHand, int reserved) {
    return '$onHand on shelf · $reserved reserved';
  }

  @override
  String get stockUntracked => 'Not tracked yet';

  @override
  String get stockLow => 'Low';

  @override
  String get stockReceive => 'Receive stock';

  @override
  String get stockQuantity => 'Quantity received';

  @override
  String get stockReceived => 'Stock updated';

  @override
  String get stockSave => 'Add';

  @override
  String get exActionReply => 'Reply';

  @override
  String get exActionCheckPayment => 'Check payment';

  @override
  String get exActionFixStock => 'Fix stock';

  @override
  String get exActionReviewOrder => 'Review order';

  @override
  String get exSubjectConversation => 'A customer chat';

  @override
  String exSubjectOrder(int number) {
    return 'Order #$number';
  }

  @override
  String get commonCancel => 'Cancel';

  @override
  String get draftFieldProduct => 'product';

  @override
  String get draftFieldVariant => 'size/colour';

  @override
  String get draftFieldQuantity => 'quantity';

  @override
  String get draftFieldName => 'name';

  @override
  String get draftFieldPhone => 'phone number';

  @override
  String get draftFieldDistrict => 'district';

  @override
  String get draftFieldMunicipality => 'municipality';

  @override
  String get draftFieldWard => 'ward';

  @override
  String get draftFieldArea => 'area';

  @override
  String get draftFieldPayment => 'payment choice';

  @override
  String get deliveryTitle => 'Delivery';

  @override
  String get deliveryChooseCourier => 'Choose how to send it';

  @override
  String get deliveryWhyDefault => 'Recommended: your default courier';

  @override
  String get deliveryWhyCheapest =>
      'Recommended: the cheapest option that fits this parcel';

  @override
  String get deliveryWhyOnly => 'The only option that can take this parcel';

  @override
  String get deliveryRecommended => 'Recommended';

  @override
  String get deliveryOwnRider => 'You arrange it and record the updates';

  @override
  String deliveryEta(int min, int max) {
    return '$min–$max days';
  }

  @override
  String get deliveryNoCouriers =>
      'No courier is set up yet. Add one in Settings on the web.';

  @override
  String deliveryCollectAmount(String amount) {
    return 'The courier collects $amount at the door';
  }

  @override
  String get deliveryTrackingOptional => 'Tracking number (optional)';

  @override
  String get deliveryCourierNameOptional => 'Courier or rider name (optional)';

  @override
  String get deliveryBook => 'Book courier';

  @override
  String get deliveryBooked => 'Courier booked';

  @override
  String deliveryTracking(String number) {
    return 'Tracking $number';
  }

  @override
  String get deliveryCopy => 'Copy tracking number';

  @override
  String get deliveryCopied => 'Tracking number copied';

  @override
  String deliveryCod(String amount) {
    return 'Cash to collect: $amount';
  }

  @override
  String get deliveryNothingToCollect => 'Paid already: nothing to collect';

  @override
  String get deliveryHistory => 'Parcel history';

  @override
  String get deliveryLateUpdate => 'Late update from the courier (not applied)';

  @override
  String deliveryAttempt(int n, String reason) {
    return 'Attempt $n: $reason';
  }

  @override
  String deliveryCustomerReply(String text) {
    return 'Customer replied: “$text”';
  }

  @override
  String get deliveryUpdated => 'Delivery updated';

  @override
  String get deliveryActionPickup => 'Request pickup';

  @override
  String get deliveryActionCancel => 'Cancel booking';

  @override
  String get deliveryActionReattempt => 'Ask the courier to try again';

  @override
  String get deliveryActionReturn => 'Return to my shop';

  @override
  String get deliveryActionReceivedBack => 'Parcel is back: restock items';

  @override
  String get deliveryActionUpdateStatus => 'Update status';

  @override
  String get deliveryActionRefresh => 'Check the courier for updates';

  @override
  String get deliveryCancelTitle => 'Cancel this booking?';

  @override
  String get deliveryCancelBody =>
      'The courier won\'t collect this parcel. You can book again.';

  @override
  String get deliveryKeep => 'Keep';

  @override
  String get deliveryConfirm => 'Confirm';

  @override
  String get deliveryReattemptTitle => 'Try delivering again';

  @override
  String get deliveryReattemptNote => 'Note for the courier (time, landmark)';

  @override
  String get deliverySend => 'Send';

  @override
  String get deliveryReturnTitle => 'Return the parcel to your shop?';

  @override
  String get deliveryReturnBody =>
      'The courier brings it back and no cash is collected.';

  @override
  String get deliveryStatusTitle => 'What happened to the parcel?';

  @override
  String get deliveryFailureReason => 'Why did the delivery fail?';

  @override
  String get deliveryReasonRequired => 'Choose a reason to continue';

  @override
  String get deliveryNote => 'Note (optional)';

  @override
  String get deliverySave => 'Save';

  @override
  String get shipStatusBooked => 'Booked';

  @override
  String get shipStatusPickupRequested => 'Pickup requested';

  @override
  String get shipStatusPickedUp => 'Picked up';

  @override
  String get shipStatusInTransit => 'On the way';

  @override
  String get shipStatusOutForDelivery => 'Out for delivery';

  @override
  String get shipStatusDelivered => 'Delivered';

  @override
  String get shipStatusDeliveryFailed => 'Delivery failed';

  @override
  String get shipStatusReattemptRequested => 'Trying again';

  @override
  String get shipStatusReturning => 'Coming back to shop';

  @override
  String get shipStatusReturnedToOrigin => 'Back at shop';

  @override
  String get shipStatusCancelled => 'Cancelled';

  @override
  String get shipStatusLost => 'Lost by courier';

  @override
  String get failReasonCustomerUnreachable =>
      'Couldn\'t reach the customer\'s phone';

  @override
  String get failReasonCustomerUnavailable => 'Nobody was there to receive it';

  @override
  String get failReasonCustomerRefused => 'Customer refused the parcel';

  @override
  String get failReasonAddressIncorrect => 'Rider couldn\'t find the address';

  @override
  String get failReasonCodNotReady => 'Cash wasn\'t ready';

  @override
  String get failReasonRescheduled => 'Customer asked for another time';

  @override
  String get failReasonOther => 'Other problem';

  @override
  String get recoveryOpen => 'Call the customer';

  @override
  String get recoveryAwaitingCustomer =>
      'We messaged the customer, waiting for a reply';

  @override
  String get recoveryCustomerReplied =>
      'Customer replied: ask the courier to try again';

  @override
  String get recoveryReattemptRequested => 'Courier asked to try again';

  @override
  String get recoveryReturning => 'Coming back to your shop';

  @override
  String get recoveryResolved => 'Resolved';

  @override
  String get recoveryEscalated => 'No reply: please call the customer';

  @override
  String get codTitle => 'Cash on delivery';

  @override
  String get codWithCouriers => 'With couriers';

  @override
  String codWithCouriersBody(int count) {
    return 'Cash from $count delivered parcels not received yet';
  }

  @override
  String codOverTwoWeeks(String amount) {
    return '$amount waiting more than 2 weeks';
  }

  @override
  String codNeedsReview(int count) {
    return '$count courier statements need checking';
  }

  @override
  String get codAwaitingTitle => 'Cash still with couriers';

  @override
  String get codAwaitingEmpty =>
      'No cash waiting: couriers have paid for every delivered parcel.';

  @override
  String codDaysWaiting(int days) {
    return '$days days waiting';
  }

  @override
  String codOrderCourier(int number, String courier) {
    return 'Order #$number · $courier';
  }

  @override
  String get codSettlementsTitle => 'Courier statements';

  @override
  String get codSettlementsEmpty => 'No courier statements yet.';

  @override
  String get codStatusNeedsReview => 'Needs checking';

  @override
  String get codStatusReconciled => 'Matches: confirm once paid';

  @override
  String get codStatusConfirmed => 'Received';

  @override
  String codIssues(int count) {
    return '$count lines don\'t match. Check them on the web.';
  }

  @override
  String get codConfirmReceived => 'Confirm money received';

  @override
  String get codConfirmed => 'Marked as received';

  @override
  String get returnsTitle => 'Returns';

  @override
  String get returnsStart => 'Start a return';

  @override
  String get returnsNone => 'No returns for this order yet.';

  @override
  String get returnStatusRequested => 'To decide';

  @override
  String get returnStatusApproved => 'Approved';

  @override
  String get returnStatusRejected => 'Rejected';

  @override
  String get returnStatusInTransit => 'On its way back';

  @override
  String get returnStatusReceived => 'Received';

  @override
  String get returnStatusInspected => 'Checked';

  @override
  String get returnStatusRefunded => 'Refunded';

  @override
  String get returnStatusExchanged => 'Exchanged';

  @override
  String get returnStatusClosed => 'Closed';

  @override
  String get returnStatusCancelled => 'Cancelled';

  @override
  String get returnResolutionRefund => 'Refund';

  @override
  String get returnResolutionExchange => 'Exchange';

  @override
  String returnRefundDue(String amount) {
    return 'Refund due: $amount';
  }

  @override
  String get returnReasonSizeSmall => 'Too small';

  @override
  String get returnReasonSizeLarge => 'Too large';

  @override
  String get returnReasonColourDifferent => 'Colour looks different';

  @override
  String get returnReasonQualityDefect => 'Quality defect';

  @override
  String get returnReasonDamagedInTransit => 'Damaged in delivery';

  @override
  String get returnReasonNotAsDescribed => 'Not as described';

  @override
  String get returnReasonChangedMind => 'Changed their mind';

  @override
  String get returnReasonLateDelivery => 'Arrived late';

  @override
  String get returnReasonWrongItem => 'Wrong item sent';

  @override
  String get returnReasonOther => 'Other';

  @override
  String get returnConditionResellable => 'Can be sold again';

  @override
  String get returnConditionDamaged => 'Damaged';

  @override
  String get returnConditionMissing => 'Missing';

  @override
  String get returnConditionUsed => 'Used';

  @override
  String returnLineItem(int qty, String title) {
    return '$qty × $title';
  }

  @override
  String returnLineCondition(String condition) {
    return 'Checked: $condition';
  }

  @override
  String returnLineExchange(String title) {
    return 'Exchange for $title';
  }

  @override
  String returnSheetTitle(int number) {
    return 'Return from order #$number';
  }

  @override
  String get returnPickItems => 'Which items are coming back?';

  @override
  String get returnQty => 'Quantity';

  @override
  String get returnReason => 'Reason';

  @override
  String get returnResolution => 'What does the customer want?';

  @override
  String get returnExchangeFor => 'Exchange for';

  @override
  String get returnNoExchangeOption => 'No other option at the same price';

  @override
  String returnOutOfStock(String title) {
    return '$title (out of stock)';
  }

  @override
  String get returnCheck => 'Check against policy';

  @override
  String get returnSubmit => 'Create return';

  @override
  String get returnCreated => 'Return created';

  @override
  String get returnNothingLeft =>
      'Everything from this order is already being returned.';

  @override
  String get returnPickReason => 'Pick a reason for each item';

  @override
  String get returnPickExchange => 'Pick what to exchange each item for';

  @override
  String get returnCheckOrderDelivered =>
      'The order hasn\'t been delivered yet';

  @override
  String returnCheckWindow(int days) {
    return 'Outside the $days-day return window';
  }

  @override
  String get returnCheckWindowPlain => 'Outside the return window';

  @override
  String get returnCheckFinalSale => 'Final sale item';

  @override
  String get returnCheckEvidence => 'A photo is needed for this reason';

  @override
  String get returnCheckQuantity => 'More than can be returned';

  @override
  String get returnCheckResolution => 'Your return policy doesn\'t allow this';

  @override
  String get returnCheckExchangeProduct =>
      'An exchange must be the same product at the same price';

  @override
  String get returnCheckExchangeStock => 'The replacement is out of stock';

  @override
  String get returnCheckGeneric => 'Doesn\'t meet your policy';

  @override
  String get returnWarningsTitle =>
      'Outside your policy. You can still create it; approving will need a reason.';

  @override
  String get returnBlockedTitle => 'This return can\'t be created';

  @override
  String get returnAllOk => 'Within your return policy';

  @override
  String returnDetailTitle(String number) {
    return 'Return $number';
  }

  @override
  String get returnChecksTitle => 'Policy checks';

  @override
  String get returnSignalsTitle => 'Worth knowing';

  @override
  String returnSignalFrequent(int count, int days) {
    return '$count returns in the last $days days';
  }

  @override
  String returnSignalRate(int returned, int orders, int days) {
    return 'Returned $returned of $orders orders in $days days';
  }

  @override
  String get returnSignalValue => 'Higher value than this shop\'s usual orders';

  @override
  String get returnSignalGeneric => 'Unusual for this shop';

  @override
  String get returnItemsTitle => 'Items';

  @override
  String get returnPickupTitle => 'Pickup';

  @override
  String get returnRefundsTitle => 'Refunds';

  @override
  String returnOverrideNote(String reason) {
    return 'Approved outside policy: $reason';
  }

  @override
  String returnRejectedNote(String reason) {
    return 'Rejected: $reason';
  }

  @override
  String get refundPending => 'Waiting for a manager\'s approval';

  @override
  String get refundStatusSucceeded => 'Sent';

  @override
  String get refundStatusFailed => 'Failed';

  @override
  String get refundStatusRejected => 'Not approved';

  @override
  String get refundStatusProcessing => 'Processing';

  @override
  String refundLine(String amount, String method) {
    return '$amount · $method';
  }

  @override
  String get refundMethodOriginal => 'Back to the original payment';

  @override
  String get refundMethodEsewa => 'eSewa';

  @override
  String get refundMethodKhalti => 'Khalti';

  @override
  String get refundMethodFonepay => 'Fonepay';

  @override
  String get refundMethodBank => 'Bank transfer';

  @override
  String get refundMethodCash => 'Cash';

  @override
  String get refundMethodOther => 'Other';

  @override
  String get returnActionApprove => 'Approve';

  @override
  String get returnActionReject => 'Reject';

  @override
  String get returnActionCancel => 'Cancel return';

  @override
  String get returnActionReceived => 'Mark as received';

  @override
  String get returnActionInspect => 'Check items';

  @override
  String get returnActionRefund => 'Refund';

  @override
  String get returnPickupOnWeb => 'Book the pickup from the web app.';

  @override
  String get returnApproveTitle => 'Approve this return?';

  @override
  String get returnOverrideHint =>
      'This return is outside your policy. Say why you\'re approving it.';

  @override
  String get returnReasonLabel => 'Reason';

  @override
  String get returnReasonRequired => 'A reason is needed';

  @override
  String get returnRejectTitle => 'Reject this return?';

  @override
  String get returnRejectLabel => 'Reason (the customer sees this)';

  @override
  String get returnCancelTitle => 'Cancel this return?';

  @override
  String get returnCancelBody =>
      'Any replacement held for it goes back on sale.';

  @override
  String get returnReceivedTitle => 'Has the item reached you?';

  @override
  String get returnReceivedBody => 'Check it next to decide the refund.';

  @override
  String get returnInspectTitle => 'Check returned items';

  @override
  String get returnRestock => 'Put back on sale';

  @override
  String get returnRestockOnlyResellable =>
      'Only items that can be sold again go back on sale';

  @override
  String get returnInspectSave => 'Save check';

  @override
  String get returnPickCondition => 'Pick a condition for each item';

  @override
  String get refundTitle => 'Refund the customer';

  @override
  String get refundAmount => 'Amount (Rs)';

  @override
  String refundMax(String amount) {
    return 'Up to $amount';
  }

  @override
  String get refundTooMuch => 'More than the customer paid';

  @override
  String get refundMethod => 'How';

  @override
  String get refundReference => 'Reference (optional)';

  @override
  String get refundSend => 'Refund';

  @override
  String get returnDone => 'Return updated';

  @override
  String get returnsTabToDecide => 'To decide';

  @override
  String get returnsTabInProgress => 'In progress';

  @override
  String get returnsTabToRefund => 'To refund';

  @override
  String get returnsTabDone => 'Done';

  @override
  String returnsTabCount(String label, int count) {
    return '$label ($count)';
  }

  @override
  String get returnsEmpty => 'Nothing here.';

  @override
  String returnsListItem(String number, int order) {
    return '$number · Order #$order';
  }

  @override
  String returnsHomeCard(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count returns to decide',
      one: '1 return to decide',
    );
    return '$_temp0';
  }

  @override
  String get returnsHomeCardBody => 'Approve or reject customer returns.';

  @override
  String get ccStateRunning => 'Your store is running.';

  @override
  String get ccStateWaiting => 'A few things are waiting for you.';

  @override
  String get ccStateAttention => 'Something needs you now.';

  @override
  String get ccModeAssisted => 'Assisted mode';

  @override
  String get ccModeSmart => 'Smart mode';

  @override
  String get ccModeAutopilot => 'Autopilot mode';

  @override
  String get ccPeriod => 'Last 7 days';

  @override
  String get ccOrders => 'Orders';

  @override
  String get ccRevenue => 'Sales';

  @override
  String get ccAiMessages => 'AI replies';

  @override
  String get ccDelivered => 'Delivered';

  @override
  String get ccInTransit => 'On the way';

  @override
  String get ccReturns => 'Returns';

  @override
  String get ccFeedLink => 'See what ran automatically';

  @override
  String get ccWorkflowsLink => 'Workflows';

  @override
  String get approvalsTitle => 'Waiting for approval';

  @override
  String get approvalsEmpty => 'Nothing is waiting for your approval.';

  @override
  String get approvalsApprove => 'Approve';

  @override
  String get approvalsReject => 'Reject';

  @override
  String get approvalsRejectTitle => 'Reject this step?';

  @override
  String get approvalsNote => 'Note (optional)';

  @override
  String get approvalsCancel => 'Keep it';

  @override
  String get approvalsManagersOnly => 'Only managers can approve automation.';

  @override
  String get approvalsDone => 'Done.';

  @override
  String get autoActionNotifySeller => 'Tell you';

  @override
  String get autoActionAddOrderNote => 'Add an order note';

  @override
  String get autoActionSendCustomerMessage => 'Message the customer';

  @override
  String get autoActionSendReviewRequest => 'Ask for a review';

  @override
  String get autoActionBookCourier => 'Book a courier';

  @override
  String get autoActionRequestPickup => 'Request pickup';

  @override
  String get autoActionRequestReattempt => 'Ask the courier to try again';

  @override
  String get autoActionApproveReturn => 'Approve a return';

  @override
  String get autoActionSendAiReply => 'Send an AI reply';

  @override
  String get autoActionIssueRefund => 'Refund the customer';

  @override
  String get autoActionContinue => 'Continue the workflow';

  @override
  String get autoActionOther => 'Automated step';

  @override
  String get ruleAssisted => 'Your shop is in Assisted mode';

  @override
  String get ruleR2Off => 'This kind of action isn\'t switched on';

  @override
  String get ruleAboveLimit => 'Above your limit';

  @override
  String get ruleNotSure => 'Not sure enough';

  @override
  String get ruleHighRisk => 'Always needs a person';

  @override
  String get ruleBlocked => 'Not possible right now';

  @override
  String get ruleApprovalStep => 'The workflow asks for your OK';

  @override
  String get ruleRanSmart => 'Ran automatically (Smart mode)';

  @override
  String get ruleRanAutopilot => 'Ran automatically (Autopilot mode)';

  @override
  String get ruleRanEnabled => 'Ran automatically: you switched this on';

  @override
  String get ruleNotice => 'Just a notice';

  @override
  String get feedTitle => 'What ran automatically';

  @override
  String get feedEmpty => 'Nothing ran automatically in the last 7 days.';

  @override
  String get workflowsTitle => 'Workflows';

  @override
  String get workflowsEmpty => 'No workflows yet. Create one on the web.';

  @override
  String get wfStatusDraft => 'Off';

  @override
  String get wfStatusActive => 'On';

  @override
  String get wfStatusPaused => 'Paused';

  @override
  String get wfBroke => 'Paused after repeated failures';

  @override
  String get wfTurnOn => 'Turn on';

  @override
  String get wfTurnOff => 'Pause';

  @override
  String get wfEditOnWeb => 'Edit workflows on the web.';

  @override
  String get wfManagersOnly => 'Only managers can turn workflows on or off.';

  @override
  String ccDoneAuto(int count) {
    return '$count done automatically';
  }

  @override
  String ccDoneTeam(int count) {
    return '$count done by your team';
  }

  @override
  String ccShare(String percent) {
    return '$percent automatic';
  }

  @override
  String ccNeedsAttention(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count things need you',
      one: '1 thing needs you',
      zero: 'Nothing needs you',
    );
    return '$_temp0';
  }

  @override
  String approvalsOrder(int number) {
    return 'Order #$number';
  }

  @override
  String approvalsWhy(String reason) {
    return 'Waiting: $reason';
  }

  @override
  String wfRuns(int done, int waiting, int failed) {
    return '$done done · $waiting in progress · $failed failed';
  }

  @override
  String get apsTitle => 'Autopilot Score';

  @override
  String get apsNotEnough => 'Not enough activity yet';

  @override
  String get apsCapNotEnough => 'not enough activity';

  @override
  String apsWindow(int days) {
    return 'Last $days days';
  }

  @override
  String apsCounts(int a, int f, int m) {
    return 'Automatic $a · Failed $f · By your team $m';
  }

  @override
  String apsExcluded(int count, String reason) {
    return '$count not counted: $reason';
  }

  @override
  String get apsExclAboveThreshold => 'Needed approval by your rules';

  @override
  String get apsExclNotInPlan => 'Not in your plan';

  @override
  String get apsExclNoCapability => 'Not possible on this channel';

  @override
  String get apsExclOther => 'Other reasons';

  @override
  String apsHoursSaved(String hours) {
    return 'About $hours hours saved (estimated)';
  }

  @override
  String get apsCapCustomerReplies => 'Customer replies';

  @override
  String get apsCapOrderCapture => 'Order capture';

  @override
  String get apsCapShipmentCreation => 'Booking couriers';

  @override
  String get apsCapPickupRequests => 'Pickup requests';

  @override
  String get apsCapDeliveryNotifications => 'Delivery messages';

  @override
  String get apsCapDeliveryRecovery => 'Failed delivery follow-up';

  @override
  String get apsCapReturns => 'Returns';

  @override
  String get apsCapRefunds => 'Refunds';

  @override
  String get apsCapMarketing => 'Marketing';

  @override
  String get apsCapOther => 'Other work';

  @override
  String get recsTitle => 'Suggestions';

  @override
  String get recSetMode => 'Switch to Smart mode';

  @override
  String get recActivateTemplate => 'Turn on “Book a courier when packed”';

  @override
  String get recEnableR2 => 'Let reattempts run by themselves';

  @override
  String get recEnableReturnAuto => 'Auto-approve small returns';

  @override
  String get recEnableNotifications => 'Message customers about deliveries';

  @override
  String get recPlanUpgrade => 'Available on a higher plan';

  @override
  String get recCourierSelection => 'Let Courier Brain pick couriers';

  @override
  String recRestock(String title) {
    return 'Restock $title';
  }

  @override
  String get recOther => 'Suggestion';

  @override
  String recWhyManualGap(String manual, String eligible, String capability) {
    return 'Your team did $manual of $eligible $capability by hand in 30 days';
  }

  @override
  String recWhyCourier(
    String theirs,
    String ours,
    String destination,
    String n,
  ) {
    return 'Another courier delivered $theirs% vs $ours% to $destination ($n parcels)';
  }

  @override
  String recWhyRestock(String sold, String available, String days) {
    return '$sold sold in 30 days, $available left (about $days days)';
  }

  @override
  String get recConfidenceHigh => 'High confidence';

  @override
  String get recConfidenceMedium => 'Medium confidence';

  @override
  String recImpactScore(String score) {
    return 'Could raise this to $score';
  }

  @override
  String recImpactCourier(String points) {
    return '+$points points delivery success';
  }

  @override
  String get recAccept => 'Apply';

  @override
  String get recDismiss => 'Dismiss';

  @override
  String get recDismissTitle => 'Why dismiss this?';

  @override
  String get recDismissReason => 'Reason';

  @override
  String get recCancel => 'Cancel';

  @override
  String get recManagersOnly => 'Only managers can apply this';

  @override
  String get recApplied => 'Done';

  @override
  String get recDismissed => 'Dismissed';

  @override
  String get riskTitle => 'Delivery risk';

  @override
  String get riskLevelLow => 'Low risk';

  @override
  String get riskLevelMedium => 'Check before sending';

  @override
  String get riskLevelHigher => 'Higher delivery risk';

  @override
  String get riskActionOk => 'Fine to send as cash on delivery';

  @override
  String get riskActionVerifyPhone => 'Call to confirm the order';

  @override
  String get riskActionPartialAdvance => 'Ask for a part payment first';

  @override
  String get riskActionManualReview => 'Review before packing';

  @override
  String riskFactorHistory(String delivered, String failed) {
    return 'Delivered $delivered, failed $failed before';
  }

  @override
  String get riskFactorNewCustomer => 'First order with you';

  @override
  String riskFactorReturns(String returns) {
    return '$returns returns before';
  }

  @override
  String get riskFactorAddressMissing => 'Address incomplete';

  @override
  String get riskFactorAddressPartial => 'Some address details missing';

  @override
  String riskFactorOrderValue(String ratio) {
    return '$ratio× your usual order';
  }

  @override
  String riskFactorRoute(String rate, String district) {
    return '$rate% failed deliveries to $district';
  }

  @override
  String get riskFairness =>
      'Based only on this customer\'s history with your shop, the address and order value. Never on name, gender, religion, caste or ethnicity.';

  @override
  String riskOverridden(String reason) {
    return 'You changed this: $reason';
  }

  @override
  String riskDisputed(String note) {
    return 'Customer disputes this: $note';
  }

  @override
  String get riskOverride => 'Change level';

  @override
  String get riskOverrideTitle => 'Change the risk level';

  @override
  String get riskOverrideReason => 'Why (at least 3 characters)';

  @override
  String get riskSave => 'Save';

  @override
  String get riskDispute => 'Customer disputes this';

  @override
  String get riskDisputeTitle => 'Record the customer\'s dispute';

  @override
  String get riskDisputeNote => 'What the customer says';

  @override
  String get riskUpdated => 'Updated';

  @override
  String get riskCancel => 'Cancel';
}
