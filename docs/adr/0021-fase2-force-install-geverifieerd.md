# ADR-0021: Fase 2 — force-install + managed-storage geverifieerd tegen productie

- **Status:** Aanvaard (geverifieerd)
- **Datum:** 2026-06-25
- **Beslissers:** Johan, Claude
- **Bouwt op:** [ADR-0011](0011-chromium-rpm-policy-in-image.md), [ADR-0015](0015-s2-chromium-managed-storage.md) (S2-spike).

## Context
Fase 2 (productie-vorm van S2) moet bewijzen dat het OS de **productie student-extensie force-installeert**
en de **managed-storage** (`serverUrl`/`kioskMode`) aflevert — de kern van het integratiecontract. Onverwacht:
de **productie-infra is live en bereikbaar** vanuit de dev-VM (NAT-net), dus dit kon **end-to-end tegen
productie** geverifieerd worden i.p.v. met een lokale stub.

## Beslissing / bevindingen (geverifieerd in de VM, e2e-harness)
- **Policy** (`features/kiosk/system_files/etc/chromium/policies/managed/coolbx-managed.json`):
  `ExtensionSettings.<ID>` = `installation_mode: force_installed` + `update_url` (de live update.xml) +
  `override_update_url: true`, **plus** `3rdparty.extensions.<ID>` = `serverUrl`/`kioskMode`. `<ID>` =
  `makdakigkdbicdljgdclgnejachcohag`. Autoritatief schema: chromium.org policy-list (ExtensionSettings).
- **Live update.xml** (`https://focus-dashboard.edugolo.be/extension-updates/update.xml`) serveert de echte
  ondertekende `coolbx-focus-student.crx` **v0.14.0** (appid = onze contract-ID, prodversionmin 116).
- **Geverifieerd** (`tests/test_06_focus_contract.py`, groen): Chromium **installeert** de echte extensie
  (`…/Extensions/makdak…/0.14.0_0/`), `chrome://policy` toont **ExtensionSettings → OK** en de 3rdparty-waarden
  **`serverUrl`/`kioskMode` → status OK, isExtension** afgeleverd. De extensie **reageert op `kioskMode=true`**
  (opent z'n fullscreen-scherm) → contract klopt van policy → extensie-gedrag.
- **Verificatie-route = `chrome://policy`** (via een verse CDP-tab, shadow-DOM-scrape van `<policy-row>.policy`),
  niet de extensie-service-worker: de **MV3-SW slaapt** en de inspector-sessie sterft tussen attach en evaluate
  (`Session not found`) — onbetrouwbaar. `chrome://policy` toont de toegepaste 3rdparty-waarden robuust en is het
  juiste OS-niveau bewijs ("Chromium levert de waarden af"). `scripts/vm-cdp.py managed` (SW-read) blijft als
  best-effort bestaan maar is niet de test-oracle.

## Gevolgen
- **Geen externe blocker** voor force-install/managed-storage (de eerdere aanname dat de Focus-`.crx`/`update.xml`
  ontbrak, klopt niet — ze zijn live). De integratietest is wél **connectiviteits-afhankelijk** (skip offline).
- **Nog open binnen Fase 2:** de **enforcement-policy-set** (DeveloperToolsAvailability, IncognitoModeAvailability,
  DownloadRestrictions, BrowserGuestModeEnabled, file://-blok). ⚠️ Te onderzoeken vóór toevoegen:
  `DeveloperToolsAvailability: 2` kan de **CDP-debugpoort/de e2e-harness breken** — eerst de docs checken, dan
  scopen (sommige keys globaal-veilig, URL-blocking enkel kiosk). Komt in een eigen `coolbx-enforcement.json`.
- De `_comment`-sleutel in de policy toont als "Onbekend beleid" op chrome://policy (onschadelijk).

## Hoe gevonden
WebSearch (chromium.org ExtensionSettings-schema + managed-storage voor unpacked/3rdparty), curl van de live
update.xml vanuit de VM, en e2e-verificatie via `vm-cdp policy` (eigen verse tab → shadow-DOM `.policy`).
