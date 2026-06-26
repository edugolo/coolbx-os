#!/usr/bin/env bash
set -ouex pipefail

# De kiosk-feature gebruikt sway + waybar + chromium (zitten al in de base-pakketlaag).
# dbus-x11 levert `dbus-launch`: waybar valt daarop terug voor een sessiebus
# (de kiosk-systeemgebruiker heeft geen user-dbus zonder lingering).
dnf5 install -y --setopt=install_weak_deps=False dbus-x11

# Scripts uitvoerbaar maken.
chmod 0755 /usr/bin/coolbx-kiosk-start /usr/bin/coolbx-kiosk-exit \
           /usr/bin/coolbx-vt-lock /usr/bin/coolbx-kiosk-return \
           /usr/share/coolbx/kiosk/chromium-kiosk.sh 2>/dev/null || true

# DEV/PROD-gate (Fase 4, ADR-0022): de prod-only Chromium-hardening (DeveloperToolsAvailability:2)
# blokkeert F12/Ctrl+Shift+I — maar óók de functionele CDP (Runtime.evaluate), geverifieerd. In een
# DEV-build (ENABLE_FIRSTBOOT_USER=1) verwijderen we 'm zodat de e2e-harness (CDP) blijft werken; de
# prod-build behoudt 'm. (Een statische test bevestigt: prod-image HEEFT het bestand, dev-image niet.)
if [[ "${ENABLE_FIRSTBOOT_USER:-0}" == "1" ]]; then
  echo "DEV-build: prod-only Chromium-hardening verwijderen (DevTools blijft aan zodat CDP/Runtime.evaluate werkt)"
  rm -f /etc/chromium/policies/managed/coolbx-hardening-prod.json
fi