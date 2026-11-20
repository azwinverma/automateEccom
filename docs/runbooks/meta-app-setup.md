# Nivaro's Meta app: setup and App Review

Facebook and Instagram customer messages only reach a shop's inbox through **Nivaro's own Meta app**
once Meta grants it **Advanced Access** to `pages_messaging` and `instagram_manage_messages`. Until
then the app works only for people who have a role on it (your team), which is exactly what the
App Review demo needs. Sellers can already *post* with their own Meta app (Settings → Channels →
Facebook & Instagram → Advanced).

## 1. Create the app (once)
1. Use a Meta Business portfolio for the company (business.facebook.com) and complete **Business
   verification** (company registration documents). App Review for messaging requires it.
2. developers.facebook.com → My apps → Create app → use case **"Other"** → type **Business** →
   attach the business portfolio.
3. Add products: **Facebook Login for Business**, **Messenger**, **Instagram** (Instagram API with
   Facebook Login).
4. Facebook Login for Business → Settings → Valid OAuth redirect URIs:
   `https://<web domain>/settings/channels/meta` (and the staging domain).
5. Webhooks: callback URL `https://<api domain>/webhooks/meta`, verify token = the value you put in
   `COS_META_VERIFY_TOKEN`. Subscribe the **Page** object to `messages`, `messaging_postbacks`, and the
   **Instagram** object to `messages`.
6. App settings → Basic: privacy policy URL, terms URL, data deletion instructions URL, app icon,
   category "Business and pages".

## 2. Configure Nivaro (secret manager, never in the repo)
```
COS_META_APP_ID=<App ID>
COS_META_APP_SECRET=<App secret>          # signs every webhook; rotate if leaked
COS_META_VERIFY_TOKEN=<long random string>
```
Settings → Channels then shows **Continue with Facebook**. Check `GET /api/v1/channels/meta/status`
returns `{"one_click_available": true}`.

## 3. Test with your team (Standard Access)
Add team members as app roles (App roles → Testers/Developers). Connect a test Page with
Continue with Facebook, message the Page from a tester's account, and watch the AI Sales Agent reply.
Messages from people without a role are not delivered to the app yet (expected).

## 4. App Review (Advanced Access)
Request: `pages_messaging`, `pages_manage_metadata`, `pages_read_engagement`, `pages_show_list`,
`business_management`, `instagram_basic`, `instagram_manage_messages`, `pages_manage_posts`,
`instagram_content_publish`. For each, Meta wants a screencast and a written use case:
- Seller signs in with Facebook, picks a Page (and its Instagram), the connection appears.
- A customer messages the Page; it arrives in the Nivaro inbox; the AI (or the seller) replies within
  24 hours; the reply arrives in Messenger.
- A product is published; the automatic post appears on the Page/Instagram after approval.
Explain data use plainly: messages are used only to answer that shop's customers; sellers can
disconnect at any time and tokens are destroyed; data deletion URL works.

## 5. After approval
Nothing to deploy. DMs from all customers start arriving for every connected shop. Watch
`integration_calls_total{provider="meta"}` and the `channel_connections_need_attention` gauge.

## Rules the product already enforces
- Replies only within 24 hours of the customer's last message (`outside_reply_window`); campaigns
  defer Messenger/Instagram customers outside the window.
- Page tokens are sealed per connection and never sent to the browser (the Page picker gets ids and
  names only; tokens wait server-side for 10 minutes under a one-time selection id).
