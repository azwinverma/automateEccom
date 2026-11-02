import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:intl/intl.dart' as intl;

import 'app_localizations_en.dart';
import 'app_localizations_ne.dart';

// ignore_for_file: type=lint

/// Callers can lookup localized strings with an instance of AppLocalizations
/// returned by `AppLocalizations.of(context)`.
///
/// Applications need to include `AppLocalizations.delegate()` in their app's
/// `localizationDelegates` list, and the locales they support in the app's
/// `supportedLocales` list. For example:
///
/// ```dart
/// import 'gen/app_localizations.dart';
///
/// return MaterialApp(
///   localizationsDelegates: AppLocalizations.localizationsDelegates,
///   supportedLocales: AppLocalizations.supportedLocales,
///   home: MyApplicationHome(),
/// );
/// ```
///
/// ## Update pubspec.yaml
///
/// Please make sure to update your pubspec.yaml to include the following
/// packages:
///
/// ```yaml
/// dependencies:
///   # Internationalization support.
///   flutter_localizations:
///     sdk: flutter
///   intl: any # Use the pinned version from flutter_localizations
///
///   # Rest of dependencies
/// ```
///
/// ## iOS Applications
///
/// iOS applications define key application metadata, including supported
/// locales, in an Info.plist file that is built into the application bundle.
/// To configure the locales supported by your app, you’ll need to edit this
/// file.
///
/// First, open your project’s ios/Runner.xcworkspace Xcode workspace file.
/// Then, in the Project Navigator, open the Info.plist file under the Runner
/// project’s Runner folder.
///
/// Next, select the Information Property List item, select Add Item from the
/// Editor menu, then select Localizations from the pop-up menu.
///
/// Select and expand the newly-created Localizations item then, for each
/// locale your application supports, add a new item and select the locale
/// you wish to add from the pop-up menu in the Value field. This list should
/// be consistent with the languages listed in the AppLocalizations.supportedLocales
/// property.
abstract class AppLocalizations {
  AppLocalizations(String locale) : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate = _AppLocalizationsDelegate();

  /// A list of this localizations delegate along with the default localizations
  /// delegates.
  ///
  /// Returns a list of localizations delegates containing this delegate along with
  /// GlobalMaterialLocalizations.delegate, GlobalCupertinoLocalizations.delegate,
  /// and GlobalWidgetsLocalizations.delegate.
  ///
  /// Additional delegates can be added by appending to this list in
  /// MaterialApp. This list does not have to be used at all if a custom list
  /// of delegates is preferred or required.
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates = <LocalizationsDelegate<dynamic>>[
    delegate,
    GlobalMaterialLocalizations.delegate,
    GlobalCupertinoLocalizations.delegate,
    GlobalWidgetsLocalizations.delegate,
  ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('ne')
  ];

  /// No description provided for @appName.
  ///
  /// In en, this message translates to:
  /// **'Nivaro'**
  String get appName;

  /// No description provided for @actionRetry.
  ///
  /// In en, this message translates to:
  /// **'Try again'**
  String get actionRetry;

  /// No description provided for @actionContinue.
  ///
  /// In en, this message translates to:
  /// **'Continue'**
  String get actionContinue;

  /// No description provided for @actionCancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get actionCancel;

  /// Tiny support reference shown under errors
  ///
  /// In en, this message translates to:
  /// **'Ref {id}'**
  String requestIdLabel(String id);

  /// No description provided for @loadingLabel.
  ///
  /// In en, this message translates to:
  /// **'Loading'**
  String get loadingLabel;

  /// No description provided for @splashLoading.
  ///
  /// In en, this message translates to:
  /// **'Opening your shop…'**
  String get splashLoading;

  /// No description provided for @offlineBanner.
  ///
  /// In en, this message translates to:
  /// **'You\'re offline. Changes wait until you\'re back.'**
  String get offlineBanner;

  /// No description provided for @offlineTitle.
  ///
  /// In en, this message translates to:
  /// **'No internet connection'**
  String get offlineTitle;

  /// No description provided for @offlineBody.
  ///
  /// In en, this message translates to:
  /// **'Check mobile data or Wi-Fi, then try again.'**
  String get offlineBody;

  /// No description provided for @errorTitle.
  ///
  /// In en, this message translates to:
  /// **'Couldn\'t load this'**
  String get errorTitle;

  /// No description provided for @permissionDeniedTitle.
  ///
  /// In en, this message translates to:
  /// **'You don\'t have access to this'**
  String get permissionDeniedTitle;

  /// No description provided for @permissionDeniedBody.
  ///
  /// In en, this message translates to:
  /// **'Ask the shop owner to give your role access.'**
  String get permissionDeniedBody;

  /// No description provided for @featureNotInPlanTitle.
  ///
  /// In en, this message translates to:
  /// **'Not in your current plan'**
  String get featureNotInPlanTitle;

  /// No description provided for @featureNotInPlanBody.
  ///
  /// In en, this message translates to:
  /// **'Upgrade your plan to use this.'**
  String get featureNotInPlanBody;

  /// No description provided for @errValidation.
  ///
  /// In en, this message translates to:
  /// **'Some details need fixing.'**
  String get errValidation;

  /// No description provided for @errNotAuthenticated.
  ///
  /// In en, this message translates to:
  /// **'Please log in again.'**
  String get errNotAuthenticated;

  /// No description provided for @errInvalidCredentials.
  ///
  /// In en, this message translates to:
  /// **'Email or password didn\'t match.'**
  String get errInvalidCredentials;

  /// No description provided for @errMfaInvalidCode.
  ///
  /// In en, this message translates to:
  /// **'That code didn\'t work. Check your authenticator app and try again.'**
  String get errMfaInvalidCode;

  /// No description provided for @errPermissionDenied.
  ///
  /// In en, this message translates to:
  /// **'You don\'t have permission to do this.'**
  String get errPermissionDenied;

  /// No description provided for @errFeatureNotInPlan.
  ///
  /// In en, this message translates to:
  /// **'This isn\'t included in your plan.'**
  String get errFeatureNotInPlan;

  /// No description provided for @errNotFound.
  ///
  /// In en, this message translates to:
  /// **'We couldn\'t find that.'**
  String get errNotFound;

  /// No description provided for @errConflict.
  ///
  /// In en, this message translates to:
  /// **'This changed somewhere else. Refresh and try again.'**
  String get errConflict;

  /// No description provided for @errIdempotencyInProgress.
  ///
  /// In en, this message translates to:
  /// **'Still working on your last request. Give it a moment.'**
  String get errIdempotencyInProgress;

  /// No description provided for @errIdempotencyKeyReused.
  ///
  /// In en, this message translates to:
  /// **'This was already sent with different details. Please start again.'**
  String get errIdempotencyKeyReused;

  /// No description provided for @errSlugTaken.
  ///
  /// In en, this message translates to:
  /// **'That shop link is taken. Try a different name.'**
  String get errSlugTaken;

  /// No description provided for @errEmailTaken.
  ///
  /// In en, this message translates to:
  /// **'An account with this email already exists. Try logging in.'**
  String get errEmailTaken;

  /// No description provided for @errUsageLimitReached.
  ///
  /// In en, this message translates to:
  /// **'You\'ve reached this period\'s limit. Buy credits, upgrade, or wait for renewal.'**
  String get errUsageLimitReached;

  /// No description provided for @errInvalidStateTransition.
  ///
  /// In en, this message translates to:
  /// **'This can\'t be done at its current stage.'**
  String get errInvalidStateTransition;

  /// No description provided for @errRateLimited.
  ///
  /// In en, this message translates to:
  /// **'Too many tries. Wait a little and try again.'**
  String get errRateLimited;

  /// No description provided for @errDependencyUnavailable.
  ///
  /// In en, this message translates to:
  /// **'A service we rely on is down. Your data is safe — try again shortly.'**
  String get errDependencyUnavailable;

  /// No description provided for @errSessionEnded.
  ///
  /// In en, this message translates to:
  /// **'For your safety we signed you out. Please log in again.'**
  String get errSessionEnded;

  /// No description provided for @errSessionReused.
  ///
  /// In en, this message translates to:
  /// **'Your login was used on another device, so we signed you out everywhere. Log in again, and change your password if that wasn\'t you.'**
  String get errSessionReused;

