#!/usr/bin/env bash
# Coolbx OS — managed-feature (Fase 4): hardening van de beheerde GNOME-laptop (vrije modus).
# Nu: klok-lockdown (geforceerde NTP + polkit weigert tijd-wijziging voor niet-beheerders).
# Follow-up (productbeslissing, "niet overdrijven"): dconf-lockdown vrije modus, downloads/print.
set -ouex pipefail

echo "::group:: managed: klok-lockdown (geforceerde NTP)"
# chronyd levert NTP → de systeemtijd volgt de server, niet de leerling. Enablen (idempotent).
systemctl enable chronyd.service 2>/dev/null || echo "warn: chronyd niet gevonden"
# De polkit-regel (system_files) weigert set-time/set-timezone/set-ntp voor niet-wheel.
echo "::endgroup::"

echo "managed feature installed"
