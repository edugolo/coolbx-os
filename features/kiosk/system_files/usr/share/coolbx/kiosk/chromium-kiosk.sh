#!/usr/bin/env bash
# Start Chromium in kiosk-modus; herstart bij crash met een limiet (geen eindeloze loop).
# Flags bewezen in de kiosk-sessie (ADR-0015 + S3): chromium-browser, --password-store=basic,
# --user-data-dir (schrijfbaar), --disable-gpu + --disable-dev-shm-usage (software-rendering in VM).
set -uo pipefail

URL="${COOLBX_KIOSK_URL:-https://focus-dashboard.edugolo.be/}"
BIN="$(command -v chromium-browser || command -v chromium || true)"
[ -n "$BIN" ] || { echo "geen chromium gevonden" >&2; exit 1; }
PROFILE="${XDG_RUNTIME_DIR:-$HOME}/coolbx-chrome"

n=0
while [ "$n" -lt 10 ]; do
  "$BIN" \
    --ozone-platform=wayland \
    --user-data-dir="$PROFILE" \
    --password-store=basic \
    --disable-gpu \
    --disable-dev-shm-usage \
    --no-first-run --no-default-browser-check \
    --disable-session-crashed-bubble --disable-infobars \
    --kiosk "$URL" || true
  n=$((n + 1))
  sleep 1
done

# Te veel crashes -> sessie netjes beëindigen (terug naar GNOME via ExecStopPost).
swaymsg exit 2>/dev/null || true