#!/usr/bin/env bash
# Coolbx OS — attest-feature (ADR-0013): per-toestel HMAC-handshake voor anti-spoofing.
# OS-kant van het integratiecontract: per-toestel-secret (root-only) + signing-daemon + de
# native-messaging-host die de Focus-extensie aanroept. Server-verificatie/allowlist = Focus-kant.
set -ouex pipefail

echo "::group:: attest: TPM2-tooling (B3.e — sealed device-secret)"
# systemd-creds sealt het per-toestel-secret in de TPM2; tpm2-tools voor
# diagnose/enrollment. Zonder TPM valt de keten terug op het file-secret (Tier 2).
dnf5 install -y --setopt=install_weak_deps=False tpm2-tools tpm2-tss || \
  echo "warn: tpm2-tooling niet beschikbaar — sealing valt terug op file-secret"
echo "::endgroup::"

chmod 0755 /usr/libexec/coolbx-gen-device-secret \
           /usr/libexec/coolbx-attestd \
           /usr/libexec/coolbx-attest-host \
           /usr/libexec/coolbx-exam-policy \
           /usr/bin/coolbx-enroll-info

# Het secret wordt bij first-boot gegenereerd (en op TPM-toestellen geseald);
# de daemon start daarna.
systemctl enable coolbx-device-secret.service
systemctl enable coolbx-attestd.service
# Crash-vangnet: achtergebleven examen-policy bij boot opruimen (B3.c).
systemctl enable coolbx-exam-policy-cleanup.service

echo "attest feature installed"
