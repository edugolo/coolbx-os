#!/usr/bin/env bash
set -ouex pipefail

# De kiosk-feature gebruikt sway + waybar + chromium (zitten al in de base-pakketlaag).
# Hier enkel: scripts uitvoerbaar maken.
chmod 0755 /usr/bin/coolbx-kiosk-start /usr/bin/coolbx-kiosk-exit \
           /usr/share/coolbx/kiosk/chromium-kiosk.sh 2>/dev/null || true