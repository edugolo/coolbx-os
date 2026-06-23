# Coolbx OS — productie-roadmap (v2)

> Status: **uitvoeringsklare blauwdruk.** v2 verwerkt een adversariële 3-lens review (techniek, security,
> operationeel) + drie richtingsbeslissingen. Code is nog niet geschreven; de repo bevat docs.
> Lees ook `CLAUDE.md` (oriëntatie) en de ADRs in `docs/adr/` (het *waarom*). Eerdere versies en de originele HANDOFF-brief zitten in de git-historie.

## Context

Coolbx OS = de "device floor": een vergrendeld Fedora **bootc**-OS dat van een schoollaptop het equivalent
van een managed Chromebook maakt, als onderlaag voor toetsafname met **Coolbx Focus**. Vers herbouwd vanuit
de bevroren POC (`/home/johan/code/coolbx-poc/coolbx-os`): Electron eruit, `schoolbx`→`coolbx`, Chromium-policy erin.

### Eerlijke framing (uit de security-review — belangrijk)

Coolbx OS beveiligt **het toestel, niet de ruimte**. Tweede toestel/telefoon/papier/kamergenoot blijven
**leerkracht-/proctoring-werk** (precies wat Focus claimt: "met de leerkracht erbij"). Examenintegriteit is
**gelaagd**: kiosk-jail + Chromium-policy (OS) + detectie/gegate-heropstart (Focus-server) + leerkracht-aanwezigheid.
`kioskMode=true` uit managed-storage is **cosmetisch** (toont enkel een wachtscherm) — alle echte enforcement zit
in de **Chromium-policy-set** + de **kiosk-jail**. v1 = "managed device + afleiding-/ontsnappingspreventie"; de
harde anti-spoofing/fysieke hardening volgt als fast-follow (zie *Security & dreigingsmodel*).

### Richtingsbeslissingen (plansessie)

| Knoop | Keuze |
|---|---|
| **Toestelmodel** | Beheerde GNOME-laptop die op aanvraag in een vergrendelde **sway**-kiosk schakelt |
| **Account-model** | **Pilot: gedeeld toestel + autologin-gastsessie** (reset bij logout/reboot). Breed model beslist na pilot-spike |
| **Base-image** | **Beslist na base-spike**: fedora-bootc minimaal vs `ublue-os/base-main`, beide bouwen + in VM vergelijken |
| **Kiosk-compositor** | sway + waybar (wifi/batterij/klok), aparte Wayland-sessie op eigen VT |
| **Browser** | RPM-Chromium (Fedora-repo), geen Flatpak, geen Electron |
| **Examen-integriteit** | Focus-server-laag (bewust afsluiten + herneemcode) + leerkracht; geen onbreekbare OS-jail |
| **Security-ambitie v1** | **Pilot-eerlijk**: kiosk-jail + Chromium-policy nu; Secure Boot/firmware-pw/enrollment-credential als fast-follow |
| **Uitrol** | Interactieve Anaconda-ISO + FOG-kloon (FOG niet-prioritair); canary `:testing`→`:stable` |

### Architectuur

```
Boot → GDM autologin → beheerde GNOME-gastsessie (reset bij logout)      [VT2, "play"/vrije modus]
                 │  leerling klikt "Toetsmodus" → pkexec coolbx-kiosk-start
                 ▼
        transiente systemd-sessie (user: kiosk, ephemeral home op tmpfs)  [VT4, "focus"/toets]
        sway (keybinds gestript, IPC-socket afgeschermd, VT-switch dood op logind-niveau)
          └─ waybar (wifi / batterij / klok / "Sessie afsluiten" + OS-confirm)
          └─ chromium --kiosk + ENFORCEMENT-policy → Focus-extensie (force-installed)
                 │  bewuste exit → OS-confirm → `systemctl stop coolbx-kiosk`
                 ▼  ExecStopPost: chvt 2 → terug naar GNOME   (herjoinen = herneemcode via Focus)
```

---

## Cross-cutting ontwerp

### Beslissingen vastleggen (ADR)
Niet-triviale keuzes worden vastgelegd als **ADR** in `docs/adr/` (MADR-lite: context → beslissing → gevolgen →
alternatieven). ROADMAP = het levende plan; ADRs = bevroren beslissingen met hun *waarom*. Tijdens autonome
uitvoering krijgt **elke spike-uitkomst en architectuurkeuze** een ADR, zodat het spoor auditeerbaar blijft.
Reeds genomen beslissingen zijn back-filled (zie `docs/adr/README.md`).

