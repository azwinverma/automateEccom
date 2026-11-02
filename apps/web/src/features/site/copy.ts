/**
 * Public website copy (en/ne). Source: docs/Autonomous_Commerce_OS_Business_Partner_Brief.pdf, specs/01, 21,
 * 25, 26. Rules: no invented numbers, customers, logos or prices; every capability carries its real build
 * status ("now" = usable in the product today, "next" = in development, see docs/IMPLEMENTATION_STATUS.md);
 * illustrative UI is labelled as such. Nepali needs native review (GAP-NE-COPY).
 */
export type Avail = "now" | "next";

export interface SiteCopy {
  nav: { how: string; product: string; intelligence: string; plans: string; signIn: string; start: string; open: string; menu: string; skip: string };
  status: Record<Avail, string>;
  illustrative: string;
  hero: {
    eyebrow: string;
    lead: string;
    emphasis: string;
    end: string;
    sub: string;
    support: string;
    primary: string;
    secondary: string;
    note: string;
    morning: {
      label: string;
      title: string;
      handled: string;
      progressing: string;
      needYou: string;
      items: string[];
      insights: string[];
    };
  };
  problem: { eyebrow: string; title: string; body: string; pains: { title: string; text: string }[]; quote: string };
  loop: { eyebrow: string; title: string; body: string; stages: { name: string; text: string; status: Avail }[] };
  control: {
    eyebrow: string;
    title: string;
    body: string;
    points: { title: string; text: string }[];
    fragment: { running: string; score: string; scoreNote: string; today: [string, string][]; attention: string; rows: { tone: "danger" | "warning" | "info"; text: string; action: string }[] };
  };
  modules: {
    eyebrow: string;
    title: string;
    items: { key: string; name: string; text: string; status: Avail }[];
    studio: { photos: string; draft: string; fields: [string, string][]; aiTag: string; price: string; priceHint: string };
    sync: { title: string; lanes: [string, string, "ok" | "pending" | "draft"][] };
    chat: { customer: string; reply: string; order: string; fields: [string, string][]; missing: string };
    journey: string[];
  };
  intelligence: {
    eyebrow: string;
    title: string;
    body: string;
    items: { name: string; text: string }[];
    examplesTitle: string;
    examples: { what: string; why: string }[];
    whyLabel: string;
  };
  position: { eyebrow: string; title: string; nots: string[]; lead: string; owns: { title: string; text: string }[] };
  trust: { eyebrow: string; title: string; body: string; items: { title: string; text: string }[] };
  audience: { eyebrow: string; title: string; body: string; points: string[] };
  plans: { eyebrow: string; title: string; note: string; tiers: { name: string; theme: string; value: string; hero?: boolean }[]; cta: string; heroTag: string };
  cta: { title: string; emphasis: string; end: string; body: string; primary: string; secondary: string; loop: [string, string, string, string] };
  footer: { tagline: string; rights: string; made: string };
}

