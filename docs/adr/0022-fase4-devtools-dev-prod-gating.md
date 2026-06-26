# ADR-0022: Fase 4 — DevTools-hardening via dev/prod-gating

- **Status:** Aanvaard (geverifieerd)
- **Datum:** 2026-06-25
- **Beslissers:** Johan, Claude
- **Bouwt op:** [ADR-0020](0020-e2e-dev-automation-harness.md) (CDP-harness), [ADR-0021](0021-fase2-force-install-geverifieerd.md).

## Context
Threat-model-observatie (harness, "ogen"): in de kiosk opent **F12 / Ctrl+Shift+I gewoon DevTools**
(2 `devtools://`-targets verschenen) — de #1 cheat/escape-vector (console, extensie uitzetten, wegnavigeren).
De sway-sessie kan die toets niet onderscheppen (Chromium handelt 'm intern af). Enige betrouwbare blokkade =
de Chromium-policy **`DeveloperToolsAvailability: 2`**.

## Beslissing
**`DeveloperToolsAvailability: 2` in PROD, weggelaten in DEV (dev/prod-gating).**
- Prod: `features/kiosk/system_files/etc/chromium/policies/managed/coolbx-hardening-prod.json` met de key.
- Dev: `features/kiosk/install.sh` verwijdert dat bestand wanneer `ENABLE_FIRSTBOOT_USER=1`
  (de Containerfile geeft die build-arg nu door aan de features-stap). `just vm-sync` doet hetzelfde live.
- De globaal-veilige enforcement (`coolbx-enforcement.json`: `IncognitoModeAvailability`,
  `BrowserGuestModeEnabled`, `BackgroundModeEnabled`) staat los en geldt in álle builds.

## Waarom gating (geverifieerd, en een correctie op een verkeerde tussenconclusie)
`DeveloperToolsAvailability: 2` blokkeert **niet alleen de F12-UI** maar **óók de functionele CDP**:
`Runtime.evaluate` faalt (`Session not found`) — wat de e2e-harness (laag C) volledig breekt.
- **Valkuil die me misleidde:** de **HTTP-discovery** (`/json/version`, `/json/list`) blíjft antwoorden
  met de policy actief; een geïsoleerde test daarop suggereerde valselijk "CDP werkt nog". Pas een test van
  het **echte pad** (`Runtime.evaluate`) toonde dat het breekt. **Les: test de functionele call, niet de metadata.**
- Daarom kan de key niet globaal: dev heeft CDP nodig (harness), prod niet. Build-gating geverifieerd:
  prod-image **bevat** `DeveloperToolsAvailability`, dev-image **niet** (`podman run … grep`).

## Gevolgen
- **Prod-verificatie zonder CDP:** in prod is CDP dood, dus de "DevTools geblokkeerd"-check gebeurt via
  QMP-F12 + `screendump`/OCR (geen devtools-paneel), niet via CDP. (Volgt; build-gating is wel bewezen.)
- **Nog open in Fase 4:** `file://`-blok (`URLBlocklist file://*` + `URLAllowlist` voor `/usr/share/coolbx/kiosk/*`)
  — uitgesteld: interactie met de dev-placeholder + de force-installed-extensie-kioskMode-pagina vraagt afstemming,
  en het kiosk-risico is laag (geen adresbalk). Downloads/print idem. dconf-lockdown (vrije-modus) volgt.
- **Harness-robuustheid:** `first_page()` slaat `chrome-extension://`/`devtools://`/`chrome://` over (de
  force-installed extensie opent in kioskMode een instabiele eigen pagina). De integratietest `test_06` is
  timing-gevoelig omdat de tmpfs-kioskhome de extensie per sessie her-downloadt.

## Hoe gevonden
Harness-threat-probe (QMP-F12 → `devtools://`-targets), WebSearch (DeveloperToolsAvailability-semantiek),
en e2e-verificatie van `Runtime.evaluate` mét/zonder de policy + de prod/dev-build-grep.