### Lokale dev-workflow (VM) — autonoom & machine-leesbaar
> De POC opende browser-VNC voor een mens — **onbruikbaar voor een autonome agent**. v2 gebruikt qemu-direct.
- **Build:** `podman build` (rootless). **Disk:** bootc-image-builder via `sudo podman` (passwordless ingesteld).
- **VM-run:** `qemu-system-x86_64` **direct** (rootless, `/dev/kvm`), met `-monitor` (unix socket) + SSH-forward `:2222`.
- **Ogen:** QEMU-monitor **`screendump out.ppm`** → Pillow → PNG die de agent leest. **Handen:** SSH + monitor `sendkey`.
- **Verificaties zijn machine-leesbaar:** SSH-CLI-checks (`bootc status`, `systemctl`, journald, policy-files) +
  screendump-PNG's. Browser-only checks (`chrome://policy`) worden vervangen door: policy-JSON valideren +
  headless `chromium` + een test-extensie die `chrome.storage.managed.get()` naar een bestand schrijft.
- Justfile: `build`, `build-prod`, `build-qcow2 [--rootfs]`, `dev-vm` (qemu-direct), `vm-ssh`, `vm-shot`, `lint`.
- `docs/DEVELOPING.md`: één pagina dev-loop. Dev-vs-prod strikt gescheiden; **CI-guard** faalt als `ENABLE_FIRSTBOOT_USER=1` in een prod-build lekt.

### Modulariteit (feature-model) — concreet mechanisme
> Een Containerfile kan **niet** "itereren" over een build-arg (geen loops).
- Eén `build_files/install-features.sh "$FEATURES"` (bash) dat over de feature-namen loopt en per feature
  `features/<naam>/install.sh` draait; één `RUN ... install-features.sh "${FEATURES}"` in de Containerfile.
- Elke feature self-contained + single-purpose (`features/<naam>/{install.sh, system_files/}`).
- **Twee lagen:** build-time features (image-capabilities: kiosk, branding) vs runtime **ansible-pull** (per-rol config).
  Kernconfig + Chromium-policy zitten in het **image**, niet in ansible (anti-drift).
- **Standalone-principe ([ADR-0012](../docs/adr/0012-standalone-os-focus-optioneel.md)):** de OS-kern staat los van Focus.
  Alle Focus-binding (extensie, managed-storage, device-auth) zit in een **optionele `focus`-feature**; een kale Coolbx OS
  heeft geen Focus-afhankelijkheid of -secrets. Coolbx OS is ook bruikbaar als generieke kiosk-/device-floor-distro.

### Identiteit, account & reset (pilot)
- **Pilot = gedeeld toestel, GDM-autologin naar een beheerd gastprofiel** dat bij logout/reboot reset → lost
  én "wie logt in" én "reset tussen leerlingen" op zonder wachtwoord-/SSO-moeras. Geen persistente persoonlijke data in pilot.
- Drie reset-niveaus expliciet: (a) **per-toets** = ephemeral kiosk-home (tmpfs); (b) **per-leerling/lesuur** =
  gast-logout wist het GNOME-profiel; (c) **factory** = powerwash (`bootc install reset`, jaarlijks/overdracht).
- `[te bevestigen na pilot]` breed model: persoonlijk lokaal account vs centrale SSO (Entra/Google/LDAP) +
  home-provisioning. Niet bouwen vóór pilot-feedback.

### Netwerk & connectiviteit *(nieuw — operationele showstopper)*
- **Schoolwifi/eduroam (WPA2-Enterprise):** NetworkManager **system connections** in het image (of via ansible),
  certificaten meegeleverd; niet afhankelijk van leerling-input.
- **Captive portals:** afhandelen op de **GNOME-laag** (connectivity-check + portal-helper) **vóór** de kiosk start;
  de kiosk start pas bij bevestigde connectiviteit. Egress-lockdown mag de portal niet blokkeren.
- **Egress-lockdown (kiosk):** nftables met **uid-match op de kiosk-user**, allowlist op focus-domeinen, vaste
  DNS-resolver, al het andere **fail-closed** drop. Bij verlies van focus-api → kiosk toont "geen verbinding —
  toets gepauzeerd" (vervangt webcontent), laat de leerling niet vrij in een offline browser.
