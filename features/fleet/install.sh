#!/usr/bin/env bash
# Coolbx OS — fleet-feature (Fase 5): staged auto-update + greenboot-health + signing-scaffold.
set -ouex pipefail

echo "::group:: fleet: greenboot (auto-rollback bij gefaalde boots)"
# greenboot rolt na N gefaalde boots automatisch terug naar de vorige deployment.
dnf5 install -y --setopt=install_weak_deps=False greenboot greenboot-default-health-checks || \
  echo "warn: greenboot niet beschikbaar in de repo — health-check blijft staan, engine ontbreekt"
chmod 0755 /etc/greenboot/check/required.d/50-coolbx-kiosk-health.sh
echo "::endgroup::"

echo "::group:: fleet: observability (coolbx-status voor schoolIT)"
# Lokaal statusoverzicht (geen open poort). Web-beheer via Cockpit = optioneel/firewalled.
chmod 0755 /usr/bin/coolbx-status
echo "::endgroup::"

echo "::group:: fleet: ansible-pull (vlootconfig per rol)"
# ansible-core voor periodieke per-rol-config-pull (Fase 6). STRAK GESCOPED: enkel runtime-config,
# nooit software/kernconfig. De repo-URL staat in /etc/coolbx/ansible.conf (no-op tot gezet).
dnf5 install -y --setopt=install_weak_deps=False ansible-core || \
  echo "warn: ansible-core niet beschikbaar in de repo"
chmod 0755 /usr/libexec/coolbx-ansible-pull
systemctl enable coolbx-ansible-pull.timer
echo "::endgroup::"

echo "::group:: fleet: staged off-hours auto-update"
# Mask de default fetch-apply-timer (kan APPLYEN/rebooten op willekeurig moment) en gebruik onze
# eigen STAGE-only timer (04:00 + Persistent + jitter). 'bootc upgrade' staget; reboot = natuurlijk moment.
systemctl mask bootc-fetch-apply-updates.timer 2>/dev/null || true
systemctl enable coolbx-update.timer
echo "::endgroup::"

echo "::group:: fleet: image-signing (scaffold — niet actief)"
# De strikte on-device handtekening-policy staat als TEMPLATE in /usr/share/coolbx/signing/ en wordt
# pas actief NA het opzetten van de cosign-keypair + gesigneerde CI-images (zie docs/SIGNING.md) —
# een 'default: reject' zonder geldige sleutel zou álle updates breken. Activatie-gate:
PUB=/ctx/features/fleet/cosign.pub
if [ -s "$PUB" ] && ! grep -q "PLACEHOLDER" "$PUB"; then
  echo "fleet: echte cosign.pub gevonden → on-device verificatie bakken"
  install -D -m0644 "$PUB" /etc/pki/containers/coolbx-os.pub
  # NB: policy.json/registries.d nog handmatig activeren met de juiste owner (docs/SIGNING.md),
  # zodat een verkeerde owner niet stilletjes alle updates breekt.
else
  echo "fleet: cosign.pub is placeholder → signing blijft scaffold (docs/SIGNING.md)"
fi
echo "::endgroup::"

echo "fleet feature installed"
