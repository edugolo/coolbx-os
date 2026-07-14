# Coolbx OS — uitrolgids voor scholen (F-07-002)

Deze gids brengt een school-ICT'er of Coolbx-beheerder van nul naar een werkende vloot:
hardware kiezen → image verkrijgen → installeren → enrollen → updaten → dagelijks beheren.

Diepere achtergrond staat bewust elders — dupliceer die niet:

| Onderwerp | Document |
|---|---|
| Toestel-attestatie, enrollment-contract, tiering, FDE | [`docs/ATTESTATION.md`](ATTESTATION.md) |
| Image-signing (cosign) & on-device verificatie | [`docs/SIGNING.md`](SIGNING.md) |
| Lokale build-/dev-loop (VM, e2e) | [`docs/DEVELOPING.md`](DEVELOPING.md) |
| Architectuurbeslissingen (het *waarom*) | [`docs/adr/`](adr/README.md) |

Alles wat in deze gids **[TE VERIFIËREN]** draagt, is nog niet in de repo of op echte hardware
bevestigd — voer die stap eerst op één testtoestel uit vóór je 'm vlootbreed toepast.

---

## 1. Overzicht & architectuur

### Wat is Coolbx OS?

Coolbx OS is een vergrendelde Fedora **bootc**-image (`quay.io/fedora/fedora-bootc:43` als base,
ADR-0003/0004) die van een gewone x86_64-schoollaptop het equivalent van een managed Chromebook
maakt. Het toestel heeft twee gezichten (ADR-0005, "play↔focus"):

- **Vrije modus (D2 — beheerd toestel):** een beheerde GNOME-desktop (NL-BE) met Chromium en een
  gecureerde set basis-apps. Geschikt voor gewoon klasgebruik en **lesbegeleiding** met Coolbx Focus.
- **Toetsmodus (D3 — examen):** de leerling (of leerkracht) start "Toetsmodus"; het toestel
  schakelt naar een vergrendelde **sway-kiosk** op een eigen VT (VT-switch geblokkeerd, ADR-0016)
  met Chromium in kiosk-modus, een default-deny URL-policy en de force-installed
  Focus-studentextensie. Examenintegriteit is gelaagd: kiosk-jail + Chromium-policy (OS) +
  detectie/herneemcode (Focus-server) + leerkracht-aanwezigheid (ADR-0007, ADR-0009).

### Relatie tot de Coolbx Focus-server

Coolbx OS staat los van Focus (ADR-0012): de OS-kern is een generieke device-floor; alle
Focus-binding (force-installed extensie, managed storage, attestatie) zit in optionele features
die in de gepubliceerde school-image wél aan staan. De **Focus-server is de enige runtime-verifier**:
hij houdt de enrollment-allowlist (deviceId→secret→klasse) bij en beslist of een toestel een
geattesteerde (examen-)sessie mag joinen. Zie `docs/ATTESTATION.md`.

### Update-model (bootc, image-based, atomair)

- Het hele OS is **één ondertekende container-image** op GHCR. Geen pakket-voor-pakket-updates,
  geen drift: elk toestel draait exact de gebouwde image.