- `[te bevestigen]` mag de leerling in vrije modus zelf een SSID/wachtwoord kiezen (botst met dconf-lockdown)?
- Documenteer proxy/captive-portal-gedrag op schoolnetwerken.

### Vrije modus — capability-matrix *(nieuw — was enkel branding-concept)*
Concreet gedrag (pilot-defaults, `[te bevestigen]`):
| Capability | Pilot-default |
|---|---|
| Apps | Chromium + bestandsbeheer + basis (geen terminal voor leerling) |
| Web-filtering | Geen (open) in vrije modus `[te bevestigen]` |
| USB-opslag | Lezen toegestaan in vrije modus, geblokkeerd in kiosk `[te bevestigen]` |
| Schrijfbare opslag | Ephemeral (gast-profiel) |
| Printen | `[te bevestigen]` — zo ja via ansible-printerconfig; anders expliciet "geen printen by design" |
Vrije modus = "play": gewoon-toestel-gevoel; kiosk = "focus": vergrendeld. Het OS draagt beide.

### Accessibility *(nieuw — wettelijk in onderwijs)*
- a11y-tools beschikbaar in kiosk én GNOME: Orca (schermlezer), vergroting, hoog-contrast.
- a11y-voorkeuren mogen **niet** door de ephemeral wipe verdwijnen → a11y-config buiten het gewiste profiel
  (systeem-dconf-defaults of een persistent a11y-laag). "Alle keybinds verwijderen" in sway mag a11y-sneltoetsen niet killen.
- Gedeelde naad: de Focus-toets-UI moet zelf a11y-vriendelijk zijn.

### Kiosk-gebruiker & bestandssysteem
- **Ephemeral, gegarandeerd schoon:** wipe in **`ExecStartPre`** (idempotent, dekt ook abrupte vorige stop) —
  niet enkel ExecStopPost. Chromium `--user-data-dir`, `--disk-cache-dir`, `TMPDIR` en `$HOME` allemaal op **tmpfs** onder `/run`.
- **Geen (of encrypted) swap** → geen profielresten op schijf.
- Aparte generieke `kiosk`-user, los van de GNOME-gast. Identiteit komt van Focus (join/herneemcode).

