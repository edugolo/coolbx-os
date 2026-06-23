# Coolbx OS — kickoff / handoff

> Geschreven op 2026-06-23 vanuit een Coolbx Focus-sessie, als brief voor een
> **verse Claude-sessie in deze map**. Niets hier is af — dit is richting + harde feiten.
>
> **Begin de nieuwe sessie met het kortsluiten van waar we naartoe willen** (§1 + §2),
> vóór er iets gepland of gebouwd wordt. Verschillende stukken staan nog open — vooral
> het kiosk/WM-mechanisme (§4) — en de POC is daar half in transitie. Eerst richting,
> dan plan-mode.

## 1. Wat is dit en waarom

**Coolbx OS = de "device floor": een vergrendeld Linux-OS** (Fedora bootc /
Universal Blue) dat van een gewone laptop het equivalent van een locked, managed
Chromebook maakt. Het is de laag die **echte toets-vergrendeling** levert die
Coolbx Focus op zichzelf níét belooft.

De positionering (vastgelegd in de Focus-repo):
- **Coolbx Focus** = lesbegeleidingstool + in-klas-toetsen mét de leerkracht erbij.
  Géén proctoring op zichzelf.
- **Coolbx OS** = het vergrendelde toestel eronder → samen = waterdichte toetsafname.
- Ze lanceren als **familie onder de coolbx-vlag**. Coolbx OS is een sterk argument
  om de OS op scholen te zetten.

We zijn bewust gestopt met proctoring benaderen via Google Workspace/Chromebook-
hardening. Coolbx OS is het eerlijke alternatief: een toestel waar de leerling
niet uit kan, met de productie-Focus-extensie er geforceerd op.

## 2. Beslissingen die al vastliggen

- **Eigen repo, los van de Focus-monorepo.** Toolchain (bootc/podman/`just`/ansible,
  ~134MB image-artefacten) deelt niets met de pnpm/vite-wereld. Afstemming gebeurt
  via 3 naden: gedeelde brand, één umbrella-site, en het integratiecontract (§4).
- **Vers herbouwen, niet de POC verderzetten.** De POC bundelt een legacy Electron
  `focus-app` — die last willen we niet meeslepen. Bouw rond de **productie-extensie**.
- **OS draait Chromium + de productie student-extensie** (zie §4), niet de Electron-app.

**Nog open (te bespreken in de nieuwe sessie, niet beslist):**
- **Kiosk/WM-mechanisme.** Cage is in de POC half uitgefaseerd (zie §3) — de keuze
  tussen cage, gnome-kiosk, labwc/sway, of een vergrendelde GNOME-sessie ligt open.
- Hoeveel "gewoon toestel" vs "pure kiosk" we willen (alleen Chromium, of ook een
  beperkt bureaublad eronder).
- Branding/naam definitief (Coolbx OS vs SchoolBX-restanten).

## 3. De POC als referentie (NIET kopiëren-en-klaar)

Bevroren in **`/home/johan/code/coolbx-poc/coolbx-os`**. Goede patronen om te
hergebruiken / als startpunt te lezen:

| Wat | POC-pad | Hergebruiken? |
|---|---|---|
| bootc image-build | `Containerfile` | ✅ patroon overnemen |
| build-recipes (VM/ISO/qcow2) | `Justfile` | ✅ |
| pakketten (chromium, gnome, ansible) | `build_files/01-packages.sh` | ✅ |
| first-boot user + locale `nl_BE`/`be` | `system_files/usr/libexec/schoolbx-firstboot-user.sh` | ✅ (hernoem schoolbx→coolbx) |
| periodieke config-pull | `system_files/.../ansible-pull.*` (repo `edugolo/ansible`) | ✅ overweeg |
| GHCR + cosign CI | `.github/workflows/build*.yml` | ✅ |
| **kiosk-sessie** | `features/focus-mode/install.sh` + `system_files/usr/bin/start-focus` | ⚠️ **open ontwerp** (zie §4) |
| **legacy Electron focus-app RPM** | `features/focus-mode/local_rpms/focus-app-*.rpm` | ❌ **droppen** |

⚠️ **De POC is inconsistent rond de kiosk** — cage staat **uitgecommentarieerd** in
`build_files/01-packages.sh:46`, terwijl `features/focus-mode/install.sh` cage nog
actief installeert; `gnome-session` wordt óók geïnstalleerd. Met andere woorden: het
kiosk/WM-mechanisme is in transitie en **niet beslist**. De POC's `start-focus` doet
nu nog `cage -- /usr/bin/focus-app` (user `focus`, tty4, VT-switch dicht) — lees het
als één mogelijke aanpak, niet als de gekozen aanpak.

## 4. Het integratiecontract (de kern van de hele oefening)

**Het WAT staat vast, het HOE (welke kiosk/WM) is open.**
- ✅ Vast: het OS draait **Chromium** met de **productie student-extensie
  force-installed** + managed-storage. Geen Electron-app.
- ⬜ Open: hóe Chromium als kiosk draait — cage, gnome-kiosk, labwc/sway, of een
  vergrendelde GNOME-sessie. Te beslissen in de nieuwe sessie (zie §3 voor POC-staat).

Productie-extensie staat in:
`/home/johan/code/coolbx/coolbx-focus/apps/student-extension`

