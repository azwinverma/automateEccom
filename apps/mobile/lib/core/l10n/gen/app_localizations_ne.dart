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
  String get permissionDeniedBody => 'पसलको मालिकलाई तपाईंको भूमिकामा अनुमति थप्न भन्नुहोस्।';

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
  String get errMfaInvalidCode => 'कोड मिलेन। Authenticator एप हेरेर फेरि हाल्नुहोस्।';

  @override
  String get errPermissionDenied => 'तपाईंलाई यो गर्ने अनुमति छैन।';

  @override
  String get errFeatureNotInPlan => 'यो तपाईंको प्लानमा पर्दैन।';

  @override
  String get errNotFound => 'त्यो भेटिएन।';

  @override
  String get errConflict => 'यो अर्को ठाउँबाट बदलियो। रिफ्रेस गरेर फेरि प्रयास गर्नुहोस्।';

  @override
  String get errIdempotencyInProgress => 'अघिल्लो काम अझै चल्दैछ। एकछिन पर्खनुहोस्।';

  @override
  String get errIdempotencyKeyReused => 'यो पहिले नै फरक विवरणसहित पठाइसकिएको छ। फेरि सुरुबाट गर्नुहोस्।';

  @override
  String get errSlugTaken => 'त्यो पसल लिंक अरूले लिइसके। अर्कै नाम राख्नुहोस्।';

  @override
  String get errEmailTaken => 'यो इमेलमा पहिल्यै खाता छ। लगइन गरेर हेर्नुहोस्।';

  @override
  String get errUsageLimitReached => 'यो अवधिको सीमा सकियो। क्रेडिट किन्नुहोस्, अपग्रेड गर्नुहोस् वा नवीकरण पर्खनुहोस्।';

  @override
  String get errInvalidStateTransition => 'अहिलेको अवस्थामा यो गर्न मिल्दैन।';

  @override
  String get errRateLimited => 'धेरै पटक प्रयास भयो। अलि पछि फेरि गर्नुहोस्।';

  @override
  String get errDependencyUnavailable => 'हामीले चलाउने एउटा सेवा अहिले बन्द छ। तपाईंको डाटा सुरक्षित छ, केहीबेरमा फेरि प्रयास गर्नुहोस्।';

  @override
  String get errSessionEnded => 'सुरक्षाका लागि लगआउट गरियो। फेरि लगइन गर्नुहोस्।';

  @override
  String get errSessionReused => 'तपाईंको लगइन अर्को डिभाइसमा चलाइयो, त्यसैले सबैतिरबाट लगआउट गरियो। फेरि लगइन गर्नुहोस्; तपाईं होइन भने पासवर्ड बदल्नुहोस्।';

  @override
  String get errSessionRevoked => 'अर्को डिभाइसबाट यो फोन लगआउट गरियो। फेरि लगइन गर्नुहोस्।';

  @override
  String get errNetwork => 'जडान भएन। इन्टरनेट हेरेर फेरि प्रयास गर्नुहोस्।';

  @override
  String get errTimeout => 'इन्टरनेट ढिलो भएर धेरै समय लाग्यो। फेरि प्रयास गर्नुहोस्।';

  @override
  String get errServer => 'हाम्रो तर्फबाट गडबड भयो। केहीबेरमा फेरि प्रयास गर्नुहोस्।';

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
    final intl.NumberFormat minNumberFormat = intl.NumberFormat.decimalPattern(localeName);
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
    final intl.NumberFormat minNumberFormat = intl.NumberFormat.decimalPattern(localeName);
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
  String get onboardingFixedNote => 'अहिलेलाई NPR र नेपाली समय मात्र। अरू विकल्प पछि आउँछ।';

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
  String get metricNotYetBody => 'अर्डर र म्यासेज जोडिएपछि यी अंक सुरु हुन्छन्। त्यतिबेलासम्म अड्कल होइन, खाली देखाउँछौं।';

  @override
  String metricUnavailableSemantics(String metric) {
    return '$metric: अहिले उपलब्ध छैन';
  }

  @override
  String get homeSectionNeedsYou => 'तपाईंले हेर्नुपर्ने';

  @override
  String get exceptionsEmptyTitle => 'अहिले तपाईंले हेर्नुपर्ने केही छैन';

  @override
  String get exceptionsEmptyBody => 'पैसा नमिलेको, डेलिभरी असफल भएको वा AI पक्का नभएका कुरा सबैभन्दा पहिले यहीँ आउँछन्।';

  @override
  String exceptionsCount(int count) {
    final intl.NumberFormat countNumberFormat = intl.NumberFormat.decimalPattern(localeName);
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
  String get autopilotModeAssistedHint => 'AI सुझाव दिन्छ, तपाईं स्वीकृत गर्नुहुन्छ';

  @override
  String get autopilotModeSmartHint => 'सामान्य काम आफैं हुन्छ, जोखिमको काम तपाईंलाई पर्खन्छ';

  @override
  String get autopilotModeAutopilotHint => 'तपाईंका नियमभित्र आफैं चल्छ';

  @override
  String autopilotAutomated(int count) {
    final intl.NumberFormat countNumberFormat = intl.NumberFormat.decimalPattern(localeName);
    final String countString = countNumberFormat.format(count);

    return '$countString आफैं भयो';
  }

  @override
  String autopilotNeedsAttention(int count) {
    final intl.NumberFormat countNumberFormat = intl.NumberFormat.decimalPattern(localeName);
    final String countString = countNumberFormat.format(count);

    return '$countString तपाईंलाई पर्खँदै';
  }

  @override
  String get autopilotNotActive => 'अहिले चालू छैन। अर्डर र म्यासेज जोडिएपछि सुरु हुन्छ।';

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
  String get comingSoonHonest => 'त्यतिबेलासम्म यहाँ नक्कली अर्डर वा बनावटी अंक देखाइँदैन।';

  @override
  String get soonAddProductBody => 'मूल्य, स्टक र साइज/रङसहित एकपटक सामान थप्नुहोस्। Instagram, Facebook र TikTok मा आफैं मिलाएर राख्छौं।';

  @override
  String get soonCaptureProductBody => 'फोनमा केही फोटो खिच्नुहोस्। ब्याकग्राउन्ड सफा गरेर नाम र विवरण तयार गर्छौं, तपाईं जाँचेर राख्नुहोस्।';

  @override
  String get soonGenerateContentBody => 'सामानको विवरणबाट नेपाली वा अंग्रेजीमा क्याप्सन लेख्छौं। तपाईंले स्वीकृत नगरी केही पोस्ट हुँदैन।';

  @override
  String get soonCreateReelBody => 'सामानका फोटो र क्लिपबाट छोटो Reel बनाउँछौं। प्लानको भिडियो क्रेडिट लाग्छ।';

  @override
  String get soonViewOrdersBody => 'च्याटदेखि ग्राहकको ढोकासम्म हरेक अर्डर: COD, कुरियरको अवस्था र फिर्ता।';

  @override
  String get soonViewMessagesBody => 'सबै ग्राहकका म्यासेज एउटै इनबक्समा। AI ले तपाईंकै स्टक र मूल्य हेरेर जवाफ तयार गर्छ।';

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
  String get sessionsRevokeOthersConfirm => 'यो फोनबाहेक सबै डिभाइसबाट लगआउट हुन्छ।';

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
    final intl.NumberFormat countNumberFormat = intl.NumberFormat.decimalPattern(localeName);
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
  String get usageLevelReached => 'सीमा सकियो। जारी राख्न क्रेडिट किन्नुहोस् वा अपग्रेड गर्नुहोस्।';

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
  String get videoMeterHelp => 'महिनाको कोटा र दैनिक सीमा छुट्टाछुट्टै छन्, एकै दिनमा महिनाभरको नसकियोस् भनेर।';

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
  String get captureIntro => '६ वटासम्म प्रस्ट फोटो थप्नुहोस्। अगाडि, पछाडि र कपडा वा लेबलको नजिकको फोटो सबैभन्दा राम्रो।';

  @override
  String get captureTakePhoto => 'फोटो खिच्नुहोस्';

  @override
  String get captureFromGallery => 'ग्यालरीबाट छान्नुहोस्';

  @override
  String capturePhotoCount(int count, int max) {
    final intl.NumberFormat countNumberFormat = intl.NumberFormat.decimalPattern(localeName);
    final String countString = countNumberFormat.format(count);
    final intl.NumberFormat maxNumberFormat = intl.NumberFormat.decimalPattern(localeName);
    final String maxString = maxNumberFormat.format(max);

    return '$maxString मध्ये $countString फोटो';
  }

  @override
  String get captureLimitReached => '६ वटा फोटो पुग्यो, एउटा ड्राफ्टमा यति नै मिल्छ।';

  @override
  String captureSkipped(int count) {
    final intl.NumberFormat countNumberFormat = intl.NumberFormat.decimalPattern(localeName);
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
  String get capturePickerError => 'क्यामेरा वा ग्यालरी खुलेन। फोनको सेटिङमा फोटो र क्यामेरा अनुमति हेर्नुहोस्।';

  @override
  String get captureResumeAll => 'अपलोड फेरि सुरु गर्नुहोस्';

  @override
  String get captureKeepsGoing => 'अर्को एप खोल्दा पनि अपलोड चलिरहन्छ। एप बन्द भए पनि रोकिएकै ठाउँबाट सुरु हुन्छ।';

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
  String get rejectTooLarge => 'फोटो धेरै ठूलो भयो। २० MB भन्दा सानो छान्नुहोस्।';

  @override
  String get rejectUnsupported => 'यो ढाँचा चल्दैन। JPEG, PNG, WebP वा HEIC प्रयोग गर्नुहोस्।';

  @override
  String get rejectMalware => 'यो फाइल असुरक्षित देखियो, त्यसैले हटाइयो।';

  @override
  String get tipLowResolution => 'फोटो सानो छ। नजिक गएर वा मुख्य क्यामेराले खिच्नुहोस्।';

  @override
  String get tipBlurry => 'फोटो धमिलो देखियो। फोन स्थिर राखेर फोकस गर्नुहोस्।';

  @override
  String get tipTooDark => 'फोटो अँध्यारो देखियो। झ्यालनजिक खिचेर हेर्नुहोस्।';

  @override
  String get tipOverexposed => 'फोटो धेरै चम्किलो भयो। सिधा घामबाट अलि पर सर्नुहोस्।';

  @override
  String get errFileTooLarge => 'फोटो धेरै ठूलो भयो (बढीमा २० MB)।';

  @override
  String get errUnsupportedMediaType => 'JPEG, PNG, WebP वा HEIC फोटो प्रयोग गर्नुहोस्।';

  @override
  String get errStorageFull => 'प्लानको फोटो स्टोरेज भरियो। पुराना फोटो हटाउनुहोस् वा अपग्रेड गर्नुहोस्।';

  @override
  String get errFileUnreadable => 'फोनबाट यो फोटो पढ्न सकिएन। फेरि छान्नुहोस्।';

  @override
  String get errUploadMissing => 'फोटो हामीसम्म आइपुगेन। फेरि अपलोड गर्नुहोस्।';

  @override
  String get errUploadExpired => 'अपलोडमा धेरै समय लाग्यो। फेरि सुरु गर्नुहोस्।';

  @override
  String get errMediaNotReady => 'केही फोटो अझै जाँच हुँदैछन्। एकछिनपछि फेरि गर्नुहोस्।';

  @override
  String get errMediaNotFound => 'केही फोटो अब भेटिँदैनन्। फेरि थप्नुहोस्।';

  @override
  String get errDraftNotReady => 'यो ड्राफ्ट अझै तयार छैन।';

  @override
  String get errNotPublishable => 'यो सामान अहिले लाइभ गर्न तयार छैन।';

  @override
  String get errProductNotActive => 'पहिले सामान लाइभ गर्नुहोस्, अनि च्यानलमा पठाउनुहोस्।';

  @override
  String get errCapabilityNotSupported => 'यो च्यानलले त्यो गर्न सक्दैन।';

  @override
  String get errVersionConflict => 'अरू कसैले यो बदल्नुभयो। नयाँ विवरण ल्याइयो, हेरेर फेरि गर्नुहोस्।';

  @override
  String get errPostLocked => 'तालिका मिलाइएको पोस्ट बदल्न मिल्दैन। पहिले तालिका हटाउनुहोस्।';

  @override
  String get errReconnectRequired => 'पहिले यो च्यानल फेरि जोड्नुहोस्।';

  @override
  String get errScheduleInPast => 'आउने समय छान्नुहोस्।';

  @override
  String get errScheduleTooFar => 'पोस्ट ९० दिनभित्र मात्र तालिकामा राख्न सकिन्छ।';

  @override
  String get errCaptionRequired => 'क्याप्सन लेख्नुहोस्।';

  @override
  String get errCaptionTooLong => 'यो क्याप्सन च्यानलका लागि धेरै लामो भयो।';

  @override
  String get errInvalidPhotoCount => '१ देखि ६ वटा फोटो छान्नुहोस्।';

  @override
  String get errNotFailed => 'असफल ड्राफ्ट मात्र फेरि चलाउन मिल्छ।';

  @override
  String get errAiUnavailable => 'लेख्ने सेवा अहिले व्यस्त छ। केही मिनेटपछि फेरि प्रयास गर्नुहोस्।';

  @override
  String get draftWorkingTitle => 'विवरण तयार गर्दैछौं';

  @override
  String get draftWorkingBody => 'तपाईंका फोटो हेरेर नेपाली र अंग्रेजीमा नाम, विवरण र क्याप्सन तयार गर्दैछौं। प्रायः एक मिनेटभित्र सकिन्छ।';

  @override
  String get draftQueued => 'पालोमा';

  @override
  String get draftRunning => 'काम हुँदैछ';

  @override
  String get draftLeaveOk => 'यो स्क्रिन छोड्न सक्नुहुन्छ, काम चलिरहन्छ। पछि \'ड्राफ्ट\' मा भेटिन्छ।';

  @override
  String get draftFailedTitle => 'ड्राफ्ट तयार गर्न सकिएन';

  @override
  String get draftFailedBody => 'लेख्ने सेवामा समस्या भयो। तपाईंका फोटो सुरक्षित छन्।';

  @override
  String get draftAppliedTitle => 'यो पहिले नै सामानको रूपमा सेभ भइसक्यो';

  @override
  String get draftOpenProduct => 'सामान खोल्नुहोस्';

  @override
  String get draftDiscarded => 'यो ड्राफ्ट हटाइएको छ।';

  @override
  String get reviewTitle => 'विवरण जाँच्नुहोस्';

  @override
  String get reviewAiNote => 'तपाईंका फोटो हेरेर AI ले लेखेको। नमिलेको कुरा बदल्नुहोस्।';

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
  String get fieldCategoryHint => 'तह छुट्याउन / राख्नुहोस्, जस्तै: लुगा / कुर्ता';

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
    final intl.NumberFormat countNumberFormat = intl.NumberFormat.decimalPattern(localeName);
    final String countString = countNumberFormat.format(count);

    return '$countString वटा विवरण अझै जाँच्न बाँकी';
  }

  @override
  String get reviewSectionPrice => 'मूल्य र विकल्प';

  @override
  String get reviewPriceNote => 'मूल्य सधैं तपाईंले नै राख्ने हो, AI ले राख्दैन।';

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
  String get optionValuesRequired => 'हरेक विकल्पमा कम्तीमा एउटा मान राख्नुहोस्';

  @override
  String variantsCount(int count) {
    final intl.NumberFormat countNumberFormat = intl.NumberFormat.decimalPattern(localeName);
    final String countString = countNumberFormat.format(count);

    return '$countString वटा भेरियन्ट';
  }

  @override
  String get tooManyVariants => '१०० भन्दा बढी जोडी बने। केही मान हटाउनुहोस्।';

  @override
  String get reviewSectionChecklist => 'AI ले थाहा पाएन, कृपया पुष्टि गर्नुहोस्';

  @override
  String get reviewSectionWarnings => 'जाँच्नुपर्ने कुरा';

  @override
  String get issueClaimPrice => 'लेखाइमा मूल्य उल्लेख छ। मूल्य तपाईंले नै राख्ने हो, कृपया जाँच्नुहोस्।';

  @override
  String get issueClaimDiscount => 'तपाईंले नभनेको छुटको कुरा लेखिएको छ। हटाउनुहोस् वा साँचो हो भने मात्र राख्नुहोस्।';

  @override
  String get issueClaimStock => 'लेखाइमा स्टकको कुरा छ। स्टक तपाईंको इन्भेन्टरीबाट आउँछ, कृपया जाँच्नुहोस्।';

  @override
  String get issueClaimDelivery => 'लेखाइमा डेलिभरीको वाचा छ। साँचो हो कि होइन जाँच्नुहोस्।';

  @override
  String get issueClaimWarranty => 'लेखाइमा वारेन्टीको कुरा छ। तपाईं दिनुहुन्छ भने मात्र राख्नुहोस्।';

  @override
  String get issueClaimAuthenticity => 'सक्कली/ओरिजिनल भनिएको छ। प्रमाण छ भने मात्र राख्नुहोस्।';

  @override
  String get issueClaimOther => 'प्रमाणित गर्न नसकिने कुरा लेखिएको छ। कृपया जाँच्नुहोस्।';

  @override
  String get issueNotProductPhoto => 'यी फोटोमा सामान नदेखिन सक्छ। सेभ गर्नुअघि जाँच्नुहोस्।';

  @override
  String get issueTooLong => 'केही लेखाइ धेरै लामो भएकाले छोटो पारियो। एकपटक पढ्नुहोस्।';

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
  String get productProblemVariant => 'कम्तीमा एउटा सक्रिय भेरियन्ट चाहिन्छ (अहिलेलाई वेब ड्यासबोर्डबाट)।';

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
  String get publishNoChannels => 'अहिलेसम्म कुनै च्यानल जोडिएको छैन। वेब ड्यासबोर्डबाट Instagram, Facebook वा TikTok जोड्नुहोस्।';

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
  String get reconnectBody => 'अहिलेलाई ब्राउजरमा वेब ड्यासबोर्ड खोलेर च्यानल जोड्नुहोस्:';

  @override
  String get reconnectCopied => 'लिंक कपी भयो';

  @override
  String get actionCopyLink => 'लिंक कपी गर्नुहोस्';

  @override
  String get postsSection => 'पोस्ट बनाउनुहोस्';

  @override
  String get postsIntro => 'AI क्याप्सनबाट हरेक च्यानलका लागि पोस्ट बनाउँछौं। पठाउनुअघि तपाईं हेर्नुहुन्छ।';

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
  String get postNeedsApprovalNote => 'AI ले लेखेको पोस्ट पठाउनुअघि स्वीकृति चाहिन्छ।';

  @override
  String get postNoApprovePermission => 'पसल मालिक वा म्यानेजरलाई स्वीकृत गर्न भन्नुहोस्।';

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
  String get draftsEmpty => 'अहिलेसम्म ड्राफ्ट छैन। सामानका केही फोटोबाट सुरु गर्नुहोस्।';

  @override
  String get draftsIntro => 'पोस्ट बनाउन ड्राफ्ट छान्नुहोस् वा नयाँ फोटोबाट सुरु गर्नुहोस्।';

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
  String get forgotSubtitle => 'आफ्नो खाताको इमेल लेख्नुहोस्, नयाँ पासवर्ड राख्ने लिंक पठाउँछौं।';

  @override
  String get forgotAction => 'रिसेट लिंक पठाउनुहोस्';

  @override
  String get forgotSentTitle => 'इमेल हेर्नुहोस्';

  @override
  String get forgotSentBody => 'त्यो इमेलको खाता छ भने रिसेट लिंक आउँदैछ। यही फोन वा कम्प्युटरमा खोल्नुहोस्। यो एक पटक मात्र र ३० मिनेटसम्म चल्छ।';

  @override
  String get forgotBack => 'साइन इनमा फर्कनुहोस्';

  @override
  String get exUsageLimit => 'प्लान सीमा';

  @override
  String exSubjectUsage(int used, int limit) {
    return 'यो महिना $limit मध्ये $used प्रयोग भयो (वेबमा प्लान हेर्नुहोस्)';
  }
}
