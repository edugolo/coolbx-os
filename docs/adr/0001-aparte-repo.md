# ADR-0001: Aparte repo, los van de Focus-monorepo

- **Status:** Aanvaard
- **Datum:** 2026-06-23
- **Beslissers:** Johan, Claude

## Context
Coolbx OS (bootc/podman/just/ansible, ~134MB image-artefacten) en Coolbx Focus (pnpm/vite) delen geen toolchain.

## Beslissing
Coolbx OS leeft in een **eigen repo**. Afstemming met Focus via drie naden: gedeelde brand, één umbrella-site,
en het integratiecontract (force-installed extensie + managed-storage).

## Gevolgen
Schone scheiding van toolchains; release-afstemming en het OS↔Focus-contract moeten expliciet beheerd worden.

## Alternatieven
Onderdeel van de Focus-monorepo — verworpen: vermengt onverenigbare toolchains.