Harde feiten (geverifieerd uit `manifest.json` + `public/managed_schema.json`):

| Item | Waarde |
|---|---|
| Extension-ID (vast via `key` in manifest) | `makdakigkdbicdljgdclgnejachcohag` |
| `minimum_chrome_version` | `116` |
| Update-bron (`update.xml`) | `https://focus-dashboard.edugolo.be/extension-updates/update.xml` |
| Managed-storage schema | `serverUrl` (string), `kioskMode` (boolean) |
| Aan te leveren managed values | `serverUrl = https://focus-api.edugolo.be`, `kioskMode = true` |
| Browser | **Chromium** (geen Electron focus-app) |
| Kiosk-compositor | **open** — cage / gnome-kiosk / labwc / sway / locked GNOME (te beslissen) |

> Dit zijn exact de waarden die op managed Chromebooks via de Google Admin Console
> werden gezet (force-install + managed storage). Coolbx OS doet hetzelfde, maar
> dan via Chromium enterprise policy op een Linux-toestel — zonder Google.

**⚠️ Open spike vóór je bouwt** — het exacte Linux-Chromium-mechanisme verifiëren:
- **Force-install** van de extensie vanaf de eigen `update.xml` → policy
  `ExtensionInstallForcelist` (of `ExtensionSettings` met `installation_mode:
  force_installed` + `update_url`), als JSON in `/etc/chromium/policies/managed/`.
- **`chrome.storage.managed` aanleveren** (serverUrl, kioskMode) op Linux Chromium —
  dit is een ander mechanisme dan browser-policy; uitzoeken waar Chromium de
  3rd-party managed-storage JSON per extensie leest. Dit is hét stuk dat je vroeg
  experimenteel moet bevestigen (in een VM via `just run-vm-*`).
- Check `chrome://policy` en `chrome.storage.managed.get()` in de extensie om te
  bewijzen dat de waarden aankomen.

## 5. Voorgestelde fasering (Part B Phase 1)

1. **Repo opzetten** — `git init`, schone Containerfile/Justfile op basis van de POC,
   GHCR + cosign CI. Naam/branding: kies definitief **"Coolbx OS"** (Containerfile-
   labels in de POC zeggen al "coolbx OS"); ruim de oude **"SchoolBX"**-restanten op
   (`branding/NAAMKEUZE-SchoolBX.md`, `schoolbx-firstboot-*`). Eigen glyph/wordmark
   binnen de coolbx-familie, parallel aan "coolbx focus".
2. **Kiosk-mechanisme kiezen + Chromium erin** — beslis eerst de WM/compositor (§4:
   cage / gnome-kiosk / labwc / locked GNOME), herwerk dan de focus-mode feature zodat
   Chromium daarin draait met force-install-policy + managed-storage. Spike in een VM.
3. **Bewijzen e2e** — VM boot → kiosk opent Chromium → extensie geforceerd aanwezig →
   verbindt met `focus-api.edugolo.be` → leerling landt op de join. Dit is hetzelfde
   gedrag als een managed Chromebook, nu op een vergrendelde laptop.
4. **Hardening** — VT-switch dicht (cage zonder `-s`), geen tty-escape, USB/devtools-
   beleid via Chromium-policy, forced re-enrollment-equivalent. Dit is de "laag 1"-
   vloer die vroeger via Workspace ging.

Daarna (latere fases): umbrella-site-sectie op `focus.edugolo.be`, release-afstemming
tussen OS- en Focus-versies.

## 6. Hoe deze sessie te starten met Claude

```bash
cd /home/johan/code/coolbx/coolbx-os
git init                      # verse repo
claude                        # of: claude --resume in een nieuwe sessie hier
```
Eerste prompt-suggestie:
> "Lees HANDOFF.md en verken de POC in /home/johan/code/coolbx-poc/coolbx-os.
>  Laten we eerst kortsluiten waar we met Coolbx OS naartoe willen: scope, het
>  kiosk/WM-mechanisme, en branding — vóór we iets plannen of bouwen."

Tip: begin met **richting kortsluiten** (een gesprek), pas daarna **plan-mode** voor
het implementatieplan. Er is veel te ontwerpen — vooral de kiosk/WM-keuze en de
managed-storage-spike — vóór er een Containerfile geschreven wordt. Distilleer deze
HANDOFF later in een `CLAUDE.md` zodra de projectstructuur staat.

## 7. Pointers

- **Volledig strategieplan** (Focus + OS): `/home/johan/.claude/plans/stateless-crunching-tide.md`
- **Focus-repo (productie)**: `/home/johan/code/coolbx/coolbx-focus`
  (remote `git@github.com:edugolo/focus-stack.git` — lokaal hernoemd naar coolbx-focus)
- **Productie-extensie**: `…/coolbx-focus/apps/student-extension`
- **Brand-masters (coolbx-familie)**: `…/coolbx-focus/branding` (parent `coolbx-mark.svg` / `coolbx-logo.svg`)
- **POC-referentie**: `/home/johan/code/coolbx-poc/coolbx-os` (+ legacy `…/coolbx-poc/focus-stack`)
- **Server/API in prod**: `https://focus-api.edugolo.be`, dashboard `https://focus-dashboard.edugolo.be`
