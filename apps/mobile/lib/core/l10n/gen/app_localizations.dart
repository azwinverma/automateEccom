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
  AppLocalizations(String locale)
    : localeName = intl.Intl.canonicalizedLocale(locale.toString());

  final String localeName;

  static AppLocalizations of(BuildContext context) {
    return Localizations.of<AppLocalizations>(context, AppLocalizations)!;
  }

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

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
  static const List<LocalizationsDelegate<dynamic>> localizationsDelegates =
      <LocalizationsDelegate<dynamic>>[
        delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
      ];

  /// A list of this localizations delegate's supported locales.
  static const List<Locale> supportedLocales = <Locale>[
    Locale('en'),
    Locale('ne'),
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

  /// No description provided for @exListingDrift.
  ///
  /// In en, this message translates to:
  /// **'Changed on a channel'**
  String get exListingDrift;

  /// No description provided for @exActionResolveDrift.
  ///
  /// In en, this message translates to:
  /// **'Choose version'**
  String get exActionResolveDrift;

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

  /// No description provided for @loginForgotPassword.
  ///
  /// In en, this message translates to:
  /// **'Forgot password?'**
  String get loginForgotPassword;

  /// No description provided for @forgotTitle.
  ///
  /// In en, this message translates to:
  /// **'Reset your password'**
  String get forgotTitle;

  /// No description provided for @forgotSubtitle.
  ///
  /// In en, this message translates to:
  /// **'Enter your account email and we\'ll send you a link to set a new password.'**
  String get forgotSubtitle;

  /// No description provided for @forgotAction.
  ///
  /// In en, this message translates to:
  /// **'Send reset link'**
  String get forgotAction;

  /// No description provided for @forgotSentTitle.
  ///
  /// In en, this message translates to:
  /// **'Check your email'**
  String get forgotSentTitle;

  /// No description provided for @forgotSentBody.
  ///
  /// In en, this message translates to:
  /// **'If an account exists for that email, a reset link is on its way. Open it on this phone or a computer. It works once and expires in 30 minutes.'**
  String get forgotSentBody;

  /// No description provided for @forgotBack.
  ///
  /// In en, this message translates to:
  /// **'Back to sign in'**
  String get forgotBack;

  /// No description provided for @exUsageLimit.
  ///
  /// In en, this message translates to:
  /// **'Plan limit'**
  String get exUsageLimit;

  /// No description provided for @exSubjectUsage.
  ///
  /// In en, this message translates to:
  /// **'{used} of {limit} used this month (see Plan on the web)'**
  String exSubjectUsage(int used, int limit);

  /// No description provided for @navOrders.
  ///
  /// In en, this message translates to:
  /// **'Orders'**
  String get navOrders;

  /// No description provided for @navInbox.
  ///
  /// In en, this message translates to:
  /// **'Inbox'**
  String get navInbox;

  /// No description provided for @ordersTitle.
  ///
  /// In en, this message translates to:
  /// **'Orders'**
  String get ordersTitle;

  /// No description provided for @ordersFilterNeedsAction.
  ///
  /// In en, this message translates to:
  /// **'To do'**
  String get ordersFilterNeedsAction;

  /// No description provided for @ordersFilterNeedsReview.
  ///
  /// In en, this message translates to:
  /// **'Needs review'**
  String get ordersFilterNeedsReview;

  /// No description provided for @ordersFilterAll.
  ///
  /// In en, this message translates to:
  /// **'All'**
  String get ordersFilterAll;

  /// No description provided for @ordersEmpty.
  ///
  /// In en, this message translates to:
  /// **'No orders here'**
  String get ordersEmpty;

  /// No description provided for @ordersEmptyBody.
  ///
  /// In en, this message translates to:
  /// **'Orders from chats, your channels and the ones you add appear here.'**
  String get ordersEmptyBody;

  /// No description provided for @orderNumber.
  ///
  /// In en, this message translates to:
  /// **'Order #{number}'**
  String orderNumber(int number);

  /// No description provided for @orderItems.
  ///
  /// In en, this message translates to:
  /// **'Items'**
  String get orderItems;

  /// No description provided for @orderTotals.
  ///
  /// In en, this message translates to:
  /// **'Total'**
  String get orderTotals;

  /// No description provided for @orderSubtotal.
  ///
  /// In en, this message translates to:
  /// **'Subtotal'**
  String get orderSubtotal;

  /// No description provided for @orderDelivery.
  ///
  /// In en, this message translates to:
  /// **'Delivery'**
  String get orderDelivery;

  /// No description provided for @orderDiscount.
  ///
  /// In en, this message translates to:
  /// **'Discount'**
  String get orderDiscount;

  /// No description provided for @orderTotal.
  ///
  /// In en, this message translates to:
  /// **'Total'**
  String get orderTotal;

  /// No description provided for @orderShipTo.
  ///
  /// In en, this message translates to:
  /// **'Deliver to'**
  String get orderShipTo;

  /// No description provided for @orderPayment.
  ///
  /// In en, this message translates to:
  /// **'Payment'**
  String get orderPayment;

  /// No description provided for @orderTimeline.
  ///
  /// In en, this message translates to:
  /// **'Timeline'**
  String get orderTimeline;

  /// No description provided for @orderNotes.
  ///
  /// In en, this message translates to:
  /// **'Notes'**
  String get orderNotes;

  /// No description provided for @orderCancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel order'**
  String get orderCancel;

  /// No description provided for @orderCancelTitle.
  ///
  /// In en, this message translates to:
  /// **'Cancel this order?'**
  String get orderCancelTitle;

  /// No description provided for @orderCancelBody.
  ///
  /// In en, this message translates to:
  /// **'Reserved stock goes back on sale. The customer isn\'t messaged automatically.'**
  String get orderCancelBody;

  /// No description provided for @orderCancelReason.
  ///
  /// In en, this message translates to:
  /// **'Reason'**
  String get orderCancelReason;

  /// No description provided for @orderCancelReasonHint.
  ///
  /// In en, this message translates to:
  /// **'e.g. customer changed their mind'**
  String get orderCancelReasonHint;

  /// No description provided for @orderCancelConfirm.
  ///
  /// In en, this message translates to:
  /// **'Cancel order'**
  String get orderCancelConfirm;

  /// No description provided for @orderCancelKeep.
  ///
  /// In en, this message translates to:
  /// **'Keep order'**
  String get orderCancelKeep;

  /// No description provided for @orderUpdated.
  ///
  /// In en, this message translates to:
  /// **'Order updated'**
  String get orderUpdated;

  /// No description provided for @orderCancelledQty.
  ///
  /// In en, this message translates to:
  /// **'{count} cancelled'**
  String orderCancelledQty(int count);

  /// No description provided for @orderUnmatchedItem.
  ///
  /// In en, this message translates to:
  /// **'Not found in your catalog'**
  String get orderUnmatchedItem;

  /// No description provided for @orderViewChat.
  ///
  /// In en, this message translates to:
  /// **'Open chat'**
  String get orderViewChat;

  /// No description provided for @orderReviewPaymentMismatch.
  ///
  /// In en, this message translates to:
  /// **'Paid amount doesn\'t match the total'**
  String get orderReviewPaymentMismatch;

  /// No description provided for @orderReviewPaidAfterCancel.
  ///
  /// In en, this message translates to:
  /// **'Paid after it was cancelled'**
  String get orderReviewPaidAfterCancel;

  /// No description provided for @orderReviewStockShort.
  ///
  /// In en, this message translates to:
  /// **'Not enough stock for this order'**
  String get orderReviewStockShort;

  /// No description provided for @orderReviewUnmatched.
  ///
  /// In en, this message translates to:
  /// **'Some items aren\'t in your catalog'**
  String get orderReviewUnmatched;

  /// No description provided for @orderReviewAddress.
  ///
  /// In en, this message translates to:
  /// **'Address is incomplete'**
  String get orderReviewAddress;

  /// No description provided for @orderStatusDraft.
  ///
  /// In en, this message translates to:
  /// **'Draft'**
  String get orderStatusDraft;

  /// No description provided for @orderStatusPendingConfirmation.
  ///
  /// In en, this message translates to:
  /// **'Awaiting confirmation'**
  String get orderStatusPendingConfirmation;

  /// No description provided for @orderStatusConfirmed.
  ///
  /// In en, this message translates to:
  /// **'Confirmed'**
  String get orderStatusConfirmed;

  /// No description provided for @orderStatusPaymentPending.
  ///
  /// In en, this message translates to:
  /// **'Awaiting payment'**
  String get orderStatusPaymentPending;

  /// No description provided for @orderStatusCodPending.
  ///
  /// In en, this message translates to:
  /// **'To pack (COD)'**
  String get orderStatusCodPending;

  /// No description provided for @orderStatusReadyToShip.
  ///
  /// In en, this message translates to:
  /// **'Ready to ship'**
  String get orderStatusReadyToShip;

  /// No description provided for @orderStatusShipped.
  ///
  /// In en, this message translates to:
  /// **'Shipped'**
  String get orderStatusShipped;

  /// No description provided for @orderStatusDelivered.
  ///
  /// In en, this message translates to:
  /// **'Delivered'**
  String get orderStatusDelivered;

  /// No description provided for @orderStatusCompleted.
  ///
  /// In en, this message translates to:
  /// **'Completed'**
  String get orderStatusCompleted;

  /// No description provided for @orderStatusCancelled.
  ///
  /// In en, this message translates to:
  /// **'Cancelled'**
  String get orderStatusCancelled;

  /// No description provided for @orderStatusDeliveryFailed.
  ///
  /// In en, this message translates to:
  /// **'Delivery failed'**
  String get orderStatusDeliveryFailed;

  /// No description provided for @orderStatusReturned.
  ///
  /// In en, this message translates to:
  /// **'Returned'**
  String get orderStatusReturned;

  /// No description provided for @orderActionConfirm.
  ///
  /// In en, this message translates to:
  /// **'Confirm order'**
  String get orderActionConfirm;

  /// No description provided for @orderActionReadyToShip.
  ///
  /// In en, this message translates to:
  /// **'Mark packed'**
  String get orderActionReadyToShip;

  /// No description provided for @orderActionShipped.
  ///
  /// In en, this message translates to:
  /// **'Mark shipped'**
  String get orderActionShipped;

  /// No description provided for @orderActionDelivered.
  ///
  /// In en, this message translates to:
  /// **'Mark delivered'**
  String get orderActionDelivered;

  /// No description provided for @orderActionCompleted.
  ///
  /// In en, this message translates to:
  /// **'Mark completed'**
  String get orderActionCompleted;

  /// No description provided for @orderActionDeliveryFailed.
  ///
  /// In en, this message translates to:
  /// **'Delivery failed'**
  String get orderActionDeliveryFailed;

  /// No description provided for @orderActionReturned.
  ///
  /// In en, this message translates to:
  /// **'Mark returned'**
  String get orderActionReturned;

  /// No description provided for @paymentCod.
  ///
  /// In en, this message translates to:
  /// **'Cash on delivery'**
  String get paymentCod;

  /// No description provided for @paymentPrepaid.
  ///
  /// In en, this message translates to:
  /// **'Prepaid'**
  String get paymentPrepaid;

  /// No description provided for @payStatusUnpaid.
  ///
  /// In en, this message translates to:
  /// **'Unpaid'**
  String get payStatusUnpaid;

  /// No description provided for @payStatusPending.
  ///
  /// In en, this message translates to:
  /// **'Waiting for payment'**
  String get payStatusPending;

  /// No description provided for @payStatusPaid.
  ///
  /// In en, this message translates to:
  /// **'Paid'**
  String get payStatusPaid;

  /// No description provided for @payStatusFailed.
  ///
  /// In en, this message translates to:
  /// **'Payment failed'**
  String get payStatusFailed;

  /// No description provided for @payStatusRefunded.
  ///
  /// In en, this message translates to:
  /// **'Refunded'**
  String get payStatusRefunded;

  /// No description provided for @payStatusCodPending.
  ///
  /// In en, this message translates to:
  /// **'To collect on delivery'**
  String get payStatusCodPending;

  /// No description provided for @payStatusCodCollected.
  ///
  /// In en, this message translates to:
  /// **'Collected by courier'**
  String get payStatusCodCollected;

  /// No description provided for @timelineCreated.
  ///
  /// In en, this message translates to:
  /// **'Order created'**
  String get timelineCreated;

  /// No description provided for @timelineImported.
  ///
  /// In en, this message translates to:
  /// **'Imported from {channel}'**
  String timelineImported(String channel);

  /// No description provided for @timelineStatus.
  ///
  /// In en, this message translates to:
  /// **'Now: {status}'**
  String timelineStatus(String status);

  /// No description provided for @timelineLinesCancelled.
  ///
  /// In en, this message translates to:
  /// **'Some items cancelled'**
  String get timelineLinesCancelled;

  /// No description provided for @timelineNote.
  ///
  /// In en, this message translates to:
  /// **'Note: {note}'**
  String timelineNote(String note);

  /// No description provided for @timelinePayment.
  ///
  /// In en, this message translates to:
  /// **'Payment received'**
  String get timelinePayment;

  /// No description provided for @timelinePaymentFailed.
  ///
  /// In en, this message translates to:
  /// **'Payment failed'**
  String get timelinePaymentFailed;

  /// No description provided for @timelinePaymentMismatch.
  ///
  /// In en, this message translates to:
  /// **'Paid amount didn\'t match'**
  String get timelinePaymentMismatch;

  /// No description provided for @timelineOther.
  ///
  /// In en, this message translates to:
  /// **'Update'**
  String get timelineOther;

  /// No description provided for @timelineByAi.
  ///
  /// In en, this message translates to:
  /// **'AI Sales Agent'**
  String get timelineByAi;

  /// No description provided for @timelineAutomatic.
  ///
  /// In en, this message translates to:
  /// **'Automatic'**
  String get timelineAutomatic;

  /// No description provided for @inboxTitle.
  ///
  /// In en, this message translates to:
  /// **'Inbox'**
  String get inboxTitle;

  /// No description provided for @inboxEmpty.
  ///
  /// In en, this message translates to:
  /// **'No open chats'**
  String get inboxEmpty;

  /// No description provided for @inboxEmptyBody.
  ///
  /// In en, this message translates to:
  /// **'Customer messages from your connected channels arrive here.'**
  String get inboxEmptyBody;

  /// No description provided for @inboxNeedsYou.
  ///
  /// In en, this message translates to:
  /// **'Needs you'**
  String get inboxNeedsYou;

  /// No description provided for @inboxYou.
  ///
  /// In en, this message translates to:
  /// **'You: {text}'**
  String inboxYou(String text);

  /// No description provided for @inboxCustomer.
  ///
  /// In en, this message translates to:
  /// **'Customer'**
  String get inboxCustomer;

  /// No description provided for @threadReplyHint.
  ///
  /// In en, this message translates to:
  /// **'Write a reply'**
  String get threadReplyHint;

  /// No description provided for @threadSend.
  ///
  /// In en, this message translates to:
  /// **'Send'**
  String get threadSend;

  /// No description provided for @threadSuggestion.
  ///
  /// In en, this message translates to:
  /// **'AI suggestion, not sent yet'**
  String get threadSuggestion;

  /// No description provided for @threadSuggestionSend.
  ///
  /// In en, this message translates to:
  /// **'Send'**
  String get threadSuggestionSend;

  /// No description provided for @threadSuggestionEdit.
  ///
  /// In en, this message translates to:
  /// **'Edit'**
  String get threadSuggestionEdit;

  /// No description provided for @threadSuggestionDiscard.
  ///
  /// In en, this message translates to:
  /// **'Discard'**
  String get threadSuggestionDiscard;

  /// No description provided for @threadEditTitle.
  ///
  /// In en, this message translates to:
  /// **'Edit before sending'**
  String get threadEditTitle;

  /// No description provided for @threadFailed.
  ///
  /// In en, this message translates to:
  /// **'Not sent'**
  String get threadFailed;

  /// No description provided for @threadRetry.
  ///
  /// In en, this message translates to:
  /// **'Retry'**
  String get threadRetry;

  /// No description provided for @threadSending.
  ///
  /// In en, this message translates to:
  /// **'Sending…'**
  String get threadSending;

  /// No description provided for @threadByAi.
  ///
  /// In en, this message translates to:
  /// **'AI'**
  String get threadByAi;

  /// No description provided for @threadHandBack.
  ///
  /// In en, this message translates to:
  /// **'Hand back to AI'**
  String get threadHandBack;

  /// No description provided for @threadHandedBack.
  ///
  /// In en, this message translates to:
  /// **'The AI will answer new messages again.'**
  String get threadHandedBack;

  /// No description provided for @threadHumanBanner.
  ///
  /// In en, this message translates to:
  /// **'You\'re handling this chat. The AI is paused.'**
  String get threadHumanBanner;

  /// No description provided for @threadEscalatedBanner.
  ///
  /// In en, this message translates to:
  /// **'The AI handed this chat to you.'**
  String get threadEscalatedBanner;

  /// No description provided for @draftCollecting.
  ///
  /// In en, this message translates to:
  /// **'Taking an order: waiting for {field}'**
  String draftCollecting(String field);

  /// No description provided for @draftAwaitingConfirmation.
  ///
  /// In en, this message translates to:
  /// **'Order summary sent. Waiting for the customer\'s yes.'**
  String get draftAwaitingConfirmation;

  /// No description provided for @draftConfirmed.
  ///
  /// In en, this message translates to:
  /// **'Order created from this chat'**
  String get draftConfirmed;

  /// No description provided for @stockSection.
  ///
  /// In en, this message translates to:
  /// **'Stock'**
  String get stockSection;

  /// No description provided for @stockAvailable.
  ///
  /// In en, this message translates to:
  /// **'{count} available'**
  String stockAvailable(int count);

  /// No description provided for @stockDetail.
  ///
  /// In en, this message translates to:
  /// **'{onHand} on shelf · {reserved} reserved'**
  String stockDetail(int onHand, int reserved);

  /// No description provided for @stockUntracked.
  ///
  /// In en, this message translates to:
  /// **'Not tracked yet'**
  String get stockUntracked;

  /// No description provided for @stockLow.
  ///
  /// In en, this message translates to:
  /// **'Low'**
  String get stockLow;

  /// No description provided for @stockReceive.
  ///
  /// In en, this message translates to:
  /// **'Receive stock'**
  String get stockReceive;

  /// No description provided for @stockQuantity.
  ///
  /// In en, this message translates to:
  /// **'Quantity received'**
  String get stockQuantity;

  /// No description provided for @stockReceived.
  ///
  /// In en, this message translates to:
  /// **'Stock updated'**
  String get stockReceived;

  /// No description provided for @stockSave.
  ///
  /// In en, this message translates to:
  /// **'Add'**
  String get stockSave;

  /// No description provided for @exActionReply.
  ///
  /// In en, this message translates to:
  /// **'Reply'**
  String get exActionReply;

  /// No description provided for @exActionCheckPayment.
  ///
  /// In en, this message translates to:
  /// **'Check payment'**
  String get exActionCheckPayment;

  /// No description provided for @exActionFixStock.
  ///
  /// In en, this message translates to:
  /// **'Fix stock'**
  String get exActionFixStock;

  /// No description provided for @exActionReviewOrder.
  ///
  /// In en, this message translates to:
  /// **'Review order'**
  String get exActionReviewOrder;

  /// No description provided for @exSubjectConversation.
  ///
  /// In en, this message translates to:
  /// **'A customer chat'**
  String get exSubjectConversation;

  /// No description provided for @exSubjectOrder.
  ///
  /// In en, this message translates to:
  /// **'Order #{number}'**
  String exSubjectOrder(int number);

  /// No description provided for @commonCancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get commonCancel;

  /// No description provided for @draftFieldProduct.
  ///
  /// In en, this message translates to:
  /// **'product'**
  String get draftFieldProduct;

  /// No description provided for @draftFieldVariant.
  ///
  /// In en, this message translates to:
  /// **'size/colour'**
  String get draftFieldVariant;

  /// No description provided for @draftFieldQuantity.
  ///
  /// In en, this message translates to:
  /// **'quantity'**
  String get draftFieldQuantity;

  /// No description provided for @draftFieldName.
  ///
  /// In en, this message translates to:
  /// **'name'**
  String get draftFieldName;

  /// No description provided for @draftFieldPhone.
  ///
  /// In en, this message translates to:
  /// **'phone number'**
  String get draftFieldPhone;

  /// No description provided for @draftFieldDistrict.
  ///
  /// In en, this message translates to:
  /// **'district'**
  String get draftFieldDistrict;

  /// No description provided for @draftFieldMunicipality.
  ///
  /// In en, this message translates to:
  /// **'municipality'**
  String get draftFieldMunicipality;

  /// No description provided for @draftFieldWard.
  ///
  /// In en, this message translates to:
  /// **'ward'**
  String get draftFieldWard;

  /// No description provided for @draftFieldArea.
  ///
  /// In en, this message translates to:
  /// **'area'**
  String get draftFieldArea;

  /// No description provided for @draftFieldPayment.
  ///
  /// In en, this message translates to:
  /// **'payment choice'**
  String get draftFieldPayment;

  /// No description provided for @deliveryTitle.
  ///
  /// In en, this message translates to:
  /// **'Delivery'**
  String get deliveryTitle;

  /// No description provided for @deliveryChooseCourier.
  ///
  /// In en, this message translates to:
  /// **'Choose how to send it'**
  String get deliveryChooseCourier;

  /// No description provided for @deliveryWhyDefault.
  ///
  /// In en, this message translates to:
  /// **'Recommended: your default courier'**
  String get deliveryWhyDefault;

  /// No description provided for @deliveryWhyCheapest.
  ///
  /// In en, this message translates to:
  /// **'Recommended: the cheapest option that fits this parcel'**
  String get deliveryWhyCheapest;

  /// No description provided for @deliveryWhyOnly.
  ///
  /// In en, this message translates to:
  /// **'The only option that can take this parcel'**
  String get deliveryWhyOnly;

  /// No description provided for @deliveryRecommended.
  ///
  /// In en, this message translates to:
  /// **'Recommended'**
  String get deliveryRecommended;

  /// No description provided for @deliveryOwnRider.
  ///
  /// In en, this message translates to:
  /// **'You arrange it and record the updates'**
  String get deliveryOwnRider;

  /// No description provided for @deliveryEta.
  ///
  /// In en, this message translates to:
  /// **'{min}–{max} days'**
  String deliveryEta(int min, int max);

  /// No description provided for @deliveryNoCouriers.
  ///
  /// In en, this message translates to:
  /// **'No courier is set up yet. Add one in Settings on the web.'**
  String get deliveryNoCouriers;

  /// No description provided for @deliveryCollectAmount.
  ///
  /// In en, this message translates to:
  /// **'The courier collects {amount} at the door'**
  String deliveryCollectAmount(String amount);

  /// No description provided for @deliveryTrackingOptional.
  ///
  /// In en, this message translates to:
  /// **'Tracking number (optional)'**
  String get deliveryTrackingOptional;

  /// No description provided for @deliveryCourierNameOptional.
  ///
  /// In en, this message translates to:
  /// **'Courier or rider name (optional)'**
  String get deliveryCourierNameOptional;

  /// No description provided for @deliveryBook.
  ///
  /// In en, this message translates to:
  /// **'Book courier'**
  String get deliveryBook;

  /// No description provided for @deliveryBooked.
  ///
  /// In en, this message translates to:
  /// **'Courier booked'**
  String get deliveryBooked;

  /// No description provided for @deliveryTracking.
  ///
  /// In en, this message translates to:
  /// **'Tracking {number}'**
  String deliveryTracking(String number);

  /// No description provided for @deliveryCopy.
  ///
  /// In en, this message translates to:
  /// **'Copy tracking number'**
  String get deliveryCopy;

  /// No description provided for @deliveryCopied.
  ///
  /// In en, this message translates to:
  /// **'Tracking number copied'**
  String get deliveryCopied;

  /// No description provided for @deliveryCod.
  ///
  /// In en, this message translates to:
  /// **'Cash to collect: {amount}'**
  String deliveryCod(String amount);

  /// No description provided for @deliveryNothingToCollect.
  ///
  /// In en, this message translates to:
  /// **'Paid already: nothing to collect'**
  String get deliveryNothingToCollect;

  /// No description provided for @deliveryHistory.
  ///
  /// In en, this message translates to:
  /// **'Parcel history'**
  String get deliveryHistory;

  /// No description provided for @deliveryLateUpdate.
  ///
  /// In en, this message translates to:
  /// **'Late update from the courier (not applied)'**
  String get deliveryLateUpdate;

  /// No description provided for @deliveryAttempt.
  ///
  /// In en, this message translates to:
  /// **'Attempt {n}: {reason}'**
  String deliveryAttempt(int n, String reason);

  /// No description provided for @deliveryCustomerReply.
  ///
  /// In en, this message translates to:
  /// **'Customer replied: “{text}”'**
  String deliveryCustomerReply(String text);

  /// No description provided for @deliveryUpdated.
  ///
  /// In en, this message translates to:
  /// **'Delivery updated'**
  String get deliveryUpdated;

  /// No description provided for @deliveryActionPickup.
  ///
  /// In en, this message translates to:
  /// **'Request pickup'**
  String get deliveryActionPickup;

  /// No description provided for @deliveryActionCancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel booking'**
  String get deliveryActionCancel;

  /// No description provided for @deliveryActionReattempt.
  ///
  /// In en, this message translates to:
  /// **'Ask the courier to try again'**
  String get deliveryActionReattempt;

  /// No description provided for @deliveryActionReturn.
  ///
  /// In en, this message translates to:
  /// **'Return to my shop'**
  String get deliveryActionReturn;

  /// No description provided for @deliveryActionReceivedBack.
  ///
  /// In en, this message translates to:
  /// **'Parcel is back: restock items'**
  String get deliveryActionReceivedBack;

  /// No description provided for @deliveryActionUpdateStatus.
  ///
  /// In en, this message translates to:
  /// **'Update status'**
  String get deliveryActionUpdateStatus;

  /// No description provided for @deliveryActionRefresh.
  ///
  /// In en, this message translates to:
  /// **'Check the courier for updates'**
  String get deliveryActionRefresh;

  /// No description provided for @deliveryCancelTitle.
  ///
  /// In en, this message translates to:
  /// **'Cancel this booking?'**
  String get deliveryCancelTitle;

  /// No description provided for @deliveryCancelBody.
  ///
  /// In en, this message translates to:
  /// **'The courier won\'t collect this parcel. You can book again.'**
  String get deliveryCancelBody;

  /// No description provided for @deliveryKeep.
  ///
  /// In en, this message translates to:
  /// **'Keep'**
  String get deliveryKeep;

  /// No description provided for @deliveryConfirm.
  ///
  /// In en, this message translates to:
  /// **'Confirm'**
  String get deliveryConfirm;

  /// No description provided for @deliveryReattemptTitle.
  ///
  /// In en, this message translates to:
  /// **'Try delivering again'**
  String get deliveryReattemptTitle;

  /// No description provided for @deliveryReattemptNote.
  ///
  /// In en, this message translates to:
  /// **'Note for the courier (time, landmark)'**
  String get deliveryReattemptNote;

  /// No description provided for @deliverySend.
  ///
  /// In en, this message translates to:
  /// **'Send'**
  String get deliverySend;

  /// No description provided for @deliveryReturnTitle.
  ///
  /// In en, this message translates to:
  /// **'Return the parcel to your shop?'**
  String get deliveryReturnTitle;

  /// No description provided for @deliveryReturnBody.
  ///
  /// In en, this message translates to:
  /// **'The courier brings it back and no cash is collected.'**
  String get deliveryReturnBody;

  /// No description provided for @deliveryStatusTitle.
  ///
  /// In en, this message translates to:
  /// **'What happened to the parcel?'**
  String get deliveryStatusTitle;

  /// No description provided for @deliveryFailureReason.
  ///
  /// In en, this message translates to:
  /// **'Why did the delivery fail?'**
  String get deliveryFailureReason;

  /// No description provided for @deliveryReasonRequired.
  ///
  /// In en, this message translates to:
  /// **'Choose a reason to continue'**
  String get deliveryReasonRequired;

  /// No description provided for @deliveryNote.
  ///
  /// In en, this message translates to:
  /// **'Note (optional)'**
  String get deliveryNote;

  /// No description provided for @deliverySave.
  ///
  /// In en, this message translates to:
  /// **'Save'**
  String get deliverySave;

  /// No description provided for @shipStatusBooked.
  ///
  /// In en, this message translates to:
  /// **'Booked'**
  String get shipStatusBooked;

  /// No description provided for @shipStatusPickupRequested.
  ///
  /// In en, this message translates to:
  /// **'Pickup requested'**
  String get shipStatusPickupRequested;

  /// No description provided for @shipStatusPickedUp.
  ///
  /// In en, this message translates to:
  /// **'Picked up'**
  String get shipStatusPickedUp;

  /// No description provided for @shipStatusInTransit.
  ///
  /// In en, this message translates to:
  /// **'On the way'**
  String get shipStatusInTransit;

  /// No description provided for @shipStatusOutForDelivery.
  ///
  /// In en, this message translates to:
  /// **'Out for delivery'**
  String get shipStatusOutForDelivery;

  /// No description provided for @shipStatusDelivered.
  ///
  /// In en, this message translates to:
  /// **'Delivered'**
  String get shipStatusDelivered;

  /// No description provided for @shipStatusDeliveryFailed.
  ///
  /// In en, this message translates to:
  /// **'Delivery failed'**
  String get shipStatusDeliveryFailed;

  /// No description provided for @shipStatusReattemptRequested.
  ///
  /// In en, this message translates to:
  /// **'Trying again'**
  String get shipStatusReattemptRequested;

  /// No description provided for @shipStatusReturning.
  ///
  /// In en, this message translates to:
  /// **'Coming back to shop'**
  String get shipStatusReturning;

  /// No description provided for @shipStatusReturnedToOrigin.
  ///
  /// In en, this message translates to:
  /// **'Back at shop'**
  String get shipStatusReturnedToOrigin;

  /// No description provided for @shipStatusCancelled.
  ///
  /// In en, this message translates to:
  /// **'Cancelled'**
  String get shipStatusCancelled;

  /// No description provided for @shipStatusLost.
  ///
  /// In en, this message translates to:
  /// **'Lost by courier'**
  String get shipStatusLost;

  /// No description provided for @failReasonCustomerUnreachable.
  ///
  /// In en, this message translates to:
  /// **'Couldn\'t reach the customer\'s phone'**
  String get failReasonCustomerUnreachable;

  /// No description provided for @failReasonCustomerUnavailable.
  ///
  /// In en, this message translates to:
  /// **'Nobody was there to receive it'**
  String get failReasonCustomerUnavailable;

  /// No description provided for @failReasonCustomerRefused.
  ///
  /// In en, this message translates to:
  /// **'Customer refused the parcel'**
  String get failReasonCustomerRefused;

  /// No description provided for @failReasonAddressIncorrect.
  ///
  /// In en, this message translates to:
  /// **'Rider couldn\'t find the address'**
  String get failReasonAddressIncorrect;

  /// No description provided for @failReasonCodNotReady.
  ///
  /// In en, this message translates to:
  /// **'Cash wasn\'t ready'**
  String get failReasonCodNotReady;

  /// No description provided for @failReasonRescheduled.
  ///
  /// In en, this message translates to:
  /// **'Customer asked for another time'**
  String get failReasonRescheduled;

  /// No description provided for @failReasonOther.
  ///
  /// In en, this message translates to:
  /// **'Other problem'**
  String get failReasonOther;

  /// No description provided for @recoveryOpen.
  ///
  /// In en, this message translates to:
  /// **'Call the customer'**
  String get recoveryOpen;

  /// No description provided for @recoveryAwaitingCustomer.
  ///
  /// In en, this message translates to:
  /// **'We messaged the customer, waiting for a reply'**
  String get recoveryAwaitingCustomer;

  /// No description provided for @recoveryCustomerReplied.
  ///
  /// In en, this message translates to:
  /// **'Customer replied: ask the courier to try again'**
  String get recoveryCustomerReplied;

  /// No description provided for @recoveryReattemptRequested.
  ///
  /// In en, this message translates to:
  /// **'Courier asked to try again'**
  String get recoveryReattemptRequested;

  /// No description provided for @recoveryReturning.
  ///
  /// In en, this message translates to:
  /// **'Coming back to your shop'**
  String get recoveryReturning;

  /// No description provided for @recoveryResolved.
  ///
  /// In en, this message translates to:
  /// **'Resolved'**
  String get recoveryResolved;

  /// No description provided for @recoveryEscalated.
  ///
  /// In en, this message translates to:
  /// **'No reply: please call the customer'**
  String get recoveryEscalated;

  /// No description provided for @codTitle.
  ///
  /// In en, this message translates to:
  /// **'Cash on delivery'**
  String get codTitle;

  /// No description provided for @codWithCouriers.
  ///
  /// In en, this message translates to:
  /// **'With couriers'**
  String get codWithCouriers;

  /// No description provided for @codWithCouriersBody.
  ///
  /// In en, this message translates to:
  /// **'Cash from {count} delivered parcels not received yet'**
  String codWithCouriersBody(int count);

  /// No description provided for @codOverTwoWeeks.
  ///
  /// In en, this message translates to:
  /// **'{amount} waiting more than 2 weeks'**
  String codOverTwoWeeks(String amount);

  /// No description provided for @codNeedsReview.
  ///
  /// In en, this message translates to:
  /// **'{count} courier statements need checking'**
  String codNeedsReview(int count);

  /// No description provided for @codAwaitingTitle.
  ///
  /// In en, this message translates to:
  /// **'Cash still with couriers'**
  String get codAwaitingTitle;

  /// No description provided for @codAwaitingEmpty.
  ///
  /// In en, this message translates to:
  /// **'No cash waiting: couriers have paid for every delivered parcel.'**
  String get codAwaitingEmpty;

  /// No description provided for @codDaysWaiting.
  ///
  /// In en, this message translates to:
  /// **'{days} days waiting'**
  String codDaysWaiting(int days);

  /// No description provided for @codOrderCourier.
  ///
  /// In en, this message translates to:
  /// **'Order #{number} · {courier}'**
  String codOrderCourier(int number, String courier);

  /// No description provided for @codSettlementsTitle.
  ///
  /// In en, this message translates to:
  /// **'Courier statements'**
  String get codSettlementsTitle;

  /// No description provided for @codSettlementsEmpty.
  ///
  /// In en, this message translates to:
  /// **'No courier statements yet.'**
  String get codSettlementsEmpty;

  /// No description provided for @codStatusNeedsReview.
  ///
  /// In en, this message translates to:
  /// **'Needs checking'**
  String get codStatusNeedsReview;

  /// No description provided for @codStatusReconciled.
  ///
  /// In en, this message translates to:
  /// **'Matches: confirm once paid'**
  String get codStatusReconciled;

  /// No description provided for @codStatusConfirmed.
  ///
  /// In en, this message translates to:
  /// **'Received'**
  String get codStatusConfirmed;

  /// No description provided for @codIssues.
  ///
  /// In en, this message translates to:
  /// **'{count} lines don\'t match. Check them on the web.'**
  String codIssues(int count);

  /// No description provided for @codConfirmReceived.
  ///
  /// In en, this message translates to:
  /// **'Confirm money received'**
  String get codConfirmReceived;

  /// No description provided for @codConfirmed.
  ///
  /// In en, this message translates to:
  /// **'Marked as received'**
  String get codConfirmed;

  /// No description provided for @returnsTitle.
  ///
  /// In en, this message translates to:
  /// **'Returns'**
  String get returnsTitle;

  /// No description provided for @returnsStart.
  ///
  /// In en, this message translates to:
  /// **'Start a return'**
  String get returnsStart;

  /// No description provided for @returnsNone.
  ///
  /// In en, this message translates to:
  /// **'No returns for this order yet.'**
  String get returnsNone;

  /// No description provided for @returnStatusRequested.
  ///
  /// In en, this message translates to:
  /// **'To decide'**
  String get returnStatusRequested;

  /// No description provided for @returnStatusApproved.
  ///
  /// In en, this message translates to:
  /// **'Approved'**
  String get returnStatusApproved;

  /// No description provided for @returnStatusRejected.
  ///
  /// In en, this message translates to:
  /// **'Rejected'**
  String get returnStatusRejected;

  /// No description provided for @returnStatusInTransit.
  ///
  /// In en, this message translates to:
  /// **'On its way back'**
  String get returnStatusInTransit;

  /// No description provided for @returnStatusReceived.
  ///
  /// In en, this message translates to:
  /// **'Received'**
  String get returnStatusReceived;

  /// No description provided for @returnStatusInspected.
  ///
  /// In en, this message translates to:
  /// **'Checked'**
  String get returnStatusInspected;

  /// No description provided for @returnStatusRefunded.
  ///
  /// In en, this message translates to:
  /// **'Refunded'**
  String get returnStatusRefunded;

  /// No description provided for @returnStatusExchanged.
  ///
  /// In en, this message translates to:
  /// **'Exchanged'**
  String get returnStatusExchanged;

  /// No description provided for @returnStatusClosed.
  ///
  /// In en, this message translates to:
  /// **'Closed'**
  String get returnStatusClosed;

  /// No description provided for @returnStatusCancelled.
  ///
  /// In en, this message translates to:
  /// **'Cancelled'**
  String get returnStatusCancelled;

  /// No description provided for @returnResolutionRefund.
  ///
  /// In en, this message translates to:
  /// **'Refund'**
  String get returnResolutionRefund;

  /// No description provided for @returnResolutionExchange.
  ///
  /// In en, this message translates to:
  /// **'Exchange'**
  String get returnResolutionExchange;

  /// No description provided for @returnRefundDue.
  ///
  /// In en, this message translates to:
  /// **'Refund due: {amount}'**
  String returnRefundDue(String amount);

  /// No description provided for @returnReasonSizeSmall.
  ///
  /// In en, this message translates to:
  /// **'Too small'**
  String get returnReasonSizeSmall;

  /// No description provided for @returnReasonSizeLarge.
  ///
  /// In en, this message translates to:
  /// **'Too large'**
  String get returnReasonSizeLarge;

  /// No description provided for @returnReasonColourDifferent.
  ///
  /// In en, this message translates to:
  /// **'Colour looks different'**
  String get returnReasonColourDifferent;

  /// No description provided for @returnReasonQualityDefect.
  ///
  /// In en, this message translates to:
  /// **'Quality defect'**
  String get returnReasonQualityDefect;

  /// No description provided for @returnReasonDamagedInTransit.
  ///
  /// In en, this message translates to:
  /// **'Damaged in delivery'**
  String get returnReasonDamagedInTransit;

  /// No description provided for @returnReasonNotAsDescribed.
  ///
  /// In en, this message translates to:
  /// **'Not as described'**
  String get returnReasonNotAsDescribed;

  /// No description provided for @returnReasonChangedMind.
  ///
  /// In en, this message translates to:
  /// **'Changed their mind'**
  String get returnReasonChangedMind;

  /// No description provided for @returnReasonLateDelivery.
  ///
  /// In en, this message translates to:
  /// **'Arrived late'**
  String get returnReasonLateDelivery;

  /// No description provided for @returnReasonWrongItem.
  ///
  /// In en, this message translates to:
  /// **'Wrong item sent'**
  String get returnReasonWrongItem;

  /// No description provided for @returnReasonOther.
  ///
  /// In en, this message translates to:
  /// **'Other'**
  String get returnReasonOther;

  /// No description provided for @returnConditionResellable.
  ///
  /// In en, this message translates to:
  /// **'Can be sold again'**
  String get returnConditionResellable;

  /// No description provided for @returnConditionDamaged.
  ///
  /// In en, this message translates to:
  /// **'Damaged'**
  String get returnConditionDamaged;

  /// No description provided for @returnConditionMissing.
  ///
  /// In en, this message translates to:
  /// **'Missing'**
  String get returnConditionMissing;

  /// No description provided for @returnConditionUsed.
  ///
  /// In en, this message translates to:
  /// **'Used'**
  String get returnConditionUsed;

  /// No description provided for @returnLineItem.
  ///
  /// In en, this message translates to:
  /// **'{qty} × {title}'**
  String returnLineItem(int qty, String title);

  /// No description provided for @returnLineCondition.
  ///
  /// In en, this message translates to:
  /// **'Checked: {condition}'**
  String returnLineCondition(String condition);

  /// No description provided for @returnLineExchange.
  ///
  /// In en, this message translates to:
  /// **'Exchange for {title}'**
  String returnLineExchange(String title);

  /// No description provided for @returnSheetTitle.
  ///
  /// In en, this message translates to:
  /// **'Return from order #{number}'**
  String returnSheetTitle(int number);

  /// No description provided for @returnPickItems.
  ///
  /// In en, this message translates to:
  /// **'Which items are coming back?'**
  String get returnPickItems;

  /// No description provided for @returnQty.
  ///
  /// In en, this message translates to:
  /// **'Quantity'**
  String get returnQty;

  /// No description provided for @returnReason.
  ///
  /// In en, this message translates to:
  /// **'Reason'**
  String get returnReason;

  /// No description provided for @returnResolution.
  ///
  /// In en, this message translates to:
  /// **'What does the customer want?'**
  String get returnResolution;

  /// No description provided for @returnExchangeFor.
  ///
  /// In en, this message translates to:
  /// **'Exchange for'**
  String get returnExchangeFor;

  /// No description provided for @returnNoExchangeOption.
  ///
  /// In en, this message translates to:
  /// **'No other option at the same price'**
  String get returnNoExchangeOption;

  /// No description provided for @returnOutOfStock.
  ///
  /// In en, this message translates to:
  /// **'{title} (out of stock)'**
  String returnOutOfStock(String title);

  /// No description provided for @returnCheck.
  ///
  /// In en, this message translates to:
  /// **'Check against policy'**
  String get returnCheck;

  /// No description provided for @returnSubmit.
  ///
  /// In en, this message translates to:
  /// **'Create return'**
  String get returnSubmit;

  /// No description provided for @returnCreated.
  ///
  /// In en, this message translates to:
  /// **'Return created'**
  String get returnCreated;

  /// No description provided for @returnNothingLeft.
  ///
  /// In en, this message translates to:
  /// **'Everything from this order is already being returned.'**
  String get returnNothingLeft;

  /// No description provided for @returnPickReason.
  ///
  /// In en, this message translates to:
  /// **'Pick a reason for each item'**
  String get returnPickReason;

  /// No description provided for @returnPickExchange.
  ///
  /// In en, this message translates to:
  /// **'Pick what to exchange each item for'**
  String get returnPickExchange;

  /// No description provided for @returnCheckOrderDelivered.
  ///
  /// In en, this message translates to:
  /// **'The order hasn\'t been delivered yet'**
  String get returnCheckOrderDelivered;

  /// No description provided for @returnCheckWindow.
  ///
  /// In en, this message translates to:
  /// **'Outside the {days}-day return window'**
  String returnCheckWindow(int days);

  /// No description provided for @returnCheckWindowPlain.
  ///
  /// In en, this message translates to:
  /// **'Outside the return window'**
  String get returnCheckWindowPlain;

  /// No description provided for @returnCheckFinalSale.
  ///
  /// In en, this message translates to:
  /// **'Final sale item'**
  String get returnCheckFinalSale;

  /// No description provided for @returnCheckEvidence.
  ///
  /// In en, this message translates to:
  /// **'A photo is needed for this reason'**
  String get returnCheckEvidence;

  /// No description provided for @returnCheckQuantity.
  ///
  /// In en, this message translates to:
  /// **'More than can be returned'**
  String get returnCheckQuantity;

  /// No description provided for @returnCheckResolution.
  ///
  /// In en, this message translates to:
  /// **'Your return policy doesn\'t allow this'**
  String get returnCheckResolution;

  /// No description provided for @returnCheckExchangeProduct.
  ///
  /// In en, this message translates to:
  /// **'An exchange must be the same product at the same price'**
  String get returnCheckExchangeProduct;

  /// No description provided for @returnCheckExchangeStock.
  ///
  /// In en, this message translates to:
  /// **'The replacement is out of stock'**
  String get returnCheckExchangeStock;

  /// No description provided for @returnCheckGeneric.
  ///
  /// In en, this message translates to:
  /// **'Doesn\'t meet your policy'**
  String get returnCheckGeneric;

  /// No description provided for @returnWarningsTitle.
  ///
  /// In en, this message translates to:
  /// **'Outside your policy. You can still create it; approving will need a reason.'**
  String get returnWarningsTitle;

  /// No description provided for @returnBlockedTitle.
  ///
  /// In en, this message translates to:
  /// **'This return can\'t be created'**
  String get returnBlockedTitle;

  /// No description provided for @returnAllOk.
  ///
  /// In en, this message translates to:
  /// **'Within your return policy'**
  String get returnAllOk;

  /// No description provided for @returnDetailTitle.
  ///
  /// In en, this message translates to:
  /// **'Return {number}'**
  String returnDetailTitle(String number);

  /// No description provided for @returnChecksTitle.
  ///
  /// In en, this message translates to:
  /// **'Policy checks'**
  String get returnChecksTitle;

  /// No description provided for @returnSignalsTitle.
  ///
  /// In en, this message translates to:
  /// **'Worth knowing'**
  String get returnSignalsTitle;

  /// No description provided for @returnSignalFrequent.
  ///
  /// In en, this message translates to:
  /// **'{count} returns in the last {days} days'**
  String returnSignalFrequent(int count, int days);

  /// No description provided for @returnSignalRate.
  ///
  /// In en, this message translates to:
  /// **'Returned {returned} of {orders} orders in {days} days'**
  String returnSignalRate(int returned, int orders, int days);

  /// No description provided for @returnSignalValue.
  ///
  /// In en, this message translates to:
  /// **'Higher value than this shop\'s usual orders'**
  String get returnSignalValue;

  /// No description provided for @returnSignalGeneric.
  ///
  /// In en, this message translates to:
  /// **'Unusual for this shop'**
  String get returnSignalGeneric;

  /// No description provided for @returnItemsTitle.
  ///
  /// In en, this message translates to:
  /// **'Items'**
  String get returnItemsTitle;

  /// No description provided for @returnPickupTitle.
  ///
  /// In en, this message translates to:
  /// **'Pickup'**
  String get returnPickupTitle;

  /// No description provided for @returnRefundsTitle.
  ///
  /// In en, this message translates to:
  /// **'Refunds'**
  String get returnRefundsTitle;

  /// No description provided for @returnOverrideNote.
  ///
  /// In en, this message translates to:
  /// **'Approved outside policy: {reason}'**
  String returnOverrideNote(String reason);

  /// No description provided for @returnRejectedNote.
  ///
  /// In en, this message translates to:
  /// **'Rejected: {reason}'**
  String returnRejectedNote(String reason);

  /// No description provided for @refundPending.
  ///
  /// In en, this message translates to:
  /// **'Waiting for a manager\'s approval'**
  String get refundPending;

  /// No description provided for @refundStatusSucceeded.
  ///
  /// In en, this message translates to:
  /// **'Sent'**
  String get refundStatusSucceeded;

  /// No description provided for @refundStatusFailed.
  ///
  /// In en, this message translates to:
  /// **'Failed'**
  String get refundStatusFailed;

  /// No description provided for @refundStatusRejected.
  ///
  /// In en, this message translates to:
  /// **'Not approved'**
  String get refundStatusRejected;

  /// No description provided for @refundStatusProcessing.
  ///
  /// In en, this message translates to:
  /// **'Processing'**
  String get refundStatusProcessing;

  /// No description provided for @refundLine.
  ///
  /// In en, this message translates to:
  /// **'{amount} · {method}'**
  String refundLine(String amount, String method);

  /// No description provided for @refundMethodOriginal.
  ///
  /// In en, this message translates to:
  /// **'Back to the original payment'**
  String get refundMethodOriginal;

  /// No description provided for @refundMethodEsewa.
  ///
  /// In en, this message translates to:
  /// **'eSewa'**
  String get refundMethodEsewa;

  /// No description provided for @refundMethodKhalti.
  ///
  /// In en, this message translates to:
  /// **'Khalti'**
  String get refundMethodKhalti;

  /// No description provided for @refundMethodFonepay.
  ///
  /// In en, this message translates to:
  /// **'Fonepay'**
  String get refundMethodFonepay;

  /// No description provided for @refundMethodBank.
  ///
  /// In en, this message translates to:
  /// **'Bank transfer'**
  String get refundMethodBank;

  /// No description provided for @refundMethodCash.
  ///
  /// In en, this message translates to:
  /// **'Cash'**
  String get refundMethodCash;

  /// No description provided for @refundMethodOther.
  ///
  /// In en, this message translates to:
  /// **'Other'**
  String get refundMethodOther;

  /// No description provided for @returnActionApprove.
  ///
  /// In en, this message translates to:
  /// **'Approve'**
  String get returnActionApprove;

  /// No description provided for @returnActionReject.
  ///
  /// In en, this message translates to:
  /// **'Reject'**
  String get returnActionReject;

  /// No description provided for @returnActionCancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel return'**
  String get returnActionCancel;

  /// No description provided for @returnActionReceived.
  ///
  /// In en, this message translates to:
  /// **'Mark as received'**
  String get returnActionReceived;

  /// No description provided for @returnActionInspect.
  ///
  /// In en, this message translates to:
  /// **'Check items'**
  String get returnActionInspect;

  /// No description provided for @returnActionRefund.
  ///
  /// In en, this message translates to:
  /// **'Refund'**
  String get returnActionRefund;

  /// No description provided for @returnPickupOnWeb.
  ///
  /// In en, this message translates to:
  /// **'Book the pickup from the web app.'**
  String get returnPickupOnWeb;

  /// No description provided for @returnApproveTitle.
  ///
  /// In en, this message translates to:
  /// **'Approve this return?'**
  String get returnApproveTitle;

  /// No description provided for @returnOverrideHint.
  ///
  /// In en, this message translates to:
  /// **'This return is outside your policy. Say why you\'re approving it.'**
  String get returnOverrideHint;

  /// No description provided for @returnReasonLabel.
  ///
  /// In en, this message translates to:
  /// **'Reason'**
  String get returnReasonLabel;

  /// No description provided for @returnReasonRequired.
  ///
  /// In en, this message translates to:
  /// **'A reason is needed'**
  String get returnReasonRequired;

  /// No description provided for @returnRejectTitle.
  ///
  /// In en, this message translates to:
  /// **'Reject this return?'**
  String get returnRejectTitle;

  /// No description provided for @returnRejectLabel.
  ///
  /// In en, this message translates to:
  /// **'Reason (the customer sees this)'**
  String get returnRejectLabel;

  /// No description provided for @returnCancelTitle.
  ///
  /// In en, this message translates to:
  /// **'Cancel this return?'**
  String get returnCancelTitle;

  /// No description provided for @returnCancelBody.
  ///
  /// In en, this message translates to:
  /// **'Any replacement held for it goes back on sale.'**
  String get returnCancelBody;

  /// No description provided for @returnReceivedTitle.
  ///
  /// In en, this message translates to:
  /// **'Has the item reached you?'**
  String get returnReceivedTitle;

  /// No description provided for @returnReceivedBody.
  ///
  /// In en, this message translates to:
  /// **'Check it next to decide the refund.'**
  String get returnReceivedBody;

  /// No description provided for @returnInspectTitle.
  ///
  /// In en, this message translates to:
  /// **'Check returned items'**
  String get returnInspectTitle;

  /// No description provided for @returnRestock.
  ///
  /// In en, this message translates to:
  /// **'Put back on sale'**
  String get returnRestock;

  /// No description provided for @returnRestockOnlyResellable.
  ///
  /// In en, this message translates to:
  /// **'Only items that can be sold again go back on sale'**
  String get returnRestockOnlyResellable;

  /// No description provided for @returnInspectSave.
  ///
  /// In en, this message translates to:
  /// **'Save check'**
  String get returnInspectSave;

  /// No description provided for @returnPickCondition.
  ///
  /// In en, this message translates to:
  /// **'Pick a condition for each item'**
  String get returnPickCondition;

  /// No description provided for @refundTitle.
  ///
  /// In en, this message translates to:
  /// **'Refund the customer'**
  String get refundTitle;

  /// No description provided for @refundAmount.
  ///
  /// In en, this message translates to:
  /// **'Amount (Rs)'**
  String get refundAmount;

  /// No description provided for @refundMax.
  ///
  /// In en, this message translates to:
  /// **'Up to {amount}'**
  String refundMax(String amount);

  /// No description provided for @refundTooMuch.
  ///
  /// In en, this message translates to:
  /// **'More than the customer paid'**
  String get refundTooMuch;

  /// No description provided for @refundMethod.
  ///
  /// In en, this message translates to:
  /// **'How'**
  String get refundMethod;

  /// No description provided for @refundReference.
  ///
  /// In en, this message translates to:
  /// **'Reference (optional)'**
  String get refundReference;

  /// No description provided for @refundSend.
  ///
  /// In en, this message translates to:
  /// **'Refund'**
  String get refundSend;

  /// No description provided for @returnDone.
  ///
  /// In en, this message translates to:
  /// **'Return updated'**
  String get returnDone;

  /// No description provided for @returnsTabToDecide.
  ///
  /// In en, this message translates to:
  /// **'To decide'**
  String get returnsTabToDecide;

  /// No description provided for @returnsTabInProgress.
  ///
  /// In en, this message translates to:
  /// **'In progress'**
  String get returnsTabInProgress;

  /// No description provided for @returnsTabToRefund.
  ///
  /// In en, this message translates to:
  /// **'To refund'**
  String get returnsTabToRefund;

  /// No description provided for @returnsTabDone.
  ///
  /// In en, this message translates to:
  /// **'Done'**
  String get returnsTabDone;

  /// No description provided for @returnsTabCount.
  ///
  /// In en, this message translates to:
  /// **'{label} ({count})'**
  String returnsTabCount(String label, int count);

  /// No description provided for @returnsEmpty.
  ///
  /// In en, this message translates to:
  /// **'Nothing here.'**
  String get returnsEmpty;

  /// No description provided for @returnsListItem.
  ///
  /// In en, this message translates to:
  /// **'{number} · Order #{order}'**
  String returnsListItem(String number, int order);

  /// No description provided for @returnsHomeCard.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =1{1 return to decide} other{{count} returns to decide}}'**
  String returnsHomeCard(int count);

  /// No description provided for @returnsHomeCardBody.
  ///
  /// In en, this message translates to:
  /// **'Approve or reject customer returns.'**
  String get returnsHomeCardBody;

  /// No description provided for @ccStateRunning.
  ///
  /// In en, this message translates to:
  /// **'Your store is running.'**
  String get ccStateRunning;

  /// No description provided for @ccStateWaiting.
  ///
  /// In en, this message translates to:
  /// **'A few things are waiting for you.'**
  String get ccStateWaiting;

  /// No description provided for @ccStateAttention.
  ///
  /// In en, this message translates to:
  /// **'Something needs you now.'**
  String get ccStateAttention;

  /// No description provided for @ccModeAssisted.
  ///
  /// In en, this message translates to:
  /// **'Assisted mode'**
  String get ccModeAssisted;

  /// No description provided for @ccModeSmart.
  ///
  /// In en, this message translates to:
  /// **'Smart mode'**
  String get ccModeSmart;

  /// No description provided for @ccModeAutopilot.
  ///
  /// In en, this message translates to:
  /// **'Autopilot mode'**
  String get ccModeAutopilot;

  /// No description provided for @ccPeriod.
  ///
  /// In en, this message translates to:
  /// **'Last 7 days'**
  String get ccPeriod;

  /// No description provided for @ccOrders.
  ///
  /// In en, this message translates to:
  /// **'Orders'**
  String get ccOrders;

  /// No description provided for @ccRevenue.
  ///
  /// In en, this message translates to:
  /// **'Sales'**
  String get ccRevenue;

  /// No description provided for @ccAiMessages.
  ///
  /// In en, this message translates to:
  /// **'AI replies'**
  String get ccAiMessages;

  /// No description provided for @ccDelivered.
  ///
  /// In en, this message translates to:
  /// **'Delivered'**
  String get ccDelivered;

  /// No description provided for @ccInTransit.
  ///
  /// In en, this message translates to:
  /// **'On the way'**
  String get ccInTransit;

  /// No description provided for @ccReturns.
  ///
  /// In en, this message translates to:
  /// **'Returns'**
  String get ccReturns;

  /// No description provided for @ccFeedLink.
  ///
  /// In en, this message translates to:
  /// **'See what ran automatically'**
  String get ccFeedLink;

  /// No description provided for @ccWorkflowsLink.
  ///
  /// In en, this message translates to:
  /// **'Workflows'**
  String get ccWorkflowsLink;

  /// No description provided for @approvalsTitle.
  ///
  /// In en, this message translates to:
  /// **'Waiting for approval'**
  String get approvalsTitle;

  /// No description provided for @approvalsEmpty.
  ///
  /// In en, this message translates to:
  /// **'Nothing is waiting for your approval.'**
  String get approvalsEmpty;

  /// No description provided for @approvalsApprove.
  ///
  /// In en, this message translates to:
  /// **'Approve'**
  String get approvalsApprove;

  /// No description provided for @approvalsReject.
  ///
  /// In en, this message translates to:
  /// **'Reject'**
  String get approvalsReject;

  /// No description provided for @approvalsRejectTitle.
  ///
  /// In en, this message translates to:
  /// **'Reject this step?'**
  String get approvalsRejectTitle;

  /// No description provided for @approvalsNote.
  ///
  /// In en, this message translates to:
  /// **'Note (optional)'**
  String get approvalsNote;

  /// No description provided for @approvalsCancel.
  ///
  /// In en, this message translates to:
  /// **'Keep it'**
  String get approvalsCancel;

  /// No description provided for @approvalsManagersOnly.
  ///
  /// In en, this message translates to:
  /// **'Only managers can approve automation.'**
  String get approvalsManagersOnly;

  /// No description provided for @approvalsDone.
  ///
  /// In en, this message translates to:
  /// **'Done.'**
  String get approvalsDone;

  /// No description provided for @autoActionNotifySeller.
  ///
  /// In en, this message translates to:
  /// **'Tell you'**
  String get autoActionNotifySeller;

  /// No description provided for @autoActionAddOrderNote.
  ///
  /// In en, this message translates to:
  /// **'Add an order note'**
  String get autoActionAddOrderNote;

  /// No description provided for @autoActionSendCustomerMessage.
  ///
  /// In en, this message translates to:
  /// **'Message the customer'**
  String get autoActionSendCustomerMessage;

  /// No description provided for @autoActionSendReviewRequest.
  ///
  /// In en, this message translates to:
  /// **'Ask for a review'**
  String get autoActionSendReviewRequest;

  /// No description provided for @autoActionBookCourier.
  ///
  /// In en, this message translates to:
  /// **'Book a courier'**
  String get autoActionBookCourier;

  /// No description provided for @autoActionRequestPickup.
  ///
  /// In en, this message translates to:
  /// **'Request pickup'**
  String get autoActionRequestPickup;

  /// No description provided for @autoActionRequestReattempt.
  ///
  /// In en, this message translates to:
  /// **'Ask the courier to try again'**
  String get autoActionRequestReattempt;

  /// No description provided for @autoActionApproveReturn.
  ///
  /// In en, this message translates to:
  /// **'Approve a return'**
  String get autoActionApproveReturn;

  /// No description provided for @autoActionSendAiReply.
  ///
  /// In en, this message translates to:
  /// **'Send an AI reply'**
  String get autoActionSendAiReply;

  /// No description provided for @autoActionIssueRefund.
  ///
  /// In en, this message translates to:
  /// **'Refund the customer'**
  String get autoActionIssueRefund;

  /// No description provided for @autoActionContinue.
  ///
  /// In en, this message translates to:
  /// **'Continue the workflow'**
  String get autoActionContinue;

  /// No description provided for @autoActionOther.
  ///
  /// In en, this message translates to:
  /// **'Automated step'**
  String get autoActionOther;

  /// No description provided for @ruleAssisted.
  ///
  /// In en, this message translates to:
  /// **'Your shop is in Assisted mode'**
  String get ruleAssisted;

  /// No description provided for @ruleR2Off.
  ///
  /// In en, this message translates to:
  /// **'This kind of action isn\'t switched on'**
  String get ruleR2Off;

  /// No description provided for @ruleAboveLimit.
  ///
  /// In en, this message translates to:
  /// **'Above your limit'**
  String get ruleAboveLimit;

  /// No description provided for @ruleNotSure.
  ///
  /// In en, this message translates to:
  /// **'Not sure enough'**
  String get ruleNotSure;

  /// No description provided for @ruleHighRisk.
  ///
  /// In en, this message translates to:
  /// **'Always needs a person'**
  String get ruleHighRisk;

  /// No description provided for @ruleBlocked.
  ///
  /// In en, this message translates to:
  /// **'Not possible right now'**
  String get ruleBlocked;

  /// No description provided for @ruleApprovalStep.
  ///
  /// In en, this message translates to:
  /// **'The workflow asks for your OK'**
  String get ruleApprovalStep;

  /// No description provided for @ruleRanSmart.
  ///
  /// In en, this message translates to:
  /// **'Ran automatically (Smart mode)'**
  String get ruleRanSmart;

  /// No description provided for @ruleRanAutopilot.
  ///
  /// In en, this message translates to:
  /// **'Ran automatically (Autopilot mode)'**
  String get ruleRanAutopilot;

  /// No description provided for @ruleRanEnabled.
  ///
  /// In en, this message translates to:
  /// **'Ran automatically: you switched this on'**
  String get ruleRanEnabled;

  /// No description provided for @ruleNotice.
  ///
  /// In en, this message translates to:
  /// **'Just a notice'**
  String get ruleNotice;

  /// No description provided for @feedTitle.
  ///
  /// In en, this message translates to:
  /// **'What ran automatically'**
  String get feedTitle;

  /// No description provided for @feedEmpty.
  ///
  /// In en, this message translates to:
  /// **'Nothing ran automatically in the last 7 days.'**
  String get feedEmpty;

  /// No description provided for @workflowsTitle.
  ///
  /// In en, this message translates to:
  /// **'Workflows'**
  String get workflowsTitle;

  /// No description provided for @workflowsEmpty.
  ///
  /// In en, this message translates to:
  /// **'No workflows yet. Create one on the web.'**
  String get workflowsEmpty;

  /// No description provided for @wfStatusDraft.
  ///
  /// In en, this message translates to:
  /// **'Off'**
  String get wfStatusDraft;

  /// No description provided for @wfStatusActive.
  ///
  /// In en, this message translates to:
  /// **'On'**
  String get wfStatusActive;

  /// No description provided for @wfStatusPaused.
  ///
  /// In en, this message translates to:
  /// **'Paused'**
  String get wfStatusPaused;

  /// No description provided for @wfBroke.
  ///
  /// In en, this message translates to:
  /// **'Paused after repeated failures'**
  String get wfBroke;

  /// No description provided for @wfTurnOn.
  ///
  /// In en, this message translates to:
  /// **'Turn on'**
  String get wfTurnOn;

  /// No description provided for @wfTurnOff.
  ///
  /// In en, this message translates to:
  /// **'Pause'**
  String get wfTurnOff;

  /// No description provided for @wfEditOnWeb.
  ///
  /// In en, this message translates to:
  /// **'Edit workflows on the web.'**
  String get wfEditOnWeb;

  /// No description provided for @wfManagersOnly.
  ///
  /// In en, this message translates to:
  /// **'Only managers can turn workflows on or off.'**
  String get wfManagersOnly;

  /// No description provided for @ccDoneAuto.
  ///
  /// In en, this message translates to:
  /// **'{count} done automatically'**
  String ccDoneAuto(int count);

  /// No description provided for @ccDoneTeam.
  ///
  /// In en, this message translates to:
  /// **'{count} done by your team'**
  String ccDoneTeam(int count);

  /// No description provided for @ccShare.
  ///
  /// In en, this message translates to:
  /// **'{percent} automatic'**
  String ccShare(String percent);

  /// No description provided for @ccNeedsAttention.
  ///
  /// In en, this message translates to:
  /// **'{count, plural, =0{Nothing needs you} =1{1 thing needs you} other{{count} things need you}}'**
  String ccNeedsAttention(int count);

  /// No description provided for @approvalsOrder.
  ///
  /// In en, this message translates to:
  /// **'Order #{number}'**
  String approvalsOrder(int number);

  /// No description provided for @approvalsWhy.
  ///
  /// In en, this message translates to:
  /// **'Waiting: {reason}'**
  String approvalsWhy(String reason);

  /// No description provided for @wfRuns.
  ///
  /// In en, this message translates to:
  /// **'{done} done · {waiting} in progress · {failed} failed'**
  String wfRuns(int done, int waiting, int failed);

  /// No description provided for @apsTitle.
  ///
  /// In en, this message translates to:
  /// **'Autopilot Score'**
  String get apsTitle;

  /// No description provided for @apsNotEnough.
  ///
  /// In en, this message translates to:
  /// **'Not enough activity yet'**
  String get apsNotEnough;

  /// No description provided for @apsCapNotEnough.
  ///
  /// In en, this message translates to:
  /// **'not enough activity'**
  String get apsCapNotEnough;

  /// No description provided for @apsWindow.
  ///
  /// In en, this message translates to:
  /// **'Last {days} days'**
  String apsWindow(int days);

  /// No description provided for @apsCounts.
  ///
  /// In en, this message translates to:
  /// **'Automatic {a} · Failed {f} · By your team {m}'**
  String apsCounts(int a, int f, int m);

  /// No description provided for @apsExcluded.
  ///
  /// In en, this message translates to:
  /// **'{count} not counted: {reason}'**
  String apsExcluded(int count, String reason);

  /// No description provided for @apsExclAboveThreshold.
  ///
  /// In en, this message translates to:
  /// **'Needed approval by your rules'**
  String get apsExclAboveThreshold;

  /// No description provided for @apsExclNotInPlan.
  ///
  /// In en, this message translates to:
  /// **'Not in your plan'**
  String get apsExclNotInPlan;

  /// No description provided for @apsExclNoCapability.
  ///
  /// In en, this message translates to:
  /// **'Not possible on this channel'**
  String get apsExclNoCapability;

  /// No description provided for @apsExclOther.
  ///
  /// In en, this message translates to:
  /// **'Other reasons'**
  String get apsExclOther;

  /// No description provided for @apsHoursSaved.
  ///
  /// In en, this message translates to:
  /// **'About {hours} hours saved (estimated)'**
  String apsHoursSaved(String hours);

  /// No description provided for @apsCapCustomerReplies.
  ///
  /// In en, this message translates to:
  /// **'Customer replies'**
  String get apsCapCustomerReplies;

  /// No description provided for @apsCapOrderCapture.
  ///
  /// In en, this message translates to:
  /// **'Order capture'**
  String get apsCapOrderCapture;

  /// No description provided for @apsCapShipmentCreation.
  ///
  /// In en, this message translates to:
  /// **'Booking couriers'**
  String get apsCapShipmentCreation;

  /// No description provided for @apsCapPickupRequests.
  ///
  /// In en, this message translates to:
  /// **'Pickup requests'**
  String get apsCapPickupRequests;

  /// No description provided for @apsCapDeliveryNotifications.
  ///
  /// In en, this message translates to:
  /// **'Delivery messages'**
  String get apsCapDeliveryNotifications;

  /// No description provided for @apsCapDeliveryRecovery.
  ///
  /// In en, this message translates to:
  /// **'Failed delivery follow-up'**
  String get apsCapDeliveryRecovery;

  /// No description provided for @apsCapReturns.
  ///
  /// In en, this message translates to:
  /// **'Returns'**
  String get apsCapReturns;

  /// No description provided for @apsCapRefunds.
  ///
  /// In en, this message translates to:
  /// **'Refunds'**
  String get apsCapRefunds;

  /// No description provided for @apsCapMarketing.
  ///
  /// In en, this message translates to:
  /// **'Marketing'**
  String get apsCapMarketing;

  /// No description provided for @apsCapOther.
  ///
  /// In en, this message translates to:
  /// **'Other work'**
  String get apsCapOther;

  /// No description provided for @recsTitle.
  ///
  /// In en, this message translates to:
  /// **'Suggestions'**
  String get recsTitle;

  /// No description provided for @recSetMode.
  ///
  /// In en, this message translates to:
  /// **'Switch to Smart mode'**
  String get recSetMode;

  /// No description provided for @recActivateTemplate.
  ///
  /// In en, this message translates to:
  /// **'Turn on “Book a courier when packed”'**
  String get recActivateTemplate;

  /// No description provided for @recEnableR2.
  ///
  /// In en, this message translates to:
  /// **'Let reattempts run by themselves'**
  String get recEnableR2;

  /// No description provided for @recEnableReturnAuto.
  ///
  /// In en, this message translates to:
  /// **'Auto-approve small returns'**
  String get recEnableReturnAuto;

  /// No description provided for @recEnableNotifications.
  ///
  /// In en, this message translates to:
  /// **'Message customers about deliveries'**
  String get recEnableNotifications;

  /// No description provided for @recPlanUpgrade.
  ///
  /// In en, this message translates to:
  /// **'Available on a higher plan'**
  String get recPlanUpgrade;

  /// No description provided for @recCourierSelection.
  ///
  /// In en, this message translates to:
  /// **'Let Courier Brain pick couriers'**
  String get recCourierSelection;

  /// No description provided for @recRestock.
  ///
  /// In en, this message translates to:
  /// **'Restock {title}'**
  String recRestock(String title);

  /// No description provided for @recOther.
  ///
  /// In en, this message translates to:
  /// **'Suggestion'**
  String get recOther;

  /// No description provided for @recWhyManualGap.
  ///
  /// In en, this message translates to:
  /// **'Your team did {manual} of {eligible} {capability} by hand in 30 days'**
  String recWhyManualGap(String manual, String eligible, String capability);

  /// No description provided for @recWhyCourier.
  ///
  /// In en, this message translates to:
  /// **'Another courier delivered {theirs}% vs {ours}% to {destination} ({n} parcels)'**
  String recWhyCourier(
    String theirs,
    String ours,
    String destination,
    String n,
  );

  /// No description provided for @recWhyRestock.
  ///
  /// In en, this message translates to:
  /// **'{sold} sold in 30 days, {available} left (about {days} days)'**
  String recWhyRestock(String sold, String available, String days);

  /// No description provided for @recConfidenceHigh.
  ///
  /// In en, this message translates to:
  /// **'High confidence'**
  String get recConfidenceHigh;

  /// No description provided for @recConfidenceMedium.
  ///
  /// In en, this message translates to:
  /// **'Medium confidence'**
  String get recConfidenceMedium;

  /// No description provided for @recImpactScore.
  ///
  /// In en, this message translates to:
  /// **'Could raise this to {score}'**
  String recImpactScore(String score);

  /// No description provided for @recImpactCourier.
  ///
  /// In en, this message translates to:
  /// **'+{points} points delivery success'**
  String recImpactCourier(String points);

  /// No description provided for @recAccept.
  ///
  /// In en, this message translates to:
  /// **'Apply'**
  String get recAccept;

  /// No description provided for @recDismiss.
  ///
  /// In en, this message translates to:
  /// **'Dismiss'**
  String get recDismiss;

  /// No description provided for @recDismissTitle.
  ///
  /// In en, this message translates to:
  /// **'Why dismiss this?'**
  String get recDismissTitle;

  /// No description provided for @recDismissReason.
  ///
  /// In en, this message translates to:
  /// **'Reason'**
  String get recDismissReason;

  /// No description provided for @recCancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get recCancel;

  /// No description provided for @recManagersOnly.
  ///
  /// In en, this message translates to:
  /// **'Only managers can apply this'**
  String get recManagersOnly;

  /// No description provided for @recApplied.
  ///
  /// In en, this message translates to:
  /// **'Done'**
  String get recApplied;

  /// No description provided for @recDismissed.
  ///
  /// In en, this message translates to:
  /// **'Dismissed'**
  String get recDismissed;

  /// No description provided for @riskTitle.
  ///
  /// In en, this message translates to:
  /// **'Delivery risk'**
  String get riskTitle;

  /// No description provided for @riskLevelLow.
  ///
  /// In en, this message translates to:
  /// **'Low risk'**
  String get riskLevelLow;

  /// No description provided for @riskLevelMedium.
  ///
  /// In en, this message translates to:
  /// **'Check before sending'**
  String get riskLevelMedium;

  /// No description provided for @riskLevelHigher.
  ///
  /// In en, this message translates to:
  /// **'Higher delivery risk'**
  String get riskLevelHigher;

  /// No description provided for @riskActionOk.
  ///
  /// In en, this message translates to:
  /// **'Fine to send as cash on delivery'**
  String get riskActionOk;

  /// No description provided for @riskActionVerifyPhone.
  ///
  /// In en, this message translates to:
  /// **'Call to confirm the order'**
  String get riskActionVerifyPhone;

  /// No description provided for @riskActionPartialAdvance.
  ///
  /// In en, this message translates to:
  /// **'Ask for a part payment first'**
  String get riskActionPartialAdvance;

  /// No description provided for @riskActionManualReview.
  ///
  /// In en, this message translates to:
  /// **'Review before packing'**
  String get riskActionManualReview;

  /// No description provided for @riskFactorHistory.
  ///
  /// In en, this message translates to:
  /// **'Delivered {delivered}, failed {failed} before'**
  String riskFactorHistory(String delivered, String failed);

  /// No description provided for @riskFactorNewCustomer.
  ///
  /// In en, this message translates to:
  /// **'First order with you'**
  String get riskFactorNewCustomer;

  /// No description provided for @riskFactorReturns.
  ///
  /// In en, this message translates to:
  /// **'{returns} returns before'**
  String riskFactorReturns(String returns);

  /// No description provided for @riskFactorAddressMissing.
  ///
  /// In en, this message translates to:
  /// **'Address incomplete'**
  String get riskFactorAddressMissing;

  /// No description provided for @riskFactorAddressPartial.
  ///
  /// In en, this message translates to:
  /// **'Some address details missing'**
  String get riskFactorAddressPartial;

  /// No description provided for @riskFactorOrderValue.
  ///
  /// In en, this message translates to:
  /// **'{ratio}× your usual order'**
  String riskFactorOrderValue(String ratio);

  /// No description provided for @riskFactorRoute.
  ///
  /// In en, this message translates to:
  /// **'{rate}% failed deliveries to {district}'**
  String riskFactorRoute(String rate, String district);

  /// No description provided for @riskFairness.
  ///
  /// In en, this message translates to:
  /// **'Based only on this customer\'s history with your shop, the address and order value. Never on name, gender, religion, caste or ethnicity.'**
  String get riskFairness;

  /// No description provided for @riskOverridden.
  ///
  /// In en, this message translates to:
  /// **'You changed this: {reason}'**
  String riskOverridden(String reason);

  /// No description provided for @riskDisputed.
  ///
  /// In en, this message translates to:
  /// **'Customer disputes this: {note}'**
  String riskDisputed(String note);

  /// No description provided for @riskOverride.
  ///
  /// In en, this message translates to:
  /// **'Change level'**
  String get riskOverride;

  /// No description provided for @riskOverrideTitle.
  ///
  /// In en, this message translates to:
  /// **'Change the risk level'**
  String get riskOverrideTitle;

  /// No description provided for @riskOverrideReason.
  ///
  /// In en, this message translates to:
  /// **'Why (at least 3 characters)'**
  String get riskOverrideReason;

  /// No description provided for @riskSave.
  ///
  /// In en, this message translates to:
  /// **'Save'**
  String get riskSave;

  /// No description provided for @riskDispute.
  ///
  /// In en, this message translates to:
  /// **'Customer disputes this'**
  String get riskDispute;

  /// No description provided for @riskDisputeTitle.
  ///
  /// In en, this message translates to:
  /// **'Record the customer\'s dispute'**
  String get riskDisputeTitle;

  /// No description provided for @riskDisputeNote.
  ///
  /// In en, this message translates to:
  /// **'What the customer says'**
  String get riskDisputeNote;

  /// No description provided for @riskUpdated.
  ///
  /// In en, this message translates to:
  /// **'Updated'**
  String get riskUpdated;

  /// No description provided for @riskCancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get riskCancel;

  /// No description provided for @pbTitle.
  ///
  /// In en, this message translates to:
  /// **'Product Brain'**
  String get pbTitle;

  /// No description provided for @pbDemand.
  ///
  /// In en, this message translates to:
  /// **'About {rate} a day, from {days} days in stock'**
  String pbDemand(String rate, int days);

  /// No description provided for @pbUnits.
  ///
  /// In en, this message translates to:
  /// **'Sold {d7} in 7 days · {d30} in 30 · {d90} in 90'**
  String pbUnits(int d7, int d30, int d90);

  /// No description provided for @pbStock.
  ///
  /// In en, this message translates to:
  /// **'{n} available · about {days} days left'**
  String pbStock(int n, String days);

  /// No description provided for @pbStockOnly.
  ///
  /// In en, this message translates to:
  /// **'{n} available'**
  String pbStockOnly(int n);

  /// No description provided for @pbStockouts.
  ///
  /// In en, this message translates to:
  /// **'Sold out {n} times in the last 90 days'**
  String pbStockouts(int n);

  /// No description provided for @pbRiskOut.
  ///
  /// In en, this message translates to:
  /// **'Sold out'**
  String get pbRiskOut;

  /// No description provided for @pbRiskHigh.
  ///
  /// In en, this message translates to:
  /// **'Runs out soon'**
  String get pbRiskHigh;

  /// No description provided for @pbRiskMedium.
  ///
  /// In en, this message translates to:
  /// **'Running low'**
  String get pbRiskMedium;

  /// No description provided for @pbRiskLow.
  ///
  /// In en, this message translates to:
  /// **'Enough stock'**
  String get pbRiskLow;

  /// No description provided for @pbMargin.
  ///
  /// In en, this message translates to:
  /// **'Margin {pct}% at today\'s price and cost'**
  String pbMargin(String pct);

  /// No description provided for @pbContribution.
  ///
  /// In en, this message translates to:
  /// **'Profit per unit: {amount}'**
  String pbContribution(String amount);

  /// No description provided for @pbContributionPartial.
  ///
  /// In en, this message translates to:
  /// **'Profit per unit: {amount} (some costs not included)'**
  String pbContributionPartial(String amount);

  /// No description provided for @pbReturnRate.
  ///
  /// In en, this message translates to:
  /// **'Returned: {pct}% of delivered'**
  String pbReturnRate(String pct);

  /// No description provided for @pbTopReason.
  ///
  /// In en, this message translates to:
  /// **'Most common reason: {reason}'**
  String pbTopReason(String reason);

  /// No description provided for @pbFitSmall.
  ///
  /// In en, this message translates to:
  /// **'Customers are told it runs small (you confirmed)'**
  String get pbFitSmall;

  /// No description provided for @pbFitLarge.
  ///
  /// In en, this message translates to:
  /// **'Customers are told it runs large (you confirmed)'**
  String get pbFitLarge;

  /// No description provided for @pbCompleteness.
  ///
  /// In en, this message translates to:
  /// **'{pct}% of this profile has data'**
  String pbCompleteness(String pct);

  /// No description provided for @niNeedsContentMetrics.
  ///
  /// In en, this message translates to:
  /// **'Channel and content results arrive with content tracking.'**
  String get niNeedsContentMetrics;

  /// No description provided for @niNeeds12Months.
  ///
  /// In en, this message translates to:
  /// **'Seasonality needs a year of sales.'**
  String get niNeeds12Months;

  /// No description provided for @niNoPromotions.
  ///
  /// In en, this message translates to:
  /// **'No promotions yet to learn from.'**
  String get niNoPromotions;

  /// No description provided for @niNotEnoughDaysInStock.
  ///
  /// In en, this message translates to:
  /// **'Not enough days in stock to estimate demand.'**
  String get niNotEnoughDaysInStock;

  /// No description provided for @niNoSales.
  ///
  /// In en, this message translates to:
  /// **'No sales in the last 90 days.'**
  String get niNoSales;

  /// No description provided for @niStockNotTracked.
  ///
  /// In en, this message translates to:
  /// **'Stock isn\'t tracked for this product.'**
  String get niStockNotTracked;

  /// No description provided for @niCostNotSet.
  ///
  /// In en, this message translates to:
  /// **'Add a cost to see margin and profit.'**
  String get niCostNotSet;

  /// No description provided for @niNotEnoughSales.
  ///
  /// In en, this message translates to:
  /// **'Profit per unit needs at least 5 sales.'**
  String get niNotEnoughSales;

  /// No description provided for @niNoDeliveredSales.
  ///
  /// In en, this message translates to:
  /// **'No delivered sales yet, so no return rate.'**
  String get niNoDeliveredSales;

  /// No description provided for @niOther.
  ///
  /// In en, this message translates to:
  /// **'Some data isn\'t available yet.'**
  String get niOther;

  /// No description provided for @profitTitle.
  ///
  /// In en, this message translates to:
  /// **'Profit, last {days} days'**
  String profitTitle(int days);

  /// No description provided for @profitRevenue.
  ///
  /// In en, this message translates to:
  /// **'Sales {amount}'**
  String profitRevenue(String amount);

  /// No description provided for @profitContribution.
  ///
  /// In en, this message translates to:
  /// **'Profit before fixed costs {amount}'**
  String profitContribution(String amount);

  /// No description provided for @profitMargin.
  ///
  /// In en, this message translates to:
  /// **'Margin {pct}%'**
  String profitMargin(String pct);

  /// No description provided for @profitGaps.
  ///
  /// In en, this message translates to:
  /// **'{n} items not included: {list}'**
  String profitGaps(int n, String list);

  /// No description provided for @pcPackaging.
  ///
  /// In en, this message translates to:
  /// **'packaging'**
  String get pcPackaging;

  /// No description provided for @pcAds.
  ///
  /// In en, this message translates to:
  /// **'ad spend'**
  String get pcAds;

  /// No description provided for @pcCogs.
  ///
  /// In en, this message translates to:
  /// **'cost of goods'**
  String get pcCogs;

  /// No description provided for @pcPaymentFees.
  ///
  /// In en, this message translates to:
  /// **'payment fees'**
  String get pcPaymentFees;

  /// No description provided for @pcChannelFees.
  ///
  /// In en, this message translates to:
  /// **'channel fees'**
  String get pcChannelFees;

  /// No description provided for @pcCourier.
  ///
  /// In en, this message translates to:
  /// **'courier cost'**
  String get pcCourier;

  /// No description provided for @pcReturnShipping.
  ///
  /// In en, this message translates to:
  /// **'return shipping'**
  String get pcReturnShipping;

  /// No description provided for @pcFailedDelivery.
  ///
  /// In en, this message translates to:
  /// **'failed deliveries'**
  String get pcFailedDelivery;

  /// No description provided for @pcOther.
  ///
  /// In en, this message translates to:
  /// **'other costs'**
  String get pcOther;

  /// No description provided for @recFitNoteSmall.
  ///
  /// In en, this message translates to:
  /// **'Tell customers {title} runs small'**
  String recFitNoteSmall(String title);

  /// No description provided for @recFitNoteLarge.
  ///
  /// In en, this message translates to:
  /// **'Tell customers {title} runs large'**
  String recFitNoteLarge(String title);

  /// No description provided for @recReviewPhotos.
  ///
  /// In en, this message translates to:
  /// **'Check the photos of {title}'**
  String recReviewPhotos(String title);

  /// No description provided for @recReviewDescription.
  ///
  /// In en, this message translates to:
  /// **'Check the description of {title}'**
  String recReviewDescription(String title);

  /// No description provided for @recReviewQuality.
  ///
  /// In en, this message translates to:
  /// **'Check the quality of {title} with your supplier'**
  String recReviewQuality(String title);

  /// No description provided for @recReviewPacking.
  ///
  /// In en, this message translates to:
  /// **'Check how {title} is packed'**
  String recReviewPacking(String title);

  /// No description provided for @recReviewReturns.
  ///
  /// In en, this message translates to:
  /// **'Look into returns of {title}'**
  String recReviewReturns(String title);

  /// No description provided for @recWhyReturns.
  ///
  /// In en, this message translates to:
  /// **'{returned} of {sold} returned ({rate}%; shop average {baseline}%)'**
  String recWhyReturns(
    String returned,
    String sold,
    String rate,
    String baseline,
  );

  /// No description provided for @recWhyReturnsNoBase.
  ///
  /// In en, this message translates to:
  /// **'{returned} of {sold} returned ({rate}%)'**
  String recWhyReturnsNoBase(String returned, String sold, String rate);

  /// No description provided for @recWhyReturnsReason.
  ///
  /// In en, this message translates to:
  /// **'{share}% of returns say: {reason}'**
  String recWhyReturnsReason(String share, String reason);

  /// No description provided for @recReviewPrice.
  ///
  /// In en, this message translates to:
  /// **'Review the price or cost of {title}'**
  String recReviewPrice(String title);

  /// No description provided for @recWhyLosing.
  ///
  /// In en, this message translates to:
  /// **'Lost {amount} on {units} sold in 30 days'**
  String recWhyLosing(String amount, String units);

  /// No description provided for @recAddCost.
  ///
  /// In en, this message translates to:
  /// **'Add a cost for {title}'**
  String recAddCost(String title);

  /// No description provided for @recWhyCostNotSet.
  ///
  /// In en, this message translates to:
  /// **'{units} sold, but profit can\'t be shown without a cost'**
  String recWhyCostNotSet(String units);

  /// No description provided for @recImpactContribution.
  ///
  /// In en, this message translates to:
  /// **'Worth about {amount} profit in 30 days'**
  String recImpactContribution(String amount);

  /// No description provided for @memTitle.
  ///
  /// In en, this message translates to:
  /// **'What Nivaro has learned'**
  String get memTitle;

  /// No description provided for @memIntro.
  ///
  /// In en, this message translates to:
  /// **'Facts from your own shop\'s data. Only facts you confirm are used when talking to customers.'**
  String get memIntro;

  /// No description provided for @memEmpty.
  ///
  /// In en, this message translates to:
  /// **'Nothing learned yet. Facts appear once there\'s enough data.'**
  String get memEmpty;

  /// No description provided for @memFitSmall.
  ///
  /// In en, this message translates to:
  /// **'{title} runs small: {share}% of returns say too small ({returns} returns, {sold} sold)'**
  String memFitSmall(String title, String share, String returns, String sold);

  /// No description provided for @memFitLarge.
  ///
  /// In en, this message translates to:
  /// **'{title} runs large: {share}% of returns say too large ({returns} returns, {sold} sold)'**
  String memFitLarge(String title, String share, String returns, String sold);

  /// No description provided for @memRepeatCycle.
  ///
  /// In en, this message translates to:
  /// **'Customers reorder about every {days} days ({customers} repeat customers)'**
  String memRepeatCycle(String days, String customers);

  /// No description provided for @memPeakHours.
  ///
  /// In en, this message translates to:
  /// **'Most orders come between {start}:00 and {end}:00 ({share}% of orders)'**
  String memPeakHours(String start, String end, String share);

  /// No description provided for @memBestCourier.
  ///
  /// In en, this message translates to:
  /// **'{courier} delivers best to {district}: {success}% of {n} parcels'**
  String memBestCourier(
    String courier,
    String district,
    String success,
    String n,
  );

  /// No description provided for @memOther.
  ///
  /// In en, this message translates to:
  /// **'Something learned about your shop'**
  String get memOther;

  /// No description provided for @memConfidence.
  ///
  /// In en, this message translates to:
  /// **'Confidence {pct}%'**
  String memConfidence(String pct);

  /// No description provided for @memWindow.
  ///
  /// In en, this message translates to:
  /// **'From the last {days} days'**
  String memWindow(String days);

  /// No description provided for @memConfirmed.
  ///
  /// In en, this message translates to:
  /// **'Confirmed by you'**
  String get memConfirmed;

  /// No description provided for @memSellerVersion.
  ///
  /// In en, this message translates to:
  /// **'Your version'**
  String get memSellerVersion;

  /// No description provided for @memVersion.
  ///
  /// In en, this message translates to:
  /// **'Version {n}'**
  String memVersion(int n);

  /// No description provided for @memConfirm.
  ///
  /// In en, this message translates to:
  /// **'Confirm'**
  String get memConfirm;

  /// No description provided for @memReject.
  ///
  /// In en, this message translates to:
  /// **'Not right'**
  String get memReject;

  /// No description provided for @memRejectTitle.
  ///
  /// In en, this message translates to:
  /// **'What\'s wrong with it?'**
  String get memRejectTitle;

  /// No description provided for @memRejectNote.
  ///
  /// In en, this message translates to:
  /// **'Reason'**
  String get memRejectNote;

  /// No description provided for @memDone.
  ///
  /// In en, this message translates to:
  /// **'Saved'**
  String get memDone;

  /// No description provided for @memCancel.
  ///
  /// In en, this message translates to:
  /// **'Cancel'**
  String get memCancel;

  /// No description provided for @memManagersOnly.
  ///
  /// In en, this message translates to:
  /// **'Only owners and managers can change these.'**
  String get memManagersOnly;

  /// No description provided for @settingsLearned.
  ///
  /// In en, this message translates to:
  /// **'What Nivaro has learned'**
  String get settingsLearned;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  Future<AppLocalizations> load(Locale locale) {
    return SynchronousFuture<AppLocalizations>(lookupAppLocalizations(locale));
  }

  @override
  bool isSupported(Locale locale) =>
      <String>['en', 'ne'].contains(locale.languageCode);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

AppLocalizations lookupAppLocalizations(Locale locale) {
  // Lookup logic when only language code is specified.
  switch (locale.languageCode) {
    case 'en':
      return AppLocalizationsEn();
    case 'ne':
      return AppLocalizationsNe();
  }

  throw FlutterError(
    'AppLocalizations.delegate failed to load unsupported locale "$locale". This is likely '
    'an issue with the localizations generation tool. Please file an issue '
    'on GitHub with a reproducible sample app and the gen-l10n configuration '
    'that was used.',
  );
}
