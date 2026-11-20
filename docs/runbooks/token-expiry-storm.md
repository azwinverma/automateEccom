# Token expiry storm

**Alerts:** ExpiredConnections (>0 for 30 min), TokenExpiryStorm (>20 in 30 min).

Channel tokens are refreshed every 5 minutes before they expire. A storm means refresh is failing.

1. `channel_connections_need_attention`; worker logs `channel_tokens_refreshed` (expired/refreshed/retry).
2. **One provider:** their OAuth is down or our app credentials changed/expired (rotated client secret,
   app review revoked). Check the provider dashboard and our `COS_*` client id/secret for it.
3. **All providers:** refresh job not running (beat down) or KEK/decryption failure (tokens are encrypted
   at rest) — check `refresh-channel-tokens` task logs for decryption errors and the KMS/KEK settings.
4. Once fixed, the next refresh run recovers connections that are still refreshable. Revoked ones need the
   seller to reconnect: they see "Reconnect" on the Channels screen and an exception on Home.

**Done when:** the count stops rising and falls as connections refresh or sellers reconnect.
