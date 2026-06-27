#!/usr/bin/env bash
# Coolbx OS — media-nonfree feature (OPTIONEEL, JURIDISCH GEVOELIG).
#
# Voegt patent-belaste codecs + hardware-videoversnelling + Widevine-DRM toe. Standaard Fedora levert
# dit bewust NIET; dit gaat verder (RPM Fusion + Google's Widevine) — het is een institutionele
# opt-in (zie ADR-0027). Een schone build laat deze feature weg. Patroon: rpmfusion.org/Howto/Multimedia
# + Widevine-extractie uit de officiële Google-Chrome-RPM (ublue/Bazzite bakken Widevine niet zelf).
set -ouex pipefail
FEDV="$(rpm -E %fedora)"

echo "::group:: media-nonfree: RPM Fusion (free + nonfree)"
# De *-release-RPM's brengen hun eigen GPG-keys + .repo-bestanden mee (geen losse import nodig).
dnf5 -y install \
  "https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-${FEDV}.noarch.rpm" \
  "https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-${FEDV}.noarch.rpm"
echo "::endgroup::"

echo "::group:: media-nonfree: hardware-video-decode (VAAPI)"
# mesa-*-freeworld vervangt Fedora's gecrippelde VA/VDPAU-drivers (--allowerasing = non-interactief,
# werkt of de Fedora-variant nu wél of niet geïnstalleerd is). intel-media-driver (iHD) voor Intel
# Gen9.5/Amber Lake (Surface Go 2) t/m nieuw. libva-utils levert `vainfo` voor verificatie.
dnf5 -y install --allowerasing \
  mesa-va-drivers-freeworld mesa-vdpau-drivers-freeworld intel-media-driver libva-utils
echo "::endgroup::"

echo "::group:: media-nonfree: brede codecs (native apps)"
# Volledige ffmpeg + nonfree gstreamer-plugins — voor de native media-apps (geluidsrecorder, snapshot).
# Chromium gebruikt gstreamer NIET (eigen media-laag + VAAPI), dus dit is voor de desktop-apps.
dnf5 -y install --allowerasing \
  ffmpeg gstreamer1-plugins-ugly gstreamer1-plugins-bad-freeworld gstreamer1-libav
echo "::endgroup::"

echo "::group:: media-nonfree: Widevine CDM (DRM) — extractie uit Google Chrome"
# Fedora-chromium zoekt de CDM o.a. in /usr/lib64/chromium-browser/WidevineCdm (immutable, mee-gebakken).
# We halen Google's eigen binaire CDM uit de officiële Chrome-RPM (juridisch het schoonst: Google
# distribueert 'm zelf) en verwijderen Chrome weer. NB: dit herdistribueert Google's CDM op interne
# schooltoestellen — gangbaar, laag risico voor intern/educatief, maar bewust (ADR-0027). Widevine = L3
# (software) op Linux → SD-DRM (Netflix/Spotify SD + meeste leerplatforms), geen HD-DRM.
dnf5 -y install "https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm"
install -d /usr/lib64/chromium-browser/WidevineCdm
cp -a /opt/google/chrome/WidevineCdm/. /usr/lib64/chromium-browser/WidevineCdm/
dnf5 -y remove google-chrome-stable
rm -rf /opt/google /etc/yum.repos.d/google-chrome.repo /etc/cron.daily/google-chrome /etc/default/google-chrome 2>/dev/null || true
echo "::endgroup::"

echo "::group:: media-nonfree: Chromium hardware-decode aanzetten"
# VAAPI-decode op Wayland. Idempotent appenden aan de door Fedora-chromium gesourcede conf.
CONF=/etc/chromium/chromium.conf
if [ -f "$CONF" ] && ! grep -q 'VaapiVideoDecoder' "$CONF"; then
  printf '\n# Coolbx OS media-nonfree: hardware-video-decode (VAAPI) op Wayland\nCHROMIUM_FLAGS="${CHROMIUM_FLAGS} --enable-features=VaapiVideoDecoder,VaapiVideoDecodeLinuxGL,VaapiIgnoreDriverChecks,PlatformHEVCDecoderSupport --use-gl=angle --use-angle=gl --ignore-gpu-blocklist"\n' >> "$CONF"
fi
echo "::endgroup::"

# Opschoning (bootc-lint: niets achterlaten in /var).
dnf5 clean all
rm -rf /var/cache/* /var/lib/dnf/history* /var/log/dnf* /var/opt 2>/dev/null || true

echo "media-nonfree feature installed"
