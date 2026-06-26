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

- **Per-toestel-secret** `/etc/coolbx/device-secret` — `0600 root`, bij first-boot gegenereerd
  (`coolbx-device-secret.service`). De leerling-sessie kan het **niet** lezen.
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

- **Pilot/dev:** secret lokaal gegenereerd (deze scaffold) — registreer `deviceId`+secret eenmalig in de
  Focus-allowlist (uitlezen kan enkel root: `sudo cat /etc/coolbx/device-secret`, of via een enrollment-flow).
- **Productie (aanbevolen):** de server deelt het secret bij enrollment uit en zet het meteen in de allowlist;
  het OS bakt het niet, maar ontvangt het via een eenmalige enrollment-call.

## Fast-follow hardening

- **Relay-resistentie:** bind de challenge aan tijd/sessie (server doet dit al via de nonce); overweeg
  peer-cred-checks op de socket zodat enkel de Focus-extensie-context tekent.
- **TPM-sealing + FDE:** seal het secret aan de TPM zodat fysieke schijf-diefstal het niet prijsgeeft (ADR-0013).
