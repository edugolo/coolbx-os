# Coolbx OS — productie-roadmap

> Status: **ter review.** Dit is het uitgewerkte plan uit de plansessie (2026-06-23),
> nog niet uitgevoerd — er is nog niets in de repo aangemaakt. Lees na, corrigeer,
> en dan starten we met Fase 0.

## Context

Coolbx OS is de "device floor": een vergrendeld Fedora **bootc**-OS dat van een gewone
laptop het equivalent van een managed Chromebook maakt, als harde onderlaag voor
waterdichte toetsafname met **Coolbx Focus**. De repo staat aan nul (enkel `HANDOFF.md`);
een bevroren POC in `/home/johan/code/coolbx-poc/coolbx-os` levert herbruikbare patronen
maar moet vers, schoon en productie-ready herbouwd worden (Electron eruit, `schoolbx`→`coolbx`,
Chromium-policy erin).

Dit plan legt de architectuur en fasering vast op basis van actueel onderzoek (juni 2026)
en de richtingskeuzes die in de plansessie zijn gemaakt.

### Vastgelegde keuzes (plansessie)

| Knoop | Keuze |
|---|---|
| **Toestelmodel** | Beheerde GNOME-laptop die **op aanvraag** in een vergrendelde kiosk-sessie schakelt |
| **Base** | `quay.io/fedora/fedora-bootc` (minimaal, bootc-native, "zo clean mogelijk"); Universal Blue als leerbron/fallback bij hardware-problemen |
| **Skelet** | Containerfile + Justfile in de stijl van `ublue-os/image-template`, gevoed met geporte POC-patronen — geen BlueBuild |
| **Kiosk-compositor** | **sway** + waybar (minimale systeem-UI: wifi/batterij/klok), Chromium in kiosk; aparte Wayland-sessie op eigen VT |
| **Browser** | RPM-**Chromium** (Fedora-repo), geen Flatpak, geen Electron |
| **Examen-integriteit** | Op de **Focus-laag**: leerling mag bewust afsluiten (waarschuwing "ingediend?"); herjoinen enkel via **herneemcode + toestemming leerkracht** (ook bij crash/wifi-verlies). OS heeft géén teacher-only hard-unlock nodig |
| **Toets starten** | Leerling start zelf via een "Toetsmodus"-launcher in GNOME |
| **Uitrol** | Interactieve Anaconda-ISO bouwt een **master** → **generaliseren** → **FOG capture → FOG deploy** voor massauitrol → bootc **OTA** neemt onderhoud over. Geen `bootc switch`-dans in productie |

### Architectuur in één beeld

```
Boot → GDM → beheerde GNOME-sessie (user: leerling)         [VT2, dagelijks gebruik]
                 │
                 │  leerling klikt "Toetsmodus" (launcher → pkexec coolbx-kiosk-start)
                 ▼
        transiente systemd-sessie (user: kiosk) op VT4        [vergrendelde toets-sessie]
        sway (keybinds gestript, VT-switch dicht)
          └─ waybar (wifi / batterij / klok / "Sessie afsluiten")
          └─ chromium --kiosk  →  Focus student-extensie (force-installed)
                                   managed-storage: serverUrl + kioskMode=true
                 │
                 │  bewuste exit (waybar-knop of extensie-flow) → confirm → sessie stopt
                 ▼
        ExecStopPost: chvt 2 → terug naar GNOME
        (herjoinen vereist herneemcode via Focus/leerkracht)
```

Examenintegriteit = detectie + gegate heropstart op de Focus-server, niet een onbreekbare
OS-jail. De OS-kiosk voorkomt *afleiding en ontsnapping binnen de sessie* (geen andere apps,
geen VT-hop, geen terminal), maar staat een *bewuste* exit toe.

---

## Lokale dev-workflow (VM) — expliciet

Doel: een **snelle, één-commando inner loop** zodat we elke wijziging in een VM kunnen zien
(zowel GNOME als de sway-kiosk grafisch), zonder echte hardware.

**Hoofd-loop (grafisch, volledige disk):** geport uit de POC.
```
just build            # podman build van de Containerfile (dev-image, met testuser)
just build-qcow2      # bootc-image-builder → output/qcow2/disk.qcow2
just run-vm-qcow2     # qemux/qemu-container, VNC in browser (localhost:8006) + SSH op :2222
```
- Dev-builds zetten een **autologin-testuser** (`ENABLE_FIRSTBOOT_USER=1`, bv. `tester/tester`)
  zodat je meteen in GNOME landt en de Toetsmodus-launcher kan klikken.