  /// No description provided for @errSessionRevoked.
  ///
  /// In en, this message translates to:
  /// **'This device was logged out from another device. Please log in again.'**
  String get errSessionRevoked;

  /// No description provided for @errNetwork.
  ///
  /// In en, this message translates to:
  /// **'No connection. Check your internet and try again.'**
  String get errNetwork;

  /// No description provided for @errTimeout.
  ///
  /// In en, this message translates to:
  /// **'The connection is slow and this took too long. Try again.'**
  String get errTimeout;

  /// No description provided for @errServer.
  ///
  /// In en, this message translates to:
  /// **'Something went wrong on our side. Try again in a bit.'**
  String get errServer;

  /// No description provided for @errUnknown.
  ///
  /// In en, this message translates to:
  /// **'Something went wrong. Try again.'**
  String get errUnknown;

  /// No description provided for @errFieldInvalid.
  ///
  /// In en, this message translates to:
  /// **'Check this field'**
  String get errFieldInvalid;

  /// No description provided for @loginTitle.
  ///
  /// In en, this message translates to:
  /// **'Log in to your shop'**
  String get loginTitle;

  /// No description provided for @loginSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Orders, messages and stock in one place.'**
  String get loginSubtitle;

  /// No description provided for @fieldEmail.
  ///
  /// In en, this message translates to:
  /// **'Email'**
  String get fieldEmail;

  /// No description provided for @fieldPassword.
  ///
  /// In en, this message translates to:
  /// **'Password'**
  String get fieldPassword;

  /// No description provided for @fieldFullName.
  ///
  /// In en, this message translates to:
  /// **'Your name'**
  String get fieldFullName;

  /// No description provided for @fieldPhone.
  ///
  /// In en, this message translates to:
  /// **'Mobile number (optional)'**
  String get fieldPhone;

  /// No description provided for @validationEmailRequired.
  ///
  /// In en, this message translates to:
  /// **'Enter your email'**
  String get validationEmailRequired;

  /// No description provided for @validationEmailInvalid.
  ///
  /// In en, this message translates to:
  /// **'That email doesn\'t look right'**
  String get validationEmailInvalid;

  /// No description provided for @validationPasswordRequired.
  ///
  /// In en, this message translates to:
  /// **'Enter your password'**
  String get validationPasswordRequired;

  /// No description provided for @validationPasswordTooShort.
  ///
  /// In en, this message translates to:
  /// **'Use at least {min} characters'**
  String validationPasswordTooShort(int min);

  /// No description provided for @validationPasswordEqualsEmail.
  ///
  /// In en, this message translates to:
  /// **'Password can\'t be the same as your email'**
  String get validationPasswordEqualsEmail;

  /// No description provided for @validationNameRequired.
  ///
  /// In en, this message translates to:
  /// **'Enter your name'**
  String get validationNameRequired;

  /// No description provided for @validationPhoneInvalid.
  ///
  /// In en, this message translates to:
  /// **'Enter a valid mobile number'**
  String get validationPhoneInvalid;

  /// No description provided for @passwordHint.
  ///
  /// In en, this message translates to:
  /// **'At least {min} characters. Avoid common passwords.'**
  String passwordHint(int min);

  /// No description provided for @loginAction.
  ///
  /// In en, this message translates to:
  /// **'Log in'**
  String get loginAction;

  /// No description provided for @loginNoAccount.
  ///
  /// In en, this message translates to:
  /// **'New here? Create an account'**
  String get loginNoAccount;

  /// No description provided for @showPassword.
  ///
  /// In en, this message translates to:
  /// **'Show password'**
  String get showPassword;

  /// No description provided for @hidePassword.
  ///
  /// In en, this message translates to:
  /// **'Hide password'**
  String get hidePassword;

  /// No description provided for @mfaTitle.
  ///
  /// In en, this message translates to:
  /// **'Enter your 6-digit code'**
  String get mfaTitle;

  /// No description provided for @mfaSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Open your authenticator app. A recovery code also works.'**
  String get mfaSubtitle;

  /// No description provided for @fieldMfaCode.
  ///
  /// In en, this message translates to:
  /// **'Code'**
  String get fieldMfaCode;

  /// No description provided for @validationCodeRequired.
  ///
  /// In en, this message translates to:
  /// **'Enter the code'**
  String get validationCodeRequired;

  /// No description provided for @mfaVerifyAction.
  ///
  /// In en, this message translates to:
  /// **'Verify'**
  String get mfaVerifyAction;

  /// No description provided for @mfaUseDifferentAccount.
  ///
  /// In en, this message translates to:
  /// **'Use a different account'**
  String get mfaUseDifferentAccount;

  /// No description provided for @registerTitle.
  ///
  /// In en, this message translates to:
  /// **'Create your seller account'**
  String get registerTitle;

  /// No description provided for @registerSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Takes about a minute.'**
  String get registerSubtitle;

  /// No description provided for @registerAction.
  ///
  /// In en, this message translates to:
  /// **'Create account'**
  String get registerAction;

  /// No description provided for @registerHaveAccount.
  ///
  /// In en, this message translates to:
  /// **'Already have an account? Log in'**
  String get registerHaveAccount;

  /// No description provided for @onboardingTitle.
  ///
  /// In en, this message translates to:
  /// **'Set up your shop'**
  String get onboardingTitle;

  /// No description provided for @onboardingSubtitle.
  ///
  /// In en, this message translates to:
  /// **'You can change these later in Settings.'**
  String get onboardingSubtitle;

  /// No description provided for @fieldBusinessName.
  ///
  /// In en, this message translates to:
  /// **'Shop or business name'**
  String get fieldBusinessName;

  /// No description provided for @fieldBusinessNameHint.
  ///
  /// In en, this message translates to:
  /// **'e.g. Thamel Handloom'**
  String get fieldBusinessNameHint;

  /// No description provided for @validationBusinessNameRequired.
  ///
  /// In en, this message translates to:
  /// **'Enter your shop name'**
  String get validationBusinessNameRequired;

  /// No description provided for @validationBusinessNameTooShort.
  ///
  /// In en, this message translates to:
  /// **'That name is too short'**
  String get validationBusinessNameTooShort;

  /// No description provided for @fieldCurrency.
  ///
  /// In en, this message translates to:
  /// **'Currency'**
  String get fieldCurrency;

  /// No description provided for @currencyNpr.
  ///
  /// In en, this message translates to:
  /// **'Nepali Rupee (NPR)'**
  String get currencyNpr;

  /// No description provided for @fieldTimezone.
  ///
  /// In en, this message translates to:
  /// **'Time zone'**
  String get fieldTimezone;

  /// No description provided for @timezoneKathmandu.
  ///
  /// In en, this message translates to:
  /// **'Kathmandu (UTC+5:45)'**
  String get timezoneKathmandu;

  /// No description provided for @onboardingFixedNote.
  ///
  /// In en, this message translates to:
  /// **'NPR and Nepal time for now. More options later.'**
  String get onboardingFixedNote;

  /// No description provided for @fieldDefaultLanguage.
  ///
  /// In en, this message translates to:
  /// **'Language for customers and receipts'**
  String get fieldDefaultLanguage;

  /// No description provided for @languageNepali.
  ///
  /// In en, this message translates to:
  /// **'नेपाली'**
  String get languageNepali;

  /// No description provided for @languageEnglish.
  ///
  /// In en, this message translates to:
  /// **'English'**
  String get languageEnglish;

  /// No description provided for @onboardingAction.
  ///
  /// In en, this message translates to:
  /// **'Create shop'**
  String get onboardingAction;

  /// No description provided for @navHome.
  ///
  /// In en, this message translates to:
  /// **'Home'**
  String get navHome;

  /// No description provided for @navSettings.
  ///
  /// In en, this message translates to:
  /// **'Settings'**
  String get navSettings;

  /// No description provided for @homeGreeting.
  ///
  /// In en, this message translates to:
  /// **'Namaste, {name}'**
  String homeGreeting(String name);

  /// No description provided for @homeSectionToday.
  ///
  /// In en, this message translates to:
  /// **'Today'**
  String get homeSectionToday;

  /// No description provided for @metricOrders.
  ///
  /// In en, this message translates to:
  /// **'Orders'**
  String get metricOrders;

  /// No description provided for @metricRevenue.
  ///
  /// In en, this message translates to:
  /// **'Revenue'**
  String get metricRevenue;

