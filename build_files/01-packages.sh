#!/usr/bin/env bash
set -ouex pipefail

# DNF-tuning voor reproduceerbare, snellere builds.
mkdir -p /etc/dnf
cat >/etc/dnf/dnf.conf <<'EOF'
[main]
gpgcheck=1
installonly_limit=3
clean_requirements_on_remove=True
install_weak_deps=False
max_parallel_downloads=10
fastestmirror=True
keepcache=True
EOF

# Gecureerde set voor een functionele beheerde GNOME-desktop + de kiosk-toolchain.
# Werkt op een kale fedora-bootc; op een batteries-included base zijn de meeste al aanwezig (no-op).
packages=(
  # GNOME desktop (minimaal-maar-functioneel)
  gnome-shell gnome-session gdm
  gnome-control-center gnome-settings-daemon
  nautilus gnome-keyring
  xdg-desktop-portal xdg-desktop-portal-gnome xdg-user-dirs-gtk
  # Graphics / firmware (hardware-support — geleerd van Universal Blue, ADR-0004)
  mesa-dri-drivers mesa-vulkan-drivers
  linux-firmware
  # Audio
  pipewire wireplumber pipewire-pulseaudio
  # Netwerk
  NetworkManager NetworkManager-wifi
  # Boot splash
  plymouth plymouth-system-theme
  # Browser + kiosk-compositor (kale OS bevat deze al; kiosk-feature gebruikt ze)
  chromium
  sway waybar
  # i18n (nl_BE)
  glibc-langpack-en glibc-langpack-nl
  google-noto-sans-fonts dejavu-sans-fonts dejavu-sans-mono-fonts
  # Config-pull + utils
  ansible-core git jq
  power-profiles-daemon
  gvfs gvfs-mtp
)

dnf5 -y install --setopt=install_weak_deps=False --allowerasing "${packages[@]}"

# Firefox eruit (we leveren Chromium)
dnf5 -y remove firefox firefox-langpacks 2>/dev/null || true

dnf5 clean all

# /var schoon houden (bootc-lint geeft anders waarschuwingen over dnf-logs/countme).
rm -rf /var/log/dnf* /var/lib/dnf/repos/*/countme 2>/dev/null || true