# ADR-0020: e2e dev-automation-harness — host-gedreven (QMP + CDP + screendump/OCR)

- **Status:** Aanvaard (richting)
- **Datum:** 2026-06-25
- **Beslissers:** Johan, Claude
- **Bron:** 4 parallelle research-agents (CDP-in-VM · Wayland-input-injectie/libei · openQA/OS-e2e · ublue-os-build),
  + door de gebruiker aangedragen `OTAKUWeBer/Wayland-automation` en `agent-sh/computer-use-linux`.

## Context
Vóór we verder bouwen, moet de **dev-automation robuust** zijn: net als de Playwright-e2e van coolbx-focus willen we
een **herhaalbaar, machine-leesbaar e2e-script** dat de hele keten boot→GNOME→Toetsmodus→sway-kiosk→Chromium→Focus-extensie
verifieert in de QEMU dev-VM. Het kernprobleem was dat GUI-interactie (klikken/velden invullen) onbetrouwbaar was:
dogtail/AT-SPI op Wayland geeft coördinaten `0,0` (Wayland heeft per design geen globaal coördinatensysteem), en
pixel-klikken waren fragiel.

De e2e-keten omvat **twee Wayland-werelden**: de gewone desktop = **GNOME/Mutter**, de kiosk = **sway/wlroots**. Geen
enkel inject-mechanisme is overal het beste; Mutter ondersteunt de wlroots-protocollen (`zwlr_virtual_pointer`,
`zwp_virtual_keyboard`) **niet**, en libei werkt op GNOME enkel via een **goedkeuringsdialoog** (onbruikbaar onbemand).

## Beslissing
**Host-gedreven harness, zwaartepunt op staat/tekst-asserts, pixels als laatste redmiddel.** Lagen:

- **A — orkestratie:** pytest-fixtures rond `just dev-vm`; elke assert is een **gepolld predicaat met timeout**
  (`wait_for_unit`/`wait_for_open_port`/`wait_for_file`/`wait_for_text`/`wait_for_cdp`) — het NixOS-testdriver-patroon
  dat de "Playwright-auto-wait"-ervaring geeft.
- **B — systeemstaat (grootste winst, minste brosheid):** **SSH-CLI** (paramiko/`pytest-testinfra`): policy-JSON
  aanwezig, kiosk-unit `active`, extensie force-installed, locale/VT-staat.
- **C — Chromium-inhoud:** **Chrome DevTools Protocol over een SSH local-forward** (`-L 9222:localhost:9222`). Leest
  échte browserstaat (geen pixels): page-titel/DOM, `chrome://policy` (JSON-export, niet DOM-scrape), en
  `chrome.storage.managed.get()` via het **extensie-service-worker-target** (raw CDP; SW eerst wekken — MV3 slaapt na ~30s).
  Dit is het directe equivalent van de coolbx-focus-Playwright-aanpak.
- **D — shell-interactie (enkel waar B/C niet volstaan):** **QMP `input-send-event` + `virtio-tablet`** (host-side,
  vast bereik 0–32767 → **resolutie-onafhankelijk**, compositor-agnostisch, geen gast-software) voor de klik;
  **OCR-locate** (tesseract `image_to_data` op een `screendump` → pixelbox van de doeltekst) om te bepalen *waar* te klikken.
- **E — visuele assert:** `screendump` → **tesseract `wait_for_text`** (robuust tegen font/thema-wissels), niet
  openQA-needles. Vaste VM-resolutie + maskering van dynamische regio's (klok/cursor).

**CDP-flags zijn DEV-ONLY (veiligheidsgate).** `--remote-debugging-port` in een productie-toetskiosk is een
valsspeel-vector (open poort = volledige browsercontrole). De debug-flags worden **env-gated** (`COOLBX_KIOSK_DEBUG=1`)
en komen **nooit** in een prod-build — analoog aan `ENABLE_FIRSTBOOT_USER` ([memory/dev-tooling-uit-prod]). Een prod-assert
faalt de build bij een lek.

## Gevolgen
- **Verworpen:** **openQA** (overkill; needle-onderhoud breekt bij font/Chromium-bumps; de bootc-wereld + Universal Blue
  gebruiken het bewust niet — die doen CLI/SSH). **libei/RemoteDesktop-portal** als live-sessie-injectie (dialoog-gate op
  GNOME; het dialoog-vrije `grdctl --system`-pad injecteert enkel in een *aparte curtained* RDP-sessie, niet de zichtbare).
  **`computer-use-linux` MCP** als harness-basis (extra bewegend deel) — wel bruikbaar als optionele *interactieve* hulp.
- **In-gast inject-fallbacks** (indien ooit nodig): **ydotool/uinput** universeel (werkt op GNOME én sway, kernel-niveau),
  **`zwlr_virtual_pointer` + `wtype`** netter binnen de **sway-kiosk** (geen root). Maar voor de testloop wint QMP-tablet.
- **CDP-launch-flags (geverifieerd, elk een stille faalmodus):** `--user-data-dir=<niet-default>` is **dwingend** vanaf
  Chrome 136; `--remote-debugging-address=0.0.0.0` werkt **niet** meer (M113+ → loopback) → altijd tunnelen;
  `--remote-allow-origins=http://localhost:9222` nodig (Chrome 111+, anders 403 op de WebSocket).
- **Tesseract-op-host vs sudo-constraint:** passwordless sudo is enkel `podman`; OCR draait daarom via een **podman-container**
  (of in de dev-image via usr-overlay), niet via een host-`dnf install`.

## Gebouwd ✓ (geverifieerd: `just e2e` = 20 tests groen op een verse, gebakken VM)
`scripts/vm-cdp.py` (connect/targets/eval/managed/policy/**fill**/**type**), env-gate in
`features/kiosk/.../chromium-kiosk.sh` + doorforward in `coolbx-kiosk-start` (`COOLBX_KIOSK_DEBUG`),
`scripts/vm-ocr.py` + `tools/ocr/Containerfile` (tesseract in podman), Justfile-recepten
(`e2e`, `vm-cdp`, `vm-ocr`, `vm-find-click`, `ocr-build`, `vm-kiosk-debug`), en `tests/` (harness.py +
conftest.py + test_01..05 over lagen B/C/security/D/input).

## Bouw-valkuilen (opgelost tijdens het bouwen — zie [[e2e-cdp-harness]])
- **qcow2-corruptie:** nooit `build-qcow2` met een draaiende VM op de qcow2 → BIB overschrijft → emergency mode.
  `build-qcow2` heeft nu een guard die weigert bij een actieve VM-pid.
- **bind-mount-cache:** feature-edits komen niet in de image zonder cache-bust → `ARG FEATURES_CACHEBUST` +
  `--build-arg FEATURES_CACHEBUST="$(date +%s)"`.
- **Meet-valkuilen (geen OS-bug):** page-targets tellen op type `page` (niet substring; `background_page` matcht mee);
  debugpoort-veiligheid meten op de **open poort** (`ss :9222`), niet op `grep remote-debugging-port` (childprocessen
  dragen een lege `remote-debugging-port=`).

## Spikes bevestigd
1. ✅ `Page.captureScreenshot`/`screendump` onder `--ozone-platform=wayland` + virtio-GPU geeft een niet-zwart beeld (OCR werkt).
2. ✅ OCR vindt GNOME/kiosk-labels betrouwbaar (`--psm 11`, nld+eng).
3. ⏳ `chrome.storage.managed` via het service-worker-target — mechanisme gecodeerd + faalt netjes; vol bewijs hangt op Fase 2's extensie.