- `GPU=Y`/`TPM=Y` + VNC tonen écht de grafische sessie → we kunnen de kiosk visueel testen.
- SSH-forward (`:2222`) om in de VM te poken (`chrome://policy` checken kan via een terminal
  + `chromium`-debug, of gewoon grafisch in de VNC).

**Snelle loop (headless, geen disk-build):** voor niet-grafische iteraties (policy-JSON,
units, scripts) is `podman-bootc` lichter — het draait de container direct als VM zonder de
BIB-stap. Toevoegen als `just dev-quick` / documenteren.

**Te leveren in Fase 0–1 (developer experience):**
- `just`-recepten: `build`, `build-prod`, `build-qcow2`, `run-vm-qcow2`, `lint`, `format` (port).
- Een korte `docs/DEVELOPING.md`: één-pagina "hoe bouw & test ik lokaal", inclusief de VNC-URL,
  SSH-toegang, en hoe je de Chromium-policy in de VM verifieert.
- Duidelijke scheiding **dev vs prod** image (testuser alleen in dev; prod = `build-prod`,
  `ENABLE_FIRSTBOOT_USER=0`).
- Optioneel: `just vm-ssh` helper en een `just clean` (port) om build-artefacten op te ruimen.

Randvoorwaarden op de dev-machine (Fedora): `podman`, `just`, `qemu`/KVM (`/dev/kvm`),
`jq`, en `bootc-image-builder` wordt als container gepulld. Documenteren in `DEVELOPING.md`.

---

## Modulariteit (feature-model)

De POC voegde zaken modulair toe via `features/<naam>/{install.sh, system_files/}`, getoggled
door een Containerfile-blok te (un)commenten. **Het concept is goed; de uitvoering was ruw.** Behouden,
maar formaliseren:
- **Toggle via build-arg** `FEATURES="kiosk branding ..."` die de Containerfile itereert
  (reproduceerbaar, CI kan varianten bouwen), i.p.v. blokken comment/uncomment.
- Elke feature **self-contained + single-purpose** (niet zoals de POC-`focus-mode` die cage + Electron + files mengde).
- **Twee-lagen-model:** build-time *features* = capabilities die ín het image moeten (kiosk, branding, optionele software);
  runtime *ansible-pull* = per-toestel/rol-config (leerling/leerkracht/admin). Niet alles is een feature — rolverschillen horen bij ansible.
- **Niet over-engineeren:** geen BlueBuild-achtig modulesysteem nodig; een dunne conventie + build-arg volstaat.

---

## Branding

Het merk is een **familie-systeem** (uit de masters in `coolbx-focus/branding/svg`): een ouder-merk
`coolbx-mark` (inkt-tegel + crème "C") met per product een eigen **glyph** (Focus = camera-viewfinder
+ amber focuspunt). Tokens: **inkt `#2b2620`**, **papier `#faf8f3`**, **amber `#e8902a` is gereserveerd voor Focus**,
wordmark lowercase in **Inter Bold** ("coolbx" inkt + productwoord in accent), gegenereerd uit SVG via `generate.sh`.

**Coolbx OS — eigen eigenheid, zelfde toon:**
- ⚠️ **Geen schild/slot-metafoor.** De OS is *niet* enkel een toets-/vergrendeltoestel — het moet ook in **vrije modus**
  bruikbaar zijn. Branding mag dus géén "security/lockdown" uitstralen.
- **Concept: de play↔focus-dualiteit** (waar de POC al mee speelde). Het toestel kent een vrije **play**-modus en een
  geconcentreerde **focus**-modus; de OS is het *platform/de vloer* die beide draagt. Glyph-richtingen: een dualiteit/toggle
  tussen open (play) en gefocust, of de coolbx-ouder-"C"-tegel als platform-merk waarop de modi leven.
- **Eigen accent** (sibling van amber, want amber = Focus) — maar **vriendelijk/neutraal, niet "secure"**. Eventueel zelfs
  een **dual-accent** (play-hue naast focus-amber). Open te kiezen.
- Wordmark **"coolbx os"** (inkt + os-accent), exact parallel aan "coolbx focus".

