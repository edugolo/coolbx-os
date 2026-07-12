#!/usr/bin/env bash
# Coolbx OS — attest-feature (ADR-0013): per-toestel HMAC-handshake voor anti-spoofing.
# OS-kant van het integratiecontract: per-toestel-secret (root-only) + signing-daemon + de
# native-messaging-host die de Focus-extensie aanroept. Server-verificatie/allowlist = Focus-kant.
set -ouex pipefail

chmod 0755 /usr/libexec/coolbx-gen-device-secret \
           /usr/libexec/coolbx-attestd \
           /usr/libexec/coolbx-attest-host \
           /usr/libexec/coolbx-exam-policy

# Het secret wordt bij first-boot gegenereerd; de daemon start daarna.
systemctl enable coolbx-device-secret.service
systemctl enable coolbx-attestd.service
# Crash-vangnet: achtergebleven examen-policy bij boot opruimen (B3.c).
systemctl enable coolbx-exam-policy-cleanup.service

echo "attest feature installed"
