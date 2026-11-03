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

  @override
  String get captureTitle => 'Capture product';

  @override
  String get captureIntro => 'Add up to 6 clear photos. Front, back and a close-up of the fabric or label work best.';

  @override
  String get captureTakePhoto => 'Take photo';

  @override
  String get captureFromGallery => 'Choose from gallery';

  @override
  String capturePhotoCount(int count, int max) {
    final intl.NumberFormat countNumberFormat = intl.NumberFormat.decimalPattern(localeName);
    final String countString = countNumberFormat.format(count);
    final intl.NumberFormat maxNumberFormat = intl.NumberFormat.decimalPattern(localeName);
    final String maxString = maxNumberFormat.format(max);

    return '$countString of $maxString photos';
  }

  @override
  String get captureLimitReached => 'That\'s 6 photos — the most one draft can use.';

  @override
  String captureSkipped(int count) {
    final intl.NumberFormat countNumberFormat = intl.NumberFormat.decimalPattern(localeName);
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
  String get capturePickerError => 'Couldn\'t open the camera or gallery. Check photo and camera access in phone Settings.';

  @override
  String get captureResumeAll => 'Resume uploads';

  @override
  String get captureKeepsGoing => 'Uploads keep going if you switch apps. If the app closes, they pick up where they left off.';

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
  String get rejectUnsupported => 'This format isn\'t supported. Use JPEG, PNG, WebP or HEIC.';

  @override
  String get rejectMalware => 'This file looked unsafe, so we deleted it.';

  @override
  String get tipLowResolution => 'Photo is small. Move closer or use the main camera.';

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
  String get errStorageFull => 'Photo storage on your plan is full. Delete old photos or upgrade.';

  @override
  String get errFileUnreadable => 'We couldn\'t read this photo from your phone. Pick it again.';

  @override
  String get errUploadMissing => 'The photo didn\'t reach us. Retry the upload.';

  @override
  String get errUploadExpired => 'The upload took too long. Start it again.';

  @override
  String get errMediaNotReady => 'Some photos are still being checked. Try again in a moment.';

  @override
  String get errMediaNotFound => 'Some photos are no longer available. Add them again.';

  @override
  String get errDraftNotReady => 'This draft isn\'t ready yet.';

  @override
  String get errNotPublishable => 'This product isn\'t ready to go live yet.';

  @override
  String get errProductNotActive => 'Make the product live first, then publish it to channels.';

  @override
  String get errCapabilityNotSupported => 'This channel can\'t do that.';

  @override
  String get errVersionConflict => 'Someone else changed this. We loaded the latest — check and try again.';

  @override
  String get errPostLocked => 'Scheduled posts can\'t be edited. Unschedule it first.';

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
  String get errAiUnavailable => 'Our writing service is busy. Try again in a few minutes.';

  @override
  String get draftWorkingTitle => 'Writing your listing';

  @override
  String get draftWorkingBody => 'Reading your photos and drafting the name, description and captions in Nepali and English. This usually takes under a minute.';

  @override
  String get draftQueued => 'In line';

  @override
  String get draftRunning => 'Working on it';

  @override
  String get draftLeaveOk => 'You can leave this screen; we\'ll keep working. Find it later under Drafts.';

  @override
  String get draftFailedTitle => 'We couldn\'t write this draft';

  @override
  String get draftFailedBody => 'Our writing service had a problem. Your photos are safe.';

  @override
  String get draftAppliedTitle => 'Already saved as a product';

  @override
  String get draftOpenProduct => 'Open product';

  @override
  String get draftDiscarded => 'This draft was discarded.';

  @override
  String get reviewTitle => 'Check your listing';

  @override
  String get reviewAiNote => 'Written by AI from your photos. Change anything that\'s off.';

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
  String get fieldCategoryHint => 'Separate levels with /, e.g. Clothing / Kurta';

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
    final intl.NumberFormat countNumberFormat = intl.NumberFormat.decimalPattern(localeName);
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
  String get reviewPriceNote => 'Prices always come from you — AI never sets them.';

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
    final intl.NumberFormat countNumberFormat = intl.NumberFormat.decimalPattern(localeName);
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
  String get tooManyVariants => 'That makes more than 100 combinations. Remove some values.';

  @override
  String get reviewSectionChecklist => 'AI couldn\'t tell — please confirm';

  @override
  String get reviewSectionWarnings => 'Things to check';

  @override
  String get issueClaimPrice => 'The text mentions a price. Prices come from you; please check.';

  @override
  String get issueClaimDiscount => 'The text mentions a discount you didn\'t give us. Remove it or make sure it\'s real.';

  @override
  String get issueClaimStock => 'The text talks about stock. Stock comes from your inventory; please check.';

  @override
  String get issueClaimDelivery => 'The text promises delivery terms. Make sure they\'re right.';

  @override
  String get issueClaimWarranty => 'The text mentions a warranty. Keep it only if you offer one.';

  @override
  String get issueClaimAuthenticity => 'The text says it\'s original or genuine. Keep it only if you can back it up.';

  @override
  String get issueClaimOther => 'The text makes a claim we couldn\'t verify. Please check.';

  @override
  String get issueNotProductPhoto => 'These photos may not show a product. Check them before saving.';

  @override
  String get issueTooLong => 'Some text was too long and was shortened. Read it once.';

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
  String get productProblemVariant => 'Add at least one active variant (from the web dashboard for now).';

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
  String get publishNoChannels => 'No shop channels connected yet. Connect Instagram, Facebook or TikTok from the web dashboard.';

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
  String get reconnectBody => 'For now, reconnect channels from the web dashboard in a browser:';

  @override
  String get reconnectCopied => 'Link copied';

  @override
  String get actionCopyLink => 'Copy link';

  @override
  String get postsSection => 'Create posts';

  @override
  String get postsIntro => 'Turn the AI captions into posts for each channel. You review before anything goes out.';

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
  String get postNeedsApprovalNote => 'AI-written posts need an approval before they go out.';

  @override
  String get postNoApprovePermission => 'Ask the shop owner or a manager to approve this.';

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
  String get draftsEmpty => 'No drafts yet. Start with a few photos of a product.';

  @override
  String get draftsIntro => 'Pick a draft to turn into posts, or start with new photos.';

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
  String get forgotSubtitle => 'Enter your account email and we\'ll send you a link to set a new password.';

  @override
  String get forgotAction => 'Send reset link';

  @override
  String get forgotSentTitle => 'Check your email';

  @override
  String get forgotSentBody => 'If an account exists for that email, a reset link is on its way. Open it on this phone or a computer. It works once and expires in 30 minutes.';

  @override
  String get forgotBack => 'Back to sign in';
}
