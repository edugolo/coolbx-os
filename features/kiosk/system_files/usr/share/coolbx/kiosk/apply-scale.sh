#!/usr/bin/env bash
# Past de door GNOME/mutter gekozen schaal toe op alle kiosk-outputs, zodat de toetskiosk dezelfde
# grootte heeft als de GNOME-desktop. Zonder dit kiest wlroots agressief integer-2.0 (kiosk groter
# dan de desktop). COOLBX_KIOSK_SCALE wordt door coolbx-kiosk-start gezet uit de monitors.xml van de
# GNOME-gebruiker die de kiosk start. Leeg → niets doen (wlroots-auto blijft gelden).
set -eu
s="${COOLBX_KIOSK_SCALE:-}"
[ -n "$s" ] || exit 0
exec swaymsg output '*' scale "$s"