### Updates, rollback & powerwash (eindgebruiker, geen terminal)
- **Updates onzichtbaar/automatisch**; **mask** `bootc-fetch-apply-updates.timer`, eigen off-hours timer met
  `Persistent=true` (toestellen die 's nachts uit staan → inhalen bij volgende boot/idle).
- **Greenboot (greenboot-rs)** = vangnet: health-checks **lokaal only** ("greeter start", "kiosk-unit start") —
  **nooit** "focus-api bereikbaar" (externe outage zou de hele vloot doen terugrollen). Auto-rollback na N gefaalde boots.
- **Knoppen zonder terminal:** oneshot-units `coolbx-update`/`coolbx-rollback`/`coolbx-powerwash` achter een polkit
  `manage-units`-rule (uupd-patroon); GTK-knopje of Cockpit doet `systemctl start`.
- **Powerwash:** `bootc install reset --experimental --apply` (verse `/etc`, lege `/var`); **fallback** gedocumenteerd
  als de experimentele knop ontbreekt (handmatig `/var` wipen + redeploy). De generaliseer-logica (FOG) deelt dit.
- **GRUB:** geauthenticeerde recovery (zie hardening), korte timeout zodat rollback-entry bereikbaar blijft.

### Security & dreigingsmodel *(reframe — pilot-eerlijk)*
**v1-enforcement (nu):**
- **Chromium ENFORCEMENT-policy-set** (first-class, in Fase 2, niet "waar nodig"): `DeveloperToolsAvailability: 2`,
  `IncognitoModeAvailability: 1`, `DownloadRestrictions`, `URLBlocklist:["*"]` + `URLAllowlist` op focus-domeinen,
  `BrowserGuestModeEnabled: false`, `AllowFileSelectionDialogs: false`, externe protocol-handlers blokkeren, `file://`/`chrome://` dicht.
- **Kiosk-jail:** VT-switch dood op **logind/kernel-niveau** (geen extra getty's op de kiosk-VT; bevestig dat
  Ctrl+Alt+F1..F12 dood is **tijdens een Chromium-crash**, niet leunen op de Ozone-keybind-quirk); sway zonder
  enige `bindsym` (ook defaults unbinden) en **`SWAYSOCK` afgeschermd** (`swaymsg exec` = terminal-spawn); externe
  monitors mirror/disable; klok niet leerling-instelbaar (polkit/dconf op timedate1 + geforceerde NTP).
- **GNOME-laag** mag tijdens een actieve kiosk niet bereikbaar zijn (geen VT-hop); polkit-regel strikt op één
  exacte action-id, launcher root-owned, geen leerling-args naar `systemd-run`.
- **Offline = fail-closed** (zie netwerk). Server is altijd tijd-/deadline-autoriteit (nooit clientklok).

**Fast-follow (na pilot, vóór "waterdicht"-claim):**
- **Anti-live-USB/fysiek:** UEFI Secure Boot AAN + **firmware-wachtwoord** + bootmenu-lock; **GRUB-wachtwoord** op edit;
  `kernel.sysrq=0`; Ctrl+Alt+Del masken. (Zonder firmware-pw is Secure Boot uit te zetten → alles waardeloos.)
- **Anti-spoofing via HMAC-handshake ([ADR-0013](../docs/adr/0013-anti-spoofing-hmac-per-device.md)):** hergebruik
  Focus' bestaande **HMAC-SHA256 handshake-schema**, maar met een **per-toestel-secret** dat bij enrollment wordt
  uitgedeeld en **root-only** (`0600 root`) bewaard, gesigneerd door een **OS-agent** (native-messaging-host, `allowed_origins`
  exact op de extension-ID) en geverifieerd door de Focus-server tegen een **allowlist** (met revocatie). **Geen gedeeld
  build-time secret** (extraheerbaar/per-toestel-loos). Veel lichter dan TPM/PKI en sluit de casual-spoof-gap. Restrisico
  (secret van schijf bij fysieke diefstal) → **TPM-sealing/FDE** hieronder.
- **Credential-bescherming:** TPM-sealing (en/of heroverweeg "geen FDE" — een credential op onversleutelde schijf is offline te stelen).
- `signing/policy.json`: `default: reject` + `sigstoreSigned`/`matchRepository` + **`keyPaths` (2 keys)** voor rotatie;
  **key-backup/recovery** gedocumenteerd (totaalverlies → vloot kan niet meer updaten).

**Extensie-permissies** (`<all_urls>`, `scripting`, `tabCapture`, `declarativeNetRequest`): blast-radius is groot →
OS-egress-lockdown staat **onafhankelijk** van de extensie (defense-in-depth). `update.xml`/dashboard = trusted compute base (pinnen).

### Toestel-attestatie — gelaagd
> Scope-bewaking: een autonome agent bouwt geen attestatie vóór de basis-kiosk e2e werkt.
- **v1 (fast-follow, concreet & licht):** HMAC-handshake met **per-toestel-secret** (zie *Security fast-follow* +
  [ADR-0013](../docs/adr/0013-anti-spoofing-hmac-per-device.md)). Hergebruikt Focus' schema; geen TPM/PKI nodig.
- **fast-follow hardening:** TPM-sealing van het per-toestel-secret + FDE tegen fysieke schijf-diefstal.
- **v2-visie:** diepe remote-attestatie (TPM-quote/measured boot) — later, gedeeld contract met Focus-server.
- **"Eén geheel" = de Focus-server** (enige runtime-verifier) + wij als operator, **niet** een gefuseerde build/deploy
  of een gedeeld build-time secret (zou de OS aan Focus koppelen — botst met [ADR-0012](../docs/adr/0012-standalone-os-focus-optioneel.md)).

### Vlootbeheer, uitrol & observability *(nieuw)*
- **Enrollment-tijdlijn (één verhaal):** v1-pilot = toestel boot met machine-id + hostname (first-boot regen); Focus-server
  vertrouwt toestellen op het schoolnetwerk (geen attestatie in pilot — **expliciet**). Fast-follow: enrollment deelt een
  **per-toestel HMAC-secret** uit (ADR-0013) → server-allowlist + revocatie (kwijt/gestolen).
- **Release-compatibiliteit (naad OS↔Focus):** een **compatibiliteits-matrix** (welke OS-versie ↔ welke Focus-server-/
  extensie-versie + HMAC-schema-versie). Aparte lifecycles/artefacten (OS-image op GHCR, Focus-server-deploy), gecoördineerd
  via dit contract — **geen** gefuseerde pijplijn ([ADR-0012](../docs/adr/0012-standalone-os-focus-optioneel.md)).
- **Canary/ring-uitrol:** image-tags `:testing` → `:stable`; handvol test-toestellen op `:testing`, vloot op `:stable`,
  **handmatige promotie**. Voorkomt dat één slechte build 's nachts de hele vloot sloopt (greenboot vangt enkel boot-crashes,
  niet "extensie laadt niet meer"). Ring-toewijzing via ansible.
