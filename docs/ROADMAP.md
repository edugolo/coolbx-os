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
- **Updates onzichtbaar/automatisch**; **mask** `bootc-fetch-apply-updates.timer`. Voorkeur: **uupd direct gebruiken**
  (COPR `ublue-os/packages`, `systemctl enable uupd.timer`) i.p.v. zelf bouwen — het **staget enkel** (`bootc upgrade`,
  **nooit** `--apply`/reboot) en levert gratis **hardware-gating** (batterij/AC/load/bandbreedte vóór het update). Timer:
  `OnCalendar=04:00` + `Persistent=true` (nacht-uit → inhalen) + `RandomizedDelaySec=15m` (thundering-herd op de update-server).
  Staged-zonder-reboot = exact onze "nooit rebooten midden in een toets"-eis; de leerling reboot op een natuurlijk moment.
- **Greenboot (greenboot-rs)** = vangnet: health-checks **lokaal only** ("greeter start", "kiosk-unit start") —
  **nooit** "focus-api bereikbaar" (externe outage zou de hele vloot doen terugrollen — door UBlue-onderzoek bevestigd
  als de juiste stance). `GREENBOOT_MAX_BOOT_ATTEMPTS=3`, eigen checks in `/etc/greenboot/check/required.d/`. Auto-rollback na N gefaalde boots.
- **Deployment-pinning per examenperiode:** `ostree admin pin <index>` zet de bekend-goede deployment vast (niet
  weg-gegarbagecollect) zodat een tussentijdse OTA nooit een examen-kritieke werkende staat overschrijft. `bootc rollback` = handmatige escape.
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
  **Géén eigen Secure-Boot-key/MOK-enrollment nodig** zolang we **geen out-of-tree kernelmodules** bouwen — Fedora's
  gesigneerde shim+kernel blijven geldig. Bewust zo houden: `mokutil`-MOK-enroll is fysiek/interactief per toestel
  (firmware-prompt) en schaalt niet in de FOG-massauitrol. → [ADR-0019](../docs/adr/0019-secure-boot-geen-custom-modules.md).
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
✅ **Force-install + managed-storage GEVERIFIEERD tegen productie** ([ADR-0021](../docs/adr/0021-fase2-force-install-geverifieerd.md),
`tests/test_06_focus_contract.py` groen): `coolbx-managed.json` met `ExtensionSettings.<ID>` (`force_installed` +
live `update_url` + `override_update_url`) **+ `3rdparty.extensions.<ID>`** (`serverUrl`/`kioskMode`). De live
`update.xml` serveert de echte `.crx` v0.14.0 → Chromium installeert + levert de managed-waarden af (chrome://policy
status OK) → de extensie reageert op `kioskMode`. **Géén externe blocker** (dashboard is live); integratietest is wel
connectiviteits-afhankelijk. `<ID>` = `makdakigkdbicdljgdclgnejachcohag`.
⏳ **Nog open: de enforcement-policy-set** (`coolbx-enforcement.json`): DeveloperToolsAvailability, IncognitoModeAvailability,
DownloadRestrictions, BrowserGuestModeEnabled, file://-blok. ⚠️ Eerst onderzoeken of `DeveloperToolsAvailability:2`
de CDP-debugpoort/e2e-harness breekt; scopen (globaal-veilige keys vs kiosk-only URL-blocking).

### Fase 3 — Vergrendelde kiosk-sessie (sway + waybar + Chromium)
`coolbx-kiosk-start` (port van de `systemd-run`/VT-mechaniek uit POC `features/focus-mode/system_files/usr/bin/start-focus`,
maar `cage`→`sway`, `focus-app`→Chromium). Unit `coolbx-kiosk` (user `kiosk`, tty4, `ExecStartPre`-wipe, `ExecStopPost=+chvt 2`).
**Geen `Restart=always` op unit-niveau** — bewuste exit = `systemctl stop`; crash-recovery enkel op de **inner browser-wrapper**
met max-restart-rate + fail-closed scherm bij crash-loop. waybar "Sessie afsluiten" met **OS-side confirm** (niet enkel Focus).
sway.conf + logind-config + `SWAYSOCK`-afscherming + multi-output-mirror als artefacten. polkit `49-coolbx-kiosk.rules` (één action-id).

