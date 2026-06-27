# ADR-0027: Nonfree media (codecs + hardware-decode + Widevine) als optionele feature

- **Status:** Aanvaard (richting)
- **Datum:** 2026-06-27
- **Beslissers:** Johan, Claude
- **Bron:** ublue-os/main + rpmfusion.org/Howto/Multimedia + Fedora chromium.spec (Widevine-zoeklocaties).

## Context
Standaard Fedora levert **bewust alleen vrije codecs** (juridisch/patenten): VP9/AV1/WebM/Opus werken,
maar volledige H.264/H.265/AAC, hardware-video-decode en DRM (Widevine) ontbreken. Voor een zuinig
schooltoestel (o.a. Surface Go 2) telt **hardware-versnelde video** zwaar (vloeiend + batterij), en
sommige les-/streamingplatforms vereisen H.264/AAC of Widevine-DRM. RPM Fusion + Google's Widevine
vullen dit, maar gaan **verder dan wat Fedora zelf doet** en raken patent-/licentie-afwegingen.

## Beslissing
**Nonfree media is een APARTE, optionele `media-nonfree`-feature** (geen OS-kern). Een schone build
kan 'm weglaten; de pilotvloot zet 'm aan (institutionele opt-in). De feature doet:

- **RPM Fusion (free + nonfree)** via de `*-release`-RPM's (eigen GPG-keys meegeleverd).
- **Hardware-decode (VAAPI):** `mesa-va-drivers-freeworld` + `mesa-vdpau-drivers-freeworld` (vervangen
  Fedora's gecrippelde variant) + `intel-media-driver` (iHD, Intel Gen9.5+) + `libva-utils`.
- **Brede codecs voor native apps:** `ffmpeg` + nonfree gstreamer-plugins. (Chromium gebruikt gstreamer
  niet; voor Chromium komt de codec-winst uit VAAPI-hardware-decode + de aanwezige `openh264`.)
- **Widevine-CDM:** geëxtraheerd uit de officiële **Google-Chrome-RPM** naar
  `/usr/lib64/chromium-browser/WidevineCdm` (waar Fedora-chromium 'm vindt), Chrome daarna verwijderd.
  Juridisch het schoonst (Google distribueert de CDM zelf); ublue/Bazzite bakken 'm bewust niet in.
- **Chromium-VAAPI-vlaggen** in `/etc/chromium/chromium.conf` (`VaapiVideoDecoder` + GL-varianten).

## Gevolgen
- **Juridisch:** patent-belaste codecs + herdistributie van Google's binaire Widevine-CDM op interne
  toestellen. Gangbaar en laag-risico voor een interne/educatieve vloot, maar **geen door de
  rechthouders verleende herdistributielicentie** — een bewuste afweging van de instelling, niet van
  Coolbx OS. Daarom optioneel + gedocumenteerd.
- **Beperkingen:** Widevine op Linux = **L3 (software)** → SD-DRM (geen HD). `chromium-libs-media-
  freeworld` bestaat niet voor F43 → Chromium's *software*-AAC kan beperkt zijn; H.264/H.265-video gaat
  via VAAPI (hardware). HEVC in Chromium is wisselvallig.
- **Onderhoud:** de Widevine-versie volgt de Chrome-RPM uit de bouw (vers per rebuild = goed, geen
  drift). RPM Fusion-swaps worden elke build opnieuw toegepast (image-rebuild-model, geen runtime-
  layering → geen versionlock nodig).

## Alternatieven
- **Niets doen (Fedora-default, alleen vrije codecs)** — verworpen voor de pilot: geen hardware-decode
  (slechte video-ervaring op de zuinige Surfaces) en geen H.264/DRM voor leerplatforms.
- **negativo17 `fedora-multimedia` (het ublue-patroon)** — gelijkwaardig alternatief voor RPM Fusion;
  niet gekozen omdat RPM Fusion's swaps eenvoudiger zijn voor onze stock-kernel-zonder-akmods.
- **`google-chrome-stable` draaien i.p.v. Fedora-chromium** — verworpen: onze stack staat op
  Fedora-chromium + de force-installed Focus-extensie ([ADR-0011](0011-chromium-rpm-policy-in-image.md)).
