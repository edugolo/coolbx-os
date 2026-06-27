#!/usr/bin/env bash
# Coolbx OS — apps-feature: gecureerde basis-apps voor de VRIJE MODUS (GNOME desktop).
# Los van de OS-kern (modulair, ADR-0012) én los van de toetsmodus/kiosk. Maakt een schooltoestel
# in vrije modus als een "echte computer" voelen i.p.v. enkel een browser. Bewust LICHT: zware
# office-suites = web (geen native LibreOffice); geen games/maps/weather. Pakketnamen geverifieerd
# in F43 (let op: nieuwe GNOME-namen — `papers` i.p.v. evince, `snapshot` = camera, `loupe` = beeld).
set -ouex pipefail

dnf5 -y install \
  gnome-calculator \
  gnome-text-editor \
  papers \
  loupe \
  file-roller \
  gnome-clocks \
  snapshot \
  gnome-sound-recorder \
  gnome-system-monitor

# NB: `snapshot` (camera) en `gnome-sound-recorder` leunen op gstreamer/pipewire. De camera-HARDWARE
# op de Surface Go 2 (Intel IPU3) werkt los hiervan (nog) niet — apart spoor, getemperde verwachting.

echo "apps feature installed"
