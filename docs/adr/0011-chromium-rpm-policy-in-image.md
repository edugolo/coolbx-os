# ADR-0011: RPM-Chromium + policy in het image (geen Flatpak, geen ansible voor policy)

- **Status:** Aanvaard
- **Datum:** 2026-06-23
- **Beslissers:** Johan, Claude

## Context
Force-install + `chrome.storage.managed` op Linux lezen uit `/etc/chromium/policies/managed/`. Flatpak-Chromium
leest die paden niet (sandbox/`/etc`). Policy is overal identiek; ansible is voor per-toestel-drift.

## Beslissing
Gebruik **RPM-Chromium** (Fedora-repo). Eén policy-JSON in `/etc/chromium/policies/managed/` met force-install +
`3rdparty` managed-storage + de enforcement-keys, **in het image** (niet via ansible, niet via Flatpak).

## Gevolgen
Voorspelbare policy-paden, past in een bootc-image bij build-time, geen sandbox-gedoe. Policy is uniform en
versiebeheerd in het image (anti-drift). Bevestigen in VM dat `chrome.storage.managed` op Fedora-Chromium aankomt.

## Alternatieven
- Flatpak-Chromium: leest de policy-paden niet standaard.
- Policy via ansible: introduceert drift en twee bronnen van waarheid.
