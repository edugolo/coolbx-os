#!/usr/bin/env bash
set -ouex pipefail

# Boot naar grafische sessie + core services.
systemctl set-default graphical.target
# Boot-kritisch: géén `|| true` — een falende enable mag niet stil een toestel zonder DM opleveren.
systemctl enable gdm.service
systemctl enable NetworkManager.service

# Locale + toetsenbord (België / Nederlands).
echo "LANG=nl_BE.UTF-8" >/etc/locale.conf
echo "KEYMAP=be" >/etc/vconsole.conf
mkdir -p /etc/X11/xorg.conf.d
cat >/etc/X11/xorg.conf.d/00-keyboard.conf <<'EOF'
Section "InputClass"
    Identifier "system-keyboard"
    MatchIsKeyboard "on"
    Option "XkbLayout" "be"
EndSection
EOF

# DEV-ONLY: first-boot test-user + GDM-autologin zodat de VM in GNOME landt voor verificatie.
# Prod-builds zetten ENABLE_FIRSTBOOT_USER=0 → geen autologin, geen testuser.
if [[ "${ENABLE_FIRSTBOOT_USER:-0}" == "1" ]]; then
  echo "DEV-build: testuser + GDM-autologin inschakelen (NOOIT prod)"
  mkdir -p /etc/coolbx
  touch /etc/coolbx/enable-firstboot-user
  systemctl enable coolbx-firstboot-user.service
  mkdir -p /etc/gdm
  cat >/etc/gdm/custom.conf <<'EOF'
[daemon]
AutomaticLoginEnable=True
AutomaticLogin=tester
EOF
else
  # Prod: fail-safe — verzeker dat er GEEN dev-naden in de image zitten.
  rm -f /etc/gdm/custom.conf
  test ! -e /etc/coolbx/enable-firstboot-user || { echo "FAIL: dev-marker in prod-build"; exit 1; }
  if systemctl is-enabled coolbx-firstboot-user.service 2>/dev/null | grep -qx enabled; then
    echo "FAIL: firstboot-unit enabled in prod-build"; exit 1
  fi
fi

chmod 0755 /usr/libexec/coolbx-firstboot-user.sh