  /// No description provided for @metricAiMessages.
  ///
  /// In en, this message translates to:
  /// **'AI-handled messages'**
  String get metricAiMessages;

  /// No description provided for @metricReadyToShip.
  ///
  /// In en, this message translates to:
  /// **'Ready to ship'**
  String get metricReadyToShip;

  /// No description provided for @metricNotYet.
  ///
  /// In en, this message translates to:
  /// **'Not counted yet'**
  String get metricNotYet;

  /// No description provided for @metricNotYetBody.
  ///
  /// In en, this message translates to:
  /// **'These numbers start once orders and messages connect. Until then we show nothing rather than guesses.'**
  String get metricNotYetBody;

  /// No description provided for @metricUnavailableSemantics.
  ///
  /// In en, this message translates to:
  /// **'{metric}: not available yet'**
  String metricUnavailableSemantics(String metric);

  /// No description provided for @homeSectionNeedsYou.
  ///
  /// In en, this message translates to:
  /// **'Needs you'**
  String get homeSectionNeedsYou;

  /// No description provided for @exceptionsEmptyTitle.
  ///
  /// In en, this message translates to:
  /// **'Nothing needs you right now'**
  String get exceptionsEmptyTitle;

  /// No description provided for @exceptionsEmptyBody.
  ///
  /// In en, this message translates to:
  /// **'Payment mismatches, failed deliveries and unsure AI replies will show up here first.'**
  String get exceptionsEmptyBody;

  /// No description provided for @exceptionsCount.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 item} other{{count} items}}'**
  String exceptionsCount(int count);

  /// No description provided for @exPaymentMismatch.
  ///
  /// In en, this message translates to:
  /// **'Payment doesn\'t match'**
  String get exPaymentMismatch;

  /// No description provided for @exLowConfidenceAi.
  ///
  /// In en, this message translates to:
  /// **'AI wasn\'t sure'**
  String get exLowConfidenceAi;

  /// No description provided for @exRefundAboveThreshold.
  ///
  /// In en, this message translates to:
  /// **'Large refund to approve'**
  String get exRefundAboveThreshold;

  /// No description provided for @exCourierFailed.
  ///
  /// In en, this message translates to:
  /// **'Delivery failed'**
  String get exCourierFailed;

  /// No description provided for @exChannelExpired.
  ///
  /// In en, this message translates to:
  /// **'Channel disconnected'**
  String get exChannelExpired;

  /// No description provided for @exInventoryMismatch.
  ///
  /// In en, this message translates to:
  /// **'Stock doesn\'t match'**
  String get exInventoryMismatch;

  /// No description provided for @exPublishFailed.
  ///
  /// In en, this message translates to:
  /// **'Post didn\'t publish'**
  String get exPublishFailed;

  /// No description provided for @exAmbiguousVariant.
  ///
  /// In en, this message translates to:
  /// **'Which size or colour?'**
  String get exAmbiguousVariant;

  /// No description provided for @exCustomerEscalation.
  ///
  /// In en, this message translates to:
  /// **'Customer wants a person'**
  String get exCustomerEscalation;

  /// No description provided for @exProviderFailure.
  ///
  /// In en, this message translates to:
  /// **'Service problem'**
  String get exProviderFailure;

  /// No description provided for @autopilotTitle.
  ///
  /// In en, this message translates to:
  /// **'Autopilot'**
  String get autopilotTitle;

  /// No description provided for @autopilotModeAssisted.
  ///
  /// In en, this message translates to:
  /// **'Assisted'**
  String get autopilotModeAssisted;

  /// No description provided for @autopilotModeSmart.
  ///
  /// In en, this message translates to:
  /// **'Smart'**
  String get autopilotModeSmart;

  /// No description provided for @autopilotModeAutopilot.
  ///
  /// In en, this message translates to:
  /// **'Autopilot'**
  String get autopilotModeAutopilot;

  /// No description provided for @autopilotModeAssistedHint.
  ///
  /// In en, this message translates to:
  /// **'AI suggests, you approve'**
  String get autopilotModeAssistedHint;

  /// No description provided for @autopilotModeSmartHint.
  ///
  /// In en, this message translates to:
  /// **'Routine work runs, risky work waits for you'**
  String get autopilotModeSmartHint;

  /// No description provided for @autopilotModeAutopilotHint.
  ///
  /// In en, this message translates to:
  /// **'Runs on its own within your rules'**
  String get autopilotModeAutopilotHint;

  /// No description provided for @autopilotAutomated.
  ///
  /// In en, this message translates to:
  /// **'{count} handled'**
  String autopilotAutomated(int count);

  /// No description provided for @autopilotNeedsAttention.
  ///
  /// In en, this message translates to:
  /// **'{count} need you'**
  String autopilotNeedsAttention(int count);

  /// No description provided for @autopilotNotActive.
  ///
  /// In en, this message translates to:
  /// **'Not active yet. Starts when orders and messages connect.'**
  String get autopilotNotActive;

  /// No description provided for @quickActionsTitle.
  ///
  /// In en, this message translates to:
  /// **'Quick actions'**
  String get quickActionsTitle;

  /// No description provided for @qaAddProduct.
  ///
  /// In en, this message translates to:
  /// **'Add product'**
  String get qaAddProduct;

  /// No description provided for @qaCaptureProduct.
  ///
  /// In en, this message translates to:
  /// **'Capture product'**
  String get qaCaptureProduct;

  /// No description provided for @qaGenerateContent.
  ///
  /// In en, this message translates to:
  /// **'Write a post'**
  String get qaGenerateContent;

  /// No description provided for @qaCreateReel.
  ///
  /// In en, this message translates to:
  /// **'Create Reel'**
  String get qaCreateReel;

  /// No description provided for @qaViewOrders.
  ///
  /// In en, this message translates to:
  /// **'Orders'**
  String get qaViewOrders;

  /// No description provided for @qaViewMessages.
  ///
  /// In en, this message translates to:
  /// **'Messages'**
  String get qaViewMessages;

  /// No description provided for @comingSoonBadge.
  ///
  /// In en, this message translates to:
  /// **'Coming in the next release'**
  String get comingSoonBadge;

  /// No description provided for @comingSoonWhat.
  ///
  /// In en, this message translates to:
  /// **'What it will do'**
  String get comingSoonWhat;

  /// No description provided for @comingSoonHonest.
  ///
  /// In en, this message translates to:
  /// **'Until then, nothing here is simulated — no sample orders or made-up numbers.'**
  String get comingSoonHonest;

  /// No description provided for @soonAddProductBody.
  ///
  /// In en, this message translates to:
  /// **'Add a product once with price, stock and sizes or colours. We keep it in sync across Instagram, Facebook and TikTok.'**
  String get soonAddProductBody;

  /// No description provided for @soonCaptureProductBody.
  ///
  /// In en, this message translates to:
  /// **'Snap a few photos on your phone. We clean up the background and draft the title and details for you to check.'**
  String get soonCaptureProductBody;

  /// No description provided for @soonGenerateContentBody.
  ///
  /// In en, this message translates to:
  /// **'Write captions in Nepali or English from your product details. Nothing is posted until you approve it.'**
  String get soonGenerateContentBody;

  /// No description provided for @soonCreateReelBody.
  ///
  /// In en, this message translates to:
  /// **'Turn your product photos and clips into a short Reel. Uses video credits from your plan.'**
  String get soonCreateReelBody;

  /// No description provided for @soonViewOrdersBody.
  ///
  /// In en, this message translates to:
  /// **'Follow every order from chat to doorstep: COD, courier status and returns.'**
  String get soonViewOrdersBody;

  /// No description provided for @soonViewMessagesBody.
  ///
  /// In en, this message translates to:
  /// **'All customer messages in one inbox. AI drafts replies from your real stock and prices.'**
  String get soonViewMessagesBody;

  /// No description provided for @settingsTitle.
  ///
  /// In en, this message translates to:
  /// **'Settings'**
  String get settingsTitle;

  /// No description provided for @settingsProfile.
  ///
  /// In en, this message translates to:
  /// **'Profile'**
  String get settingsProfile;

  /// No description provided for @settingsShop.
  ///
  /// In en, this message translates to:
  /// **'Shop'**
  String get settingsShop;

  /// No description provided for @settingsLanguage.
  ///
  /// In en, this message translates to:
  /// **'App language'**
  String get settingsLanguage;

