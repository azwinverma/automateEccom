#!/usr/bin/env bash
# Run the Nivaro Flutter app against the local stack (start scripts/dev.sh first).
#
#   scripts/mobile.sh            # first connected Android phone, else Chrome
#   scripts/mobile.sh android    # USB Android phone (adb reverse: the phone's localhost → this Mac)
#   scripts/mobile.sh chrome     # Flutter web in Chrome (port 5310)
#   scripts/mobile.sh <device-id>
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
API_PORT="${API_PORT:-8090}"
WEB_PORT="${WEB_PORT:-3010}"
FLUTTER_WEB_PORT="${FLUTTER_WEB_PORT:-5310}"
TARGET="${1:-auto}"

fail() { printf '\033[31m✗ %s\033[0m\n' "$*" >&2; exit 1; }
ok() { printf '\033[32m✓\033[0m %s\n' "$*"; }

command -v flutter >/dev/null || fail "flutter not found"
curl -sf -o /dev/null "http://localhost:$API_PORT/readyz" || fail "Nivaro API is not running on :$API_PORT. Start it with scripts/dev.sh"
ok "API reachable on :$API_PORT"

ADB="$(command -v adb || true)"
[[ -z "$ADB" && -x "$HOME/Library/Android/sdk/platform-tools/adb" ]] && ADB="$HOME/Library/Android/sdk/platform-tools/adb"

android_id() { [[ -n "$ADB" ]] && "$ADB" devices | awk 'NR>1 && $2=="device" {print $1; exit}'; }

if [[ "$TARGET" == "auto" ]]; then
  if [[ -n "$(android_id || true)" ]]; then TARGET="android"; else TARGET="chrome"; fi
fi

DEFINES=(--dart-define=API_BASE_URL="http://localhost:$API_PORT" --dart-define=WEB_BASE_URL="http://localhost:$WEB_PORT")
cd "$ROOT/apps/mobile"

case "$TARGET" in
  android)
    [[ -n "$ADB" ]] || fail "adb not found (Android SDK platform-tools)"
    DEVICE="$(android_id)"
    [[ -n "$DEVICE" ]] || fail "no Android phone connected (enable USB debugging, accept the prompt on the phone)"
    # The phone's localhost:8090/3010 now reach this Mac, so signed upload URLs and links just work.
    "$ADB" -s "$DEVICE" reverse "tcp:$API_PORT" "tcp:$API_PORT" >/dev/null
    "$ADB" -s "$DEVICE" reverse "tcp:$WEB_PORT" "tcp:$WEB_PORT" >/dev/null
    ok "adb reverse :$API_PORT and :$WEB_PORT on $DEVICE"
    exec flutter run -d "$DEVICE" "${DEFINES[@]}"
    ;;
  chrome)
    exec flutter run -d chrome --web-port "$FLUTTER_WEB_PORT" "${DEFINES[@]}"
    ;;
  *)
    exec flutter run -d "$TARGET" "${DEFINES[@]}"
    ;;
esac
