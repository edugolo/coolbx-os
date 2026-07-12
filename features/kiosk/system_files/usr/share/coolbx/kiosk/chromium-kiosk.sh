#!/usr/bin/env bash
# Start Chromium in kiosk-modus; herstart bij crash met een limiet (geen eindeloze loop).
# Flags bewezen in de kiosk-sessie (ADR-0015 + S3): chromium-browser, --password-store=basic,
# --user-data-dir (schrijfbaar), --disable-gpu + --disable-dev-shm-usage (software-rendering in VM).
set -uo pipefail

URL="${COOLBX_KIOSK_URL:-https://focus-dashboard.edugolo.be/}"
BIN="$(command -v chromium-browser || command -v chromium || true)"
[ -n "$BIN" ] || { echo "geen chromium gevonden" >&2; exit 1; }
PROFILE="${XDG_RUNTIME_DIR:-$HOME}/coolbx-chrome"

# DEV-ONLY (ADR-0020): CDP-debugpoort voor de e2e-harness. NOOIT in productie —
# een open remote-debugging-port in een toetskiosk = volledige browsercontrole
# (valsspeel-vector). Enkel actief als de dev-VM COOLBX_KIOSK_DEBUG=1 zet; de
# prod-image zet die env nooit. user-data-dir (niet-default) is sowieso al gezet,
# wat Chrome 136+ vereist; --remote-allow-origins is nodig vanaf Chrome 111.
DEBUG_FLAGS=()
if [ "${COOLBX_KIOSK_DEBUG:-0}" = "1" ]; then
  echo "WAARSCHUWING: CDP-debugpoort 9222 actief (COOLBX_KIOSK_DEBUG=1) — DEV ONLY" >&2
  DEBUG_FLAGS=(
    --remote-debugging-port=9222
    --remote-allow-origins=http://127.0.0.1:9222
  )
fi
# DEV-ONLY: laad de Focus-extensie UNPACKED uit een pad (test van managed-storage tegen de
# echte extensie zonder de productie-force-install/.crx). Productie gebruikt force-install
# via ExtensionSettings (update.xml). NOOIT in prod — env wordt daar nooit gezet.
if [ -n "${COOLBX_KIOSK_LOAD_EXT:-}" ] && [ -d "${COOLBX_KIOSK_LOAD_EXT}" ]; then
  echo "DEV: unpacked extensie laden uit ${COOLBX_KIOSK_LOAD_EXT}" >&2
  DEBUG_FLAGS+=(
    "--load-extension=${COOLBX_KIOSK_LOAD_EXT}"
    "--disable-extensions-except=${COOLBX_KIOSK_LOAD_EXT}"
  )
fi

n=0
while [ "$n" -lt 10 ]; do
  # Singleton afdwingen: ruim een eventueel nog draaiende chromium voor DIT profiel op.
  # Anders draagt een nieuwe start z'n URL over aan de bestaande instance (singleton-handoff),
  # keert meteen terug, en zou deze herstart-loop stapels --app-vensters openen.
  pkill -f -- "--user-data-dir=$PROFILE" 2>/dev/null && sleep 1 || true

  # GPU-loos alleen bij software-rendering (F-02-050): coolbx-kiosk-start zet
  # COOLBX_KIOSK_SW_RENDER=1 in een VM/dev; op echte hardware gebruikt de
  # kiosk de GPU (vlottere examen-rendering).
  GPU_FLAGS=()
  [ "${COOLBX_KIOSK_SW_RENDER:-0}" = "1" ] && GPU_FLAGS+=(--disable-gpu)

  start=$SECONDS
  "$BIN" \
    --ozone-platform=wayland \
    --user-data-dir="$PROFILE" \
    --password-store=basic \
    "${GPU_FLAGS[@]}" \
    --disable-dev-shm-usage \
    --no-first-run --no-default-browser-check \
    --disable-session-crashed-bubble --disable-infobars \
    --start-maximized \
    "${DEBUG_FLAGS[@]}" \
    --app="$URL" || true

  # Te snel terug (<5s) = handoff of directe crash → tel als faal (anti-spin);
  # een normale, langere sessie reset de teller zodat één late crash niet meetelt.
  if [ $(( SECONDS - start )) -lt 5 ]; then n=$((n + 1)); else n=0; fi
  sleep 1
done

# Te veel crashes -> sessie netjes beëindigen (terug naar GNOME via ExecStopPost).
swaymsg exit 2>/dev/null || true