**Wow-touchpoints (impact-volgorde) — waar de OS premium moet voelen:**
1. **Plymouth boot-splash** (logo + spinner) — het eerste wow-moment bij power-on.
2. **GDM-login** (logo, achtergrond, accent).
3. **Desktop**: wallpaper light/dark + **GNOME-accentkleur** (GNOME 47+) + thema.
4. **Kiosk**: waybar-styling (CSS, kan prachtig) + branded toets-splash terwijl Chromium laadt + de afsluit-dialoog.
5. **OS-identiteit**: `/etc/os-release` (`NAME="Coolbx OS"`, `PRETTY_NAME`, `LOGO`, `HOME_URL`, `ANSI_COLOR`).
6. **Anaconda-installer** (ISO-branding); secundair: GRUB-thema, lockscreen.

**Aanpak:** één brand-token-bron + een `generate.sh`-pijplijn (zoals Focus al heeft) die álle OS-assets emit;
ingebouwd als een **"branding"-feature** (haakt aan modulariteit hierboven). Eerlijk: de hero-art (glyph, wallpaper)
is designwerk — ik scaffold de pijplijn + alle touchpoints en hergebruik de masters; de finale art verfijnen we.
*Ik kan een eerste SVG-pass van de OS-glyph + wordmark maken in de familie-stijl als startpunt.*

---

## Kiosk-gebruiker & bestandssysteem

> **Stond nog niet expliciet in het plan — terecht punt.** De POC maakte `/home/focus` net *persistent*
> (tmpfiles `d /home/focus 0750`). Voor een toets-kiosk willen we het **omgekeerde**.

- **Ephemeral, schoon per sessie:** de kiosk-user-home + Chromium-profiel op **tmpfs** (Chromium `--user-data-dir`
  onder `/run`, of een tmpfs-mount op de kiosk-home, of wipe in `ExecStartPre`/`ExecStopPost`). Elke toets start
  *pristine*: geen profiel-carryover, geen gecachte logins, **privacy tussen leerlingen**.
- Op bootc zijn `/home` en `/var` standaard persistent → dit moeten we **expliciet** ephemeral maken.
- **Aparte `kiosk`-user**, los van de GNOME-leerling-identiteit (die blijft persistent voor dagelijks gebruik).
  De identiteit vóór de toets komt van **Focus** (join/herneemcode), niet van de OS-user → de OS-user mag generiek + wegwerpbaar zijn.
- Sluit aan op integriteit: een toets laat geen sporen na op het toestel.

---

## Updates, rollback & powerwash (eindgebruiker-UX)

> Eindgebruikers doen **nooit** `bootc upgrade`/`rollback` in een terminal. In de bootc-wereld bestaat er géén
> kant-en-klare ChromeOS-Powerwash-knop of GUI-rollback — we assembleren volwassen bouwstenen.

- **Updates = onzichtbaar & automatisch.** Stuur ze zelf via een off-hours timer (Fase 5) en **mask**
  `bootc-fetch-apply-updates.timer` zodat auto-updates niet vechten met handmatige rollback. Gebruiker doet niets.
- **Vangnet = greenboot (greenboot-rs voor bootc).** Health-checks na elke update; na N gefaalde boots **auto-rollback**
  naar de vorige deployment. Eigen `required.d`-checks: "kiosk/greeter start" + "focus-api bereikbaar". Zit **niet**
  standaard in Fedora/UB bootc → zelf toevoegen + enablen. Dé robuustheidspijler voor onbeheerde toestellen.
- **Knoppen zonder terminal (uupd-patroon):** oneshot-units `coolbx-update` / `coolbx-rollback` / `coolbx-powerwash`
  achter een **polkit `manage-units`-rule**; een kleine "Coolbx-instellingen"-GUI (of **Cockpit** voor admin) roept
  `systemctl start <unit>` aan. Geen sudo, geen pkexec-shell, geen wachtwoord.
- **Powerwash (ChromeOS-stijl factory reset):** primair **`bootc install reset --experimental --apply`** → verse `/etc`
  uit het image + lege `/var` (incl. `/var/home`). Schoon toestel voor de volgende leerling/jaar. (UB heeft
  `ujust powerwash` als referentie.) Lange-termijn-alternatief: systemd `factory-reset.target` (vereist systemd ≥258
  + aparte `/var`/`/home`-partities). De *generaliseer*-logica (FOG) en powerwash delen dezelfde basis.
