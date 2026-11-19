// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Nepali (`ne`).
class AppLocalizationsNe extends AppLocalizations {
  AppLocalizationsNe([String locale = 'ne']) : super(locale);

  @override
  String get appName => 'Nivaro';

  @override
  String get actionRetry => 'फेरि प्रयास गर्नुहोस्';

  @override
  String get actionContinue => 'अगाडि बढ्नुहोस्';

  @override
  String get actionCancel => 'रद्द गर्नुहोस्';

  @override
  String requestIdLabel(String id) {
    return 'सन्दर्भ $id';
  }

  @override
  String get loadingLabel => 'लोड हुँदैछ';

  @override
  String get splashLoading => 'पसल खोल्दैछौं…';

  @override
  String get offlineBanner => 'इन्टरनेट छैन। जोडिएपछि काम अगाडि बढ्छ।';

  @override
  String get offlineTitle => 'इन्टरनेट जडान छैन';

  @override
  String get offlineBody => 'मोबाइल डाटा वा Wi-Fi हेरेर फेरि प्रयास गर्नुहोस्।';

  @override
  String get errorTitle => 'लोड हुन सकेन';

  @override
  String get permissionDeniedTitle => 'तपाईंलाई यो हेर्ने अनुमति छैन';

  @override
  String get permissionDeniedBody =>
      'पसलको मालिकलाई तपाईंको भूमिकामा अनुमति थप्न भन्नुहोस्।';

  @override
  String get featureNotInPlanTitle => 'हालको प्लानमा यो छैन';

  @override
  String get featureNotInPlanBody => 'यो चलाउन प्लान अपग्रेड गर्नुहोस्।';

  @override
  String get errValidation => 'केही विवरण मिलाउनुपर्छ।';

  @override
  String get errNotAuthenticated => 'कृपया फेरि लगइन गर्नुहोस्।';

  @override
  String get errInvalidCredentials => 'इमेल वा पासवर्ड मिलेन।';

  @override
  String get errMfaInvalidCode =>
      'कोड मिलेन। Authenticator एप हेरेर फेरि हाल्नुहोस्।';

  @override
  String get errPermissionDenied => 'तपाईंलाई यो गर्ने अनुमति छैन।';

  @override
  String get errFeatureNotInPlan => 'यो तपाईंको प्लानमा पर्दैन।';

  @override
  String get errNotFound => 'त्यो भेटिएन।';

  @override
  String get errConflict =>
      'यो अर्को ठाउँबाट बदलियो। रिफ्रेस गरेर फेरि प्रयास गर्नुहोस्।';

  @override
  String get errIdempotencyInProgress =>
      'अघिल्लो काम अझै चल्दैछ। एकछिन पर्खनुहोस्।';

  @override
  String get errIdempotencyKeyReused =>
      'यो पहिले नै फरक विवरणसहित पठाइसकिएको छ। फेरि सुरुबाट गर्नुहोस्।';

  @override
  String get errSlugTaken =>
      'त्यो पसल लिंक अरूले लिइसके। अर्कै नाम राख्नुहोस्।';

  @override
  String get errEmailTaken => 'यो इमेलमा पहिल्यै खाता छ। लगइन गरेर हेर्नुहोस्।';

  @override
  String get errUsageLimitReached =>
      'यो अवधिको सीमा सकियो। क्रेडिट किन्नुहोस्, अपग्रेड गर्नुहोस् वा नवीकरण पर्खनुहोस्।';

  @override
  String get errInvalidStateTransition => 'अहिलेको अवस्थामा यो गर्न मिल्दैन।';

  @override
  String get errRateLimited => 'धेरै पटक प्रयास भयो। अलि पछि फेरि गर्नुहोस्।';

  @override
  String get errDependencyUnavailable =>
      'हामीले चलाउने एउटा सेवा अहिले बन्द छ। तपाईंको डाटा सुरक्षित छ, केहीबेरमा फेरि प्रयास गर्नुहोस्।';

  @override
  String get errSessionEnded =>
      'सुरक्षाका लागि लगआउट गरियो। फेरि लगइन गर्नुहोस्।';

  @override
  String get errSessionReused =>
      'तपाईंको लगइन अर्को डिभाइसमा चलाइयो, त्यसैले सबैतिरबाट लगआउट गरियो। फेरि लगइन गर्नुहोस्; तपाईं होइन भने पासवर्ड बदल्नुहोस्।';

  @override
  String get errSessionRevoked =>
      'अर्को डिभाइसबाट यो फोन लगआउट गरियो। फेरि लगइन गर्नुहोस्।';

  @override
  String get errNetwork => 'जडान भएन। इन्टरनेट हेरेर फेरि प्रयास गर्नुहोस्।';

  @override
  String get errTimeout =>
      'इन्टरनेट ढिलो भएर धेरै समय लाग्यो। फेरि प्रयास गर्नुहोस्।';

  @override
  String get errServer =>
      'हाम्रो तर्फबाट गडबड भयो। केहीबेरमा फेरि प्रयास गर्नुहोस्।';

  @override
  String get errUnknown => 'केही गडबड भयो। फेरि प्रयास गर्नुहोस्।';

  @override
  String get errFieldInvalid => 'यो विवरण जाँच्नुहोस्';

  @override
  String get loginTitle => 'आफ्नो पसलमा लगइन गर्नुहोस्';

  @override
  String get loginSubtitle => 'अर्डर, म्यासेज र स्टक एकै ठाउँमा।';

  @override
  String get fieldEmail => 'इमेल';

  @override
  String get fieldPassword => 'पासवर्ड';

  @override
  String get fieldFullName => 'तपाईंको नाम';

  @override
  String get fieldPhone => 'मोबाइल नम्बर (नभए पनि हुन्छ)';

  @override
  String get validationEmailRequired => 'इमेल हाल्नुहोस्';

  @override
  String get validationEmailInvalid => 'इमेल मिलेन जस्तो छ';

  @override
  String get validationPasswordRequired => 'पासवर्ड हाल्नुहोस्';

  @override
  String validationPasswordTooShort(int min) {
    final intl.NumberFormat minNumberFormat = intl.NumberFormat.decimalPattern(
      localeName,
    );
    final String minString = minNumberFormat.format(min);

    return 'कम्तीमा $minString अक्षर राख्नुहोस्';
  }

  @override
  String get validationPasswordEqualsEmail => 'पासवर्ड र इमेल एउटै हुन मिल्दैन';

  @override
  String get validationNameRequired => 'नाम हाल्नुहोस्';

  @override
  String get validationPhoneInvalid => 'सही मोबाइल नम्बर हाल्नुहोस्';

  @override
  String passwordHint(int min) {
    final intl.NumberFormat minNumberFormat = intl.NumberFormat.decimalPattern(
      localeName,
    );
    final String minString = minNumberFormat.format(min);

    return 'कम्तीमा $minString अक्षर। सजिलै अनुमान हुने पासवर्ड नराख्नुहोस्।';
  }

  @override
  String get loginAction => 'लगइन';

  @override
  String get loginNoAccount => 'नयाँ हो? खाता खोल्नुहोस्';

  @override
  String get showPassword => 'पासवर्ड देखाउनुहोस्';

  @override
  String get hidePassword => 'पासवर्ड लुकाउनुहोस्';

  @override
  String get mfaTitle => '६ अंकको कोड हाल्नुहोस्';

  @override
  String get mfaSubtitle => 'Authenticator एप खोल्नुहोस्। रिकभरी कोड पनि चल्छ।';

  @override
  String get fieldMfaCode => 'कोड';

  @override
  String get validationCodeRequired => 'कोड हाल्नुहोस्';

  @override
  String get mfaVerifyAction => 'पुष्टि गर्नुहोस्';

  @override
  String get mfaUseDifferentAccount => 'अर्कै खाता चलाउनुहोस्';

  @override
  String get registerTitle => 'बिक्रेता खाता खोल्नुहोस्';

  @override
  String get registerSubtitle => 'करिब एक मिनेट लाग्छ।';

  @override
  String get registerAction => 'खाता खोल्नुहोस्';

  @override
  String get registerHaveAccount => 'खाता छ? लगइन गर्नुहोस्';

  @override
  String get onboardingTitle => 'आफ्नो पसल मिलाउनुहोस्';

  @override
  String get onboardingSubtitle => 'यी कुरा पछि सेटिङमा बदल्न सकिन्छ।';

  @override
  String get fieldBusinessName => 'पसल वा व्यवसायको नाम';

  @override
  String get fieldBusinessNameHint => 'जस्तै: ठमेल ह्यान्डलुम';

  @override
  String get validationBusinessNameRequired => 'पसलको नाम हाल्नुहोस्';

  @override
  String get validationBusinessNameTooShort => 'नाम धेरै छोटो भयो';

  @override
  String get fieldCurrency => 'मुद्रा';

  @override
  String get currencyNpr => 'नेपाली रुपैयाँ (NPR)';

  @override
  String get fieldTimezone => 'समय क्षेत्र';

  @override
  String get timezoneKathmandu => 'काठमाडौं (UTC+५:४५)';

  @override
  String get onboardingFixedNote =>
      'अहिलेलाई NPR र नेपाली समय मात्र। अरू विकल्प पछि आउँछ।';

  @override
  String get fieldDefaultLanguage => 'ग्राहक र रसिदको भाषा';

  @override
  String get languageNepali => 'नेपाली';

  @override
  String get languageEnglish => 'English';

  @override
  String get onboardingAction => 'पसल बनाउनुहोस्';

  @override
  String get navHome => 'गृह';

  @override
  String get navSettings => 'सेटिङ';

  @override
  String homeGreeting(String name) {
    return 'नमस्ते, $name';
  }

  @override
  String get homeSectionToday => 'आज';

  @override
  String get metricOrders => 'अर्डर';

  @override
  String get metricRevenue => 'बिक्री रकम';

  @override
  String get metricAiMessages => 'AI ले जवाफ दिएका म्यासेज';

  @override
  String get metricReadyToShip => 'पठाउन तयार';

  @override
  String get metricNotYet => 'अहिले गनिँदैन';

  @override
  String get metricNotYetBody =>
      'अर्डर र म्यासेज जोडिएपछि यी अंक सुरु हुन्छन्। त्यतिबेलासम्म अड्कल होइन, खाली देखाउँछौं।';

  @override
  String metricUnavailableSemantics(String metric) {
    return '$metric: अहिले उपलब्ध छैन';
  }

  @override
  String get homeSectionNeedsYou => 'तपाईंले हेर्नुपर्ने';

  @override
  String get exceptionsEmptyTitle => 'अहिले तपाईंले हेर्नुपर्ने केही छैन';

  @override
  String get exceptionsEmptyBody =>
      'पैसा नमिलेको, डेलिभरी असफल भएको वा AI पक्का नभएका कुरा सबैभन्दा पहिले यहीँ आउँछन्।';