  /// No description provided for @languageSystem.
  ///
  /// In en, this message translates to:
  /// **'Same as phone'**
  String get languageSystem;

  /// No description provided for @settingsSecurity.
  ///
  /// In en, this message translates to:
  /// **'Security & devices'**
  String get settingsSecurity;

  /// No description provided for @settingsPlan.
  ///
  /// In en, this message translates to:
  /// **'Plan & usage'**
  String get settingsPlan;

  /// No description provided for @settingsLogout.
  ///
  /// In en, this message translates to:
  /// **'Log out'**
  String get settingsLogout;

  /// No description provided for @logoutConfirmTitle.
  ///
  /// In en, this message translates to:
  /// **'Log out of this phone?'**
  String get logoutConfirmTitle;

  /// No description provided for @emailUnverified.
  ///
  /// In en, this message translates to:
  /// **'Email not verified'**
  String get emailUnverified;

  /// No description provided for @mfaOn.
  ///
  /// In en, this message translates to:
  /// **'Two-step login is on'**
  String get mfaOn;

  /// No description provided for @mfaOff.
  ///
  /// In en, this message translates to:
  /// **'Two-step login is off'**
  String get mfaOff;

  /// No description provided for @securityTitle.
  ///
  /// In en, this message translates to:
  /// **'Security & devices'**
  String get securityTitle;

  /// No description provided for @sessionsTitle.
  ///
  /// In en, this message translates to:
  /// **'Logged-in devices'**
  String get sessionsTitle;

  /// No description provided for @sessionThisDevice.
  ///
  /// In en, this message translates to:
  /// **'This phone'**
  String get sessionThisDevice;

  /// No description provided for @sessionLastUsed.
  ///
  /// In en, this message translates to:
  /// **'Last used {when}'**
  String sessionLastUsed(String when);

  /// No description provided for @sessionUnknownDevice.
  ///
  /// In en, this message translates to:
  /// **'Unknown device'**
  String get sessionUnknownDevice;

  /// No description provided for @sessionRevoke.
  ///
  /// In en, this message translates to:
  /// **'Log out'**
  String get sessionRevoke;

  /// No description provided for @sessionRevokeConfirm.
  ///
  /// In en, this message translates to:
  /// **'Log out {device}?'**
  String sessionRevokeConfirm(String device);

  /// No description provided for @sessionsRevokeOthers.
  ///
  /// In en, this message translates to:
  /// **'Log out all other devices'**
  String get sessionsRevokeOthers;

  /// No description provided for @sessionsRevokeOthersConfirm.
  ///
  /// In en, this message translates to:
  /// **'Every device except this phone will be logged out.'**
  String get sessionsRevokeOthersConfirm;

  /// No description provided for @sessionsRevokedToast.
  ///
  /// In en, this message translates to:
  /// **'Logged out'**
  String get sessionsRevokedToast;

  /// No description provided for @sessionsOnlyThis.
  ///
  /// In en, this message translates to:
  /// **'Only this phone is logged in.'**
  String get sessionsOnlyThis;

  /// No description provided for @planTitle.
  ///
  /// In en, this message translates to:
  /// **'Plan & usage'**
  String get planTitle;

  /// No description provided for @planStatusTrialing.
  ///
  /// In en, this message translates to:
  /// **'Trial · ends {date}'**
  String planStatusTrialing(String date);

  /// No description provided for @planStatusActive.
  ///
  /// In en, this message translates to:
  /// **'Active'**
  String get planStatusActive;

  /// No description provided for @planStatusPastDue.
  ///
  /// In en, this message translates to:
  /// **'Payment due'**
  String get planStatusPastDue;

  /// No description provided for @planStatusCanceled.
  ///
  /// In en, this message translates to:
  /// **'Canceled'**
  String get planStatusCanceled;

  /// No description provided for @planPeriod.
  ///
  /// In en, this message translates to:
  /// **'Current period {start} – {end}'**
  String planPeriod(String start, String end);

  /// No description provided for @usageTitle.
  ///
  /// In en, this message translates to:
  /// **'Usage'**
  String get usageTitle;

  /// No description provided for @usageUsedOf.
  ///
  /// In en, this message translates to:
  /// **'{used} of {limit}'**
  String usageUsedOf(String used, String limit);

  /// No description provided for @usageUnlimited.
  ///
  /// In en, this message translates to:
  /// **'Unlimited'**
  String get usageUnlimited;

  /// No description provided for @usageReserved.
  ///
  /// In en, this message translates to:
  /// **'{count} in progress'**
  String usageReserved(int count);

  /// No description provided for @usagePeriodMonth.
  ///
  /// In en, this message translates to:
  /// **'This month'**
  String get usagePeriodMonth;

  /// No description provided for @usagePeriodDay.
  ///
  /// In en, this message translates to:
  /// **'Today'**
  String get usagePeriodDay;

  /// No description provided for @usageLevelNotice.
  ///
  /// In en, this message translates to:
  /// **'Over 70% used'**
  String get usageLevelNotice;

  /// No description provided for @usageLevelWarning.
  ///
  /// In en, this message translates to:
  /// **'Almost at the limit'**
  String get usageLevelWarning;

  /// No description provided for @usageLevelReached.
  ///
  /// In en, this message translates to:
  /// **'Limit reached. Buy credits or upgrade to keep going.'**
  String get usageLevelReached;

  /// No description provided for @usageEmpty.
  ///
  /// In en, this message translates to:
  /// **'Nothing on your plan is metered yet.'**
  String get usageEmpty;

  /// No description provided for @creditsTitle.
  ///
  /// In en, this message translates to:
  /// **'Credits'**
  String get creditsTitle;

  /// No description provided for @creditsBalance.
  ///
  /// In en, this message translates to:
  /// **'{balance} credits'**
  String creditsBalance(String balance);

  /// No description provided for @creditsNoTransactions.
  ///
  /// In en, this message translates to:
  /// **'No credit activity yet'**
  String get creditsNoTransactions;

  /// No description provided for @videoMeterTitle.
  ///
  /// In en, this message translates to:
  /// **'Video credits'**
  String get videoMeterTitle;

  /// No description provided for @videoMeterMonthly.
  ///
  /// In en, this message translates to:
  /// **'This month'**
  String get videoMeterMonthly;

  /// No description provided for @videoMeterDaily.
  ///
  /// In en, this message translates to:
  /// **'Today'**
  String get videoMeterDaily;

  /// No description provided for @videoMeterNoDailyCap.
  ///
  /// In en, this message translates to:
  /// **'No daily cap'**
  String get videoMeterNoDailyCap;

  /// No description provided for @videoMeterDailyReached.
  ///
  /// In en, this message translates to:
  /// **'Today\'s cap reached. It resets tomorrow.'**
  String get videoMeterDailyReached;

  /// No description provided for @videoMeterHelp.
  ///
  /// In en, this message translates to:
  /// **'A monthly quota plus a daily cap, so one busy day can\'t use up the whole month.'**
  String get videoMeterHelp;

  /// No description provided for @resAiTextGenerations.
  ///
  /// In en, this message translates to:
  /// **'AI writing'**
  String get resAiTextGenerations;

  /// No description provided for @resAiInboxReplies.
  ///
  /// In en, this message translates to:
  /// **'AI replies'**
  String get resAiInboxReplies;

  /// No description provided for @resAiImages.
  ///
  /// In en, this message translates to:
  /// **'AI images'**
  String get resAiImages;

  /// No description provided for @resAutoReels.
  ///
  /// In en, this message translates to:
  /// **'Auto Reels'**
  String get resAutoReels;

  /// No description provided for @resPremiumVideo.
  ///
  /// In en, this message translates to:
  /// **'Premium video'**
  String get resPremiumVideo;

  /// No description provided for @resProducts.
  ///
  /// In en, this message translates to:
  /// **'Products'**
  String get resProducts;

  /// No description provided for @resOrders.
  ///
  /// In en, this message translates to:
  /// **'Orders'**
  String get resOrders;

  /// No description provided for @resChannels.
  ///
  /// In en, this message translates to:
  /// **'Channels'**
  String get resChannels;

  /// No description provided for @resTeamMembers.
  ///
  /// In en, this message translates to:
  /// **'Team members'**
  String get resTeamMembers;

  /// No description provided for @resStores.
  ///
  /// In en, this message translates to:
  /// **'Stores'**
  String get resStores;

