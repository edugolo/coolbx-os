# Toestel-attestatie — HMAC-handshake (ADR-0013)

Anti-spoofing: bewijst aan de Focus-server dat de Focus-extensie op een **echt Coolbx OS-toestel** draait
(en niet op een willekeurige laptop met de extensie). Sluit de casual-spoof-gap; relay-resistentie + TPM
zijn fast-follow.

## Architectuur (OS-kant — gebouwd in de `attest`-feature)

```
Focus-extensie ──connectNative("be.edugolo.coolbx.attest")──▶ coolbx-attest-host  (draait als kiosk-user)
   {challenge: <server-nonce>}                                      │ unix-socket
                                                                    ▼
                                            coolbx-attestd (root) ── leest /etc/coolbx/device-secret (0600 root)
                                                                    │ HMAC-SHA256(secret, challenge)
   {deviceId, signature} ◀──────────────────────────────────────── ┘  (secret verlaat het root-proces NOOIT)
```

- **Per-toestel-secret** — bij first-boot gegenereerd (`coolbx-device-secret.service`). Sinds B3.e
  (F-03-006) **TPM2-sealed** op toestellen met een TPM: op schijf staat alleen
  `/etc/coolbx/device-secret.cred` (systemd-creds, `0600 root`); de plaintext bestaat enkel in het
  geheugen van de daemon. Zonder TPM (Tier 2): plain file `/etc/coolbx/device-secret` (`0600 root`).
  Een bestaand plain secret wordt bij de eerste boot mét TPM **in-place geseald** (zelfde waarde →
  de server-registratie blijft geldig) en de plaintext vernietigd. De leerling-sessie kan in geen
  van beide vormen lezen.
- **Signing-daemon** `coolbx-attestd` (root, `/run/coolbx-attest.sock`) — tekent challenges, lekt het
  secret nooit. De leerling kan wél een server-nonce laten tekenen (legitiem) maar het secret niet extraheren.
- **Native-messaging-host** `coolbx-attest-host` (kiosk-user) + manifest
  `/etc/chromium/native-messaging-hosts/be.edugolo.coolbx.attest.json` met `allowed_origins` = **exact** de
  Focus-extensie-ID (`makdakigkdbicdljgdclgnejachcohag`).

## Contract met de Focus-server (Focus-kant)

1. Server stuurt een **nonce** (challenge) naar de extensie.
2. Extensie → `connectNative` → `{deviceId, session, signature}` met
   **`signature = HMAC-SHA256(secret, nonce + "|" + session)`**.
3. Server zoekt `deviceId` in de **enrollment-allowlist** (deviceId→secret), herberekent
   `HMAC(secret, nonce + "|" + session)` en verifieert. Match → vertrouwd toestel; geen match → weigeren.
4. **Proctored toets ⇒ vereis `session == "kiosk"`.** Een `session=free`-claim mag wél een begeleidende
   Focus-modus gebruiken, maar **geen proctoring**. De claim zit in de getekende boodschap → onvervalsbaar:
   een vrije-modus-proces krijgt `session=free` van de kernel (SO_PEERCRED) en kan geen geldige
   `kiosk`-signature produceren (heeft het secret niet).
5. **Revocatie:** verwijder `deviceId` uit de allowlist (kwijt/gestolen toestel).

`deviceId` = `sha256("coolbx:" + machine-id)[:32]` (stabiel, lekt de machine-id niet).
`session` ∈ {`kiosk`, `free`}, bepaald door de UID van de aanroeper (coolbx-kiosk → kiosk).

### `kioskMode` vs `session` (belangrijk)
De `kioskMode`-managed-storage-vlag is het **ChromeOS-MGS**-signaal (één kiosk-sessie per toestel) en staat
op Coolbx OS **bewust niet** in de globale policy — een globale vlag zou de extensie óók in de vrije GNOME-modus
"kiosk" laten denken (de join/proctoring-UI verscheen daar). Op Coolbx OS is **`session=kiosk` (deze attestatie)
het gezaghebbende, per-sessie, onvervalsbare kiosk-signaal**. De extensie bepaalt "kiosk-context" als:
`session=="kiosk"` (Coolbx OS) **OR** `kioskMode==true` (ChromeOS-MGS-fallback).

## Enrollment

- **Pilot/dev:** secret lokaal gegenereerd — registreer het toestel eenmalig in de Focus-device-registratie
  met **`sudo coolbx-enroll-info`** (JSON: `deviceId`, `deviceClass`, `fde`, `secret`). Het secret is
  gevoelig: alleen tijdens de enrollment tonen/kopiëren. Registreer de **klasse mee** (`tpm-sealed` of
  `file-secret`) — de server handhaaft er tiering op (zie onder).