  @override
  String exceptionsCount(int count) {
    final intl.NumberFormat countNumberFormat = intl
        .NumberFormat.decimalPattern(localeName);
    final String countString = countNumberFormat.format(count);

    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$countString वटा',
      one: '१ वटा',
    );
    return '$_temp0';
  }

  @override
  String get exPaymentMismatch => 'भुक्तानी मिलेन';

  @override
  String get exLowConfidenceAi => 'AI पक्का भएन';

  @override
  String get exRefundAboveThreshold => 'ठूलो रिफन्ड स्वीकृत गर्नुपर्ने';

  @override
  String get exCourierFailed => 'डेलिभरी असफल';

  @override
  String get exChannelExpired => 'च्यानल छुट्यो';

  @override
  String get exInventoryMismatch => 'स्टक मिलेन';

  @override
  String get exListingDrift => 'च्यानलमा बदलियो';

  @override
  String get exActionResolveDrift => 'संस्करण छान्नुहोस्';

  @override
  String get exPublishFailed => 'पोस्ट हुन सकेन';

  @override
  String get exAmbiguousVariant => 'कुन साइज वा रङ?';

  @override
  String get exCustomerEscalation => 'ग्राहक मान्छेसँगै कुरा गर्न चाहनुहुन्छ';

  @override
  String get exProviderFailure => 'सेवामा समस्या';

  @override
  String get autopilotTitle => 'अटोपाइलट';

  @override
  String get autopilotModeAssisted => 'सहायक';

  @override
  String get autopilotModeSmart => 'स्मार्ट';

  @override
  String get autopilotModeAutopilot => 'अटोपाइलट';

  @override
  String get autopilotModeAssistedHint =>
      'AI सुझाव दिन्छ, तपाईं स्वीकृत गर्नुहुन्छ';

  @override
  String get autopilotModeSmartHint =>
      'सामान्य काम आफैं हुन्छ, जोखिमको काम तपाईंलाई पर्खन्छ';

  @override
  String get autopilotModeAutopilotHint => 'तपाईंका नियमभित्र आफैं चल्छ';

  @override
  String autopilotAutomated(int count) {
    final intl.NumberFormat countNumberFormat = intl
        .NumberFormat.decimalPattern(localeName);
    final String countString = countNumberFormat.format(count);

    return '$countString आफैं भयो';
  }

  @override
  String autopilotNeedsAttention(int count) {
    final intl.NumberFormat countNumberFormat = intl
        .NumberFormat.decimalPattern(localeName);
    final String countString = countNumberFormat.format(count);

    return '$countString तपाईंलाई पर्खँदै';
  }

  @override
  String get autopilotNotActive =>
      'अहिले चालू छैन। अर्डर र म्यासेज जोडिएपछि सुरु हुन्छ।';

  @override
  String get quickActionsTitle => 'छिटो काम';

  @override
  String get qaAddProduct => 'सामान थप्नुहोस्';

  @override
  String get qaCaptureProduct => 'फोटो खिच्नुहोस्';

  @override
  String get qaGenerateContent => 'पोस्ट लेखाउनुहोस्';

  @override
  String get qaCreateReel => 'Reel बनाउनुहोस्';

  @override
  String get qaViewOrders => 'अर्डर';

  @override
  String get qaViewMessages => 'म्यासेज';

  @override
  String get comingSoonBadge => 'अर्को अपडेटमा आउँदैछ';

  @override
  String get comingSoonWhat => 'यसले के गर्छ';

  @override
  String get comingSoonHonest =>
      'त्यतिबेलासम्म यहाँ नक्कली अर्डर वा बनावटी अंक देखाइँदैन।';

  @override
  String get soonAddProductBody =>
      'मूल्य, स्टक र साइज/रङसहित एकपटक सामान थप्नुहोस्। Instagram, Facebook र TikTok मा आफैं मिलाएर राख्छौं।';

  @override
  String get soonCaptureProductBody =>
      'फोनमा केही फोटो खिच्नुहोस्। ब्याकग्राउन्ड सफा गरेर नाम र विवरण तयार गर्छौं, तपाईं जाँचेर राख्नुहोस्।';

  @override
  String get soonGenerateContentBody =>
      'सामानको विवरणबाट नेपाली वा अंग्रेजीमा क्याप्सन लेख्छौं। तपाईंले स्वीकृत नगरी केही पोस्ट हुँदैन।';

  @override
  String get soonCreateReelBody =>
      'सामानका फोटो र क्लिपबाट छोटो Reel बनाउँछौं। प्लानको भिडियो क्रेडिट लाग्छ।';

  @override
  String get soonViewOrdersBody =>
      'च्याटदेखि ग्राहकको ढोकासम्म हरेक अर्डर: COD, कुरियरको अवस्था र फिर्ता।';

  @override
  String get soonViewMessagesBody =>
      'सबै ग्राहकका म्यासेज एउटै इनबक्समा। AI ले तपाईंकै स्टक र मूल्य हेरेर जवाफ तयार गर्छ।';

  @override
  String get settingsTitle => 'सेटिङ';

  @override
  String get settingsProfile => 'प्रोफाइल';

  @override
  String get settingsShop => 'पसल';

  @override
  String get settingsLanguage => 'एपको भाषा';

  @override
  String get languageSystem => 'फोनकै भाषा';

  @override
  String get settingsSecurity => 'सुरक्षा र डिभाइस';

  @override
  String get settingsPlan => 'प्लान र प्रयोग';

  @override
  String get settingsLogout => 'लगआउट';

  @override
  String get logoutConfirmTitle => 'यो फोनबाट लगआउट गर्ने?';

  @override
  String get emailUnverified => 'इमेल प्रमाणित भएको छैन';

  @override
  String get mfaOn => 'दुई-चरण लगइन चालू छ';

  @override
  String get mfaOff => 'दुई-चरण लगइन बन्द छ';

  @override
  String get securityTitle => 'सुरक्षा र डिभाइस';

  @override
  String get sessionsTitle => 'लगइन भएका डिभाइस';

  @override
  String get sessionThisDevice => 'यो फोन';

  @override
  String sessionLastUsed(String when) {
    return 'पछिल्लो पटक $when';
  }

  @override
  String get sessionUnknownDevice => 'नचिनिएको डिभाइस';

  @override
  String get sessionRevoke => 'लगआउट';

  @override
  String sessionRevokeConfirm(String device) {
    return '$device बाट लगआउट गर्ने?';
  }

  @override
  String get sessionsRevokeOthers => 'अरू सबै डिभाइसबाट लगआउट';

  @override
  String get sessionsRevokeOthersConfirm =>
      'यो फोनबाहेक सबै डिभाइसबाट लगआउट हुन्छ।';

  @override
  String get sessionsRevokedToast => 'लगआउट भयो';

  @override
  String get sessionsOnlyThis => 'यो फोनमा मात्र लगइन छ।';

  @override
  String get planTitle => 'प्लान र प्रयोग';

  @override
  String planStatusTrialing(String date) {
    return 'ट्रायल · $date मा सकिन्छ';
  }

  @override
  String get planStatusActive => 'चालू';

  @override
  String get planStatusPastDue => 'भुक्तानी बाँकी';

  @override
  String get planStatusCanceled => 'रद्द भयो';

  @override
  String planPeriod(String start, String end) {
    return 'हालको अवधि $start – $end';
  }

  @override
  String get usageTitle => 'प्रयोग';

  @override
  String usageUsedOf(String used, String limit) {
    return '$limit मध्ये $used';
  }

  @override
  String get usageUnlimited => 'असीमित';

  @override
  String usageReserved(int count) {
    final intl.NumberFormat countNumberFormat = intl
        .NumberFormat.decimalPattern(localeName);
    final String countString = countNumberFormat.format(count);

    return '$countString प्रक्रियामा';
  }

  @override
  String get usagePeriodMonth => 'यो महिना';

  @override
  String get usagePeriodDay => 'आज';

  @override
  String get usageLevelNotice => '७०% भन्दा बढी प्रयोग भयो';

  @override
  String get usageLevelWarning => 'सीमा नजिक पुग्यो';

  @override
  String get usageLevelReached =>
      'सीमा सकियो। जारी राख्न क्रेडिट किन्नुहोस् वा अपग्रेड गर्नुहोस्।';

  @override
  String get usageEmpty => 'तपाईंको प्लानमा अहिले केही नापिँदैन।';

  @override
  String get creditsTitle => 'क्रेडिट';

  @override
  String creditsBalance(String balance) {
    return '$balance क्रेडिट';
  }

  @override
  String get creditsNoTransactions => 'अहिलेसम्म क्रेडिट कारोबार छैन';

  @override
  String get videoMeterTitle => 'भिडियो क्रेडिट';

  @override
  String get videoMeterMonthly => 'यो महिना';

  @override
  String get videoMeterDaily => 'आज';

  @override
  String get videoMeterNoDailyCap => 'दैनिक सीमा छैन';

  @override
  String get videoMeterDailyReached => 'आजको सीमा सकियो। भोलि फेरि खुल्छ।';

  @override
  String get videoMeterHelp =>
      'महिनाको कोटा र दैनिक सीमा छुट्टाछुट्टै छन्, एकै दिनमा महिनाभरको नसकियोस् भनेर।';

  @override
  String get resAiTextGenerations => 'AI लेखन';

  @override
  String get resAiInboxReplies => 'AI जवाफ';

  @override
  String get resAiImages => 'AI तस्बिर';

  @override
  String get resAutoReels => 'Auto Reel';

  @override
  String get resPremiumVideo => 'प्रिमियम भिडियो';

  @override
  String get resProducts => 'सामान';

  @override
  String get resOrders => 'अर्डर';

  @override
  String get resChannels => 'च्यानल';

  @override
  String get resTeamMembers => 'टिमका सदस्य';

  @override
  String get resStores => 'स्टोर';

  @override
  String get resStorage => 'स्टोरेज';

  @override
  String get resAutomationRuns => 'अटोमेसन';

  @override
  String get resApiCalls => 'API कल';

  @override
  String get captureTitle => 'सामानको फोटो';

  @override
  String get captureIntro =>
      '६ वटासम्म प्रस्ट फोटो थप्नुहोस्। अगाडि, पछाडि र कपडा वा लेबलको नजिकको फोटो सबैभन्दा राम्रो।';

  @override
  String get captureTakePhoto => 'फोटो खिच्नुहोस्';

  @override
  String get captureFromGallery => 'ग्यालरीबाट छान्नुहोस्';

  @override
  String capturePhotoCount(int count, int max) {
    final intl.NumberFormat countNumberFormat = intl
        .NumberFormat.decimalPattern(localeName);
    final String countString = countNumberFormat.format(count);
    final intl.NumberFormat maxNumberFormat = intl.NumberFormat.decimalPattern(
      localeName,
    );
    final String maxString = maxNumberFormat.format(max);

    return '$maxString मध्ये $countString फोटो';
  }

  @override
  String get captureLimitReached =>
      '६ वटा फोटो पुग्यो, एउटा ड्राफ्टमा यति नै मिल्छ।';

  @override
  String captureSkipped(int count) {
    final intl.NumberFormat countNumberFormat = intl
        .NumberFormat.decimalPattern(localeName);
    final String countString = countNumberFormat.format(count);

    return '$countString वटा फोटो थपिएन, ६ वटा मात्र मिल्छ।';
  }

  @override
  String get captureNotesLabel => 'थप जानकारी (नभए पनि हुन्छ)';

  @override
  String get captureNotesHint => 'जस्तै: शुद्ध सुती, भक्तपुरमा हातले बनेको';

  @override
  String get captureMakeDraft => 'विवरण तयार गर्नुहोस्';

  @override
  String get captureWaitForUploads => 'फोटो अपलोड सकिन पर्खँदै…';

  @override
  String get captureNeedOneReady => 'अगाडि बढ्न कम्तीमा एउटा फोटो चाहिन्छ।';

  @override
  String get captureRemovePhoto => 'फोटो हटाउनुहोस्';

  @override
  String get capturePickerError =>
      'क्यामेरा वा ग्यालरी खुलेन। फोनको सेटिङमा फोटो र क्यामेरा अनुमति हेर्नुहोस्।';

  @override
  String get captureResumeAll => 'अपलोड फेरि सुरु गर्नुहोस्';

  @override
  String get captureKeepsGoing =>
      'अर्को एप खोल्दा पनि अपलोड चलिरहन्छ। एप बन्द भए पनि रोकिएकै ठाउँबाट सुरु हुन्छ।';

  @override
  String get uploadQueued => 'पालो पर्खँदै';

  @override
  String uploadUploading(String percent) {
    return 'अपलोड हुँदै $percent';
  }

  @override
  String get uploadProcessing => 'फोटो जाँच्दै';

  @override
  String get uploadReady => 'तयार';

  @override
  String get uploadPaused => 'रोकियो, इन्टरनेट छैन';

  @override
  String get uploadRetrying => 'फेरि प्रयास गर्दै…';

  @override
  String get uploadRejected => 'यो फोटो चल्दैन';

  @override
  String get uploadFailed => 'अपलोड भएन';

  @override
  String get uploadTapRetry => 'फेरि प्रयास गर्न थिच्नुहोस्';

  @override
  String get rejectNotAnImage => 'यो फाइल फोटो होइन।';

  @override
  String get rejectTooLarge =>
      'फोटो धेरै ठूलो भयो। २० MB भन्दा सानो छान्नुहोस्।';

  @override
  String get rejectUnsupported =>
      'यो ढाँचा चल्दैन। JPEG, PNG, WebP वा HEIC प्रयोग गर्नुहोस्।';

  @override
  String get rejectMalware => 'यो फाइल असुरक्षित देखियो, त्यसैले हटाइयो।';

  @override
  String get tipLowResolution =>
      'फोटो सानो छ। नजिक गएर वा मुख्य क्यामेराले खिच्नुहोस्।';

  @override
  String get tipBlurry => 'फोटो धमिलो देखियो। फोन स्थिर राखेर फोकस गर्नुहोस्।';

  @override
  String get tipTooDark => 'फोटो अँध्यारो देखियो। झ्यालनजिक खिचेर हेर्नुहोस्।';

  @override
  String get tipOverexposed =>
      'फोटो धेरै चम्किलो भयो। सिधा घामबाट अलि पर सर्नुहोस्।';

  @override
  String get errFileTooLarge => 'फोटो धेरै ठूलो भयो (बढीमा २० MB)।';

  @override
  String get errUnsupportedMediaType =>
      'JPEG, PNG, WebP वा HEIC फोटो प्रयोग गर्नुहोस्।';

  @override
  String get errStorageFull =>
      'प्लानको फोटो स्टोरेज भरियो। पुराना फोटो हटाउनुहोस् वा अपग्रेड गर्नुहोस्।';

  @override
  String get errFileUnreadable => 'फोनबाट यो फोटो पढ्न सकिएन। फेरि छान्नुहोस्।';

  @override
  String get errUploadMissing => 'फोटो हामीसम्म आइपुगेन। फेरि अपलोड गर्नुहोस्।';

  @override
  String get errUploadExpired =>
      'अपलोडमा धेरै समय लाग्यो। फेरि सुरु गर्नुहोस्।';

  @override
  String get errMediaNotReady =>
      'केही फोटो अझै जाँच हुँदैछन्। एकछिनपछि फेरि गर्नुहोस्।';

  @override
  String get errMediaNotFound => 'केही फोटो अब भेटिँदैनन्। फेरि थप्नुहोस्।';

  @override
  String get errDraftNotReady => 'यो ड्राफ्ट अझै तयार छैन।';

  @override
  String get errNotPublishable => 'यो सामान अहिले लाइभ गर्न तयार छैन।';

  @override
  String get errProductNotActive =>
      'पहिले सामान लाइभ गर्नुहोस्, अनि च्यानलमा पठाउनुहोस्।';

  @override
  String get errCapabilityNotSupported => 'यो च्यानलले त्यो गर्न सक्दैन।';

  @override
  String get errVersionConflict =>
      'अरू कसैले यो बदल्नुभयो। नयाँ विवरण ल्याइयो, हेरेर फेरि गर्नुहोस्।';

  @override
  String get errPostLocked =>
      'तालिका मिलाइएको पोस्ट बदल्न मिल्दैन। पहिले तालिका हटाउनुहोस्।';

  @override
  String get errReconnectRequired => 'पहिले यो च्यानल फेरि जोड्नुहोस्।';

  @override
  String get errScheduleInPast => 'आउने समय छान्नुहोस्।';

  @override
  String get errScheduleTooFar =>
      'पोस्ट ९० दिनभित्र मात्र तालिकामा राख्न सकिन्छ।';

  @override
  String get errCaptionRequired => 'क्याप्सन लेख्नुहोस्।';

  @override
  String get errCaptionTooLong => 'यो क्याप्सन च्यानलका लागि धेरै लामो भयो।';

  @override
  String get errInvalidPhotoCount => '१ देखि ६ वटा फोटो छान्नुहोस्।';

  @override
  String get errNotFailed => 'असफल ड्राफ्ट मात्र फेरि चलाउन मिल्छ।';

  @override
  String get errAiUnavailable =>
      'लेख्ने सेवा अहिले व्यस्त छ। केही मिनेटपछि फेरि प्रयास गर्नुहोस्।';

  @override
  String get draftWorkingTitle => 'विवरण तयार गर्दैछौं';

  @override
  String get draftWorkingBody =>
      'तपाईंका फोटो हेरेर नेपाली र अंग्रेजीमा नाम, विवरण र क्याप्सन तयार गर्दैछौं। प्रायः एक मिनेटभित्र सकिन्छ।';

  @override
  String get draftQueued => 'पालोमा';

  @override
  String get draftRunning => 'काम हुँदैछ';

  @override
  String get draftLeaveOk =>
      'यो स्क्रिन छोड्न सक्नुहुन्छ, काम चलिरहन्छ। पछि \'ड्राफ्ट\' मा भेटिन्छ।';

  @override
  String get draftFailedTitle => 'ड्राफ्ट तयार गर्न सकिएन';

  @override
  String get draftFailedBody =>
      'लेख्ने सेवामा समस्या भयो। तपाईंका फोटो सुरक्षित छन्।';

  @override
  String get draftAppliedTitle => 'यो पहिले नै सामानको रूपमा सेभ भइसक्यो';

  @override
  String get draftOpenProduct => 'सामान खोल्नुहोस्';

  @override
  String get draftDiscarded => 'यो ड्राफ्ट हटाइएको छ।';

  @override
  String get reviewTitle => 'विवरण जाँच्नुहोस्';

  @override
  String get reviewAiNote =>
      'तपाईंका फोटो हेरेर AI ले लेखेको। नमिलेको कुरा बदल्नुहोस्।';

  @override
  String get reviewSectionText => 'नाम र विवरण';

  @override
  String get fieldTitleNe => 'नाम (नेपाली)';

  @override
  String get fieldTitleEn => 'नाम (अंग्रेजी)';

  @override
  String get fieldDescriptionNe => 'विवरण (नेपाली)';

  @override
  String get fieldDescriptionEn => 'विवरण (अंग्रेजी)';

  @override
  String get validationTitleRequired => 'नेपाली वा अंग्रेजीमा नाम राख्नुहोस्';

  @override
  String get reviewSectionCategory => 'श्रेणी';

  @override
  String get fieldCategoryHint =>
      'तह छुट्याउन / राख्नुहोस्, जस्तै: लुगा / कुर्ता';

  @override
  String confidenceLabel(String percent) {
    return '$percent पक्का';
  }

  @override
  String get reviewSectionDetails => 'विस्तृत जानकारी';

  @override
  String get attrPleaseCheck => 'कृपया जाँच्नुहोस्';

  @override
  String get attrAccept => 'ठीक छ';

  @override
  String get attrEdit => 'बदल्नुहोस्';

  @override
  String get attrAccepted => 'जाँचियो';

  @override
  String get attrEdited => 'तपाईंले बदल्नुभयो';

  @override
  String attrEditTitle(String name) {
    return '$name बदल्नुहोस्';
  }

  @override
  String get actionSave => 'सेभ गर्नुहोस्';

  @override
  String attrUncheckedError(int count) {
    final intl.NumberFormat countNumberFormat = intl
        .NumberFormat.decimalPattern(localeName);
    final String countString = countNumberFormat.format(count);

    return '$countString वटा विवरण अझै जाँच्न बाँकी';
  }

  @override
  String get reviewSectionPrice => 'मूल्य र विकल्प';

  @override
  String get reviewPriceNote =>
      'मूल्य सधैं तपाईंले नै राख्ने हो, AI ले राख्दैन।';

  @override
  String get fieldPrice => 'मूल्य (रू)';

  @override
  String fieldPriceFor(String variant) {
    return '$variant को मूल्य';
  }

  @override
  String get fieldSku => 'SKU (नभए पनि हुन्छ)';

  @override
  String get samePriceToggle => 'सबै विकल्पको एउटै मूल्य';

  @override
  String get validationPriceRequired => 'मूल्य हाल्नुहोस्';

  @override
  String get validationPriceInvalid => 'अंक मात्र, जस्तै: 1250 वा 1250.50';

  @override
  String get validationPriceDecimals => 'बढीमा २ दशमलव (पैसा)';

  @override
  String get validationPriceTooLarge => 'मूल्य धेरै भयो';

  @override
  String get optionAdd => 'विकल्प थप्नुहोस् (जस्तै: साइज)';

  @override
  String get optionName => 'विकल्पको नाम';

  @override
  String get optionValuesHint => 'मानहरू, अल्पविरामले छुट्याएर';

  @override
  String get optionRemove => 'विकल्प हटाउनुहोस्';

  @override
  String get optionValuesRequired =>
      'हरेक विकल्पमा कम्तीमा एउटा मान राख्नुहोस्';

  @override
  String variantsCount(int count) {
    final intl.NumberFormat countNumberFormat = intl
        .NumberFormat.decimalPattern(localeName);
    final String countString = countNumberFormat.format(count);

    return '$countString वटा भेरियन्ट';
  }

  @override
  String get tooManyVariants => '१०० भन्दा बढी जोडी बने। केही मान हटाउनुहोस्।';

  @override
  String get reviewSectionChecklist =>
      'AI ले थाहा पाएन, कृपया पुष्टि गर्नुहोस्';

  @override
  String get reviewSectionWarnings => 'जाँच्नुपर्ने कुरा';

  @override
  String get issueClaimPrice =>
      'लेखाइमा मूल्य उल्लेख छ। मूल्य तपाईंले नै राख्ने हो, कृपया जाँच्नुहोस्।';

  @override
  String get issueClaimDiscount =>
      'तपाईंले नभनेको छुटको कुरा लेखिएको छ। हटाउनुहोस् वा साँचो हो भने मात्र राख्नुहोस्।';

  @override
  String get issueClaimStock =>
      'लेखाइमा स्टकको कुरा छ। स्टक तपाईंको इन्भेन्टरीबाट आउँछ, कृपया जाँच्नुहोस्।';

  @override
  String get issueClaimDelivery =>
      'लेखाइमा डेलिभरीको वाचा छ। साँचो हो कि होइन जाँच्नुहोस्।';

  @override
  String get issueClaimWarranty =>
      'लेखाइमा वारेन्टीको कुरा छ। तपाईं दिनुहुन्छ भने मात्र राख्नुहोस्।';

  @override
  String get issueClaimAuthenticity =>
      'सक्कली/ओरिजिनल भनिएको छ। प्रमाण छ भने मात्र राख्नुहोस्।';

  @override
  String get issueClaimOther =>
      'प्रमाणित गर्न नसकिने कुरा लेखिएको छ। कृपया जाँच्नुहोस्।';

  @override
  String get issueNotProductPhoto =>
      'यी फोटोमा सामान नदेखिन सक्छ। सेभ गर्नुअघि जाँच्नुहोस्।';

  @override
  String get issueTooLong =>
      'केही लेखाइ धेरै लामो भएकाले छोटो पारियो। एकपटक पढ्नुहोस्।';

  @override
  String issueInField(String field) {
    return 'ठाउँ: $field';
  }

  @override
  String get reviewCreate => 'सामान सेभ गर्नुहोस्';

  @override
  String get reviewFixProblems => 'अगाडि बढ्न रातो देखिएका कुरा मिलाउनुहोस्।';

  @override
  String get productTitle => 'सामान';

  @override
  String get productStatusDraft => 'ड्राफ्ट';

  @override
  String get productStatusActive => 'लाइभ';

  @override
  String get productStatusArchived => 'संग्रहित';

  @override
  String get productSaved => 'ड्राफ्टको रूपमा सेभ भयो। तपाईंलाई मात्र देखिन्छ।';

  @override
  String get productGoLive => 'लाइभ गर्नुहोस्';

  @override
  String get productIsLive => 'क्याटलगमा लाइभ छ';

  @override
  String get productConfirmSection => 'AI विवरण पुष्टि गर्नुहोस्';

  @override
  String get productConfirmAll => 'सबै पुष्टि गर्नुहोस्';

  @override
  String get productProblemPrice => 'हरेक भेरियन्टको मूल्य चाहिन्छ।';

  @override
  String get productProblemAttributes => 'तलका AI विवरण पुष्टि गर्नुहोस्।';

  @override
  String get productProblemVariant =>
      'कम्तीमा एउटा सक्रिय भेरियन्ट चाहिन्छ (अहिलेलाई वेब ड्यासबोर्डबाट)।';

  @override
  String get productProblemTitle => 'सामानको नाम राख्नुहोस्।';

  @override
  String get productFix => 'मिलाउनुहोस्';

  @override
  String get productEditPrice => 'मूल्य बदल्नुहोस्';

  @override
  String get productEditTitle => 'नाम बदल्नुहोस्';

  @override
  String get productPrices => 'मूल्य';

  @override
  String get defaultVariant => 'मूल';

  @override
  String get publishSection => 'च्यानलमा पठाउनुहोस्';

  @override
  String get publishNeedsLive => 'च्यानलमा पठाउन पहिले लाइभ गर्नुहोस्।';

  @override
  String get publishNoChannels =>
      'अहिलेसम्म कुनै च्यानल जोडिएको छैन। वेब ड्यासबोर्डबाट Instagram, Facebook वा TikTok जोड्नुहोस्।';

  @override
  String get publishAction => 'पठाउनुहोस्';

  @override
  String get publishSelectOne => 'कम्तीमा एउटा च्यानल छान्नुहोस्';

  @override
  String get channelReconnect => 'फेरि जोड्नुहोस्';

  @override
  String get channelExpiredNote => 'जडान सकियो';

  @override
  String get listingPending => 'पालोमा';

  @override
  String get listingPublishing => 'पठाउँदै…';

  @override
  String get listingPublished => 'पठाइयो';

  @override
  String get listingFailed => 'असफल';

  @override
  String get listingOutOfSync => 'मिलेन';

  @override
  String get listingUnpublished => 'हटाइएको';

  @override
  String listingError(String code) {
    return 'कारण: $code';
  }

  @override
  String reconnectTitle(String channel) {
    return '$channel फेरि जोड्नुहोस्';
  }

  @override
  String get reconnectChannelGeneric => 'च्यानल';

  @override
  String get reconnectBody =>
      'अहिलेलाई ब्राउजरमा वेब ड्यासबोर्ड खोलेर च्यानल जोड्नुहोस्:';

  @override
  String get reconnectCopied => 'लिंक कपी भयो';

  @override
  String get actionCopyLink => 'लिंक कपी गर्नुहोस्';

  @override
  String get postsSection => 'पोस्ट बनाउनुहोस्';

  @override
  String get postsIntro =>
      'AI क्याप्सनबाट हरेक च्यानलका लागि पोस्ट बनाउँछौं। पठाउनुअघि तपाईं हेर्नुहुन्छ।';

  @override
  String get postsCreate => 'ड्राफ्ट बनाउनुहोस्';

  @override
  String get postsNoChannels => 'पोस्ट गर्न मिल्ने च्यानल अझै जोडिएको छैन।';

  @override
  String get postsNoDraft => 'पोस्ट बनाउन यो सामानको AI ड्राफ्ट चाहिन्छ।';

  @override
  String get postsTitle => 'पोस्ट';

  @override
  String get postStatusDraft => 'ड्राफ्ट';

  @override
  String get postStatusPendingApproval => 'स्वीकृतिको पर्खाइमा';

  @override
  String get postStatusApproved => 'स्वीकृत';

  @override
  String postStatusScheduled(String when) {
    return '$when मा तय';
  }

  @override
  String get postStatusPublishing => 'पठाउँदै…';

  @override
  String get postStatusPublished => 'प्रकाशित';

  @override
  String get postStatusFailed => 'असफल';

  @override
  String get postStatusCancelled => 'रद्द';

  @override
  String get fieldCaption => 'क्याप्सन';

  @override
  String get postSaveCaption => 'क्याप्सन सेभ गर्नुहोस्';

  @override
  String get postSubmit => 'पेस गर्नुहोस्';

  @override
  String get postApprove => 'स्वीकृत गर्नुहोस्';

  @override
  String get postPublishNow => 'अहिल्यै पठाउनुहोस्';

  @override
  String get postSchedule => 'समय तोक्नुहोस्';

  @override
  String get postNeedsApprovalNote =>
      'AI ले लेखेको पोस्ट पठाउनुअघि स्वीकृति चाहिन्छ।';

  @override
  String get postNoApprovePermission =>
      'पसल मालिक वा म्यानेजरलाई स्वीकृत गर्न भन्नुहोस्।';

  @override
  String get postCaptionSaved => 'क्याप्सन सेभ भयो';

  @override
  String get postNotFound => 'यो पोस्ट अब उपलब्ध छैन।';

  @override
  String get postsEmpty => 'अहिलेसम्म पोस्ट छैन।';

  @override
  String get draftsTitle => 'ड्राफ्ट';

  @override
  String get draftsNew => 'फोटोबाट नयाँ';

  @override
  String get draftsEmpty =>
      'अहिलेसम्म ड्राफ्ट छैन। सामानका केही फोटोबाट सुरु गर्नुहोस्।';

  @override
  String get draftsIntro =>
      'पोस्ट बनाउन ड्राफ्ट छान्नुहोस् वा नयाँ फोटोबाट सुरु गर्नुहोस्।';

  @override
  String get draftStatusWorking => 'लेख्दैछ…';

  @override
  String get draftStatusReady => 'जाँच्न तयार';

  @override
  String get draftStatusFailed => 'असफल';

  @override
  String get draftStatusApplied => 'सामान बनिसक्यो';

  @override
  String get draftStatusDiscarded => 'हटाइयो';

  @override
  String get draftUntitled => 'नाम नभएको ड्राफ्ट';

  @override
  String get exSubjectDraft => 'AI ड्राफ्ट';

  @override
  String get exSubjectPost => 'पोस्ट';

  @override
  String get exSubjectProduct => 'सामान';

  @override
  String get exActionReconnect => 'फेरि जोड्नुहोस्';

  @override
  String get exActionRetryPublish => 'फेरि पठाउनुहोस्';

  @override
  String get exActionReschedule => 'फेरि समय तोक्नुहोस्';

  @override
  String get exActionReviewPost => 'पोस्ट हेर्नुहोस्';

  @override
  String get exActionReviewDraft => 'ड्राफ्ट हेर्नुहोस्';

  @override
  String get exActionRetryDraft => 'ड्राफ्ट फेरि चलाउनुहोस्';

  @override
  String get exActionConfirmAttributes => 'विवरण पुष्टि गर्नुहोस्';

  @override
  String get exActionDismiss => 'लुकाउनुहोस्';

  @override
  String get homeSectionCatalog => 'क्याटलग';

  @override
  String get settingsTheme => 'थिम';

  @override
  String get themeLight => 'उज्यालो';

  @override
  String get themeDark => 'अँध्यारो';

  @override
  String get themeSystem => 'फोनकै थिम';

  @override
  String get loginForgotPassword => 'पासवर्ड बिर्सनुभयो?';

  @override
  String get forgotTitle => 'पासवर्ड रिसेट गर्नुहोस्';

  @override
  String get forgotSubtitle =>
      'आफ्नो खाताको इमेल लेख्नुहोस्, नयाँ पासवर्ड राख्ने लिंक पठाउँछौं।';

  @override
  String get forgotAction => 'रिसेट लिंक पठाउनुहोस्';

  @override
  String get forgotSentTitle => 'इमेल हेर्नुहोस्';

  @override
  String get forgotSentBody =>
      'त्यो इमेलको खाता छ भने रिसेट लिंक आउँदैछ। यही फोन वा कम्प्युटरमा खोल्नुहोस्। यो एक पटक मात्र र ३० मिनेटसम्म चल्छ।';

  @override
  String get forgotBack => 'साइन इनमा फर्कनुहोस्';

  @override
  String get exUsageLimit => 'प्लान सीमा';

  @override
  String exSubjectUsage(int used, int limit) {
    return 'यो महिना $limit मध्ये $used प्रयोग भयो (वेबमा प्लान हेर्नुहोस्)';
  }

  @override
  String get navOrders => 'अर्डर';

  @override
  String get navInbox => 'इनबक्स';

  @override
  String get ordersTitle => 'अर्डरहरू';

  @override
  String get ordersFilterNeedsAction => 'गर्न बाँकी';

  @override
  String get ordersFilterNeedsReview => 'जाँच्नुपर्ने';

  @override
  String get ordersFilterAll => 'सबै';

  @override
  String get ordersEmpty => 'यहाँ कुनै अर्डर छैन';

  @override
  String get ordersEmptyBody =>
      'च्याट, च्यानल र तपाईंले थपेका अर्डर यहाँ देखिन्छन्।';

  @override
  String orderNumber(int number) {
    return 'अर्डर #$number';
  }

  @override
  String get orderItems => 'सामान';

  @override
  String get orderTotals => 'जम्मा';

  @override
  String get orderSubtotal => 'उप-जम्मा';

  @override
  String get orderDelivery => 'डेलिभरी';

  @override
  String get orderDiscount => 'छुट';

  @override
  String get orderTotal => 'जम्मा';

  @override
  String get orderShipTo => 'डेलिभरी ठेगाना';

  @override
  String get orderPayment => 'भुक्तानी';

  @override
  String get orderTimeline => 'समयरेखा';

  @override
  String get orderNotes => 'टिप्पणी';

  @override
  String get orderCancel => 'अर्डर रद्द गर्नुहोस्';

  @override
  String get orderCancelTitle => 'यो अर्डर रद्द गर्ने?';

  @override
  String get orderCancelBody =>
      'राखिएको स्टक फेरि बिक्रीमा जान्छ। ग्राहकलाई आफैं सन्देश जाँदैन।';

  @override
  String get orderCancelReason => 'कारण';

  @override
  String get orderCancelReasonHint => 'जस्तै: ग्राहकले मन बदले';

  @override
  String get orderCancelConfirm => 'रद्द गर्नुहोस्';

  @override
  String get orderCancelKeep => 'अर्डर राख्नुहोस्';

  @override
  String get orderUpdated => 'अर्डर अपडेट भयो';

  @override
  String orderCancelledQty(int count) {
    return '$count रद्द';
  }

  @override
  String get orderUnmatchedItem => 'तपाईंको क्याटलगमा भेटिएन';

  @override
  String get orderViewChat => 'च्याट खोल्नुहोस्';

  @override
  String get orderReviewPaymentMismatch => 'तिरेको रकम जम्मासँग मिलेन';

  @override
  String get orderReviewPaidAfterCancel => 'रद्द भएपछि भुक्तानी आयो';

  @override
  String get orderReviewStockShort => 'यो अर्डरका लागि स्टक पुगेन';

  @override
  String get orderReviewUnmatched => 'केही सामान क्याटलगमा छैनन्';

  @override
  String get orderReviewAddress => 'ठेगाना अधुरो छ';

  @override
  String get orderStatusDraft => 'ड्राफ्ट';

  @override
  String get orderStatusPendingConfirmation => 'पक्का हुन बाँकी';

  @override
  String get orderStatusConfirmed => 'पक्का';

  @override
  String get orderStatusPaymentPending => 'भुक्तानी बाँकी';

  @override
  String get orderStatusCodPending => 'प्याक गर्न बाँकी (COD)';

  @override
  String get orderStatusReadyToShip => 'पठाउन तयार';

  @override
  String get orderStatusShipped => 'पठाइयो';

  @override
  String get orderStatusDelivered => 'डेलिभर भयो';

  @override
  String get orderStatusCompleted => 'सम्पन्न';

  @override
  String get orderStatusCancelled => 'रद्द';

  @override
  String get orderStatusDeliveryFailed => 'डेलिभरी असफल';

  @override
  String get orderStatusReturned => 'फिर्ता';

  @override
  String get orderActionConfirm => 'अर्डर पक्का गर्नुहोस्';

  @override
  String get orderActionReadyToShip => 'प्याक भयो';

  @override
  String get orderActionShipped => 'पठाइयो';

  @override
  String get orderActionDelivered => 'डेलिभर भयो';

  @override
  String get orderActionCompleted => 'सम्पन्न गर्नुहोस्';

  @override
  String get orderActionDeliveryFailed => 'डेलिभरी असफल';

  @override
  String get orderActionReturned => 'फिर्ता आयो';

  @override
  String get paymentCod => 'डेलिभरीमा नगद';

  @override
  String get paymentPrepaid => 'अग्रिम भुक्तानी';

  @override
  String get payStatusUnpaid => 'नतिरेको';

  @override
  String get payStatusPending => 'भुक्तानी कुर्दै';

  @override
  String get payStatusPaid => 'तिरिसकेको';

  @override
  String get payStatusFailed => 'भुक्तानी असफल';

  @override
  String get payStatusRefunded => 'फिर्ता गरियो';

  @override
  String get payStatusCodPending => 'डेलिभरीमा उठाउने';

  @override
  String get payStatusCodCollected => 'कुरियरले उठायो';

  @override
  String get timelineCreated => 'अर्डर बन्यो';

  @override
  String timelineImported(String channel) {
    return '$channel बाट आयो';
  }

  @override
  String timelineStatus(String status) {
    return 'अब: $status';
  }

  @override
  String get timelineLinesCancelled => 'केही सामान रद्द';

  @override
  String timelineNote(String note) {
    return 'टिप्पणी: $note';
  }

  @override
  String get timelinePayment => 'भुक्तानी आयो';

  @override
  String get timelinePaymentFailed => 'भुक्तानी असफल';

  @override
  String get timelinePaymentMismatch => 'तिरेको रकम मिलेन';

  @override
  String get timelineOther => 'अपडेट';

  @override
  String get timelineByAi => 'AI बिक्री सहायक';

  @override
  String get timelineAutomatic => 'स्वचालित';

  @override
  String get inboxTitle => 'इनबक्स';

  @override
  String get inboxEmpty => 'खुला च्याट छैन';

  @override
  String get inboxEmptyBody => 'जोडिएका च्यानलबाट ग्राहकका सन्देश यहाँ आउँछन्।';

  @override
  String get inboxNeedsYou => 'तपाईं चाहियो';

  @override
  String inboxYou(String text) {
    return 'तपाईं: $text';
  }

  @override
  String get inboxCustomer => 'ग्राहक';

  @override
  String get threadReplyHint => 'जवाफ लेख्नुहोस्';

  @override
  String get threadSend => 'पठाउनुहोस्';

  @override
  String get threadSuggestion => 'AI सुझाव, अझै पठाइएको छैन';

  @override
  String get threadSuggestionSend => 'पठाउनुहोस्';

  @override
  String get threadSuggestionEdit => 'सम्पादन';

  @override
  String get threadSuggestionDiscard => 'हटाउनुहोस्';

  @override
  String get threadEditTitle => 'पठाउनुअघि सम्पादन';

  @override
  String get threadFailed => 'पठाइएन';

  @override
  String get threadRetry => 'फेरि प्रयास';

  @override
  String get threadSending => 'पठाउँदै…';

  @override
  String get threadByAi => 'AI';

  @override
  String get threadHandBack => 'AI लाई फिर्ता दिनुहोस्';

  @override
  String get threadHandedBack => 'नयाँ सन्देशको जवाफ फेरि AI ले दिनेछ।';

  @override
  String get threadHumanBanner =>
      'यो च्याट तपाईं हेर्दै हुनुहुन्छ। AI रोकिएको छ।';

  @override
  String get threadEscalatedBanner => 'AI ले यो च्याट तपाईंलाई दियो।';

  @override
  String draftCollecting(String field) {
    return 'अर्डर लिँदै: $field कुर्दै';
  }

  @override
  String get draftAwaitingConfirmation =>
      'अर्डर विवरण पठाइयो। ग्राहकको \'हो\' कुर्दै।';

  @override
  String get draftConfirmed => 'यो च्याटबाट अर्डर बन्यो';

  @override
  String get stockSection => 'स्टक';

  @override
  String stockAvailable(int count) {
    return '$count उपलब्ध';
  }

  @override
  String stockDetail(int onHand, int reserved) {
    return '$onHand र्‍याकमा · $reserved राखिएको';
  }

  @override
  String get stockUntracked => 'अझै ट्र्याक गरिएको छैन';

  @override
  String get stockLow => 'कम';

  @override
  String get stockReceive => 'स्टक थप्नुहोस्';

  @override
  String get stockQuantity => 'आएको संख्या';

  @override
  String get stockReceived => 'स्टक अपडेट भयो';

  @override
  String get stockSave => 'थप्नुहोस्';

  @override
  String get exActionReply => 'जवाफ दिनुहोस्';

  @override
  String get exActionCheckPayment => 'भुक्तानी जाँच्नुहोस्';

  @override
  String get exActionFixStock => 'स्टक मिलाउनुहोस्';

  @override
  String get exActionReviewOrder => 'अर्डर हेर्नुहोस्';

  @override
  String get exSubjectConversation => 'ग्राहकको च्याट';

  @override
  String exSubjectOrder(int number) {
    return 'अर्डर #$number';
  }

  @override
  String get commonCancel => 'रद्द';

  @override
  String get draftFieldProduct => 'सामान';

  @override
  String get draftFieldVariant => 'साइज/रङ';

  @override
  String get draftFieldQuantity => 'संख्या';

  @override
  String get draftFieldName => 'नाम';

  @override
  String get draftFieldPhone => 'फोन नम्बर';

  @override
  String get draftFieldDistrict => 'जिल्ला';

  @override
  String get draftFieldMunicipality => 'नगरपालिका';

  @override
  String get draftFieldWard => 'वडा';

  @override
  String get draftFieldArea => 'टोल';

  @override
  String get draftFieldPayment => 'भुक्तानी विधि';

  @override
  String get deliveryTitle => 'डेलिभरी';

  @override
  String get deliveryChooseCourier => 'कसरी पठाउने छान्नुहोस्';

  @override
  String get deliveryWhyDefault => 'सिफारिस: तपाईंको मुख्य कुरियर';

  @override
  String get deliveryWhyCheapest =>
      'सिफारिस: यो पार्सलका लागि सबैभन्दा सस्तो विकल्प';

  @override
  String get deliveryWhyOnly => 'यो पार्सल लैजान सक्ने एउटै विकल्प';

  @override
  String get deliveryRecommended => 'सिफारिस';

  @override
  String get deliveryOwnRider =>
      'तपाईं आफैं पठाउनुहुन्छ र अवस्था अद्यावधिक गर्नुहुन्छ';

  @override
  String deliveryEta(int min, int max) {
    return '$min–$max दिन';
  }

  @override
  String get deliveryNoCouriers =>
      'अहिलेसम्म कुरियर जोडिएको छैन। वेबको सेटिङमा थप्नुहोस्।';

  @override
  String deliveryCollectAmount(String amount) {
    return 'कुरियरले ढोकामा $amount उठाउँछ';
  }

  @override
  String get deliveryTrackingOptional => 'ट्र्याकिङ नम्बर (ऐच्छिक)';

  @override
  String get deliveryCourierNameOptional => 'कुरियर वा राइडरको नाम (ऐच्छिक)';

  @override
  String get deliveryBook => 'कुरियर बुक गर्नुहोस्';

  @override
  String get deliveryBooked => 'कुरियर बुक भयो';

  @override
  String deliveryTracking(String number) {
    return 'ट्र्याकिङ $number';
  }

  @override
  String get deliveryCopy => 'ट्र्याकिङ नम्बर कपी गर्नुहोस्';

  @override
  String get deliveryCopied => 'ट्र्याकिङ नम्बर कपी भयो';

  @override
  String deliveryCod(String amount) {
    return 'उठाउने नगद: $amount';
  }

  @override
  String get deliveryNothingToCollect => 'भुक्तानी भइसक्यो: उठाउनु पर्दैन';

  @override
  String get deliveryHistory => 'पार्सलको इतिहास';

  @override
  String get deliveryLateUpdate => 'कुरियरको ढिलो जानकारी (लागू गरिएन)';

  @override
  String deliveryAttempt(int n, String reason) {
    return 'प्रयास $n: $reason';
  }

  @override
  String deliveryCustomerReply(String text) {
    return 'ग्राहकको जवाफ: “$text”';
  }

  @override
  String get deliveryUpdated => 'डेलिभरी अद्यावधिक भयो';

  @override
  String get deliveryActionPickup => 'पिकअप माग्नुहोस्';

  @override
  String get deliveryActionCancel => 'बुकिङ रद्द गर्नुहोस्';

  @override
  String get deliveryActionReattempt => 'फेरि डेलिभर गर्न कुरियरलाई भन्नुहोस्';

  @override
  String get deliveryActionReturn => 'पसलमा फिर्ता ल्याउनुहोस्';

  @override
  String get deliveryActionReceivedBack =>
      'पार्सल फिर्ता आयो: स्टकमा थप्नुहोस्';

  @override
  String get deliveryActionUpdateStatus => 'अवस्था अद्यावधिक गर्नुहोस्';

  @override
  String get deliveryActionRefresh => 'कुरियरसँग नयाँ जानकारी हेर्नुहोस्';

  @override
  String get deliveryCancelTitle => 'यो बुकिङ रद्द गर्ने?';

  @override
  String get deliveryCancelBody =>
      'कुरियरले यो पार्सल लैजाँदैन। फेरि बुक गर्न सकिन्छ।';

  @override
  String get deliveryKeep => 'राख्नुहोस्';

  @override
  String get deliveryConfirm => 'पक्का गर्नुहोस्';

  @override
  String get deliveryReattemptTitle => 'फेरि डेलिभर गर्ने';

  @override
  String get deliveryReattemptNote => 'कुरियरका लागि टिपोट (समय, चिनारी)';

  @override
  String get deliverySend => 'पठाउनुहोस्';

  @override
  String get deliveryReturnTitle => 'पार्सल पसलमा फिर्ता ल्याउने?';

  @override
  String get deliveryReturnBody => 'कुरियरले फिर्ता ल्याउँछ र नगद उठ्दैन।';

  @override
  String get deliveryStatusTitle => 'पार्सललाई के भयो?';

  @override
  String get deliveryFailureReason => 'डेलिभरी किन भएन?';

  @override
  String get deliveryReasonRequired => 'अगाडि बढ्न कारण छान्नुहोस्';

  @override
  String get deliveryNote => 'टिपोट (ऐच्छिक)';

  @override
  String get deliverySave => 'सेभ गर्नुहोस्';

  @override
  String get shipStatusBooked => 'बुक भयो';

  @override
  String get shipStatusPickupRequested => 'पिकअप मागियो';

  @override
  String get shipStatusPickedUp => 'कुरियरले लग्यो';

  @override
  String get shipStatusInTransit => 'बाटोमा';

  @override
  String get shipStatusOutForDelivery => 'डेलिभरीमा निस्केको';

  @override
  String get shipStatusDelivered => 'डेलिभर भयो';

  @override
  String get shipStatusDeliveryFailed => 'डेलिभरी भएन';

  @override
  String get shipStatusReattemptRequested => 'फेरि प्रयास हुँदै';

  @override
  String get shipStatusReturning => 'पसलमा फर्कंदै';

  @override
  String get shipStatusReturnedToOrigin => 'पसलमा फिर्ता आयो';

  @override
  String get shipStatusCancelled => 'रद्द';

  @override
  String get shipStatusLost => 'कुरियरबाट हरायो';

  @override
  String get failReasonCustomerUnreachable => 'ग्राहकको फोनमा सम्पर्क भएन';

  @override
  String get failReasonCustomerUnavailable => 'बुझ्ने कोही थिएन';

  @override
  String get failReasonCustomerRefused => 'ग्राहकले पार्सल लिएनन्';

  @override
  String get failReasonAddressIncorrect => 'राइडरले ठेगाना भेटेनन्';

  @override
  String get failReasonCodNotReady => 'नगद तयार थिएन';

  @override
  String get failReasonRescheduled => 'ग्राहकले अर्को समय मागे';

  @override
  String get failReasonOther => 'अन्य समस्या';

  @override
  String get recoveryOpen => 'ग्राहकलाई फोन गर्नुहोस्';

  @override
  String get recoveryAwaitingCustomer => 'ग्राहकलाई सन्देश पठाइयो, जवाफ कुर्दै';

  @override
  String get recoveryCustomerReplied =>
      'ग्राहकले जवाफ दिए: कुरियरलाई फेरि पठाउन भन्नुहोस्';

  @override
  String get recoveryReattemptRequested => 'कुरियरलाई फेरि प्रयास गर्न भनियो';

  @override
  String get recoveryReturning => 'तपाईंको पसलमा फर्कंदै';

  @override
  String get recoveryResolved => 'समाधान भयो';

  @override
  String get recoveryEscalated => 'जवाफ आएन: ग्राहकलाई फोन गर्नुहोस्';

  @override
  String get codTitle => 'डेलिभरीमा नगद';

  @override
  String get codWithCouriers => 'कुरियरसँग';

  @override
  String codWithCouriersBody(int count) {
    return 'डेलिभर भएका $count पार्सलको नगद आउन बाँकी';
  }

  @override
  String codOverTwoWeeks(String amount) {
    return '$amount दुई हप्ताभन्दा बढी देखि बाँकी';
  }

  @override
  String codNeedsReview(int count) {
    return '$count कुरियर विवरण जाँच्नुपर्ने';
  }

  @override
  String get codAwaitingTitle => 'अझै कुरियरसँग रहेको नगद';

  @override
  String get codAwaitingEmpty =>
      'कुनै नगद बाँकी छैन: कुरियरले सबै डेलिभर भएका पार्सलको भुक्तानी गरे।';

  @override
  String codDaysWaiting(int days) {
    return '$days दिनदेखि बाँकी';
  }

  @override
  String codOrderCourier(int number, String courier) {
    return 'अर्डर #$number · $courier';
  }

  @override
  String get codSettlementsTitle => 'कुरियर विवरण';

  @override
  String get codSettlementsEmpty => 'अहिलेसम्म कुरियर विवरण छैन।';

  @override
  String get codStatusNeedsReview => 'जाँच्नुपर्ने';

  @override
  String get codStatusReconciled => 'मिल्यो: पैसा आएपछि पक्का गर्नुहोस्';

  @override
  String get codStatusConfirmed => 'प्राप्त भयो';

  @override
  String codIssues(int count) {
    return '$count लाइन मिलेनन्। वेबमा जाँच्नुहोस्।';
  }

  @override
  String get codConfirmReceived => 'पैसा आयो भनी पक्का गर्नुहोस्';

  @override
  String get codConfirmed => 'प्राप्त भनी जनाइयो';

  @override
  String get returnsTitle => 'फिर्ता';

  @override
  String get returnsStart => 'फिर्ता सुरु गर्नुहोस्';

  @override
  String get returnsNone => 'यो अर्डरको फिर्ता छैन।';

  @override
  String get returnStatusRequested => 'निर्णय बाँकी';

  @override
  String get returnStatusApproved => 'स्वीकृत';

  @override
  String get returnStatusRejected => 'अस्वीकृत';

  @override
  String get returnStatusInTransit => 'फिर्ता आउँदै';

  @override
  String get returnStatusReceived => 'आइपुग्यो';

  @override
  String get returnStatusInspected => 'जाँचियो';

  @override
  String get returnStatusRefunded => 'रकम फिर्ता भयो';

  @override
  String get returnStatusExchanged => 'साटियो';

  @override
  String get returnStatusClosed => 'बन्द';

  @override
  String get returnStatusCancelled => 'रद्द';

  @override
  String get returnResolutionRefund => 'रकम फिर्ता';

  @override
  String get returnResolutionExchange => 'साट्ने';

  @override
  String returnRefundDue(String amount) {
    return 'फिर्ता गर्नुपर्ने: $amount';
  }

  @override
  String get returnReasonSizeSmall => 'सानो भयो';

  @override
  String get returnReasonSizeLarge => 'ठूलो भयो';

  @override
  String get returnReasonColourDifferent => 'रङ फरक देखियो';

  @override
  String get returnReasonQualityDefect => 'गुणस्तरमा खोट';

  @override
  String get returnReasonDamagedInTransit => 'ढुवानीमा बिग्रियो';

  @override
  String get returnReasonNotAsDescribed => 'विवरण अनुसार होइन';

  @override
  String get returnReasonChangedMind => 'मन परिवर्तन भयो';

  @override
  String get returnReasonLateDelivery => 'ढिलो आइपुग्यो';

  @override
  String get returnReasonWrongItem => 'गलत सामान पठाइयो';

  @override
  String get returnReasonOther => 'अन्य';

  @override
  String get returnConditionResellable => 'फेरि बेच्न मिल्ने';

  @override
  String get returnConditionDamaged => 'बिग्रिएको';

  @override
  String get returnConditionMissing => 'हराएको';

  @override
  String get returnConditionUsed => 'प्रयोग गरिएको';

  @override
  String returnLineItem(int qty, String title) {
    return '$qty × $title';
  }

  @override
  String returnLineCondition(String condition) {
    return 'जाँच: $condition';
  }

  @override
  String returnLineExchange(String title) {
    return '$title सँग साट्ने';
  }

  @override
  String returnSheetTitle(int number) {
    return 'अर्डर #$number बाट फिर्ता';
  }

  @override
  String get returnPickItems => 'कुन सामान फिर्ता आउँदैछ?';

  @override
  String get returnQty => 'संख्या';

  @override
  String get returnReason => 'कारण';

  @override
  String get returnResolution => 'ग्राहक के चाहन्छन्?';

  @override
  String get returnExchangeFor => 'सट्टामा';

  @override
  String get returnNoExchangeOption => 'उही मूल्यमा अर्को विकल्प छैन';

  @override
  String returnOutOfStock(String title) {
    return '$title (स्टक छैन)';
  }

  @override
  String get returnCheck => 'नीति अनुसार जाँच्नुहोस्';

  @override
  String get returnSubmit => 'फिर्ता बनाउनुहोस्';

  @override
  String get returnCreated => 'फिर्ता बन्यो';

  @override
  String get returnNothingLeft =>
      'यो अर्डरका सबै सामान पहिल्यै फिर्ता हुँदैछन्।';

  @override
  String get returnPickReason => 'हरेक सामानको कारण छान्नुहोस्';

  @override
  String get returnPickExchange => 'हरेक सामान केसँग साट्ने छान्नुहोस्';

  @override
  String get returnCheckOrderDelivered => 'अर्डर अझै डेलिभर भएको छैन';

  @override
  String returnCheckWindow(int days) {
    return '$days दिने फिर्ता अवधि नाघ्यो';
  }

  @override
  String get returnCheckWindowPlain => 'फिर्ता अवधि नाघ्यो';

  @override
  String get returnCheckFinalSale => 'फिर्ता नहुने (फाइनल सेल) सामान';

  @override
  String get returnCheckEvidence => 'यो कारणका लागि फोटो चाहिन्छ';

  @override
  String get returnCheckQuantity => 'फिर्ता गर्न मिल्ने भन्दा बढी';

  @override
  String get returnCheckResolution => 'तपाईंको फिर्ता नीतिले यो दिँदैन';

  @override
  String get returnCheckExchangeProduct =>
      'साट्दा उही सामान, उही मूल्यको हुनुपर्छ';

  @override
  String get returnCheckExchangeStock => 'सट्टाको सामान स्टकमा छैन';

  @override
  String get returnCheckGeneric => 'नीति अनुसार छैन';

  @override
  String get returnWarningsTitle =>
      'नीतिभन्दा बाहिर। बनाउन सकिन्छ, स्वीकृत गर्दा कारण चाहिन्छ।';

  @override
  String get returnBlockedTitle => 'यो फिर्ता बनाउन मिल्दैन';

  @override
  String get returnAllOk => 'फिर्ता नीतिभित्र';

  @override
  String returnDetailTitle(String number) {
    return 'फिर्ता $number';
  }

  @override
  String get returnChecksTitle => 'नीति जाँच';

  @override
  String get returnSignalsTitle => 'थाहा पाउनुपर्ने';

  @override
  String returnSignalFrequent(int count, int days) {
    return 'पछिल्लो $days दिनमा $count फिर्ता';
  }

  @override
  String returnSignalRate(int returned, int orders, int days) {
    return '$days दिनमा $orders मध्ये $returned अर्डर फिर्ता';
  }

  @override
  String get returnSignalValue => 'पसलको सामान्य अर्डरभन्दा बढी मूल्य';

  @override
  String get returnSignalGeneric => 'यो पसलको लागि असामान्य';

  @override
  String get returnItemsTitle => 'सामान';

  @override
  String get returnPickupTitle => 'सामान लिने';

  @override
  String get returnRefundsTitle => 'रकम फिर्ता';

  @override
  String returnOverrideNote(String reason) {
    return 'नीतिबाहिर स्वीकृत: $reason';
  }

  @override
  String returnRejectedNote(String reason) {
    return 'अस्वीकृत: $reason';
  }

  @override
  String get refundPending => 'व्यवस्थापकको स्वीकृति कुर्दै';

  @override
  String get refundStatusSucceeded => 'पठाइयो';

  @override
  String get refundStatusFailed => 'असफल';

  @override
  String get refundStatusRejected => 'स्वीकृत भएन';

  @override
  String get refundStatusProcessing => 'प्रक्रियामा';

  @override
  String refundLine(String amount, String method) {
    return '$amount · $method';
  }

  @override
  String get refundMethodOriginal => 'मूल भुक्तानीमै फिर्ता';

  @override
  String get refundMethodEsewa => 'eSewa';

  @override
  String get refundMethodKhalti => 'Khalti';

  @override
  String get refundMethodFonepay => 'Fonepay';

  @override
  String get refundMethodBank => 'बैंक ट्रान्सफर';

  @override
  String get refundMethodCash => 'नगद';

  @override
  String get refundMethodOther => 'अन्य';

  @override
  String get returnActionApprove => 'स्वीकृत गर्नुहोस्';

  @override
  String get returnActionReject => 'अस्वीकार गर्नुहोस्';

  @override
  String get returnActionCancel => 'फिर्ता रद्द गर्नुहोस्';

  @override
  String get returnActionReceived => 'आइपुग्यो भनी चिनो लगाउनुहोस्';

  @override
  String get returnActionInspect => 'सामान जाँच्नुहोस्';

  @override
  String get returnActionRefund => 'रकम फिर्ता गर्नुहोस्';

  @override
  String get returnPickupOnWeb => 'सामान लिने बुकिङ वेबबाट गर्नुहोस्।';

  @override
  String get returnApproveTitle => 'यो फिर्ता स्वीकृत गर्ने?';

  @override
  String get returnOverrideHint =>
      'यो फिर्ता नीतिबाहिर छ। किन स्वीकृत गर्दै हुनुहुन्छ लेख्नुहोस्।';

  @override
  String get returnReasonLabel => 'कारण';

  @override
  String get returnReasonRequired => 'कारण चाहिन्छ';

  @override
  String get returnRejectTitle => 'यो फिर्ता अस्वीकार गर्ने?';

  @override
  String get returnRejectLabel => 'कारण (ग्राहकले देख्छन्)';

  @override
  String get returnCancelTitle => 'यो फिर्ता रद्द गर्ने?';

  @override
  String get returnCancelBody =>
      'यसका लागि राखिएको सट्टाको सामान फेरि बिक्रीमा जान्छ।';

  @override
  String get returnReceivedTitle => 'सामान आइपुग्यो?';

  @override
  String get returnReceivedBody => 'अब जाँचेर फिर्ता रकम तय गर्नुहोस्।';

  @override
  String get returnInspectTitle => 'फिर्ता आएका सामान जाँच्नुहोस्';

  @override
  String get returnRestock => 'फेरि बिक्रीमा राख्ने';

  @override
  String get returnRestockOnlyResellable =>
      'फेरि बेच्न मिल्ने सामान मात्र बिक्रीमा फर्किन्छ';

  @override
  String get returnInspectSave => 'जाँच सेभ गर्नुहोस्';

  @override
  String get returnPickCondition => 'हरेक सामानको अवस्था छान्नुहोस्';

  @override
  String get refundTitle => 'ग्राहकलाई रकम फिर्ता';

  @override
  String get refundAmount => 'रकम (रु)';

  @override
  String refundMax(String amount) {
    return 'बढीमा $amount';
  }

  @override
  String get refundTooMuch => 'ग्राहकले तिरेको भन्दा बढी';

  @override
  String get refundMethod => 'कसरी';

  @override
  String get refundReference => 'सन्दर्भ (ऐच्छिक)';

  @override
  String get refundSend => 'फिर्ता गर्नुहोस्';

  @override
  String get returnDone => 'फिर्ता अपडेट भयो';

  @override
  String get returnsTabToDecide => 'निर्णय बाँकी';

  @override
  String get returnsTabInProgress => 'प्रक्रियामा';

  @override
  String get returnsTabToRefund => 'रकम फिर्ता गर्न बाँकी';

  @override
  String get returnsTabDone => 'सकियो';

  @override
  String returnsTabCount(String label, int count) {
    return '$label ($count)';
  }

  @override
  String get returnsEmpty => 'यहाँ केही छैन।';

  @override
  String returnsListItem(String number, int order) {
    return '$number · अर्डर #$order';
  }

  @override
  String returnsHomeCard(int count) {
    return '$count फिर्तामा निर्णय बाँकी';
  }

  @override
  String get returnsHomeCardBody =>
      'ग्राहकका फिर्ता स्वीकृत वा अस्वीकार गर्नुहोस्।';

  @override
  String get ccStateRunning => 'तपाईंको पसल चलिरहेको छ।';

  @override
  String get ccStateWaiting => 'केही कुरा तपाईंलाई कुरिरहेका छन्।';

  @override
  String get ccStateAttention => 'अहिले तपाईं चाहिने कुरा छ।';

  @override
  String get ccModeAssisted => 'सहायक मोड';

  @override
  String get ccModeSmart => 'स्मार्ट मोड';

  @override
  String get ccModeAutopilot => 'अटोपाइलट मोड';

  @override
  String get ccPeriod => 'पछिल्लो ७ दिन';

  @override
  String get ccOrders => 'अर्डर';

  @override
  String get ccRevenue => 'बिक्री';

  @override
  String get ccAiMessages => 'AI जवाफ';

  @override
  String get ccDelivered => 'डेलिभर भयो';

  @override
  String get ccInTransit => 'बाटोमा';

  @override
  String get ccReturns => 'फिर्ता';

  @override
  String get ccFeedLink => 'स्वचालित रूपमा भएका काम हेर्नुहोस्';

  @override
  String get ccWorkflowsLink => 'वर्कफ्लो';

  @override
  String get approvalsTitle => 'स्वीकृति कुर्दै';

  @override
  String get approvalsEmpty => 'स्वीकृति कुरिरहेको केही छैन।';

  @override
  String get approvalsApprove => 'स्वीकृत गर्नुहोस्';

  @override
  String get approvalsReject => 'अस्वीकार गर्नुहोस्';

  @override
  String get approvalsRejectTitle => 'यो चरण अस्वीकार गर्ने?';

  @override
  String get approvalsNote => 'टिपोट (ऐच्छिक)';

  @override
  String get approvalsCancel => 'राख्नुहोस्';

  @override
  String get approvalsManagersOnly =>
      'म्यानेजरले मात्र स्वचालन स्वीकृत गर्न सक्छन्।';

  @override
  String get approvalsDone => 'भयो।';

  @override
  String get autoActionNotifySeller => 'तपाईंलाई खबर गर्ने';

  @override
  String get autoActionAddOrderNote => 'अर्डरमा टिपोट थप्ने';

  @override
  String get autoActionSendCustomerMessage => 'ग्राहकलाई सन्देश पठाउने';

  @override
  String get autoActionSendReviewRequest => 'समीक्षा माग्ने';

  @override
  String get autoActionBookCourier => 'कुरियर बुक गर्ने';

  @override
  String get autoActionRequestPickup => 'पिकअप माग्ने';

  @override
  String get autoActionRequestReattempt => 'कुरियरलाई फेरि प्रयास गर्न भन्ने';

  @override
  String get autoActionApproveReturn => 'फिर्ता स्वीकृत गर्ने';

  @override
  String get autoActionSendAiReply => 'AI जवाफ पठाउने';

  @override
  String get autoActionIssueRefund => 'ग्राहकलाई रकम फिर्ता';

  @override
  String get autoActionContinue => 'वर्कफ्लो अगाडि बढाउने';

  @override
  String get autoActionOther => 'स्वचालित चरण';

  @override
  String get ruleAssisted => 'तपाईंको पसल सहायक मोडमा छ';

  @override
  String get ruleR2Off => 'यस्तो काम खोलिएको छैन';

  @override
  String get ruleAboveLimit => 'तपाईंको सीमाभन्दा माथि';

  @override
  String get ruleNotSure => 'पर्याप्त निश्चित छैन';

  @override
  String get ruleHighRisk => 'सधैं मान्छे चाहिन्छ';

  @override
  String get ruleBlocked => 'अहिले सम्भव छैन';

  @override
  String get ruleApprovalStep => 'वर्कफ्लोले तपाईंको अनुमति माग्छ';

  @override
  String get ruleRanSmart => 'स्वचालित रूपमा भयो (स्मार्ट मोड)';

  @override
  String get ruleRanAutopilot => 'स्वचालित रूपमा भयो (अटोपाइलट मोड)';

  @override
  String get ruleRanEnabled => 'स्वचालित रूपमा भयो: तपाईंले यो खोल्नुभएको छ';

  @override
  String get ruleNotice => 'सूचना मात्र';

  @override
  String get feedTitle => 'स्वचालित रूपमा भएका काम';

  @override
  String get feedEmpty => 'पछिल्लो ७ दिनमा केही स्वचालित भएन।';

  @override
  String get workflowsTitle => 'वर्कफ्लो';

  @override
  String get workflowsEmpty => 'अहिलेसम्म वर्कफ्लो छैन। वेबमा बनाउनुहोस्।';

  @override
  String get wfStatusDraft => 'बन्द';

  @override
  String get wfStatusActive => 'चालु';

  @override
  String get wfStatusPaused => 'रोकिएको';

  @override
  String get wfBroke => 'पटक-पटक असफल भएपछि रोकियो';

  @override
  String get wfTurnOn => 'चालु गर्नुहोस्';

  @override
  String get wfTurnOff => 'रोक्नुहोस्';

  @override
  String get wfEditOnWeb => 'वर्कफ्लो वेबमा सम्पादन गर्नुहोस्।';

  @override
  String get wfManagersOnly =>
      'म्यानेजरले मात्र वर्कफ्लो चालु वा बन्द गर्न सक्छन्।';

  @override
  String ccDoneAuto(int count) {
    return '$count स्वचालित रूपमा';
  }

  @override
  String ccDoneTeam(int count) {
    return '$count तपाईंको टोलीले';
  }

  @override
  String ccShare(String percent) {
    return '$percent स्वचालित';
  }

  @override
  String ccNeedsAttention(int count) {
    String _temp0 = intl.Intl.pluralLogic(
      count,
      locale: localeName,
      other: '$count कुरामा तपाईं चाहिन्छ',
      one: '१ कुरामा तपाईं चाहिन्छ',
      zero: 'तपाईं चाहिने केही छैन',
    );
    return '$_temp0';
  }

  @override
  String approvalsOrder(int number) {
    return 'अर्डर #$number';
  }

  @override
  String approvalsWhy(String reason) {
    return 'कुर्दै: $reason';
  }

  @override
  String wfRuns(int done, int waiting, int failed) {
    return '$done सकियो · $waiting चलिरहेको · $failed असफल';
  }

  @override
  String get apsTitle => 'अटोपाइलट स्कोर';

  @override
  String get apsNotEnough => 'अझै पर्याप्त गतिविधि छैन';

  @override
  String get apsCapNotEnough => 'पर्याप्त गतिविधि छैन';

  @override
  String apsWindow(int days) {
    return 'पछिल्लो $days दिन';
  }

  @override
  String apsCounts(int a, int f, int m) {
    return 'स्वचालित $a · असफल $f · टोलीले $m';
  }

  @override
  String apsExcluded(int count, String reason) {
    return '$count गनिएन: $reason';
  }

  @override
  String get apsExclAboveThreshold => 'तपाईंको नियमले स्वीकृति चाहियो';

  @override
  String get apsExclNotInPlan => 'तपाईंको योजनामा छैन';

  @override
  String get apsExclNoCapability => 'यो च्यानलमा सम्भव छैन';

  @override
  String get apsExclOther => 'अन्य कारण';

  @override
  String apsHoursSaved(String hours) {
    return 'करिब $hours घण्टा बचत (अनुमानित)';
  }

  @override
  String get apsCapCustomerReplies => 'ग्राहकलाई जवाफ';

  @override
  String get apsCapOrderCapture => 'अर्डर लिने';

  @override
  String get apsCapShipmentCreation => 'कुरियर बुकिङ';

  @override
  String get apsCapPickupRequests => 'पिकअप अनुरोध';

  @override
  String get apsCapDeliveryNotifications => 'डेलिभरी सन्देश';

  @override
  String get apsCapDeliveryRecovery => 'नभएको डेलिभरीको पछि लाग्ने';

  @override
  String get apsCapReturns => 'फिर्ता';

  @override
  String get apsCapRefunds => 'रकम फिर्ता';

  @override
  String get apsCapMarketing => 'मार्केटिङ';

  @override
  String get apsCapOther => 'अन्य काम';

  @override
  String get recsTitle => 'सुझाव';

  @override
  String get recSetMode => 'स्मार्ट मोडमा जानुहोस्';

  @override
  String get recActivateTemplate => '“प्याक भएपछि कुरियर बुक” चालु गर्नुहोस्';

  @override
  String get recEnableR2 => 'फेरि पठाउने काम आफैं चल्न दिनुहोस्';

  @override
  String get recEnableReturnAuto => 'साना फिर्ता आफैं स्वीकृत गर्नुहोस्';

  @override
  String get recEnableNotifications =>
      'ग्राहकलाई डेलिभरीबारे सन्देश पठाउनुहोस्';

  @override
  String get recPlanUpgrade => 'माथिल्लो योजनामा उपलब्ध';

  @override
  String get recCourierSelection => 'कुरियर ब्रेनलाई कुरियर छान्न दिनुहोस्';

  @override
  String recRestock(String title) {
    return '$title थप्नुहोस्';
  }

  @override
  String get recOther => 'सुझाव';

  @override
  String recWhyManualGap(String manual, String eligible, String capability) {
    return '३० दिनमा $eligible मध्ये $manual $capability टोलीले हातैले गर्‍यो';
  }

  @override
  String recWhyCourier(
    String theirs,
    String ours,
    String destination,
    String n,
  ) {
    return 'अर्को कुरियरले $destination मा $theirs% डेलिभर गर्‍यो, तपाईंकोले $ours% ($n पार्सल)';
  }

  @override
  String recWhyRestock(String sold, String available, String days) {
    return '३० दिनमा $sold बिक्री, $available बाँकी (करिब $days दिन)';
  }

  @override
  String get recConfidenceHigh => 'उच्च विश्वास';

  @override
  String get recConfidenceMedium => 'मध्यम विश्वास';

  @override
  String recImpactScore(String score) {
    return 'यसलाई $score सम्म पुर्‍याउन सक्छ';
  }

  @override
  String recImpactCourier(String points) {
    return 'डेलिभरी सफलतामा +$points अंक';
  }

  @override
  String get recAccept => 'लागू गर्नुहोस्';

  @override
  String get recDismiss => 'हटाउनुहोस्';

  @override
  String get recDismissTitle => 'किन हटाउने?';

  @override
  String get recDismissReason => 'कारण';

  @override
  String get recCancel => 'रद्द';

  @override
  String get recManagersOnly => 'म्यानेजरले मात्र यो लागू गर्न सक्छन्';

  @override
  String get recApplied => 'भयो';

  @override
  String get recDismissed => 'हटाइयो';

  @override
  String get riskTitle => 'डेलिभरी जोखिम';

  @override
  String get riskLevelLow => 'कम जोखिम';

  @override
  String get riskLevelMedium => 'पठाउनुअघि जाँच्नुहोस्';

  @override
  String get riskLevelHigher => 'डेलिभरी जोखिम बढी';

  @override
  String get riskActionOk => 'डेलिभरीमा नगदको रूपमा पठाउन ठिक छ';

  @override
  String get riskActionVerifyPhone => 'अर्डर पक्का गर्न फोन गर्नुहोस्';

  @override
  String get riskActionPartialAdvance =>
      'पहिले केही अग्रिम भुक्तानी माग्नुहोस्';

  @override
  String get riskActionManualReview => 'प्याक गर्नुअघि जाँच्नुहोस्';

  @override
  String riskFactorHistory(String delivered, String failed) {
    return 'पहिले $delivered डेलिभर, $failed असफल';
  }

  @override
  String get riskFactorNewCustomer => 'तपाईंसँग पहिलो अर्डर';

  @override
  String riskFactorReturns(String returns) {
    return 'पहिले $returns फिर्ता';
  }

  @override
  String get riskFactorAddressMissing => 'ठेगाना अधुरो';

  @override
  String get riskFactorAddressPartial => 'ठेगानाका केही विवरण छैनन्';

  @override
  String riskFactorOrderValue(String ratio) {
    return 'तपाईंको सामान्य अर्डरको $ratio गुणा';
  }

  @override
  String riskFactorRoute(String rate, String district) {
    return '$district मा $rate% डेलिभरी असफल';
  }

  @override
  String get riskFairness =>
      'यो ग्राहकको तपाईंको पसलसँगको इतिहास, ठेगाना र अर्डर मूल्यमा मात्र आधारित। नाम, लिङ्ग, धर्म, जात वा जातीयतामा कहिल्यै होइन।';

  @override
  String riskOverridden(String reason) {
    return 'तपाईंले बदल्नुभयो: $reason';
  }

  @override
  String riskDisputed(String note) {
    return 'ग्राहक असहमत: $note';
  }

  @override
  String get riskOverride => 'स्तर बदल्नुहोस्';

  @override
  String get riskOverrideTitle => 'जोखिम स्तर बदल्नुहोस्';

  @override
  String get riskOverrideReason => 'किन (कम्तीमा ३ अक्षर)';

  @override
  String get riskSave => 'सेभ';

  @override
  String get riskDispute => 'ग्राहक असहमत छन्';

  @override
  String get riskDisputeTitle => 'ग्राहकको असहमति दर्ता';

  @override
  String get riskDisputeNote => 'ग्राहक के भन्छन्';

  @override
  String get riskUpdated => 'अपडेट भयो';

  @override
  String get riskCancel => 'रद्द';
}