  /// No description provided for @resStorage.
  ///
  /// In en, this message translates to:
  /// **'Storage'**
  String get resStorage;

  /// No description provided for @resAutomationRuns.
  ///
  /// In en, this message translates to:
  /// **'Automation runs'**
  String get resAutomationRuns;

  /// No description provided for @resApiCalls.
  ///
  /// In en, this message translates to:
  /// **'API calls'**
  String get resApiCalls;

  /// No description provided for @captureTitle.
  ///
  /// In en, this message translates to:
  /// **'Capture product'**
  String get captureTitle;

  /// No description provided for @captureIntro.
  ///
  /// In en, this message translates to:
  /// **'Add up to 6 clear photos. Front, back and a close-up of the fabric or label work best.'**
  String get captureIntro;

  /// No description provided for @captureTakePhoto.
  ///
  /// In en, this message translates to:
  /// **'Take photo'**
  String get captureTakePhoto;

  /// No description provided for @captureFromGallery.
  ///
  /// In en, this message translates to:
  /// **'Choose from gallery'**
  String get captureFromGallery;

  /// No description provided for @capturePhotoCount.
  ///
  /// In en, this message translates to:
  /// **'{count} of {max} photos'**
  String capturePhotoCount(int count, int max);

  /// No description provided for @captureLimitReached.
  ///
  /// In en, this message translates to:
  /// **'That\'s 6 photos — the most one draft can use.'**
  String get captureLimitReached;

  /// No description provided for @captureSkipped.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 photo wasn\'t added} other{{count} photos weren\'t added}} — 6 is the limit.'**
  String captureSkipped(int count);

  /// No description provided for @captureNotesLabel.
  ///
  /// In en, this message translates to:
  /// **'Anything we should know? (optional)'**
  String get captureNotesLabel;

  /// No description provided for @captureNotesHint.
  ///
  /// In en, this message translates to:
  /// **'e.g. pure cotton, handmade in Bhaktapur'**
  String get captureNotesHint;

  /// No description provided for @captureMakeDraft.
  ///
  /// In en, this message translates to:
  /// **'Write my listing'**
  String get captureMakeDraft;

  /// No description provided for @captureWaitForUploads.
  ///
  /// In en, this message translates to:
  /// **'Waiting for photos to finish uploading…'**
  String get captureWaitForUploads;

  /// No description provided for @captureNeedOneReady.
  ///
  /// In en, this message translates to:
  /// **'Add at least one photo to continue.'**
  String get captureNeedOneReady;

  /// No description provided for @captureRemovePhoto.
  ///
  /// In en, this message translates to:
  /// **'Remove photo'**
  String get captureRemovePhoto;

  /// No description provided for @capturePickerError.
  ///
  /// In en, this message translates to:
  /// **'Couldn\'t open the camera or gallery. Check photo and camera access in phone Settings.'**
  String get capturePickerError;

  /// No description provided for @captureResumeAll.
  ///
  /// In en, this message translates to:
  /// **'Resume uploads'**
  String get captureResumeAll;

  /// No description provided for @captureKeepsGoing.
  ///
  /// In en, this message translates to:
  /// **'Uploads keep going if you switch apps. If the app closes, they pick up where they left off.'**
  String get captureKeepsGoing;

  /// No description provided for @uploadQueued.
  ///
  /// In en, this message translates to:
  /// **'Waiting'**
  String get uploadQueued;

  /// No description provided for @uploadUploading.
  ///
  /// In en, this message translates to:
  /// **'Uploading {percent}'**
  String uploadUploading(String percent);

  /// No description provided for @uploadProcessing.
  ///
  /// In en, this message translates to:
  /// **'Checking photo'**
  String get uploadProcessing;

  /// No description provided for @uploadReady.
  ///
  /// In en, this message translates to:
  /// **'Ready'**
  String get uploadReady;

  /// No description provided for @uploadPaused.
  ///
  /// In en, this message translates to:
  /// **'Paused — no connection'**
  String get uploadPaused;

  /// No description provided for @uploadRetrying.
  ///
  /// In en, this message translates to:
  /// **'Retrying…'**
  String get uploadRetrying;

  /// No description provided for @uploadRejected.
  ///
  /// In en, this message translates to:
  /// **'Can\'t use this photo'**
  String get uploadRejected;

  /// No description provided for @uploadFailed.
  ///
  /// In en, this message translates to:
  /// **'Upload failed'**
  String get uploadFailed;

  /// No description provided for @uploadTapRetry.
  ///
  /// In en, this message translates to:
  /// **'Tap to retry'**
  String get uploadTapRetry;

  /// No description provided for @rejectNotAnImage.
  ///
  /// In en, this message translates to:
  /// **'This file isn\'t a photo.'**
  String get rejectNotAnImage;

  /// No description provided for @rejectTooLarge.
  ///
  /// In en, this message translates to:
  /// **'Photo is too big. Pick one under 20 MB.'**
  String get rejectTooLarge;

  /// No description provided for @rejectUnsupported.
  ///
  /// In en, this message translates to:
  /// **'This format isn\'t supported. Use JPEG, PNG, WebP or HEIC.'**
  String get rejectUnsupported;

  /// No description provided for @rejectMalware.
  ///
  /// In en, this message translates to:
  /// **'This file looked unsafe, so we deleted it.'**
  String get rejectMalware;

  /// No description provided for @tipLowResolution.
  ///
  /// In en, this message translates to:
  /// **'Photo is small. Move closer or use the main camera.'**
  String get tipLowResolution;

  /// No description provided for @tipBlurry.
  ///
  /// In en, this message translates to:
  /// **'Photo looks blurry. Hold steady and tap to focus.'**
  String get tipBlurry;

  /// No description provided for @tipTooDark.
  ///
  /// In en, this message translates to:
  /// **'Photo looks dark. Try near a window.'**
  String get tipTooDark;

  /// No description provided for @tipOverexposed.
  ///
  /// In en, this message translates to:
  /// **'Photo is too bright. Move out of direct sun.'**
  String get tipOverexposed;

  /// No description provided for @errFileTooLarge.
  ///
  /// In en, this message translates to:
  /// **'Photo is too big (max 20 MB).'**
  String get errFileTooLarge;

  /// No description provided for @errUnsupportedMediaType.
  ///
  /// In en, this message translates to:
  /// **'Use a JPEG, PNG, WebP or HEIC photo.'**
  String get errUnsupportedMediaType;

  /// No description provided for @errStorageFull.
  ///
  /// In en, this message translates to:
  /// **'Photo storage on your plan is full. Delete old photos or upgrade.'**
  String get errStorageFull;

  /// No description provided for @errFileUnreadable.
  ///
  /// In en, this message translates to:
  /// **'We couldn\'t read this photo from your phone. Pick it again.'**
  String get errFileUnreadable;

  /// No description provided for @errUploadMissing.
  ///
  /// In en, this message translates to:
  /// **'The photo didn\'t reach us. Retry the upload.'**
  String get errUploadMissing;

  /// No description provided for @errUploadExpired.
  ///
  /// In en, this message translates to:
  /// **'The upload took too long. Start it again.'**
  String get errUploadExpired;

  /// No description provided for @errMediaNotReady.
  ///
  /// In en, this message translates to:
  /// **'Some photos are still being checked. Try again in a moment.'**
  String get errMediaNotReady;

  /// No description provided for @errMediaNotFound.
  ///
  /// In en, this message translates to:
  /// **'Some photos are no longer available. Add them again.'**
  String get errMediaNotFound;

  /// No description provided for @errDraftNotReady.
  ///
  /// In en, this message translates to:
  /// **'This draft isn\'t ready yet.'**
  String get errDraftNotReady;

  /// No description provided for @errNotPublishable.
  ///
  /// In en, this message translates to:
  /// **'This product isn\'t ready to go live yet.'**
  String get errNotPublishable;

  /// No description provided for @errProductNotActive.
  ///
  /// In en, this message translates to:
  /// **'Make the product live first, then publish it to channels.'**
  String get errProductNotActive;

  /// No description provided for @errCapabilityNotSupported.
  ///
  /// In en, this message translates to:
  /// **'This channel can\'t do that.'**
  String get errCapabilityNotSupported;

  /// No description provided for @errVersionConflict.
  ///
  /// In en, this message translates to:
  /// **'Someone else changed this. We loaded the latest — check and try again.'**
  String get errVersionConflict;