- **Observability/support:** lokale status (greenboot-status, laatste OTA, kiosk-fouten) zichtbaar voor schoolIT
  (Cockpit lokaal); `[te bevestigen]` centrale telemetrie (privacygevoelig — minderjarigen). Support-/escalatiepad definiëren.
- **Leerkracht-interactie met het toestel:** OS biedt de waybar-exit + basis-toestelbediening; klassikaal beheer
  (30 toestellen in toetsmodus, status zien) = Focus-feature. Expliciet benoemen wat OS wél/niet doet.

---

## Fasering

### Fase 0 — Repo & skelet ✅ (gestart)
Repo geïnit (`main`), `.gitignore`, docs. Nog: skelet (`Containerfile`, `Justfile`, `build_files/`, `system_files/`,
`features/`, `.github/workflows/`, `docs/DEVELOPING.md`) + de qemu-direct dev-harness (`dev-vm`, `vm-ssh`, `vm-shot`).

### Fase 1 — De-risk spikes (vooraan, parallel) ⚠️ gate voor al de rest
Bewijs in de VM, machine-leesbaar, vóór fasen "af" heten:
1. **S1 base-spike:** triviaal `fedora-bootc:43 + GNOME` **én** `ublue-os/base-main` minimaal bouwen + booten in VM
   (+ liefst echte testhardware). **Beslis de base op bewijs.** Lever de volledige geverifieerde pakketlijst.
2. **S2 Chromium-spike:** `3rdparty` managed-storage (`serverUrl`/`kioskMode`) **+ de ENFORCEMENT-policy-set** met een
   **lokaal geladen** test-extensie (losgekoppeld van de externe `update.xml`). Verificatie = "devtools/downloads/`file://` dood",
   niet enkel "waarde komt aan".
3. **S3 kiosk-escape-spike:** sway-gestript + VT-lockdown op logind-niveau + SWAYSOCK afgeschermd; bewijs dat
   Ctrl+Alt+Fx dood is **tijdens een Chromium-crash**. Boot-time escape-test (GRUB/sysrq/live-USB) genoteerd voor fast-follow.
4. **S4 update-spike:** bestaat `bootc install reset --experimental` op de base? werkt greenboot-rs auto-rollback op het bootc-pad? → anders fallbacks.

### Fase 2 — Chromium-policy + enforcement (productie-vorm van S2)
Eén policy-JSON `system_files/etc/chromium/policies/managed/coolbx-focus.json`: `ExtensionSettings.<ID>`
(`force_installed` + `update_url` + `override_update_url`) **+ `3rdparty.extensions.<ID>`** (`serverUrl`, `kioskMode`)
**+ de enforcement-keys**. `<ID>` = `makdakigkdbicdljgdclgnejachcohag`. **Harde dependency-gate:** Focus-team levert
ondertekende `.crx` + bereikbare `update.xml` (anders blokkeert force-install — externe blocker).

### Fase 3 — Vergrendelde kiosk-sessie (sway + waybar + Chromium)
`coolbx-kiosk-start` (port van de `systemd-run`/VT-mechaniek uit POC `features/focus-mode/system_files/usr/bin/start-focus`,
maar `cage`→`sway`, `focus-app`→Chromium). Unit `coolbx-kiosk` (user `kiosk`, tty4, `ExecStartPre`-wipe, `ExecStopPost=+chvt 2`).
**Geen `Restart=always` op unit-niveau** — bewuste exit = `systemctl stop`; crash-recovery enkel op de **inner browser-wrapper**
met max-restart-rate + fail-closed scherm bij crash-loop. waybar "Sessie afsluiten" met **OS-side confirm** (niet enkel Focus).
sway.conf + logind-config + `SWAYSOCK`-afscherming + multi-output-mirror als artefacten. polkit `49-coolbx-kiosk.rules` (één action-id).

### Fase 4 — Hardening + vrije-modus + a11y
Kiosk-jail (zie security v1), vrije-modus capability-matrix toepassen (dconf-lockdown pragmatisch), klok-lockdown,
accessibility-laag. GNOME-gast onbereikbaar tijdens kiosk.