- **Productie (aanbevolen):** de server deelt het secret bij enrollment uit en zet het meteen in de allowlist;
  het OS bakt het niet, maar ontvangt het via een eenmalige enrollment-call.

## Toestelklassen & tiering (B3.e, F-03-006 / F-03-014)

| Klasse | Secret-opslag | Examen-kiosk |
|---|---|---|
| **Tier 1 — `tpm-sealed`** | TPM2-sealed credential (`device-secret.cred`); schijf-uitlezen levert niets op | ja |
| **Tier 2 — `file-secret`** | plain file `0600 root`; te weren via server-config | alleen als het deployment dat toelaat |

- De klasse wordt door het OS gerapporteerd (`/etc/coolbx/device-class`, `coolbx-enroll-info`) maar de
  **server vertrouwt uitsluitend zijn eigen register** (klasse gezet bij registratie). Handhaving:
  `EXAM_MIN_DEVICE_CLASS=tpm-sealed` in het Focus-deployment weigert kiosk-claims van Tier-2-toestellen.
- **PCR-binding bewust uit** (`--tpm2-pcrs=""`): het credential is aan de TPM-chip (het toestel) gebonden,
  niet aan de firmware-meetstand — een firmware/SecureBoot-update maakt het secret niet onbruikbaar.
  Measured-boot-binding (PCR-policy + SecureBoot-beheer) is de volgende hardening-trede.

## FDE — volledige schijfversleuteling (D2-persistentie, Tier 1)

De dev-qcow2 draait zónder FDE (bootc-image-builder ondersteunt geen LUKS-partities in de
disk-customization). FDE hoort bij de **hardware-installatie**:

```bash
# Tier-1-installatie op echt hardware (wist de doelschijf!):
sudo bootc install to-disk --block-setup tpm2-luks /dev/<doelschijf>
# Na de eerste boot: recovery-key toevoegen (verplicht — zonder failover sluit een
# TPM/firmware-wijziging het toestel buiten) en veilig bewaren:
sudo systemd-cryptenroll --recovery-key /dev/<luks-partitie>
```

Verifieer na installatie met `sudo coolbx-enroll-info` → `"fde": true`. Toestellen zonder TPM krijgen
geen `tpm2-luks`-pad (Tier 2): geen FDE-autounlock en — bij `EXAM_MIN_DEVICE_CLASS=tpm-sealed` —
geen examen-kiosk.

## Fast-follow hardening

- **Relay-resistentie:** bind de challenge aan tijd/sessie (server doet dit al via de nonce); overweeg
  peer-cred-checks op de socket zodat enkel de Focus-extensie-context tekent.
- **Measured boot:** PCR-policy-binding van het credential + SecureBoot-beheer (volgende trede na B3.e).

## Per-examen kiosk-policy (B3.c, Focus-audit F-03-007)

Zelfde socket (`/run/coolbx-attest.sock`), tweede request-type. De Focus-server stuurt bij examen-start
`exam:policy {phase, allowDomains}` naar kiosk-geattesteerde extensies; de extensie relayt hem als
`{"examPolicy": {"phase": "exam"|"lobby", "allowDomains": [...]}}` naar de native host → daemon.

- **Alleen een kiosk-peer** (SO_PEERCRED, kernel-bepaald) mag dit — de vrije modus of ssh kan de
  browser-policy niet zetten. Response: `{"ok": true, "phase": ...}` of `{"error": ...}`.
- De daemon roept `/usr/libexec/coolbx-exam-policy` aan: valideert de domeinen (kale hostnames,
  `*.x` → `x`, max 100), schrijft atomair `/etc/chromium/policies/managed/coolbx-exam.json`
  (`URLBlocklist:["*"]` + `URLAllowlist` = extensie + Focus-infra (`/etc/coolbx/focus-infra.domains`)
  + les-domeinen + examen-hardeningset) en herstart de kiosk-Chromium (de herstartloop van
  `chromium-kiosk.sh` brengt hem terug mét policy).
- **Lifecycle** (de policy-dir is globaal, dus het bestand leeft alléén met de kiosk):
  `coolbx-kiosk-start` schrijft de default-deny **lobby-baseline** (alleen infra + extensie);
  `phase:"exam"` verruimt naar de les-set; `phase:"lobby"` herstelt de baseline;
  `coolbx-kiosk-return` verwijdert het bestand; `coolbx-exam-policy-cleanup.service` ruimt een
  crash-artefact bij boot op. Zie `tests/test_13_exam_policy.py`.