  /// No description provided for @errPostLocked.
  ///
  /// In en, this message translates to:
  /// **'Scheduled posts can\'t be edited. Unschedule it first.'**
  String get errPostLocked;

  /// No description provided for @errReconnectRequired.
  ///
  /// In en, this message translates to:
  /// **'Reconnect this channel first.'**
  String get errReconnectRequired;

  /// No description provided for @errScheduleInPast.
  ///
  /// In en, this message translates to:
  /// **'Pick a time in the future.'**
  String get errScheduleInPast;

  /// No description provided for @errScheduleTooFar.
  ///
  /// In en, this message translates to:
  /// **'Posts can be scheduled up to 90 days ahead.'**
  String get errScheduleTooFar;

  /// No description provided for @errCaptionRequired.
  ///
  /// In en, this message translates to:
  /// **'Write a caption.'**
  String get errCaptionRequired;

  /// No description provided for @errCaptionTooLong.
  ///
  /// In en, this message translates to:
  /// **'This caption is too long for the channel.'**
  String get errCaptionTooLong;

  /// No description provided for @errInvalidPhotoCount.
  ///
  /// In en, this message translates to:
  /// **'Choose 1 to 6 photos.'**
  String get errInvalidPhotoCount;

  /// No description provided for @errNotFailed.
  ///
  /// In en, this message translates to:
  /// **'Only failed drafts can be retried.'**
  String get errNotFailed;

  /// No description provided for @errAiUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Our writing service is busy. Try again in a few minutes.'**
  String get errAiUnavailable;

  /// No description provided for @draftWorkingTitle.
  ///
  /// In en, this message translates to:
  /// **'Writing your listing'**
  String get draftWorkingTitle;

  /// No description provided for @draftWorkingBody.
  ///
  /// In en, this message translates to:
  /// **'Reading your photos and drafting the name, description and captions in Nepali and English. This usually takes under a minute.'**
  String get draftWorkingBody;

  /// No description provided for @draftQueued.
  ///
  /// In en, this message translates to:
  /// **'In line'**
  String get draftQueued;

  /// No description provided for @draftRunning.
  ///
  /// In en, this message translates to:
  /// **'Working on it'**
  String get draftRunning;

  /// No description provided for @draftLeaveOk.
  ///
  /// In en, this message translates to:
  /// **'You can leave this screen; we\'ll keep working. Find it later under Drafts.'**
  String get draftLeaveOk;

  /// No description provided for @draftFailedTitle.
  ///
  /// In en, this message translates to:
  /// **'We couldn\'t write this draft'**
  String get draftFailedTitle;

  /// No description provided for @draftFailedBody.
  ///
  /// In en, this message translates to:
  /// **'Our writing service had a problem. Your photos are safe.'**
  String get draftFailedBody;

  /// No description provided for @draftAppliedTitle.
  ///
  /// In en, this message translates to:
  /// **'Already saved as a product'**
  String get draftAppliedTitle;

  /// No description provided for @draftOpenProduct.
  ///
  /// In en, this message translates to:
  /// **'Open product'**
  String get draftOpenProduct;

  /// No description provided for @draftDiscarded.
  ///
  /// In en, this message translates to:
  /// **'This draft was discarded.'**
  String get draftDiscarded;

  /// No description provided for @reviewTitle.
  ///
  /// In en, this message translates to:
  /// **'Check your listing'**
  String get reviewTitle;

  /// No description provided for @reviewAiNote.
  ///
  /// In en, this message translates to:
  /// **'Written by AI from your photos. Change anything that\'s off.'**
  String get reviewAiNote;

  /// No description provided for @reviewSectionText.
  ///
  /// In en, this message translates to:
  /// **'Name and description'**
  String get reviewSectionText;

  /// No description provided for @fieldTitleNe.
  ///
  /// In en, this message translates to:
  /// **'Name (Nepali)'**
  String get fieldTitleNe;

  /// No description provided for @fieldTitleEn.
  ///
  /// In en, this message translates to:
  /// **'Name (English)'**
  String get fieldTitleEn;

  /// No description provided for @fieldDescriptionNe.
  ///
  /// In en, this message translates to:
  /// **'Description (Nepali)'**
  String get fieldDescriptionNe;

  /// No description provided for @fieldDescriptionEn.
  ///
  /// In en, this message translates to:
  /// **'Description (English)'**
  String get fieldDescriptionEn;

  /// No description provided for @validationTitleRequired.
  ///
  /// In en, this message translates to:
  /// **'Add a name in Nepali or English'**
  String get validationTitleRequired;

  /// No description provided for @reviewSectionCategory.
  ///
  /// In en, this message translates to:
  /// **'Category'**
  String get reviewSectionCategory;

  /// No description provided for @fieldCategoryHint.
  ///
  /// In en, this message translates to:
  /// **'Separate levels with /, e.g. Clothing / Kurta'**
  String get fieldCategoryHint;

  /// No description provided for @confidenceLabel.
  ///
  /// In en, this message translates to:
  /// **'{percent} sure'**
  String confidenceLabel(String percent);

  /// No description provided for @reviewSectionDetails.
  ///
  /// In en, this message translates to:
  /// **'Details'**
  String get reviewSectionDetails;

  /// No description provided for @attrPleaseCheck.
  ///
  /// In en, this message translates to:
  /// **'Please check'**
  String get attrPleaseCheck;

  /// No description provided for @attrAccept.
  ///
  /// In en, this message translates to:
  /// **'Looks right'**
  String get attrAccept;

  /// No description provided for @attrEdit.
  ///
  /// In en, this message translates to:
  /// **'Edit'**
  String get attrEdit;

  /// No description provided for @attrAccepted.
  ///
  /// In en, this message translates to:
  /// **'Checked'**
  String get attrAccepted;

  /// No description provided for @attrEdited.
  ///
  /// In en, this message translates to:
  /// **'Edited by you'**
  String get attrEdited;

  /// No description provided for @attrEditTitle.
  ///
  /// In en, this message translates to:
  /// **'Edit {name}'**
  String attrEditTitle(String name);

  /// No description provided for @actionSave.
  ///
  /// In en, this message translates to:
  /// **'Save'**
  String get actionSave;

  /// No description provided for @attrUncheckedError.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 detail still needs a check} other{{count} details still need a check}}'**
  String attrUncheckedError(int count);

  /// No description provided for @reviewSectionPrice.
  ///
  /// In en, this message translates to:
  /// **'Price and options'**
  String get reviewSectionPrice;

  /// No description provided for @reviewPriceNote.
  ///
  /// In en, this message translates to:
  /// **'Prices always come from you — AI never sets them.'**
  String get reviewPriceNote;

  /// No description provided for @fieldPrice.
  ///
  /// In en, this message translates to:
  /// **'Price (Rs)'**
  String get fieldPrice;

  /// No description provided for @fieldPriceFor.
  ///
  /// In en, this message translates to:
  /// **'Price for {variant}'**
  String fieldPriceFor(String variant);

  /// No description provided for @fieldSku.
  ///
  /// In en, this message translates to:
  /// **'SKU (optional)'**
  String get fieldSku;

  /// No description provided for @samePriceToggle.
  ///
  /// In en, this message translates to:
  /// **'Same price for all options'**
  String get samePriceToggle;

  /// No description provided for @validationPriceRequired.
  ///
  /// In en, this message translates to:
  /// **'Enter a price'**
  String get validationPriceRequired;

  /// No description provided for @validationPriceInvalid.
  ///
  /// In en, this message translates to:
  /// **'Use numbers only, e.g. 1250 or 1250.50'**
  String get validationPriceInvalid;

  /// No description provided for @validationPriceDecimals.
  ///
  /// In en, this message translates to:
  /// **'Up to 2 decimal places (paisa)'**
  String get validationPriceDecimals;

  /// No description provided for @validationPriceTooLarge.
  ///
  /// In en, this message translates to:
  /// **'That price is too high'**
  String get validationPriceTooLarge;

  /// No description provided for @optionAdd.
  ///
  /// In en, this message translates to:
  /// **'Add option (e.g. Size)'**
  String get optionAdd;

  /// No description provided for @optionName.
  ///
  /// In en, this message translates to:
  /// **'Option name'**
  String get optionName;

  /// No description provided for @optionValuesHint.
  ///
  /// In en, this message translates to:
  /// **'Values, separated by commas'**
  String get optionValuesHint;

