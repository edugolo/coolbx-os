# ADR-0027 — TPM2-sealed device-secret, FDE-installatiepad en toestel-tiering (B3.e)

**Status:** geaccepteerd · **Datum:** 2026-07-13 · **Audit:** F-03-006 (+F-03-014-aansluiting)
**Context:** verbeterplan fase B, deelpakket B3.e (briefs/B3-implementatiebrief.md).

## Beslissing

1. **Secret-sealing (Tier 1).** Het per-toestel HMAC-secret (ADR-0013/0024) leeft op TPM-toestellen
   uitsluitend als TPM2-sealed credential: `/etc/coolbx/device-secret.cred`, gemaakt met
   `systemd-creds encrypt --with-key=tpm2` in `coolbx-gen-device-secret` (boot-oneshot zolang er
   geen credential is). `coolbx-attestd` decrypt in-memory (`systemd-creds decrypt` als subprocess,
   gecachet); plaintext raakt de schijf nooit. Fysieke schijf-extractie levert dus geen bruikbaar
   secret meer op — de TPM van hetzelfde toestel is nodig.
2. **Upgrade-in-place.** Een bestaand plain secret (pre-B3.e-toestel) wordt bij de eerste boot met
   bruikbare TPM geseald **met behoud van waarde** en daarna geshred: de bestaande server-registratie
   (deviceId→secret) blijft geldig, geen her-enrollment nodig.
3. **Geen PCR-binding** (`--tpm2-pcrs=""`). Binding aan de chip = binding aan het toestel; binding
   aan PCR's (firmware-meetstand) zou elk firmware/SecureBoot-event het secret onklaar laten maken
   zonder recovery-pad. Measured-boot-binding is een aparte volgende trede (vereist PCR-policy- en
   SecureBoot-beheer in de vloot).
4. **Tiering.** `/etc/coolbx/device-class` = `tpm-sealed` | `file-secret` (informatief);
   `coolbx-enroll-info` (root) print `{deviceId, deviceClass, fde, secret}` voor de registratie-flow.
   De Focus-server vertrouwt enkel de klasse in zíjn register en handhaaft met
   `EXAM_MIN_DEVICE_CLASS` (B3.a). Tier 2 (geen TPM) blijft werken voor lesbegeleiding; examen-kiosk
   is per deployment te weren.
5. **FDE = installatiepad, niet de dev-qcow2.** bootc-image-builder kent geen LUKS-disk-customization
   (geverifieerd: blueprint-reference ondersteunt enkel `plain`/`lvm`), dus FDE komt van
   `bootc install to-disk --block-setup tpm2-luks` bij de hardware-uitrol + verplichte
   recovery-key-enrollment na de eerste boot (bekende bootc-caveat: zonder failover sluit een
   TPM-wijziging het toestel buiten). `coolbx-enroll-info` rapporteert de FDE-status eerlijk
   (`lsblk`-crypt-detectie) zodat een Tier-1-registratie verifieerbaar is.

## Testbaarheid (e2e)

De dev-VM krijgt een **swtpm-vTPM** (Justfile `dev-vm`/`dev-vm-gui`; staat in `output/swtpm`,
`--terminate` koppelt de levensduur aan qemu). `tests/test_15_tpm_seal.py` bewijst: TPM zichtbaar +
bruikbaar voor systemd-creds; sealed credential zonder plaintext-restant; klasse `tpm-sealed`;
HMAC-verificatie end-to-end met het via `coolbx-enroll-info` verkregen secret (echte crypto-check);
en het upgrade-pad (plain → sealed, waarde behouden, in de -snapshot-VM). `test_09` is tier-bewust.
FDE-in-VM is bewust niet geautomatiseerd (geen LUKS-qcow2 bouwbaar); het installatiepad staat in
docs/ATTESTATION.md.

## Gevolgen

- Image: `tpm2-tools`/`tpm2-tss` in de attest-feature; nieuwe `coolbx-enroll-info`;
  `coolbx-device-secret.service` draait op conditie `!device-secret.cred` (dekt first-boot én upgrade).
- Enrollment-doc en tier-tabel: docs/ATTESTATION.md. Focus-kant hoefde niet te wijzigen
  (device-class-register + `EXAM_MIN_DEVICE_CLASS` bestaan sinds B3.a).
- [extern] Voor Tier-1-vloten: `EXAM_MIN_DEVICE_CLASS=tpm-sealed` zetten in het Focus-deployment
  zodra alle examen-toestellen tpm-sealed geregistreerd zijn.