export const siteEn: SiteCopy = {
  nav: {
    how: "How it works",
    product: "Product",
    intelligence: "Intelligence",
    plans: "Plans",
    signIn: "Sign in",
    start: "Start free",
    open: "Open Nivaro",
    menu: "Menu",
    skip: "Skip to content",
  },
  status: { now: "Available now", next: "In development" },
  illustrative: "Illustrative",
  hero: {
    eyebrow: "Autonomous Commerce OS",
    lead: "Your store, on",
    emphasis: "autopilot",
    end: ".",
    sub: "From product photo to delivered order, Nivaro helps automate the work behind selling online.",
    support: "Create once. Sell everywhere. Let Nivaro handle the routine work.",
    primary: "Start free",
    secondary: "See how it works",
    note: "Free trial. No card to start. English and नेपाली.",
    morning: {
      label: "Illustrative morning view",
      title: "Your store is running.",
      handled: "orders handled overnight",
      progressing: "progressing normally",
      needYou: "need you",
      items: ["2 orders need stock confirmation", "1 exchange request", "1 refund approval"],
      insights: ["Black XL may sell out in 5 days", "Yesterday's Reel generated 11 orders"],
    },
  },
  problem: {
    eyebrow: "The problem",
    title: "You are the human integration layer.",
    body: "Instagram, Facebook, TikTok, payment apps, courier portals, spreadsheets. Each tool solves a piece. Every handoff between them is manual work, a delay, a stock mistake or a lost order.",
    pains: [
      { title: "Product onboarding", text: "Photos, edits, titles, descriptions, resizing and channel-specific copy, again and again." },
      { title: "Social selling", text: "Posting on every channel and answering the same price, size and delivery questions." },
      { title: "Order capture", text: "Copying names, phones, addresses and variants from chats into another system." },
      { title: "Inventory", text: "Keeping stock right across social pages, a website and the shop." },
      { title: "Payments and COD", text: "Verifying payments, tracking COD exposure and reconciling courier settlements." },
      { title: "Fulfillment", text: "Re-typing addresses into courier portals and chasing failed deliveries." },
      { title: "Returns", text: "Deciding eligibility, arranging pickups, exchanges and refunds by hand." },
      { title: "Business insight", text: "Seeing revenue, but not what each product really earns after returns, delivery and ads." },
    ],
    quote: "The pain is not a lack of software. It is that the seller is still the glue between all of it.",
  },
  loop: {
    eyebrow: "One lifecycle",
    title: "From product photo to delivered order.",
    body: "One product record runs through every step. Nivaro does the routine; you only see what needs judgment. We are building the loop in order, and we label what you can use today.",
    stages: [
      { name: "Capture", text: "Take or pick product photos on your phone or computer.", status: "now" },
      { name: "Create", text: "AI drafts titles, descriptions and attributes in English and Nepali, and makes Auto Reels.", status: "now" },
      { name: "Publish", text: "List and schedule across connected channels, starting with your WooCommerce store.", status: "now" },
      { name: "Converse", text: "One inbox; an AI Sales Agent answers from real stock, price and delivery data.", status: "next" },
      { name: "Order", text: "A chat or a channel sale becomes one structured order.", status: "next" },
      { name: "Pay", text: "Payment or COD is verified and reconciled.", status: "next" },
      { name: "Fulfill", text: "Stock reserved, courier chosen, shipment created and tracked.", status: "next" },
      { name: "Recover", text: "Failed deliveries, exchanges, returns and refunds follow your policy.", status: "next" },
      { name: "Retain", text: "Reviews, win-back and repeat-purchase campaigns run on their own.", status: "next" },
      { name: "Learn", text: "Profit, content, courier and return intelligence improve the next decision.", status: "next" },
    ],
  },
  control: {
    eyebrow: "Autopilot Control Center",
    title: "Is my store running, and what actually needs me?",
    body: "Home answers one question. Routine work is counted, not shown. Only exceptions reach you, each with the reason and one clear action.",
    points: [
      { title: "Store status", text: "A plain operating state: running, or what is holding it up." },
      { title: "Today", text: "Orders, revenue, AI-handled conversations, shipments, returns, content published." },
      { title: "Autopilot Score", text: "The share of eligible operations done automatically, with the denominator shown. Never a vanity number." },
      { title: "Needs your attention", text: "Refund approvals, expired channel logins, stock risk, payment mismatches, escalations." },
    ],
    fragment: {
      running: "Your store is running.",
      score: "Autopilot Score",
      scoreNote: "of eligible operations, last 7 days",
      today: [
        ["Orders", "38"],
        ["Revenue", "रू 1,24,600"],
        ["AI-handled chats", "112"],
        ["Shipments", "31"],
      ],
      attention: "Needs your attention",
      rows: [
        { tone: "danger", text: "Refund approval · Order #2041 · रू 4,800", action: "Review" },
        { tone: "warning", text: "Instagram login expires in 2 days", action: "Reconnect" },
        { tone: "warning", text: "Black kurta XL: 5 days of stock left", action: "Reorder" },
        { tone: "info", text: "COD mismatch on courier settlement #1988", action: "Check" },
      ],
    },
  },
  modules: {
    eyebrow: "Product",
    title: "Everything between the photo and the payout.",
    items: [
      { key: "studio", name: "AI Product Studio", text: "Add up to six photos. Nivaro drafts the title, description, attributes and channel copy in English and Nepali. You set the price; the AI never does.", status: "now" },
      { key: "video", name: "Auto Reels", text: "Reels assembled from your own product photos, with price and Nepali text overlays. Premium generative video comes with credits.", status: "now" },
      { key: "publish", name: "Channel publishing", text: "One product, every connected channel, with each listing's state in view and drift fixed automatically.", status: "now" },
      { key: "inbox", name: "Inbox and AI Sales Agent", text: "Answers price, size, stock and delivery questions from real catalog data, collects the details and turns the chat into an order.", status: "next" },
      { key: "orders", name: "Orders, COD and delivery", text: "Stock reserved, COD verified, courier booked, tracking shared, failed deliveries recovered.", status: "next" },
      { key: "returns", name: "Returns and exchanges", text: "Policy-driven eligibility, reverse pickup, replacement reservation and controlled refunds.", status: "next" },
    ],
    studio: {
      photos: "3 photos",
      draft: "Draft",
      fields: [
        ["Title", "Handloom cotton kurta, maroon"],
        ["Fabric", "Cotton (Dhaka weave)"],
        ["Sizes", "M · L · XL"],
      ],
      aiTag: "AI · please check",
      price: "Price",
      priceHint: "You set this",
    },
    sync: {
      title: "Handloom cotton kurta",
      lanes: [
        ["Website (WooCommerce)", "Synced", "ok"],
        ["Instagram", "Scheduled 7:30 PM", "pending"],
        ["TikTok", "Draft", "draft"],
      ],
    },
    chat: {
      customer: "XL ma maroon cha? Kathmandu delivery kati din?",
      reply: "Cha, XL ma 4 ota baki chan. Kathmandu bhitra 1–2 din. Order garnu huncha?",
      order: "Order draft",
      fields: [
        ["Item", "Kurta · Maroon · XL"],
        ["Payment", "COD"],
        ["Deliver to", "Baneshwor, Kathmandu"],
      ],
      missing: "Phone number missing",
    },
    journey: ["Order", "Paid · COD", "Packed", "With courier", "Delivered"],
  },
  intelligence: {
    eyebrow: "Intelligence",
    title: "It learns how your store makes money.",
    body: "Single AI features are easy to copy. Nivaro's value compounds: every order, return and post makes the next decision better, for your store, from your own data. These layers switch on as trustworthy data builds up.",
    items: [
      { name: "Product Brain", text: "One profile per product: stock, cost, price, content, questions, returns and performance." },
      { name: "Commerce Memory", text: "What sells, who buys, what fails and what makes profit, with evidence you can correct." },
      { name: "Digital Store Twin", text: "A live, derived picture of your store for answers, recommendations and what-ifs." },
      { name: "Creative Genome", text: "The hooks, formats, timing, language and CTAs that convert for your audience." },
      { name: "Operational intelligence", text: "COD risk, courier performance, return patterns and supplier economics." },
      { name: "Closed learning loop", text: "Observe, decide, act, measure, learn, improve. Every outcome feeds the next decision." },
    ],
    examplesTitle: "How Nivaro will explain a recommendation (examples)",
    whyLabel: "Why",
    examples: [
      { what: "Black XL may sell out in five days.", why: "Daily demand is 3.2 units and 16 are available." },
      { what: "Don't increase promotion on Product A.", why: "High revenue, but low contribution after returns and ad spend." },
      { what: "Use Courier B for this COD route.", why: "Its first-attempt delivery success on this route is higher." },
      { what: "Add a fit warning and suggest one size up.", why: "61% of returns for this product are size-related." },
      { what: "Show the price in the first two seconds.", why: "Your audience converts better on 8–11 second Reels that do." },
    ],
  },
  position: {
    eyebrow: "Why Nivaro",
    title: "Not another store builder.",
    nots: ["A store builder", "A unified inbox", "A chatbot", "An inventory tool", "A caption generator"],
    lead: "Nivaro is the operating layer that runs the work between all of them.",
    owns: [
      { title: "Automation depth", text: "The full lifecycle, not isolated tasks." },
      { title: "Exception-first", text: "You manage only what needs judgment." },
      { title: "Profit-aware", text: "Decisions optimise contribution, not vanity metrics." },
      { title: "Learns your store", text: "It gets smarter for each store over time." },
      { title: "Provider-independent AI", text: "Routes across Claude, OpenAI, Gemini and media providers, with failover." },
    ],
  },
  trust: {
    eyebrow: "Controlled autonomy",
    title: "Automate the routine. Explain the important. Keep people in control.",
    body: "To run real commerce, automation has to be reliable before it is clever.",
    items: [
      { title: "One source of truth", text: "Products, customers, orders, stock, payments, shipments and returns share one record." },
      { title: "AI that checks facts", text: "Prices, stock and delivery come from your live data, never a guess." },
      { title: "Keeps working", text: "If one AI provider fails, Nivaro routes to another instead of stopping your shop." },
      { title: "No duplicates", text: "Retries and repeated webhooks never create a second order, refund or shipment." },
      { title: "Your approval", text: "Large refunds, price changes and purchase orders can require you." },
      { title: "Your data stays yours", text: "Every store is isolated, and every action is recorded with who or what did it." },
    ],
  },
  audience: {
    eyebrow: "Who it's for",
    title: "Built first for fashion and visual sellers in Nepal.",
    body: "Clothing, shoes, bags and accessories sold through Instagram, Facebook and TikTok, delivered by courier with cash on delivery.",
    points: [
      "Frequent launches with many photos, sizes and colours",
      "High DM volume and COD-heavy operations",
      "Small teams that have outgrown spreadsheets but don't need an ERP",
    ],
  },
  plans: {
    eyebrow: "Plans",
    title: "Plans that grow with your automation.",
    note: "Pricing will be announced at launch. Start with a free trial today.",
    heroTag: "Most automation",
    cta: "Start free trial",
    tiers: [
      { name: "Starter", theme: "Create", value: "Catalog, AI copy, image tools, basic orders and inventory, Auto Reels." },
      { name: "Growth", theme: "Sell", value: "Unified inbox, customers, AI replies and order extraction, payment and courier integrations." },
      { name: "Pro", theme: "Automate", value: "AI Sales Agent, workflows, returns and refunds automation, AI Store Manager, profit intelligence.", hero: true },
      { name: "Business", theme: "Scale", value: "Several stores and warehouses, teams and roles, API, higher limits, your own AI keys." },
      { name: "Enterprise", theme: "Govern", value: "SSO, SLA, custom integrations, negotiated usage and governance." },
    ],
  },
  cta: {
    title: "Add your first product in",
    emphasis: "minutes",
    end: ".",
    body: "Take a photo, check the draft, publish. Nivaro handles what comes next.",
    primary: "Start free",
    secondary: "Sign in",
    loop: ["Create", "Sell", "Fulfill", "Learn"],
  },
  footer: {
    tagline: "Your store, on autopilot.",
    rights: "© 2026 Nivaro",
    made: "Made for online sellers in Nepal",
  },
};