- **GRUB-spanning:** verborgen kiosk-GRUB vs. zichtbaarheid van de rollback-entry — bewuste keuze (korte timeout of
  Shift/Esc toelaten) zodat een mens in nood nog kan terugvallen.

---

## Toestel-attestatie & vertrouwen (proof of genuine kiosk)

> **Open kernvraag:** hoe bewijst een client aan de Focus-server dat het écht Coolbx OS is, in een kiosk-sessie, met de
> echte extensie — en niet een nagebootste browser/extensie op een gewone laptop? Zelf-gerapporteerde waarden
> (`kioskMode=true` uit managed-storage) zijn **zwak**: een vervalste client liegt gewoon.

Gelaagde aanpak (haalbaar-nu → later-spike):
1. **Toestel-identiteit + enrollment.** Elk toestel enrollt bij eerste boot bij de Focus-server en krijgt een
   **device-credential, idealiter TPM-gebonden**. Server houdt een allowlist; toetsen aanvaarden enkel enrolled toestellen.
2. **Genuine OS via secure boot + signed image.** UEFI Secure Boot + gesigneerde bootc-image + `policy.json` (Fase 5) →
   aantoonbaar de echte Coolbx OS. **TPM measured boot** kan dit naar de server attesteren (PCR-quote).
3. **Lokale attestatie-agent (géén browser-extensie) als vertrouwensanker.** Een kleine *privileged* OS-service die de
   device-credential houdt en een **getekend sessie-token** levert ("dit is toestel X, nú in kiosk-modus"). De extensie
   praat ermee via **native messaging** (zelfde host als het exit-signaal, punt 5) en presenteert het token aan de server.
   Een OS-agent geworteld in de TPM is veel sterker dan de extensie alleen (die op een ander OS na te bootsen is).
4. **Egress-lockdown in kiosk-modus.** Het OS laat in kiosk enkel verkeer naar `focus-api`/`dashboard` toe.

**Eerlijk over het dreigingsmodel:** dit zet de lat enorm veel hoger dan een gewone laptop, maar volledige
remote-attestatie van "vergrendelde kiosk + echte extensie" is serieus werk (ChromeOS gebruikt TPM-backed Verified
Access). Diepe TPM-attestatie is een **latere fase/spike**; maar we **ontwerpen er nu voor** (enrollment/device-identiteit,
TPM-beschikbaarheid, native-messaging-agent, egress-lockdown). **Gedeeld contract met het Focus-server-team.**

---

## Fasering

### Fase 0 — Repo & skelet opzetten
- `git init` in `/home/johan/code/coolbx/coolbx-os`; basis op `ublue-os/image-template`-structuur
  (Containerfile, Justfile, `build_files/`, `system_files/`, `.github/workflows/`).
- Naamgeving meteen correct: `coolbx-os` overal; **geen** `schoolbx`-restanten meenemen.
- `.gitignore` voor build-artefacten (POC had `_build-bib.*`, `output/`, `cosign.key` ingecheckt — **niet** doen; cosign-private key via GitHub secret).
- README + deze roadmap onder `docs/`; `docs/DEVELOPING.md` (zie dev-workflow hierboven).

### Fase 1 — Base image: fedora-bootc + beheerde GNOME → boot in VM
- `Containerfile`: `FROM quay.io/fedora/fedora-bootc:43` (verifieer huidige tag op quay.io).
- `build_files/01-packages.sh` (port + opschonen van POC): GNOME-desktop op de minimale base
  (`gnome-shell`, `gdm`, `gnome-control-center`, NetworkManager, `gnome-terminal` optioneel),
  `chromium`, `sway`, `waybar`, `ansible-core`. Firefox weglaten. **cage niet meer.**
- `build_files/02-config.sh`: locale `nl_BE.UTF-8` + keymap `be`, GDM autologin overweegbaar,
  units enablen. Hernoem alle `schoolbx-*` → `coolbx-*` (firstboot-user, presets, tmpfiles, `/etc/coolbx`, `/var/lib/coolbx`).
- `build_files/03-gnome-dconf.sh`: coolbx-wallpapers + GNOME-defaults (port).
- First-boot testuser (`coolbx-firstboot-user.sh`) enkel in dev-builds (`ENABLE_FIRSTBOOT_USER`), `=0` voor prod.
- Justfile-recepten porten: `build`, `build-prod`, `build-qcow2`, `run-vm-qcow2`, `lint`.
- **Verificatie:** `just build && just build-qcow2 && just run-vm-qcow2` → boot tot GNOME, NL/BE-locale klopt.

