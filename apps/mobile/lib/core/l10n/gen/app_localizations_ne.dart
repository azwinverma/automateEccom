// ignore: unused_import
import 'package:intl/intl.dart' as intl;
import 'app_localizations.dart';

// ignore_for_file: type=lint

/// The translations for Nepali (`ne`).
class AppLocalizationsNe extends AppLocalizations {
  AppLocalizationsNe([String locale = 'ne']) : super(locale);

  @override
  String get appName => 'Commerce OS';

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
}
