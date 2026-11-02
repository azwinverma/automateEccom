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
  /// **'Commerce OS'**
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
