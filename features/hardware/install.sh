#!/usr/bin/env bash
# Coolbx OS — hardware-feature: hardware-/input-enablement los van cosmetische branding.
# Vandaag: GNOME input-defaults (touchpad altijd aan op 2-in-1's zoals de Surface — de Type
# Cover meldt zich óók als 'muis', wat GNOME's touchpad-uitschakeling triggert). Groeit mee
# met laptopmodel-quirks. Firmware-pakketten zelf zitten in build_files/01-packages.sh.
#
# Let op: de dconf-`local`-db-machinerie (profile/user) komt van de branding-feature; daarom
# hoort 'hardware' ná 'branding' in FEATURES te staan. We draaien hier zelf `dconf update`
# (idempotent) zodat onze key-file óók gecompileerd wordt als branding's update al liep.
set -ouex pipefail

echo "::group:: hardware: GNOME input-defaults (dconf)"
if command -v dconf >/dev/null 2>&1; then
    dconf update || echo "warn: dconf update failed (db compiles at boot)"
fi
echo "::endgroup::"

echo "hardware feature installed"