export const siteNe: SiteCopy = {
  nav: {
    how: "कसरी चल्छ",
    product: "प्रोडक्ट",
    intelligence: "इन्टेलिजेन्स",
    plans: "प्लान",
    signIn: "साइन इन",
    start: "निःशुल्क सुरु गर्नुहोस्",
    open: "Nivaro खोल्नुहोस्",
    menu: "मेनु",
    skip: "सामग्रीमा जानुहोस्",
  },
  status: { now: "अहिले उपलब्ध", next: "बन्दैछ" },
  illustrative: "उदाहरण",
  hero: {
    eyebrow: "Autonomous Commerce OS",
    lead: "तपाईंको पसल,",
    emphasis: "अटोपाइलटमा",
    end: "।",
    sub: "सामानको फोटोदेखि डेलिभर भएको अर्डरसम्म, अनलाइन बेच्ने पछाडिको काम Nivaro ले आफैं गर्न मद्दत गर्छ।",
    support: "एक पटक बनाउनुहोस्। जताततै बेच्नुहोस्। दोहोरिने काम Nivaro लाई छोड्नुहोस्।",
    primary: "निःशुल्क सुरु गर्नुहोस्",
    secondary: "कसरी चल्छ हेर्नुहोस्",
    note: "निःशुल्क ट्रायल। कार्ड चाहिँदैन। English र नेपाली।",
    morning: {
      label: "बिहानको उदाहरण",
      title: "तपाईंको पसल चलिरहेको छ।",
      handled: "अर्डर राति आफैं सम्हालियो",
      progressing: "ठीकसँग अगाडि बढ्दै",
      needYou: "तपाईं चाहिने",
      items: ["२ अर्डरमा स्टक पुष्टि चाहिन्छ", "१ एक्सचेन्ज अनुरोध", "१ रिफन्ड स्वीकृति"],
      insights: ["कालो XL ५ दिनमा सकिन सक्छ", "हिजोको रिलबाट ११ अर्डर आए"],
    },
  },
  problem: {
    eyebrow: "समस्या",
    title: "सबै सफ्टवेयर जोड्ने काम तपाईं आफैं गरिरहनुभएको छ।",
    body: "Instagram, Facebook, TikTok, पेमेन्ट एप, कुरियर पोर्टल, स्प्रेडसिट। हरेक टुलले एउटा टुक्रा मात्र सुल्झाउँछ। बीचको हरेक हस्तान्तरण हातले गर्ने काम, ढिलाइ, स्टकको गल्ती वा छुटेको अर्डर हो।",
    pains: [
      { title: "सामान थप्ने", text: "फोटो, सम्पादन, शीर्षक, विवरण, साइज मिलाउने र च्यानलअनुसार लेख्ने काम बारम्बार।" },
      { title: "सोसल बिक्री", text: "हरेक च्यानलमा पोस्ट गर्ने र उही मूल्य, साइज, डेलिभरीका प्रश्नको जवाफ दिने।" },
      { title: "अर्डर लिने", text: "च्याटबाट नाम, फोन, ठेगाना र भेरियन्ट अर्को ठाउँमा सार्ने।" },
      { title: "स्टक", text: "सोसल पेज, वेबसाइट र पसलमा स्टक मिलाइराख्ने।" },
      { title: "पेमेन्ट र COD", text: "पेमेन्ट जाँच्ने, COD हिसाब राख्ने र कुरियर सेटलमेन्ट मिलाउने।" },
      { title: "डेलिभरी", text: "कुरियर पोर्टलमा ठेगाना फेरि टाइप गर्ने र असफल डेलिभरी पछ्याउने।" },
      { title: "रिटर्न", text: "योग्यता, पिकअप, एक्सचेन्ज र रिफन्ड हातैले मिलाउने।" },
      { title: "व्यवसायको बुझाइ", text: "आम्दानी देखिन्छ, तर रिटर्न, डेलिभरी र विज्ञापनपछि हरेक सामानले कति कमायो देखिँदैन।" },
    ],
    quote: "समस्या सफ्टवेयरको कमी होइन। सबै कुरा जोड्ने काम अझै सेलर आफैंले गर्नुपर्छ।",
  },
  loop: {
    eyebrow: "एउटै चक्र",
    title: "सामानको फोटोदेखि डेलिभर भएको अर्डरसम्म।",
    body: "एउटै सामानको रेकर्ड हरेक चरणमा जान्छ। दोहोरिने काम Nivaro गर्छ; तपाईंले निर्णय चाहिने कुरा मात्र हेर्नुहुन्छ। हामी चक्र क्रमैसँग बनाउँदैछौं, र आज के प्रयोग गर्न मिल्छ लेखेर देखाउँछौं।",
    stages: [
      { name: "खिच्ने", text: "फोन वा कम्प्युटरबाट सामानको फोटो खिच्नुहोस् वा छान्नुहोस्।", status: "now" },
      { name: "बनाउने", text: "AI ले English र नेपालीमा शीर्षक, विवरण र विशेषता ड्राफ्ट गर्छ, र अटो रिल बनाउँछ।", status: "now" },
      { name: "प्रकाशन", text: "जोडिएका च्यानलमा लिस्ट र तालिका, तपाईंको WooCommerce स्टोरबाट सुरु।", status: "now" },
      { name: "कुराकानी", text: "एउटै इनबक्स; AI सेल्स एजेन्टले साँचो स्टक, मूल्य र डेलिभरी डाटाबाट जवाफ दिन्छ।", status: "next" },
      { name: "अर्डर", text: "च्याट वा च्यानलको बिक्री एउटै व्यवस्थित अर्डर बन्छ।", status: "next" },
      { name: "पेमेन्ट", text: "पेमेन्ट वा COD जाँचिन्छ र मिलाइन्छ।", status: "next" },
      { name: "डेलिभरी", text: "स्टक रिजर्भ, कुरियर छनोट, सिपमेन्ट बनाइन्छ र ट्र्याक हुन्छ।", status: "next" },
      { name: "सुधार", text: "असफल डेलिभरी, एक्सचेन्ज, रिटर्न र रिफन्ड तपाईंको नीतिअनुसार चल्छन्।", status: "next" },
      { name: "फेरि किनाउने", text: "रिभ्यु, फर्काउने र दोहोरो खरिदका अभियान आफैं चल्छन्।", status: "next" },
      { name: "सिक्ने", text: "नाफा, कन्टेन्ट, कुरियर र रिटर्नको जानकारीले अर्को निर्णय सुधार्छ।", status: "next" },
    ],
  },
  control: {
    eyebrow: "अटोपाइलट कन्ट्रोल सेन्टर",
    title: "मेरो पसल चलिरहेको छ? र मैले के हेर्नुपर्छ?",
    body: "होमले एउटै प्रश्नको जवाफ दिन्छ। दोहोरिने काम गनिन्छ, देखाइँदैन। अपवाद मात्र तपाईंसम्म आउँछ, कारण र एउटा स्पष्ट कामसहित।",
    points: [
      { title: "पसलको अवस्था", text: "सीधा अवस्था: चलिरहेको छ, वा केले रोकेको छ।" },
      { title: "आज", text: "अर्डर, आम्दानी, AI ले सम्हालेका कुराकानी, सिपमेन्ट, रिटर्न, प्रकाशित कन्टेन्ट।" },
      { title: "अटोपाइलट स्कोर", text: "योग्य कामहरूमध्ये आफैं भएको हिस्सा, कुल संख्यासहित। देखावटी अंक होइन।" },
      { title: "तपाईंले हेर्नुपर्ने", text: "रिफन्ड स्वीकृति, सकिएको च्यानल लगइन, स्टक जोखिम, पेमेन्ट नमिलेको, गुनासो।" },
    ],
    fragment: {
      running: "तपाईंको पसल चलिरहेको छ।",
      score: "अटोपाइलट स्कोर",
      scoreNote: "योग्य कामको, पछिल्लो ७ दिन",
      today: [
        ["अर्डर", "३८"],
        ["आम्दानी", "रू १,२४,६००"],
        ["AI ले सम्हालेका च्याट", "११२"],
        ["सिपमेन्ट", "३१"],
      ],
      attention: "तपाईंले हेर्नुपर्ने",
      rows: [
        { tone: "danger", text: "रिफन्ड स्वीकृति · अर्डर #2041 · रू ४,८००", action: "हेर्नुहोस्" },
        { tone: "warning", text: "Instagram लगइन २ दिनमा सकिन्छ", action: "फेरि जोड्नुहोस्" },
        { tone: "warning", text: "कालो कुर्ता XL: ५ दिनको स्टक बाँकी", action: "थप मगाउनुहोस्" },
        { tone: "info", text: "कुरियर सेटलमेन्ट #1988 मा COD नमिलेको", action: "जाँच्नुहोस्" },
      ],
    },
  },
  modules: {
    eyebrow: "प्रोडक्ट",
    title: "फोटोदेखि पैसा हातमा आउँदासम्मको सबै काम।",
    items: [
      { key: "studio", name: "AI प्रोडक्ट स्टुडियो", text: "छ वटासम्म फोटो थप्नुहोस्। Nivaro ले English र नेपालीमा शीर्षक, विवरण, विशेषता र च्यानलको लेख ड्राफ्ट गर्छ। मूल्य तपाईं राख्नुहुन्छ; AI ले कहिल्यै राख्दैन।", status: "now" },
      { key: "video", name: "अटो रिल", text: "तपाईंकै फोटोबाट मूल्य र नेपाली टेक्स्टसहित रिल। प्रिमियम AI भिडियो क्रेडिटसँग आउँछ।", status: "now" },
      { key: "publish", name: "च्यानलमा प्रकाशन", text: "एउटा सामान, सबै जोडिएका च्यानल, हरेक लिस्टिङको अवस्था देखिने र फरक परे आफैं मिल्ने।", status: "now" },
      { key: "inbox", name: "इनबक्स र AI सेल्स एजेन्ट", text: "साँचो क्याटलगबाट मूल्य, साइज, स्टक र डेलिभरीको जवाफ दिन्छ, विवरण लिन्छ र च्याटलाई अर्डर बनाउँछ।", status: "next" },
      { key: "orders", name: "अर्डर, COD र डेलिभरी", text: "स्टक रिजर्भ, COD जाँच, कुरियर बुक, ट्र्याकिङ पठाइन्छ, असफल डेलिभरी सम्हालिन्छ।", status: "next" },
      { key: "returns", name: "रिटर्न र एक्सचेन्ज", text: "नीतिअनुसार योग्यता, रिभर्स पिकअप, बदलाको स्टक रिजर्भ र नियन्त्रित रिफन्ड।", status: "next" },
    ],
    studio: {
      photos: "३ फोटो",
      draft: "ड्राफ्ट",
      fields: [
        ["शीर्षक", "हाते तानको सुती कुर्ता, मरुन"],
        ["कपडा", "सुती (ढाका बुनाइ)"],
        ["साइज", "M · L · XL"],
      ],
      aiTag: "AI · जाँच्नुहोस्",
      price: "मूल्य",
      priceHint: "तपाईं राख्नुहुन्छ",
    },
    sync: {
      title: "हाते तानको सुती कुर्ता",
      lanes: [
        ["वेबसाइट (WooCommerce)", "मिलेको", "ok"],
        ["Instagram", "बेलुका ७:३० मा तालिका", "pending"],
        ["TikTok", "ड्राफ्ट", "draft"],
      ],
    },
    chat: {
      customer: "XL मा मरुन छ? काठमाडौं डेलिभरी कति दिन?",
      reply: "छ, XL मा ४ वटा बाँकी छन्। काठमाडौंभित्र १–२ दिन। अर्डर गर्नुहुन्छ?",
      order: "अर्डर ड्राफ्ट",
      fields: [
        ["सामान", "कुर्ता · मरुन · XL"],
        ["पेमेन्ट", "COD"],
        ["ठेगाना", "बानेश्वर, काठमाडौं"],
      ],
      missing: "फोन नम्बर बाँकी",
    },
    journey: ["अर्डर", "COD", "प्याक", "कुरियरमा", "डेलिभर"],
  },
  intelligence: {
    eyebrow: "इन्टेलिजेन्स",
    title: "तपाईंको पसलले कसरी पैसा कमाउँछ, यसले सिक्छ।",
    body: "एउटा AI फिचर नक्कल गर्न सजिलो छ। Nivaro को मूल्य थपिँदै जान्छ: हरेक अर्डर, रिटर्न र पोस्टले अर्को निर्णय राम्रो बनाउँछ, तपाईंको पसलका लागि, तपाईंकै डाटाबाट। भरपर्दो डाटा जम्मा भएपछि यी तहहरू सुरु हुन्छन्।",
    items: [
      { name: "प्रोडक्ट ब्रेन", text: "हरेक सामानको एउटा प्रोफाइल: स्टक, लागत, मूल्य, कन्टेन्ट, प्रश्न, रिटर्न र प्रदर्शन।" },
      { name: "कमर्स मेमोरी", text: "के बिक्छ, को किन्छ, के असफल हुन्छ र केले नाफा दिन्छ, सच्याउन मिल्ने प्रमाणसहित।" },
      { name: "डिजिटल स्टोर ट्विन", text: "जवाफ, सुझाव र 'यसो भए के हुन्छ' का लागि पसलको जीवित चित्र।" },
      { name: "क्रिएटिभ जिनोम", text: "तपाईंका ग्राहकलाई किन्न लगाउने हुक, ढाँचा, समय, भाषा र CTA।" },
      { name: "सञ्चालन इन्टेलिजेन्स", text: "COD जोखिम, कुरियर प्रदर्शन, रिटर्नको ढाँचा र सप्लायरको हिसाब।" },
      { name: "बन्द सिकाइ चक्र", text: "हेर्ने, निर्णय, काम, नाप्ने, सिक्ने, सुधार्ने। हरेक नतिजा अर्को निर्णयमा जान्छ।" },
    ],
    examplesTitle: "Nivaro ले सुझाव कसरी बुझाउँछ (उदाहरण)",
    whyLabel: "किन",
    examples: [
      { what: "कालो XL पाँच दिनमा सकिन सक्छ।", why: "दिनको माग ३.२ थान छ र १६ थान मात्र बाँकी छ।" },
      { what: "सामान A को प्रचार नबढाउनुहोस्।", why: "आम्दानी धेरै, तर रिटर्न र विज्ञापनपछि योगदान कम।" },
      { what: "यो COD रुटमा कुरियर B प्रयोग गर्नुहोस्।", why: "यो रुटमा पहिलो प्रयासमै डेलिभरी हुने दर बढी छ।" },
      { what: "फिटको चेतावनी थप्नुहोस् र एक साइज ठूलो सुझाउनुहोस्।", why: "यो सामानका ६१% रिटर्न साइजका कारण हुन्।" },
      { what: "पहिलो दुई सेकेन्डमै मूल्य देखाउनुहोस्।", why: "त्यसो गर्ने ८–११ सेकेन्डका रिलमा तपाईंका ग्राहक बढी किन्छन्।" },
    ],
  },
  position: {
    eyebrow: "किन Nivaro",
    title: "अर्को स्टोर बिल्डर होइन।",
    nots: ["स्टोर बिल्डर", "इनबक्स मात्र", "च्याटबट", "स्टक टुल", "क्याप्सन जेनेरेटर"],
    lead: "Nivaro ती सबैबीचको काम चलाउने सञ्चालन तह हो।",
    owns: [
      { title: "पूरा अटोमेसन", text: "छुट्टाछुट्टै काम होइन, पूरा चक्र।" },
      { title: "अपवाद मात्र", text: "निर्णय चाहिने कुरा मात्र तपाईंले हेर्नुहुन्छ।" },
      { title: "नाफामा ध्यान", text: "देखावटी अंक होइन, साँचो योगदानका लागि निर्णय।" },
      { title: "तपाईंको पसल सिक्छ", text: "समयसँगै हरेक पसलका लागि अझ जान्ने हुन्छ।" },
      { title: "एउटै AI मा भर नपर्ने", text: "Claude, OpenAI, Gemini र मिडिया प्रोभाइडरबीच रुटिङ, विकल्पसहित।" },
    ],
  },
  trust: {
    eyebrow: "नियन्त्रित अटोमेसन",
    title: "दोहोरिने काम आफैं। महत्त्वपूर्ण कुरा बुझाएर। नियन्त्रण तपाईंकै हातमा।",
    body: "साँचो व्यापार चलाउन, अटोमेसन चलाख हुनुअघि भरपर्दो हुनुपर्छ।",
    items: [
      { title: "एउटै सत्य स्रोत", text: "सामान, ग्राहक, अर्डर, स्टक, पेमेन्ट, सिपमेन्ट र रिटर्न एउटै रेकर्डमा।" },
      { title: "तथ्य जाँच्ने AI", text: "मूल्य, स्टक र डेलिभरी तपाईंको जीवित डाटाबाट, अनुमानबाट होइन।" },
      { title: "रोकिँदैन", text: "एउटा AI प्रोभाइडर बिग्रिए अर्कोमा जान्छ, पसल रोकिँदैन।" },
      { title: "दोहोरो हुँदैन", text: "दोहोरिएका अनुरोधले दोस्रो अर्डर, रिफन्ड वा सिपमेन्ट बनाउँदैन।" },
      { title: "तपाईंको स्वीकृति", text: "ठूला रिफन्ड, मूल्य परिवर्तन र खरिद अर्डरमा तपाईंको स्वीकृति लिन मिल्छ।" },
      { title: "डाटा तपाईंकै", text: "हरेक पसल अलग, र हरेक काम कसले वा केले गर्‍यो रेकर्ड हुन्छ।" },
    ],
  },
  audience: {
    eyebrow: "कसका लागि",
    title: "सुरुमा नेपालका फेसन र भिजुअल सेलरका लागि।",
    body: "Instagram, Facebook र TikTok बाट बेचिने कपडा, जुत्ता, झोला र एक्सेसरिज, कुरियर र COD बाट डेलिभरी।",
    points: ["धेरै फोटो, साइज र रङसहित बारम्बार नयाँ सामान", "धेरै DM र COD मा आधारित काम", "स्प्रेडसिटभन्दा ठूलो तर ERP नचाहिने सानो टिम"],
  },
  plans: {
    eyebrow: "प्लान",
    title: "अटोमेसनसँगै बढ्ने प्लान।",
    note: "मूल्य सुरुवातमा घोषणा हुनेछ। आजै निःशुल्क ट्रायल सुरु गर्नुहोस्।",
    heroTag: "सबैभन्दा धेरै अटोमेसन",
    cta: "निःशुल्क ट्रायल सुरु गर्नुहोस्",
    tiers: [
      { name: "Starter", theme: "बनाउने", value: "क्याटलग, AI लेखन, फोटो टुल, सामान्य अर्डर र स्टक, अटो रिल।" },
      { name: "Growth", theme: "बेच्ने", value: "एउटै इनबक्स, ग्राहक, AI जवाफ र अर्डर निकाल्ने, पेमेन्ट र कुरियर जडान।" },
      { name: "Pro", theme: "अटोमेट", value: "AI सेल्स एजेन्ट, वर्कफ्लो, रिटर्न र रिफन्ड अटोमेसन, AI स्टोर म्यानेजर, नाफा इन्टेलिजेन्स।", hero: true },
      { name: "Business", theme: "बढाउने", value: "धेरै स्टोर र गोदाम, टिम र भूमिका, API, बढी सीमा, आफ्नै AI कि।" },
      { name: "Enterprise", theme: "सुशासन", value: "SSO, SLA, कस्टम जडान, सम्झौताको प्रयोग र सुशासन।" },
    ],
  },
  cta: {
    title: "पहिलो सामान थप्न",
    emphasis: "केही मिनेट",
    end: " मात्र लाग्छ।",
    body: "फोटो खिच्नुहोस्, ड्राफ्ट जाँच्नुहोस्, प्रकाशन गर्नुहोस्। त्यसपछिको काम Nivaro ले सम्हाल्छ।",
    primary: "निःशुल्क सुरु गर्नुहोस्",
    secondary: "साइन इन",
    loop: ["बनाउने", "बेच्ने", "पठाउने", "सिक्ने"],
  },
  footer: {
    tagline: "तपाईंको पसल, अटोपाइलटमा।",
    rights: "© २०२६ Nivaro",
    made: "नेपालका अनलाइन सेलरका लागि बनाइएको",
  },
};