### Fase 2 — Chromium-policy spike (de-risk het kernmechanisme) ⚠️ kritisch & vroeg
Dit is de enige echt onzekere bouwsteen; bewijs het in een VM vóór de rest af is.
- Eén policy-JSON `system_files/etc/chromium/policies/managed/coolbx-focus.json` met **zowel**:
  - `ExtensionSettings.<ID>`: `installation_mode: force_installed`, `update_url`
    = `https://focus-dashboard.edugolo.be/extension-updates/update.xml`, `override_update_url: true`.
  - `3rdparty.extensions.<ID>`: `serverUrl = https://focus-api.edugolo.be`, `kioskMode = true`.
  - `<ID>` = `makdakigkdbicdljgdclgnejachcohag` (vast via `key` in manifest).
- **Verificatie in VM:** `chrome://policy` toont force-install; in de extensie/DevTools geeft
  `chrome.storage.managed.get()` → `{serverUrl, kioskMode:true}`. `chrome://extensions` toont
  "geïnstalleerd door beleid" met juiste ID.
- Valkuilen om te checken: ID-mismatch (`.crx` gesigneerd met juiste key), Fedora-pad `/etc/chromium/...`,
  schema-validatie tegen `managed_schema.json`, `minimum_chrome_version: 116` gehaald door Fedora-Chromium.
- Bron-extensie + `update.xml`-hosting liggen in de Focus-repo/dashboard (apart traject) — bevestig dat de
  `update.xml` en `.crx` bereikbaar/gesigneerd zijn.

### Fase 3 — Vergrendelde kiosk-sessie (sway + waybar + Chromium)
- Port en herwerk het POC-`start-focus`-mechanisme → `coolbx-kiosk-start`:
  - `systemd-run` transiente unit `coolbx-kiosk` als user `kiosk`, `PAMName=login`, op `/dev/tty4`,
    `ExecStopPost=+/usr/bin/chvt 2`, dan `chvt 4`. (Patroon uit POC `start-focus`.)
  - Start `sway` met een dichtgetimmerde config i.p.v. `cage`:
    `sway -c /usr/share/coolbx/kiosk/sway.conf` die `exec` Chromium `--ozone-platform=wayland --kiosk <Focus-URL>`.
- `sway.conf` hardening: **alle keybinds verwijderen** (geen workspace-switch, geen exec, geen `mode`),
  geen titelbalk/floating, VT-switch geblokkeerd. Let op de bekende quirk: Chromium/Ozone 103+ vangt
  keybinds af bij focus — in ons voordeel, maar in VM bevestigen.
- `waybar` met minimale modules: netwerk (wifi), batterij, klok, en een **"Sessie afsluiten"**-knop die de
  bewuste-exit-flow start (confirm → `systemctl stop coolbx-kiosk`). De "ingediend?"-waarschuwing zelf hoort
  bij de Focus-extensie; waybar-knop is de OS-fallback.
- Crash-recovery: `Restart=always` op de Chromium-laag binnen sway (of `while true`-wrapper), zodat een
  browsercrash de sessie niet stilletjes naar GNOME laat vallen.
- `sysusers.d/kiosk.conf`, AccountsService, polkit-regel (port `49-focus.rules` → `49-coolbx-kiosk.rules`)
  zodat de launcher zonder wachtwoord via `pkexec` mag starten. Launcher = `coolbx-toetsmodus.desktop`.
- **Ephemeral kiosk-home** (zie sectie *Kiosk-gebruiker & bestandssysteem*): Chromium-profiel op tmpfs / wipe per sessie.
- **Verificatie e2e:** GNOME → klik Toetsmodus → sway-kiosk op VT4 → Chromium fullscreen → extensie aanwezig
  → verbindt met `focus-api.edugolo.be` → leerling op join. Ctrl+Alt+Fn doet niets. "Afsluiten" → terug GNOME.

### Fase 4 — Hardening (de "laag 1"-vloer)
- **In de kiosk:** geen VT-switch (sway), geen sway-exec/keybinds, geen terminal, Chromium-policy tegen
  devtools/incognito/downloads/printen waar nodig, USB-mass-storage-beleid overwegen.
