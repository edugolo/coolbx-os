#!/usr/bin/env bash
set -ouex pipefail

# Boot naar grafische sessie + core services.
systemctl set-default graphical.target
systemctl enable gdm.service || true
systemctl enable NetworkManager.service || true

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
if [[ "${ENABLE_FIRSTBOOT_USER:-1}" == "1" ]]; then
  mkdir -p /etc/coolbx
  touch /etc/coolbx/enable-firstboot-user
  systemctl enable coolbx-firstboot-user.service || true
  mkdir -p /etc/gdm
  cat >/etc/gdm/custom.conf <<'EOF'
[daemon]
AutomaticLoginEnable=True
AutomaticLogin=tester
EOF
fi

chmod 0755 /usr/libexec/coolbx-firstboot-user.sh || true