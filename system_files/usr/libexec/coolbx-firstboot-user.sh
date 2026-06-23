#!/usr/bin/env bash
set -ouex pipefail

# DEV-ONLY first-boot test-user, zodat een VM in GNOME landt voor verificatie.
# Draait één keer (markerbestand). NOOIT in prod (ENABLE_FIRSTBOOT_USER=0).
# Veiligheidsgrendel: enkel draaien als de dev-marker bestaat (defense-in-depth naast de unit-conditie).
test -e /etc/coolbx/enable-firstboot-user || { echo "geen dev-marker — firstboot-user overgeslagen"; exit 0; }

USER_NAME="${COOLBX_TEST_USER:-tester}"
USER_PASS="${COOLBX_TEST_PASS:-tester}"

mkdir -p /var/lib/coolbx
if ! id "$USER_NAME" &>/dev/null; then
  useradd -m -s /usr/bin/bash -G wheel "$USER_NAME"
  echo "${USER_NAME}:${USER_PASS}" | chpasswd
fi
touch /var/lib/coolbx/firstboot-user-done