  /// No description provided for @optionRemove.
  ///
  /// In en, this message translates to:
  /// **'Remove option'**
  String get optionRemove;

  /// No description provided for @optionValuesRequired.
  ///
  /// In en, this message translates to:
  /// **'Add at least one value for each option'**
  String get optionValuesRequired;

  /// No description provided for @variantsCount.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 variant} other{{count} variants}}'**
  String variantsCount(int count);

  /// No description provided for @tooManyVariants.
  ///
  /// In en, this message translates to:
  /// **'That makes more than 100 combinations. Remove some values.'**
  String get tooManyVariants;

  /// No description provided for @reviewSectionChecklist.
  ///
  /// In en, this message translates to:
  /// **'AI couldn\'t tell — please confirm'**
  String get reviewSectionChecklist;

  /// No description provided for @reviewSectionWarnings.
  ///
  /// In en, this message translates to:
  /// **'Things to check'**
  String get reviewSectionWarnings;

  /// No description provided for @issueClaimPrice.
  ///
  /// In en, this message translates to:
  /// **'The text mentions a price. Prices come from you; please check.'**
  String get issueClaimPrice;

  /// No description provided for @issueClaimDiscount.
  ///
  /// In en, this message translates to:
  /// **'The text mentions a discount you didn\'t give us. Remove it or make sure it\'s real.'**
  String get issueClaimDiscount;

  /// No description provided for @issueClaimStock.
  ///
  /// In en, this message translates to:
  /// **'The text talks about stock. Stock comes from your inventory; please check.'**
  String get issueClaimStock;

  /// No description provided for @issueClaimDelivery.
  ///
  /// In en, this message translates to:
  /// **'The text promises delivery terms. Make sure they\'re right.'**
  String get issueClaimDelivery;

  /// No description provided for @issueClaimWarranty.
  ///
  /// In en, this message translates to:
  /// **'The text mentions a warranty. Keep it only if you offer one.'**
  String get issueClaimWarranty;

  /// No description provided for @issueClaimAuthenticity.
  ///
  /// In en, this message translates to:
  /// **'The text says it\'s original or genuine. Keep it only if you can back it up.'**
  String get issueClaimAuthenticity;

  /// No description provided for @issueClaimOther.
  ///
  /// In en, this message translates to:
  /// **'The text makes a claim we couldn\'t verify. Please check.'**
  String get issueClaimOther;

  /// No description provided for @issueNotProductPhoto.
  ///
  /// In en, this message translates to:
  /// **'These photos may not show a product. Check them before saving.'**
  String get issueNotProductPhoto;

  /// No description provided for @issueTooLong.
  ///
  /// In en, this message translates to:
  /// **'Some text was too long and was shortened. Read it once.'**
  String get issueTooLong;

  /// No description provided for @issueInField.
  ///
  /// In en, this message translates to:
  /// **'In: {field}'**
  String issueInField(String field);

  /// No description provided for @reviewCreate.
  ///
  /// In en, this message translates to:
  /// **'Save product'**
  String get reviewCreate;

  /// No description provided for @reviewFixProblems.
  ///
  /// In en, this message translates to:
  /// **'Fix the highlighted items to continue.'**
  String get reviewFixProblems;

  /// No description provided for @productTitle.
  ///
  /// In en, this message translates to:
  /// **'Product'**
  String get productTitle;

  /// No description provided for @productStatusDraft.
  ///
  /// In en, this message translates to:
  /// **'Draft'**
  String get productStatusDraft;

  /// No description provided for @productStatusActive.
  ///
  /// In en, this message translates to:
  /// **'Live'**
  String get productStatusActive;

  /// No description provided for @productStatusArchived.
  ///
  /// In en, this message translates to:
  /// **'Archived'**
  String get productStatusArchived;

  /// No description provided for @productSaved.
  ///
  /// In en, this message translates to:
  /// **'Saved as a draft. Only you can see it.'**
  String get productSaved;

  /// No description provided for @productGoLive.
  ///
  /// In en, this message translates to:
  /// **'Go live'**
  String get productGoLive;

  /// No description provided for @productIsLive.
  ///
  /// In en, this message translates to:
  /// **'Live in your catalog'**
  String get productIsLive;

  /// No description provided for @productConfirmSection.
  ///
  /// In en, this message translates to:
  /// **'Confirm AI details'**
  String get productConfirmSection;

  /// No description provided for @productConfirmAll.
  ///
  /// In en, this message translates to:
  /// **'Confirm all'**
  String get productConfirmAll;

  /// No description provided for @productProblemPrice.
  ///
  /// In en, this message translates to:
  /// **'Every variant needs a price.'**
  String get productProblemPrice;

  /// No description provided for @productProblemAttributes.
  ///
  /// In en, this message translates to:
  /// **'Confirm the AI details below.'**
  String get productProblemAttributes;

  /// No description provided for @productProblemVariant.
  ///
  /// In en, this message translates to:
  /// **'Add at least one active variant (from the web dashboard for now).'**
  String get productProblemVariant;

  /// No description provided for @productProblemTitle.
  ///
  /// In en, this message translates to:
  /// **'Add a product name.'**
  String get productProblemTitle;

  /// No description provided for @productFix.
  ///
  /// In en, this message translates to:
  /// **'Fix'**
  String get productFix;

  /// No description provided for @productEditPrice.
  ///
  /// In en, this message translates to:
  /// **'Edit price'**
  String get productEditPrice;

  /// No description provided for @productEditTitle.
  ///
  /// In en, this message translates to:
  /// **'Edit name'**
  String get productEditTitle;

  /// No description provided for @productPrices.
  ///
  /// In en, this message translates to:
  /// **'Prices'**
  String get productPrices;

  /// No description provided for @defaultVariant.
  ///
  /// In en, this message translates to:
  /// **'Default'**
  String get defaultVariant;

  /// No description provided for @publishSection.
  ///
  /// In en, this message translates to:
  /// **'Publish to channels'**
  String get publishSection;

  /// No description provided for @publishNeedsLive.
  ///
  /// In en, this message translates to:
  /// **'Go live first to publish to channels.'**
  String get publishNeedsLive;

  /// No description provided for @publishNoChannels.
  ///
  /// In en, this message translates to:
  /// **'No shop channels connected yet. Connect Instagram, Facebook or TikTok from the web dashboard.'**
  String get publishNoChannels;

  /// No description provided for @publishAction.
  ///
  /// In en, this message translates to:
  /// **'Publish'**
  String get publishAction;

  /// No description provided for @publishSelectOne.
  ///
  /// In en, this message translates to:
  /// **'Choose at least one channel'**
  String get publishSelectOne;

  /// No description provided for @channelReconnect.
  ///
  /// In en, this message translates to:
  /// **'Reconnect'**
  String get channelReconnect;

  /// No description provided for @channelExpiredNote.
  ///
  /// In en, this message translates to:
  /// **'Connection expired'**
  String get channelExpiredNote;

  /// No description provided for @listingPending.
  ///
  /// In en, this message translates to:
  /// **'Waiting'**
  String get listingPending;

  /// No description provided for @listingPublishing.
  ///
  /// In en, this message translates to:
  /// **'Publishing…'**
  String get listingPublishing;

  /// No description provided for @listingPublished.
  ///
  /// In en, this message translates to:
  /// **'Published'**
  String get listingPublished;

  /// No description provided for @listingFailed.
  ///
  /// In en, this message translates to:
  /// **'Failed'**
  String get listingFailed;

  /// No description provided for @listingOutOfSync.
  ///
  /// In en, this message translates to:
  /// **'Out of sync'**
  String get listingOutOfSync;

  /// No description provided for @listingUnpublished.
  ///
  /// In en, this message translates to:
  /// **'Not listed'**
  String get listingUnpublished;

  /// No description provided for @listingError.
  ///
  /// In en, this message translates to:
  /// **'Reason: {code}'**
  String listingError(String code);

  /// No description provided for @reconnectTitle.
  ///
  /// In en, this message translates to:
  /// **'Reconnect {channel}'**
  String reconnectTitle(String channel);

  /// No description provided for @reconnectChannelGeneric.
  ///
  /// In en, this message translates to:
  /// **'channel'**
  String get reconnectChannelGeneric;

