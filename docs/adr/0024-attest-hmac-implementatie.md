# ADR-0024: Toestel-attestatie HMAC-scaffold — implementatie

- **Status:** Aanvaard (geverifieerd; OS-kant compleet, server-kant = Focus)
- **Datum:** 2026-06-25
- **Beslissers:** Johan, Claude
- **Implementeert:** [ADR-0013](0013-anti-spoofing-hmac-per-device.md) (richting).

## Wat
De OS-kant van de anti-spoofing-handshake ([ADR-0013](0013-anti-spoofing-hmac-per-device.md)) is gebouwd als
de `attest`-feature en koude-boot-geverifieerd (`tests/test_09_attest.py`, 37/37). Volledige beschrijving +
het server-contract: `docs/ATTESTATION.md`.

- **Per-toestel-secret** `/etc/coolbx/device-secret` (`0600 root`), first-boot gegenereerd
  (`coolbx-device-secret.service`). **Geverifieerd:** de leerling-sessie (tester) kan het niet lezen.
- **Root signing-daemon** `coolbx-attestd` op `/run/coolbx-attest.sock`: tekent challenges met
  HMAC-SHA256, **lekt het secret nooit**. **Geverifieerd:** correcte HMAC (matcht onafhankelijke berekening),
  andere challenge → andere signature (geen replay).
- **Native-messaging-host** `coolbx-attest-host` (kiosk-user) forwardt de extensie-challenge naar de daemon;
  manifest met `allowed_origins` = **exact** `chrome-extension://makdakigkdbicdljgdclgnejachcohag/`.
  **Geverifieerd:** de native-messaging-wire (4-byte LE-lengte + JSON) levert `{deviceId, signature}`.
- `deviceId = sha256("coolbx:" + machine-id)[:32]` (stabiel, lekt machine-id niet).

## Privilegemodel (de kern van het ontwerp)
Het secret is root-only, maar de native-host draait als kiosk-user (kind van Chromium). Daarom **tekent een
root-daemon** op een unix-socket i.p.v. de host het secret te laten lezen: de leerling kan wél een server-nonce
laten tekenen (de legitieme operatie) maar het secret **niet extraheren**. Socket `0666` — tekenen is de
toegestane operatie; exfiltratie kan niet.

## Grenzen (bewust, conform ADR-0013 = fast-follow)
- **Relay-aanval** (nonce doorsturen naar een echt toestel) niet volledig dicht — bind challenge aan
  sessie/tijd (server doet dit deels) + overweeg peer-cred op de socket.
- **Fysieke schijf-diefstal** geeft het secret prijs → **TPM-sealing + FDE** als hardening.
- **Server-kant** (allowlist deviceId→secret, verificatie, revocatie) = Focus-team (`docs/ATTESTATION.md`).
- **Enrollment:** pilot = lokaal secret + handmatig registreren; productie = server deelt secret bij enrollment uit.

## Hoe geverifieerd
Zelf-bevattende lokale test van de echte daemon+host (HMAC-correctheid, native-messaging-wire, geen replay) +
koude-boot e2e (`test_09`: secret root-only, daemon active, tekent, manifest-extensie-ID).
