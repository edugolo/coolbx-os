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