- Updates zijn **atomair en A/B-staged**: `bootc upgrade` (via de `coolbx-update.timer`, 's nachts)
  schrijft de nieuwe deployment weg maar activeert die pas bij de **volgende reboot** — nooit een
  reboot midden in een toets (ADR-0017, ADR-0023).
- **Greenboot** is het vangnet: na herhaald gefaalde boots rolt het toestel automatisch terug naar
  de vorige, werkende deployment. Handmatig terug kan altijd met `bootc rollback`.
- **Powerwash** (factory-reset in ChromeOS-stijl) bestaat als primitief: `bootc install reset`
  (ADR-0017) — zie §7.

---

## 2. Hardware-eisen & device-tiering

### Device-tiering: Tier 1 vs Tier 2

De attestatie-keten (ADR-0013/0024/0027) kent twee toestelklassen; het OS bepaalt de klasse zelf
bij de eerste boot en rapporteert ze via `sudo coolbx-enroll-info` en `/etc/coolbx/device-class`.
De volledige tabel en het server-contract staan in `docs/ATTESTATION.md` — samengevat:

| | **Tier 1 — `tpm-sealed`** | **Tier 2 — `file-secret`** |
|---|---|---|
| Hardware | TPM 2.0 + UEFI (+ Secure Boot aan) | geen (bruikbare) TPM |
| Device-secret | TPM2-sealed credential (`/etc/coolbx/device-secret.cred`); een uitgelezen/gestolen schijf levert niets op | plain file `0600 root` (`/etc/coolbx/device-secret`) |
| Schijfversleuteling (FDE) | ja — transparant, TPM-autounlock (`--block-setup tpm2-luks`, §4) | **nee** — geen tpm2-luks-pad |
| Examen-kiosk (geattesteerde toets) | **ja** | **nee**, zodra de server `EXAM_MIN_DEVICE_CLASS=tpm-sealed` handhaaft |

**Wat mag een school met een Tier 2-toestel?** Het blijft een volwaardig beheerd toestel:
vrije modus, updates, vlootbeheer en **lesbegeleiding met Focus** werken gewoon. Wat níét mag:
**geattesteerde/proctored toetsen** — het secret staat op een onversleutelde schijf en is met
fysieke toegang te stelen, dus het toestelbewijs is zwakker. Het Focus-deployment weert deze
klasse voor examens met `EXAM_MIN_DEVICE_CLASS=tpm-sealed` (zet die instelling zodra álle
examen-toestellen als `tpm-sealed` geregistreerd zijn — zie ADR-0027). Communiceer dit expliciet
naar leerkrachten: een Tier 2-karretje is een les-karretje, geen examen-karretje.

### Minimale hardware-eisen

Uit de repo afleidbaar (base-pakketten, dev-VM-parameters, disk-blueprint):

| Onderdeel | Eis | Bron / status |
|---|---|---|
| CPU-architectuur | **x86_64** | CI en dev-harness bouwen/booten uitsluitend x86_64 |
| Firmware | **UEFI** (dev/tests booten enkel UEFI/OVMF) | Legacy-BIOS-boot: **[TE VERIFIËREN]** — niet getest |
| TPM | **TPM 2.0 voor Tier 1** (examens + FDE); zonder TPM → Tier 2 | ADR-0027 |
| RAM | dev-VM draait met **4 GiB** (GNOME + kiosk-Chromium). Formeel minimum en comfort-aanbeveling (8 GB?) op echte toestellen: **[TE VERIFIËREN]** | `Justfile` (`-m 4096`) |
| Schijf | root-filesystem minstens **20 GiB** (blueprint-minimum); praktische aanbeveling voor updates (twee deployments naast elkaar) + `/var`: ruimer nemen, richtwaarde **[TE VERIFIËREN]** | `disk_config/disk.toml` |
| Wifi | brede firmware-dekking ingebakken (Intel iwlwifi, Atheros, Broadcom, MediaTek, Realtek, …) | `build_files/01-packages.sh` |
| GPU | Intel/AMD volledig; **NVIDIA enkel via nouveau** — geen proprietaire driver (bewust: geen out-of-tree modules, ADR-0019) | ADR-0025 |
| Audio | pipewire + sof-firmware (moderne Intel/AMD-laptops) | `build_files/01-packages.sh` |
| Camera | UVC-webcams en Intel IPU6 (2021+) werken; **Surface Go 2 (IPU3) camera werkt niet** | ADR-0026 |

Bekende hardware-uitzonderingen: Microsoft Surface-toestellen hebben quirks (Type-Cover-input is
opgevangen in de `hardware`-feature; de IPU3-camera is niet ondersteund zonder linux-surface-kernel,
die er bewust niet in zit — ADR-0026/0019).

**Firmware-instellingen per toestel (Tier 1):** UEFI-boot, Secure Boot **aan**, TPM 2.0 **aan**.
Aanbevolen hardening (roadmap fast-follow, nog geen vaste vlootprocedure): firmware-wachtwoord +
bootmenu-lock, zodat een leerling niet vanaf USB om het OS heen kan booten.

---

## 3. Image bouwen & verkrijgen

### Optie A (aanbevolen): kant-en-klare image van GHCR

De CI bouwt bij elke push naar `main` én dagelijks (CVE-doorstroom vanuit fedora-bootc) een
**productie-image** — zonder dev-testuser, mét DevTools-/`file://`-hardening — en pusht naar:

```
ghcr.io/coolbx/coolbx-os:stable            # het vloot-kanaal
ghcr.io/coolbx/coolbx-os:stable.YYYYMMDD   # gedateerde tag (pinnen/terugkijken)
ghcr.io/coolbx/coolbx-os:testing           # canary-ring — handmatige promotie
```

De gepubliceerde image bevat de features `kiosk branding hardware fleet attest managed apps
media-nonfree` (zie `.github/workflows/build.yml`). Let op: de `:testing`-ring stond bij het
schrijven van deze gids nog niet gepromoveerd (ROADMAP Fase 5) — **[TE VERIFIËREN]** of de tag al
bestaat vóór je er canary-toestellen op zet.

### Signing-verificatie (vóór je uitrolt)

Elke gepushte image is **verplicht keyless gesigneerd** (cosign, Fulcio/Rekor via GitHub-OIDC).
Verifieer een image vanaf je beheermachine (zie `docs/SIGNING.md` voor context):

```bash
cosign verify \
  --certificate-identity-regexp 'github.com/coolbx/coolbx-os' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com \
  ghcr.io/coolbx/coolbx-os@<digest>
```

**On-device enforcement** (het toestel weigert zélf ongesigneerde updates via
`/etc/containers/policy.json`) is een bewust nog **niet-actieve scaffold**: de templates staan in
`/usr/share/coolbx/signing/`, maar activatie vereist eerst de cosign-keypair-opzet uit
`docs/SIGNING.md` (een `default: reject` zonder geldige sleutel breekt álle updates). Tot die
stap gezet is, is de verificatie hierboven een beheerders-controle, geen toestel-garantie.

### Optie B: zelf bouwen

Vereisten en de volledige dev-loop: `docs/DEVELOPING.md`. Kern:

```bash
just build-prod        # productie-container-image (GEEN testuser/autologin)
just build-qcow2       # bootable qcow2 voor de dev-VM
```

> ⚠️ **`just build-qcow2` is een DEV-artefact**: het bakt bewust de autologin-testuser
> (`tester`/`tester`) in voor de lokale VM-loop. **Nooit** die qcow2 naar leerlingtoestellen
> uitrollen. Voor school-uitrol gebruik je de GHCR-productie-image (optie A) of een zelf
> gepushte `build-prod`-image. Een productie-disk-image bouwen (prod-build + bootc-image-builder)
> is met de bouwstenen uit de `Justfile` mogelijk maar bestaat nog niet als kant-en-klaar
> recept: **[TE VERIFIËREN]**.

---

## 4. Installatie / imaging

### Het standaardpad: `bootc install to-disk`

Coolbx OS wordt geïnstalleerd door de container-image zichzelf naar de schijf te laten schrijven.
Er is (nog) geen eigen installatie-ISO — de interactieve Anaconda-ISO + FOG-kloonflow is gepland
maar bewust niet-prioritair (ROADMAP Fase 5b).

**Tier 1 (TPM 2.0 aanwezig) — mét transparante FDE.** Dit is het gedocumenteerde en aanbevolen
pad (`docs/ATTESTATION.md`, ADR-0027):

```bash
# WIST DE DOELSCHIJF! Draai vanuit de Coolbx OS-image op het doeltoestel:
sudo bootc install to-disk --block-setup tpm2-luks /dev/<doelschijf>
```

`--block-setup tpm2-luks` maakt een LUKS-versleutelde installatie die bij het booten automatisch
ontgrendelt via de TPM — transparant voor de leerling, maar een uitgebouwde/gestolen schijf is
onleesbaar.

**Verplicht direct na de eerste boot: recovery-key toevoegen.** Zonder failover sluit een
TPM-/firmware-wijziging het toestel definitief buiten (bekende bootc-caveat, ADR-0027):

```bash
sudo systemd-cryptenroll --recovery-key /dev/<luks-partitie>
```

Bewaar de recovery-key per toestel in de wachtwoordkluis van de school (koppel aan inventarisnummer).

**Tier 2 (geen TPM) — zonder FDE:**

```bash
# WIST DE DOELSCHIJF!
sudo bootc install to-disk /dev/<doelschijf>
```

Geen `tpm2-luks`, geen FDE-autounlock — en dus (bij `EXAM_MIN_DEVICE_CLASS=tpm-sealed`) geen
examen-kiosk (§2).

### USB-installatiepad

Zolang er geen Coolbx-installatie-ISO bestaat, is het praktische pad: boot het doeltoestel vanaf
een **generieke live-Linux-USB** (bv. een Fedora-live-omgeving met podman), pull daar de
Coolbx-image en laat die zichzelf installeren via het bovenstaande `bootc install to-disk`-commando
(het standaard bootc-patroon: het commando draait *vanuit* de container-image, met privileges en
toegang tot `/dev`). De exacte `podman run`-aanroep vanaf een live-USB is nog niet in deze repo
vastgelegd of op echte hardware doorlopen: **[TE VERIFIËREN]** — documenteer 'm na de eerste
hardware-installatie hier. Massale kloon-uitrol (FOG) is gepland als Fase 5b, nog niet gebouwd.

### Secure Boot-instellingen in de firmware

- **Secure Boot kan (en moet) gewoon áán blijven.** Coolbx OS bouwt geen out-of-tree
  kernelmodules; Fedora's gesigneerde shim + kernel volstaan. Er is **geen MOK-enrollment of
  eigen key** nodig — geen firmware-prompts per toestel (ADR-0019).
- Moet de live-USB niet booten door Secure Boot? Gebruik een Secure Boot-compatibele live-image
  (bv. officiële Fedora-media) in plaats van Secure Boot uit te schakelen.
- Aanbevolen na installatie (fysieke hardening, roadmap fast-follow): firmware-wachtwoord zetten
  en het bootmenu vergrendelen, zodat leerlingen de USB-bootvolgorde niet kunnen misbruiken.

---

## 5. Enrollment (registratie bij de Focus-server)

Bij de **eerste boot** genereert `coolbx-device-secret.service` automatisch het per-toestel
HMAC-secret (op Tier 1 meteen TPM2-sealed) en zet het de toestelklasse. Volledige architectuur en
het server-contract: `docs/ATTESTATION.md`.

### Stap voor stap

1. **Toestel booten** en met het (school)netwerk verbinden.
2. **Enrollment-info uitlezen** (root; toon het secret alléén tijdens deze stap):

   ```bash
   sudo coolbx-enroll-info
   # → {"deviceId":"…","deviceClass":"tpm-sealed","fde":true,"secret":"…"}
   ```

   Controleer voor een examen-toestel dat `deviceClass` = `tpm-sealed` **en** `fde` = `true`
   is — anders is de Tier 1-installatie (§4) niet gelukt.
3. **Registreren in de Focus-device-registratie** (de `device_attestation`-allowlist aan
   serverkant): `deviceId` + `secret` + **de klasse** (`tpm-sealed`/`file-secret`). De server
   vertrouwt uitsluitend de klasse in zijn éigen register — wat het toestel rapporteert is enkel
   informatief. De exacte registratie-flow (dashboard-scherm of API-endpoint) leeft in de
   Focus-repo: **[TE VERIFIËREN]** — zie het contract in `docs/ATTESTATION.md`.
4. **Labelen.** Koppel in je inventaris het fysieke toestel (inventarisnummer/sticker) aan de
   `deviceId` en — voor Tier 1 — aan de bewaarde LUKS-recovery-key. De `deviceId` is stabiel
   (afgeleid van de machine-id) zolang het toestel niet opnieuw geïnstalleerd/gepowerwashed wordt.
5. **Verifiëren dat het toestel attesteert:**

   ```bash
   coolbx-status                                  # overzicht: attestatie-daemon, toestel-ID, kiosk-gereedheid
   systemctl is-active coolbx-attestd.service     # moet "active" zijn
   ```

   End-to-end-bewijs: start "Toetsmodus" (§7) en laat het toestel een geattesteerde sessie joinen
   tegen de Focus-server; een niet- of fout-geregistreerd toestel wordt door de server geweigerd.

> **Productie-enrollment (aanbevolen richting, nog niet gebouwd):** de server deelt het secret bij
> enrollment zelf uit via een eenmalige enrollment-call, in plaats van het lokaal gegenereerde
> secret over te tikken (`docs/ATTESTATION.md` §Enrollment). Status: **[TE VERIFIËREN]** — tot dan
> is de flow hierboven (lokaal secret + handmatige registratie) het werkende pad.

---

## 6. Updates & vloot

### Hoe updates werken

- De `fleet`-feature enablet **`coolbx-update.timer`**: elke nacht om **04:00** (± 15 min jitter;
  `Persistent=true`, dus toestellen die 's nachts uit staan halen in bij de volgende boot) draait
  `bootc upgrade` — **stage-only**. De nieuwe image wordt klaargezet; ze wordt pas actief bij de
  **volgende reboot**. Een toets wordt dus nooit door een update onderbroken; het "update-venster"
  is effectief: nachtelijke download + activatie bij de eerstvolgende (ochtend)herstart.
- De default `bootc-fetch-apply-updates.timer` (die wél zelf kan rebooten) is bewust **gemaskeerd**.
- De vloot volgt de GHCR-tag waarop ze geïnstalleerd is — normaal **`:stable`**.

Controle en handwerk op een toestel:

```bash
coolbx-status                        # o.a. "Update gestaged: JA/nee" + volgende timer-run
sudo bootc status                    # volledige deployment-status (booted/staged/rollback)
sudo bootc upgrade                   # nu een update stagen (i.p.v. wachten op 04:00)
sudo systemctl start coolbx-update.service   # idem, via de unit
```

### Canary-ring

Zet een handvol testtoestellen op de canary-tag en promoveer pas daarna handmatig naar `:stable`
(ROADMAP: greenboot vangt alleen boot-crashes, niet "extensie laadt niet meer"):

```bash
sudo bootc switch ghcr.io/coolbx/coolbx-os:testing   # toestel → canary-ring
sudo bootc switch ghcr.io/coolbx/coolbx-os:stable    # terug naar het vloot-kanaal
```

(Voorwaarde: de `:testing`-tag wordt effectief gepubliceerd — zie §3, **[TE VERIFIËREN]**.)

### Greenboot: automatische rollback bij gefaalde boot

De `fleet`-feature installeert greenboot met een **lokale** health-check
(`/etc/greenboot/check/required.d/50-coolbx-kiosk-health.sh`): GDM actief, Chromium/sway/
kiosk-launcher/Focus-policy aanwezig, geen stapel gefaalde units. Bewust wordt **nooit** de
bereikbaarheid van de Focus-server gecheckt — een externe outage mag de vloot niet doen
terugrollen. Faalt de check meerdere boots op rij, dan rolt bootc/ostree automatisch terug naar
de vorige deployment. Status bekijken:

```bash
coolbx-status                                        # regel "Boot-status"
cat /etc/motd.d/boot-status                          # greenboot-verdict van deze boot
journalctl -u greenboot-healthcheck.service -b       # detail van de checks
```

### Een update handmatig terugdraaien

```bash
sudo bootc rollback     # wissel terug naar de vorige deployment; daarna rebooten
```

**Examenperiodes:** pin vooraf de bekend-goede deployment zodat een tussentijdse update de
werkende staat nooit kan opruimen (ROADMAP §Updates):

```bash
sudo ostree admin pin 0        # pin de huidige (index 0) deployment
```

(Exacte pin/unpin-conventie in de vlootpraktijk: **[TE VERIFIËREN]** — nog geen vaste procedure.)

### Vlootconfig via ansible-pull

Per-rol runtime-config (netwerk/printer/ring/toggles — **nooit** software of kernconfig, dat zit
in het image) komt uit een school-configrepo via `coolbx-ansible-pull.timer` (bij boot + periodiek).
Standaard is dit een veilige no-op; activeren zonder rebuild:

```bash
# /etc/coolbx/ansible.conf — vervang de PLACEHOLDER:
ANSIBLE_PULL_URL="https://github.com/<school-of-coolbx>/coolbx-ansible.git"
ANSIBLE_PULL_PLAYBOOK="local.yml"
```

De rol van het toestel staat in `/usr/share/coolbx/ansible/laptop-group` (default `leerlingen`)
en gaat als `coolbx_group`-extra-var mee zodat `local.yml` per rol kan vertakken. De echte
playbook-repo bestond bij het schrijven nog niet: **[TE VERIFIËREN]**.

---

## 7. Dagelijks beheer

### Snel toestand checken

```bash
coolbx-status
```

Toont: OS-image, gestagede update, boot-gezondheid (greenboot), update-timer, kiosk-/Focus-
gereedheid, attestatie-daemon, toestel-ID en gefaalde units. Lokaal, geen open poort.

### Toestel her-enrollen (nieuw secret)

Bij een gecompromitteerd of "verweesd" secret (bv. registratie kwijt aan serverkant):

```bash
sudo rm -f /etc/coolbx/device-secret /etc/coolbx/device-secret.cred
sudo systemctl start coolbx-device-secret.service   # genereert (en sealt) een nieuw secret
sudo systemctl restart coolbx-attestd.service
sudo coolbx-enroll-info                             # nieuw secret → opnieuw registreren (§5)
```

Verwijder daarna de **oude** registratie aan serverkant. (De `deviceId` blijft gelijk zolang de
machine-id niet wijzigt; na een herinstallatie of powerwash wijzigt die doorgaans wél — behandel
zo'n toestel gewoon als nieuw en doorloop §5. Exact machine-id-gedrag na `bootc install reset`:
**[TE VERIFIËREN]**.)

### Toestel revoken (kwijt/gestolen)

Revocatie is een **server-handeling**: verwijder de `deviceId` uit de enrollment-allowlist van de
Focus-server (`docs/ATTESTATION.md` §Contract, punt 5). Het toestel kan dan geen geattesteerde
sessie meer joinen. Bij een Tier 1-toestel is de schijf bovendien versleuteld (FDE) — vernietig
ook de bewaarde recovery-key als het toestel definitief weg is.

### Kiosk-/examenmodus-controle

- **Starten:** de leerling/leerkracht start "Toetsmodus" vanuit GNOME (launcher
  `coolbx-toetsmodus.desktop` → `pkexec /usr/bin/coolbx-kiosk-start`). Het toestel wisselt naar
  de vergrendelde sway-kiosk; de Chromium-policy start in default-deny-lobby (alleen Focus-infra
  + extensie) tot de server een per-examen-allowlist stuurt (`docs/ATTESTATION.md` §Per-examen
  kiosk-policy).
- **Controleren dat een toestel examen-klaar is:** `coolbx-status` (kiosk-launcher +
  Focus-extensie-policy "aanwezig", attestatie-daemon "active") + registratieklasse `tpm-sealed`
  aan serverkant + `EXAM_MIN_DEVICE_CLASS=tpm-sealed` in het Focus-deployment.
- **Afsluiten:** de leerling sluit bewust af via de waybar-knop ("Sessie afsluiten" + bevestiging);
  het toestel keert terug naar GNOME en de examen-policy wordt opgeruimd. Herjoinen na een exit =
  herneemcode via Focus (leerkracht). Blijft een kiosk hangen, dan kan een beheerder via een
  root-shell `coolbx-kiosk-exit` draaien.

### Powerwash (factory-reset)

Voor jaarlijkse schoonmaak of toesteloverdracht bestaat het bootc-primitief (ADR-0017):

```bash
sudo bootc install reset    # verse /etc + lege /var, OS-image blijft
```

De roadmap vermeldt hiervoor de vlaggen `--experimental --apply`; de exacte aanroep en het gedrag
op een FDE-toestel zijn nog niet als vlootprocedure doorlopen: **[TE VERIFIËREN]**. Na een
powerwash: toestel her-enrollen (§5) — het oude secret is weg.

### Troubleshooting

| Symptoom | Oorzaak / check | Actie |
|---|---|---|
| Toestel blijft bij het aanzetten hangen **vóór** het Coolbx-logo (soms in het UEFI-/bootmenu) | **Gekend issue** (boot-flake, F-06-008): de boot hangt sporadisch vóór de kernel. In de dev-omgeving vangt de harness dit met een automatische reset op (`just vm-wait`); een structurele fix is nog open | Toestel hard resetten/herstarten — de volgende boot slaagt doorgaans. Frequentie op echte schoolhardware: **[TE VERIFIËREN]** |
| "Update gestaged: JA" maar toestel draait oude versie | Staged-only-model: activatie gebeurt pas bij reboot | Toestel (laten) herstarten op een natuurlijk moment |
| Toestel bootte plots een oudere versie | Greenboot heeft teruggerold na gefaalde boots | `cat /etc/motd.d/boot-status` + `journalctl -u greenboot-healthcheck.service -b`; oorzaak fixen vóór opnieuw updaten |
| Toestel wordt door de Focus-server geweigerd bij (examen-)join | Niet/fout geregistreerd, gerevoked, of Tier 2 bij `EXAM_MIN_DEVICE_CLASS=tpm-sealed` | `sudo coolbx-enroll-info` → vergelijk `deviceId`/klasse met het server-register; `systemctl is-active coolbx-attestd.service` |
| `coolbx-enroll-info`: "geen device-secret aanwezig" | First-boot-unit nog niet gedraaid | `sudo systemctl start coolbx-device-secret.service` en opnieuw proberen |
| `deviceClass` is `file-secret` op een toestel mét TPM | TPM 2.0 uitgeschakeld in firmware, of niet bruikbaar bij first-boot | TPM aanzetten in firmware en rebooten — een bestaand plain secret wordt dan automatisch in-place geseald (waarde blijft; registratie blijft geldig) |
| `fde: false` op een toestel dat Tier 1 moet zijn | Geïnstalleerd zonder `--block-setup tpm2-luks` | Herinstalleren volgens §4 (FDE kan niet achteraf zonder herinstallatie: **[TE VERIFIËREN]**) |
| Geen wifi | Ontbrekende firmware is onwaarschijnlijk (brede set ingebakken); check `nmcli device` | Bij exotische chipset: melden — firmware-lijst staat in `build_files/01-packages.sh` |
| Kiosk sluit niet af / toestel "vast" in toetsmodus | Kiosk-sessie hangt | Als beheerder (ssh/andere console indien beschikbaar): `coolbx-kiosk-exit`; ultiem: hard rebooten — de boot-cleanup (`coolbx-exam-policy-cleanup.service`) ruimt achtergebleven examen-policy op |
| Kiosk toont wit/geblokkeerd scherm i.p.v. de toets | Default-deny-lobbypolicy actief en toets-domein niet in de examen-allowlist | Domeinen worden per examen door de Focus-server gepusht; check de examen-instellingen aan Focus-kant (`docs/ATTESTATION.md` §Per-examen kiosk-policy) |
| Na TPM-/firmware-wissel vraagt het toestel een LUKS-wachtwoord | TPM-autounlock verbroken | Ontgrendel met de **recovery-key** (daarom is die verplicht, §4); daarna TPM-enrolment van de LUKS-partitie herstellen: **[TE VERIFIËREN]** (procedure nog niet gedocumenteerd) |

---

## 8. Bijlage — checklists

### Checklist A: nieuw toestel → klaar voor de klas (D2)

- [ ] Hardware voldoet (§2): x86_64, UEFI; wifi/GPU/camera gecheckt tegen de uitzonderingenlijst
- [ ] Firmware: UEFI-boot, Secure Boot aan; (Tier 1) TPM 2.0 aan
- [ ] Image-herkomst geverifieerd met `cosign verify` (§3)
- [ ] Geïnstalleerd met `bootc install to-disk` (§4) — Tier 1 mét `--block-setup tpm2-luks`
- [ ] (Tier 1) Recovery-key toegevoegd (`systemd-cryptenroll --recovery-key`) én in de kluis, gekoppeld aan het inventarisnummer
- [ ] Eerste boot ok; netwerk verbonden
- [ ] `sudo coolbx-enroll-info` uitgelezen; `deviceId` + klasse + secret geregistreerd bij de Focus-server (§5)
- [ ] Toestel gelabeld (inventarisnummer ↔ `deviceId`)
- [ ] `coolbx-status`: geen gefaalde units, update-timer enabled, attestatie-daemon actief
- [ ] Vrije modus getest: GNOME start, Chromium werkt, wifi ok
- [ ] (optioneel) `ansible.conf` gezet + `laptop-group` correct voor de rol van het toestel (§6)
- [ ] (aanbevolen) Firmware-wachtwoord gezet + bootmenu vergrendeld

### Checklist B: toestel klaar voor examens (D3 — Tier 1)

Alles uit checklist A, plus:

- [ ] `sudo coolbx-enroll-info` → `"deviceClass": "tpm-sealed"` **én** `"fde": true`
- [ ] Toestel aan serverkant geregistreerd mét klasse `tpm-sealed`
- [ ] Focus-deployment handhaaft `EXAM_MIN_DEVICE_CLASS=tpm-sealed`
- [ ] "Toetsmodus" gestart: kiosk komt op, VT-switch/escape geblokkeerd, extensie aanwezig
- [ ] Proefjoin van een geattesteerde sessie geslaagd (server accepteert het toestel, `session=kiosk`)
- [ ] Bewuste exit getest: bevestiging → terug naar GNOME → examen-policy opgeruimd
- [ ] (examenperiode) Bekend-goede deployment gepind (`ostree admin pin`, §6) en geen canary-tag actief (`bootc status` toont `:stable`)