- **In GNOME (beheerd):** dconf-lockdown (geen systeeminstellingen wijzigen, geen extra software,
  vergrendelde locale/keyboard). GNOME-integriteit is voor *toestelbeheer*, niet voor examenintegriteit
  (die zit op de Focus-laag), dus pragmatisch dichttimmeren — niet overdrijven.
- Overweeg `gnome-terminal` weglaten op leerling-profiel.

### Fase 5 — Signing, policy.json & auto-update (productie-distributie)
- **CI** (port POC `build.yml`): buildah → GHCR `ghcr.io/<owner>/coolbx-os`, **cosign sign-by-digest**,
  enkel op default branch, key via secret. `build-disk.yml` voor qcow2/anaconda-iso via bootc-image-builder
  (container werkt nog; bron-repo is gearchiveerd naar `osbuild/image-builder`).
- **On-device verificatie:** `system_files/etc/containers/policy.json` met `default: reject` +
  `sigstoreSigned`/`matchRepository` voor de GHCR-namespace; **`keyPaths` (meervoud, 2 keys)** vanaf dag 1
  voor sleutelrotatie; `registries.d` met `use-sigstore-attachments: true`; public key in `/etc/pki/containers/coolbx.pub`.
- **Auto-update voor onbeheerde schooltoestellen:** geen kale 8u-timer (rebootet midden in een toets).
  Drop-in op `bootc-fetch-apply-updates.timer` met **off-hours window** (`--download-only` overdag,
  `--from-downloaded --apply` 's nachts), of uupd-stijl (stage + apply bij natuurlijke reboot). Verifieer
  timer-waarden op de gekozen base.

### Fase 5b — Deployment op hardware (FOG-flow) — *niet prioritair, latere fase*
Interactief master-image → generaliseren → FOG capture → FOG deploy → first-boot regen → OTA.
- **`build-disk.yml`**: behoud interactieve **`anaconda-iso`** (master-build) + `raw`/`qcow2` voor test.
  Bouw de master-rootfs als **`ext4`** (BIB `--rootfs=ext4`) voor FOG-vriendelijke, resizable images
  (btrfs werkt via partclone maar is fussier) — bevestig in test.
- **`coolbx-generalize`** (`system_files/usr/bin/`, bootc-"sysprep"): wis vóór FOG-capture
  `/etc/machine-id` (leeg laten), SSH host keys, persistente net-regels, journald-logs,
  `/var/lib/coolbx/*`-markers en ansible-state. Te draaien op de master net vóór capture.
- **First-boot regen-service** (`coolbx-firstboot-*`): per toestel machine-id (systemd auto bij lege id),
  hostname (of FOG's hostname-feature), `growfs`/`growpart` als doelschijf groter is.
- **Aannames/hardening:** identieke of grotere schijf + zelfde partitielayout (bootc BLS blijft geldig);
  geen full-disk-encryptie (kiosk, geen lokale data).
- **Verificatie:** master interactief installeren → generaliseren → FOG capture → deploy op 2 toestellen →
  beide unieke machine-id/hostname → `bootc status` ok → **OTA-update pullt door na de kloon**.

### Fase 6 — Vlootbeheer via ansible-pull (port)
- Port de POC `ansible-pull.timer/.service` → repo `github.com/edugolo/ansible` (of `coolbx-ansible`).
- Groepsdetectie via `/usr/share/ansible/laptop-group` (leerlingen/leerkrachten/administratie) → per-rol playbooks.
  Beheerde GNOME-laptop maakt dit zinvol (verschillende profielen, niet enkel kiosk).
- **Haalbaar voor scholen?** Ja — git-gebaseerde `ansible-pull` vereist **geen centrale server/MDM-infra** en is
  operationeel eenvoudig (een git-repo, geen orchestrator). **Maar scope het strak:** enkel voor échte
  runtime/per-toestel/per-rol-config (groepslidmaatschap, netwerk/printer, enrollment, kleine policy-toggles).
  **Niet** voor software-installatie of kernconfig — dat hoort in het *image*, anders vecht het met bootc's immutable
  model (config-drift + twee bronnen van waarheid). De Chromium-policy/managed-storage zit dus in het **image**, niet in ansible.
- Idempotente, minimale playbooks. Fleet/MDM (de POC's uitgecommentarieerde `fleetctl`) is een latere optie bij grote schaal.

### Fase 7 — Branding & afronding
- coolbx-glyph/wordmark binnen de coolbx-familie (parallel aan "coolbx focus"); GNOME-wallpapers + GDM.
- Schrap POC-restanten (`NAAMKEUZE-SchoolBX.md`, `chatgpt/`-assets).
- Distilleer relevante delen terug in `CLAUDE.md` (statusupdate: niet langer "nul").

---

## Te creëren/wijzigen sleutelbestanden (nieuw, geïnspireerd op POC-paden)

- `Containerfile`, `Justfile`, `.github/workflows/build.yml` + `build-disk.yml`
- `build_files/01-packages.sh`, `02-config.sh`, `03-gnome-dconf.sh`
- `system_files/etc/chromium/policies/managed/coolbx-focus.json`  ← **Fase 2 kern**
- `system_files/usr/bin/coolbx-kiosk-start`  (port van POC `start-focus`)
- `system_files/usr/share/coolbx/kiosk/sway.conf` + `waybar/`-config
- `system_files/usr/share/applications/coolbx-toetsmodus.desktop` + `etc/polkit-1/rules.d/49-coolbx-kiosk.rules`
- `system_files/usr/lib/sysusers.d/kiosk.conf`, AccountsService
- `system_files/etc/containers/policy.json`, `registries.d/`, `/etc/pki/containers/coolbx.pub`
- `system_files/usr/bin/coolbx-generalize` (bootc-"sysprep" vóór FOG-capture) + first-boot regen-service
- `system_files/usr/lib/systemd/...` units (firstboot-user, ansible-pull, update-drop-in) — `coolbx-*` benaming
- `docs/DEVELOPING.md` (lokale dev-workflow / VM)

## Open spikes / risico's
1. **`chrome.storage.managed` op Fedora-Chromium** (Fase 2) — minst gedocumenteerd; vroeg in VM bewijzen.
2. **sway-versie + Ozone-keybind-gedrag** — bevestig dat keybinds écht onbruikbaar zijn voor de leerling en VT-switch dicht is.
3. **fedora-bootc + GNOME** — minimale base zelf tot bruikbare beheerde desktop maken (Fedora-docs "building your own atomic bootc desktop" als gids); UB-`build_files` als referentie bij hardware-/firmware-problemen.
4. **`.crx`-signing & `update.xml`-hosting** (Focus-kant) — ID `makdakigkdbicdljgdclgnejachcohag` moet kloppen.
5. **OS↔Focus exit-signaal (extensie blijft cross-platform).** v1: bewuste exit = **waybar-knop** (OS-side, schone stop); de extensie toont enkel de "ingediend? zeker?"-UX en sluit haar venster. v2 (nice-to-have): **native-messaging host** op Coolbx OS die de extensie kan aanspreken om de sessie te beëindigen — **feature-detected**, zodat dezelfde extensie op andere platforms gewoon no-opt. Bewuste exit vs. crash onderscheiden via Chromium-exitcode (anders herstart `Restart=always` de browser).
6. **FOG-kloon van bootc — niet prioritair (latere fase).** Near-term uitrol = interactieve Anaconda-ISO. De generaliseer-logica is sowieso nuttig (zie *Powerwash*), maar de FOG-kloonvalidatie (`ext4`-rootfs, machine-id-regen, BLS overleeft kloon, OTA-na-kloon) schuift naar later.
7. **Toestel-attestatie** (zie sectie) — TPM-enrollment + native-messaging-agent ontwerpen we nu; diepe remote-attestatie is later. Gedeeld contract met Focus-server.
8. **Powerwash/rollback** (zie sectie) — `bootc install reset` experimental-status, greenboot-rs op het bootc-pad, systemd-versie ≥258, Cockpit-ostree op bootc: in VM bevestigen.

## Eindverificatie (e2e in VM, `just run-vm-qcow2`)
Boot → beheerde GNOME (NL/BE) → "Toetsmodus" → vergrendelde sway-kiosk → Chromium kiosk met
geforceerde Focus-extensie → managed-storage (`serverUrl`/`kioskMode`) bevestigd via `chrome://policy` +
`chrome.storage.managed.get()` → leerling landt op join via `focus-api.edugolo.be` → geen ontsnapping
(VT/keybinds dood) → bewuste "Afsluiten" → terug naar GNOME. Update- en signing-pad getest met een tweede image-tag.
```
```
