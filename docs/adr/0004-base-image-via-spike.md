# ADR-0004: Concrete base-image beslist via spike

- **Status:** Voorgesteld (beslist na spike S1)
- **Datum:** 2026-06-23
- **Beslissers:** Johan, Claude

## Context
"Zo clean mogelijk" pleit voor kaal `quay.io/fedora/fedora-bootc`, maar dat betekent de **volledige GNOME-stack +
hardware-firmware zelf bouwen/debuggen**. `ublue-os/base-main` (POC-basis) levert dat batteries-included; hardware-
support is hét waarschijnlijke faalpad op heterogene schoollaptops.

## Beslissing
**Nog niet vastgelegd.** Bouw beide minimaal (S1-spike), boot in VM (+ echte testhardware), en kies op bewijs.
Deze ADR wordt geüpdatet/vervangen met de uitkomst + rationale.

## Gevolgen
Korte vertraging vooraan in ruil voor een bewijs-gebaseerde keuze op het meest risicovolle fundament.

## Alternatieven
- Kaal fedora-bootc: zuiverst, hoogste werk/risk.
- Universal Blue base-main: pragmatisch, minder "clean".
- BlueBuild (recipe.yml): verworpen (herschrijving van de Containerfile/Justfile-aanpak).
