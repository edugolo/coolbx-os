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
  # Audio (incl. sof-firmware: DSP-firmware = vaak dé showstopper op moderne Intel/AMD-laptops)
  pipewire wireplumber pipewire-pulseaudio
  alsa-sof-firmware
  # Netwerk
  NetworkManager NetworkManager-wifi
  # Boot splash
  plymouth plymouth-system-theme
  # Browser + kiosk-compositor (kale OS bevat deze al; kiosk-feature gebruikt ze)
  chromium
  sway waybar
  # i18n (nl_BE) — glibc-locale + GNOME-UI-vertalingen
  glibc-langpack-en glibc-langpack-nl langpacks-nl
  google-noto-sans-fonts dejavu-sans-fonts dejavu-sans-mono-fonts
  # Config-pull + utils
  ansible-core git jq
  power-profiles-daemon
  gvfs gvfs-mtp
)

dnf5 -y install --setopt=install_weak_deps=False --allowerasing "${packages[@]}"

# Hardware-firmware voor brede vlootdekking op WILLEKEURIGE schoollaptops.
# Sinds Fedora 42/43 is firmware opgesplitst en komt 'm grotendeels via comps-groep
# `@hardware-support` binnen (atheros/realtek/mt7xxx/brcmfmac + amd/intel/nvidia-gpu + sof/cirrus/
# intel-audio). Met install_weak_deps=False mist een kale fedora-bootc die firmware -> geen wifi.
dnf5 -y group install hardware-support

# iwlwifi (Intel-wifi) EXPLICIET: zit NIET in de hardware-support-comps van de fedora-bootc:43
# build-snapshot (bewezen: groep installeerde wél atheros/realtek/mt7xxx maar GEEN iwlwifi -> Intel
# AX200 bleef zonder iwlwifi-cc-a0-77.ucode). Het pakket levert exact die ucode. dvm=oud, mvm=AX2xx
# (trekt mld=BE2xx mee). Niet op de groep vertrouwen voor Intel-wifi.
dnf5 -y install iwlwifi-dvm-firmware iwlwifi-mvm-firmware

# Firefox eruit (we leveren Chromium)
dnf5 -y remove firefox firefox-langpacks 2>/dev/null || true

dnf5 clean all

# /var schoon houden (bootc-lint geeft anders waarschuwingen over dnf-logs/countme).
rm -rf /var/log/dnf* /var/lib/dnf/repos/*/countme 2>/dev/null || true