### Fase 5 — Signing, policy.json, auto-update + **canary**
CI (port POC `build.yml` — **verifieer dat de cosign-sign-stap er effectief in zit**): buildah → GHCR
`ghcr.io/<owner>/coolbx-os`, sign-by-digest, enkel default branch. **Canary-tags `:testing`/`:stable`.** policy.json
(`default: reject`, `keyPaths` ×2, key-recovery), `registries.d`, public key. Off-hours update-timer (`Persistent=true`).
greenboot-rs + **lokale** `required.d`-checks. BIB-image **gepind** (niet `:latest`).

### Fase 5b — Deployment FOG-flow — *niet prioritair, latere fase*
Interactieve Anaconda-ISO (master) → `coolbx-generalize` (sysprep: machine-id=`uninitialized\n`, SSH-keys, logs,
`/var/lib/coolbx/*`, ansible-state) → FOG capture → deploy → first-boot regen (machine-id/hostname/growfs) → OTA.
Master-rootfs `ext4` (parametriseer `--rootfs`; draai ≥1 ext4-build in de loop). Validatie van OTA-na-kloon = later.

### Fase 6 — Vlootbeheer via ansible-pull (strak gescoped)
Port `ansible-pull.timer/.service` → `github.com/edugolo/ansible`. **Enkel** runtime/per-rol-config (groep, netwerk/printer,
ring-toewijzing, kleine toggles) — **niet** software/kernconfig (die in image). Groepstoewijzing: hoe krijgt toestel #347
zijn `laptop-group`? (FOG/host_vars/handmatig — `[te bevestigen]`). Idempotent, minimaal. Vendoring i.p.v. netwerk-call in build.

### Fase 7 — Branding (play↔focus)
Eigen OS-glyph + accent (géén schild) rond de **play↔focus-dualiteit**; Plymouth/GDM/os-release vroeg zetten zodat
latere fasen niet op "generieke Fedora" testen. `generate.sh`-pijplijn als "branding"-feature. Hero-art = designpass (ik scaffold).

### Fase 8 — Observability & support  *(nieuw)*
Lokale vlootstatus (Cockpit), support-/escalatiepad, `[te bevestigen]` centrale telemetrie.

### Fase 9 — Pilot & school-documentatie  *(nieuw)*
School-/admin-docs (enrollment, reset, wifi, troubleshooting). Pilot op canary-ring met echte toestellen + feedback → breed accountmodel beslissen.

---

## Te creëren/wijzigen sleutelbestanden
`Containerfile`, `Justfile`, `.github/workflows/build.yml`+`build-disk.yml`, `build_files/{01-packages,02-config,03-gnome-dconf,install-features}.sh`,
`features/{kiosk,branding}/…`, `system_files/etc/chromium/policies/managed/coolbx-focus.json`, `…/usr/bin/coolbx-kiosk-start`,
`…/usr/share/coolbx/kiosk/{sway.conf,waybar/}`, `…/etc/polkit-1/rules.d/49-coolbx-kiosk.rules`, `…/usr/lib/sysusers.d/kiosk.conf`,
nftables egress-config, `…/etc/containers/{policy.json,registries.d/}` + `/etc/pki/containers/coolbx.pub`,
`…/usr/bin/coolbx-generalize`, greenboot `required.d`-checks, systemd units (`coolbx-*`), `docs/{DEVELOPING,SCHOOL-ADMIN}.md`.

## Open productkeuzes om te bevestigen (pilot-defaults gekozen, verfijnbaar)
Web-filtering vrije modus · USB-beleid · printen · meertaligheid (NL-only vs NL/FR + layout-switch) · zelf wifi kiezen ·
centrale telemetrie (minderjarigen) · `laptop-group`-toewijzingsbron · breed account-model (na pilot).

## Eindverificatie (e2e in VM, machine-leesbaar)
Boot → beheerde GNOME-gast (NL/BE) → "Toetsmodus" → sway-kiosk (VT4) → Chromium kiosk **met enforcement-policy
bewezen** (devtools/downloads/`file://`/VT-switch dood, ook tijdens crash) → Focus-extensie aanwezig → join via
`focus-api.edugolo.be` → offline = fail-closed → bewuste exit (OS-confirm) → terug GNOME → gast-logout wist profiel →
powerwash test → update/canary + greenboot-rollback test. Verificatie via SSH-CLI-checks + `screendump`-PNG's.