  /// No description provided for @reconnectBody.
  ///
  /// In en, this message translates to:
  /// **'For now, reconnect channels from the web dashboard in a browser:'**
  String get reconnectBody;

  /// No description provided for @reconnectCopied.
  ///
  /// In en, this message translates to:
  /// **'Link copied'**
  String get reconnectCopied;

  /// No description provided for @actionCopyLink.
  ///
  /// In en, this message translates to:
  /// **'Copy link'**
  String get actionCopyLink;

  /// No description provided for @postsSection.
  ///
  /// In en, this message translates to:
  /// **'Create posts'**
  String get postsSection;

  /// No description provided for @postsIntro.
  ///
  /// In en, this message translates to:
  /// **'Turn the AI captions into posts for each channel. You review before anything goes out.'**
  String get postsIntro;

  /// No description provided for @postsCreate.
  ///
  /// In en, this message translates to:
  /// **'Create drafts'**
  String get postsCreate;

  /// No description provided for @postsNoChannels.
  ///
  /// In en, this message translates to:
  /// **'No channel that can post is connected yet.'**
  String get postsNoChannels;

  /// No description provided for @postsNoDraft.
  ///
  /// In en, this message translates to:
  /// **'Posts need the AI draft this product came from.'**
  String get postsNoDraft;

  /// No description provided for @postsTitle.
  ///
  /// In en, this message translates to:
  /// **'Posts'**
  String get postsTitle;

  /// No description provided for @postStatusDraft.
  ///
  /// In en, this message translates to:
  /// **'Draft'**
  String get postStatusDraft;

  /// No description provided for @postStatusPendingApproval.
  ///
  /// In en, this message translates to:
  /// **'Waiting for approval'**
  String get postStatusPendingApproval;

  /// No description provided for @postStatusApproved.
  ///
  /// In en, this message translates to:
  /// **'Approved'**
  String get postStatusApproved;

  /// No description provided for @postStatusScheduled.
  ///
  /// In en, this message translates to:
  /// **'Scheduled {when}'**
  String postStatusScheduled(String when);

  /// No description provided for @postStatusPublishing.
  ///
  /// In en, this message translates to:
  /// **'Publishing…'**
  String get postStatusPublishing;

  /// No description provided for @postStatusPublished.
  ///
  /// In en, this message translates to:
  /// **'Published'**
  String get postStatusPublished;

  /// No description provided for @postStatusFailed.
  ///
  /// In en, this message translates to:
  /// **'Failed'**
  String get postStatusFailed;

  /// No description provided for @postStatusCancelled.
  ///
  /// In en, this message translates to:
  /// **'Cancelled'**
  String get postStatusCancelled;

  /// No description provided for @fieldCaption.
  ///
  /// In en, this message translates to:
  /// **'Caption'**
  String get fieldCaption;

  /// No description provided for @postSaveCaption.
  ///
  /// In en, this message translates to:
  /// **'Save caption'**
  String get postSaveCaption;

  /// No description provided for @postSubmit.
  ///
  /// In en, this message translates to:
  /// **'Submit'**
  String get postSubmit;

  /// No description provided for @postApprove.
  ///
  /// In en, this message translates to:
  /// **'Approve'**
  String get postApprove;

  /// No description provided for @postPublishNow.
  ///
  /// In en, this message translates to:
  /// **'Publish now'**
  String get postPublishNow;

  /// No description provided for @postSchedule.
  ///
  /// In en, this message translates to:
  /// **'Schedule'**
  String get postSchedule;

  /// No description provided for @postNeedsApprovalNote.
  ///
  /// In en, this message translates to:
  /// **'AI-written posts need an approval before they go out.'**
  String get postNeedsApprovalNote;

  /// No description provided for @postNoApprovePermission.
  ///
  /// In en, this message translates to:
  /// **'Ask the shop owner or a manager to approve this.'**
  String get postNoApprovePermission;

  /// No description provided for @postCaptionSaved.
  ///
  /// In en, this message translates to:
  /// **'Caption saved'**
  String get postCaptionSaved;

  /// No description provided for @postNotFound.
  ///
  /// In en, this message translates to:
  /// **'This post is no longer available.'**
  String get postNotFound;

  /// No description provided for @postsEmpty.
  ///
  /// In en, this message translates to:
  /// **'No posts yet.'**
  String get postsEmpty;

  /// No description provided for @draftsTitle.
  ///
  /// In en, this message translates to:
  /// **'Drafts'**
  String get draftsTitle;

  /// No description provided for @draftsNew.
  ///
  /// In en, this message translates to:
  /// **'New from photos'**
  String get draftsNew;

  /// No description provided for @draftsEmpty.
  ///
  /// In en, this message translates to:
  /// **'No drafts yet. Start with a few photos of a product.'**
  String get draftsEmpty;

  /// No description provided for @draftsIntro.
  ///
  /// In en, this message translates to:
  /// **'Pick a draft to turn into posts, or start with new photos.'**
  String get draftsIntro;

  /// No description provided for @draftStatusWorking.
  ///
  /// In en, this message translates to:
  /// **'Writing…'**
  String get draftStatusWorking;

  /// No description provided for @draftStatusReady.
  ///
  /// In en, this message translates to:
  /// **'Ready to check'**
  String get draftStatusReady;

  /// No description provided for @draftStatusFailed.
  ///
  /// In en, this message translates to:
  /// **'Failed'**
  String get draftStatusFailed;

  /// No description provided for @draftStatusApplied.
  ///
  /// In en, this message translates to:
  /// **'Saved as product'**
  String get draftStatusApplied;

  /// No description provided for @draftStatusDiscarded.
  ///
  /// In en, this message translates to:
  /// **'Discarded'**
  String get draftStatusDiscarded;

  /// No description provided for @draftUntitled.
  ///
  /// In en, this message translates to:
  /// **'Untitled draft'**
  String get draftUntitled;

  /// No description provided for @exSubjectDraft.
  ///
  /// In en, this message translates to:
  /// **'AI draft'**
  String get exSubjectDraft;

  /// No description provided for @exSubjectPost.
  ///
  /// In en, this message translates to:
  /// **'Post'**
  String get exSubjectPost;

  /// No description provided for @exSubjectProduct.
  ///
  /// In en, this message translates to:
  /// **'Product'**
  String get exSubjectProduct;

  /// No description provided for @exActionReconnect.
  ///
  /// In en, this message translates to:
  /// **'Reconnect'**
  String get exActionReconnect;

  /// No description provided for @exActionRetryPublish.
  ///
  /// In en, this message translates to:
  /// **'Retry publish'**
  String get exActionRetryPublish;

  /// No description provided for @exActionReschedule.
  ///
  /// In en, this message translates to:
  /// **'Reschedule'**
  String get exActionReschedule;

  /// No description provided for @exActionReviewPost.
  ///
  /// In en, this message translates to:
  /// **'Review post'**
  String get exActionReviewPost;

  /// No description provided for @exActionReviewDraft.
  ///
  /// In en, this message translates to:
  /// **'Review draft'**
  String get exActionReviewDraft;

  /// No description provided for @exActionRetryDraft.
  ///
  /// In en, this message translates to:
  /// **'Retry draft'**
  String get exActionRetryDraft;

  /// No description provided for @exActionConfirmAttributes.
  ///
  /// In en, this message translates to:
  /// **'Confirm details'**
  String get exActionConfirmAttributes;

  /// No description provided for @exActionDismiss.
  ///
  /// In en, this message translates to:
  /// **'Hide'**
  String get exActionDismiss;

  /// No description provided for @homeSectionCatalog.
  ///
  /// In en, this message translates to:
  /// **'Catalog'**
  String get homeSectionCatalog;

  /// No description provided for @settingsTheme.
  ///
  /// In en, this message translates to:
  /// **'Theme'**
  String get settingsTheme;

  /// No description provided for @themeLight.
  ///
  /// In en, this message translates to:
  /// **'Light'**
  String get themeLight;

  /// No description provided for @themeDark.
  ///
  /// In en, this message translates to:
  /// **'Dark'**
  String get themeDark;

  /// No description provided for @themeSystem.
  ///
  /// In en, this message translates to:
  /// **'Same as phone'**
  String get themeSystem;
}

class _AppLocalizationsDelegate extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) => <String>['en', 'ne'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {


  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en': return AppLocalizationsEn();
    case 'ne': return AppLocalizationsNe();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.'
  );
}