### Fase 4 — Hardening + vrije-modus + a11y
✅ **DevTools-block (de #1 cheat-vector) — dev/prod-gated, geverifieerd** ([ADR-0022](../docs/adr/0022-fase4-devtools-dev-prod-gating.md)):
threat-probe toonde dat F12/Ctrl+Shift+I gewoon DevTools opent in de kiosk → `DeveloperToolsAvailability:2` in
`coolbx-hardening-prod.json` (prod), in dev verwijderd door `install.sh`/`vm-sync` (want het breekt óók `Runtime.evaluate`/CDP
— harness). Build-gating bewezen (prod-image heeft de key, dev niet). Globaal-veilige enforcement (`coolbx-enforcement.json`:
Incognito/GuestMode/BackgroundMode) geldt in álle builds. Harness robuust gemaakt (first_page skipt extensie-pagina's, policy-poll).
✅ **`file://`-blok** (`URLBlocklist file://*`) ook in `coolbx-hardening-prod.json` — runtime-geverifieerd: `/etc/passwd`
geblokkeerd, prod-kiosk laadt https. ✅ **Klok-lockdown** (`managed`-feature, `test_10`): polkit weigert
`timedate1.set-time/-timezone/-ntp` voor niet-wheel + geforceerde NTP (chronyd) → leerling kan de examentijd niet manipuleren.
⏳ **Nog open in Fase 4 (lager/productbeslissing):** brede dconf-lockdown vrije modus (gschema-override + locks/), downloads/print-policy,
prod-runtime-verificatie van de DevTools-block (QMP-F12+screendump, want CDP is dan dood), GNOME-gast onbereikbaar tijdens kiosk, a11y.
**dconf-aanpak (UBlue-patroon):** schrijf defaults als
**gschema-override** (de enige bron), valideer met `glib-compile-schemas --strict` in een wegwerp-dir (vangt typefouten
vóór ship), en gebruik **`db/distro.d/locks/`** om kiosk-relevante keys **hard te vergrendelen** tegen wijziging
(sterker dan losse db-keyfiles handmatig schrijven).

### Fase 5 — Signing, policy.json, auto-update + **canary**
✅ **GROTENDEELS GEBOUWD + (deels) geverifieerd** ([ADR-0023](../docs/adr/0023-fase5-ci-signing-update.md), `test_07_fleet.py`):
`.github/workflows/build.yml` (GHCR + cosign sign-by-digest, prod-build, dagelijkse cron, rechunk, SHA-gepind, `:stable`/PR-gating);
`fleet`-feature met **staged auto-update** (default-timer masked, `coolbx-update.timer` stage-only 04:00+Persistent+jitter) en
**greenboot** (lokale required.d-check, géén focus-api) — beide koude-boot-geverifieerd. **Signing-scaffold** veilig niet-actief
(`docs/SIGNING.md`) tot de cosign-keypair bestaat. ⏳ **Jouw eenmalige opzet:** cosign-keypair + `SIGNING_SECRET`-secret +
`cosign.pub` committen → policy activeren. **Canary:** `:testing`-ring nog te promoten. **Renovate** + BIB-pin nog toe te voegen.

CI (start van `ublue-os/image-template:build.yml` — één image, **géén** multi-flavor matrix): buildah → GHCR
`ghcr.io/<owner>/coolbx-os`, **cosign sign-by-digest** (`--digestfile` → `cosign sign @${DIGEST}`), login/push/sign
**`if`-gated** op default branch (PR's bouwen maar publiceren/signen nooit). **Dagelijkse `schedule`-cron** zodat
fedora-bootc-CVE-fixes automatisch doorvloeien naar de vloot; **actions SHA-gepind + Renovate**. **Canary-tags
`:testing`/`:stable`.** On-device: `policy.json` (`default: reject` + `sigstoreSigned`/`matchRepository`, `keyPaths` ×2
voor rotatie, key-recovery) + `registries.d` (**`use-sigstore-attachments: true`**) + `/etc/pki/containers/coolbx.pub`.
**Rechunk tussen build en push** (`rpm-ostree compose build-chunked-oci --max-layers 127 --bootc`, root) → pakket-gegroepeerde
lagen → veel kleinere `bootc upgrade`-deltas (cruciaal voor laptops over schoolnet). **`bootc container lint`** als laatste
Containerfile-laag (faalt non-conforme builds). Off-hours update-timer (`Persistent=true`). greenboot-rs + **lokale**
`required.d`-checks. BIB-image **gepind** (niet `:latest`). *(SBOM/provenance = optioneel, later; past bij het scholen-vertrouwensverhaal.)*

### Fase 5b — Deployment FOG-flow — *niet prioritair, latere fase*
Interactieve Anaconda-ISO (master) via BIB `--type anaconda-iso`, naar het `ublue-os` `iso-gnome.toml`-patroon:
Anaconda-modules **disabled** (Network/Security/Services/Users/Subscription/Timezone), enkel **Storage+Runtime** →
minimale snelle installer; kickstart-post `bootc switch --mutate-in-place --transport registry ghcr.io/<owner>/coolbx-os:stable`
zodat de master meteen op het juiste OTA-kanaal staat. Daarna `coolbx-generalize` (sysprep: machine-id=`uninitialized\n`,
SSH-keys, logs, `/var/lib/coolbx/*`, ansible-state — **ons eigen werk**, UBlue kloont niet) → FOG capture → deploy →
first-boot regen (machine-id/hostname/growfs) → OTA. Master-rootfs `ext4` (parametriseer `--rootfs`; bevestig dat FOG
btrfs aankan, anders ext4 forceren; draai ≥1 ext4-build in de loop). Validatie van OTA-na-kloon = later.

### Fase 6 — Vlootbeheer via ansible-pull (strak gescoped)
✅ **GEBOUWD + koude-boot-geverifieerd** (`fleet`-feature, `test_08_ansible.py`, 32/32): `coolbx-ansible-pull`
(system-oneshot) + `.timer` (OnBoot+1h, Persistent, jitter). **Configureerbare repo** via `/etc/coolbx/ansible.conf`
(no-op zolang placeholder → veilig default, geen rebuild nodig om te activeren). Rol via `/usr/share/coolbx/ansible/laptop-group`
(default `leerlingen`) → meegegeven als `coolbx_group`-extra-var zodat `local.yml` per rol vertakt. **Strak gescoped**
(test bewaakt: geen dnf/rpm/bootc in de puller). Mechaniek bewezen: pull → apply → **idempotent** (`changed=1`→`changed=0`).
⏳ **Jouw kant:** de echte playbook-repo (`github.com/edugolo/coolbx-ansible` met `local.yml`) + de URL in `ansible.conf`/ansible
zetten. Groepstoewijzing per toestel (FOG/host_vars/handmatig) — `[te bevestigen]`.

### Fase 7 — Branding (play↔focus)
Eigen OS-glyph + accent (géén schild) rond de **play↔focus-dualiteit**; Plymouth/GDM/os-release vroeg zetten zodat
latere fasen niet op "generieke Fedora" testen. `generate.sh`-pijplijn als "branding"-feature. Hero-art = designpass (ik scaffold).

### Fase 8 — Observability & support  *(nieuw)*
✅ **`coolbx-status` gebouwd + geverifieerd** (`fleet`-feature, `test_11`): lokaal overzicht voor schoolIT —
OS-image, update-stand (gestaged/volgende run), boot-gezondheid (greenboot), kiosk-/Focus-gereedheid, attestatie-daemon,
toestel-ID, gefaalde units. **Bewust geen open admin-poort** (Cockpit = gevlagde optie, firewall-naar-schoolnet).
⏳ Nog: support-/escalatiepad, `[te bevestigen]` centrale telemetrie (privacy — minderjarigen).

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
