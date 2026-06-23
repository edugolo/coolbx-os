# ADR-0002: Vers herbouwen rond de productie-extensie, geen Electron

- **Status:** Aanvaard
- **Datum:** 2026-06-23
- **Beslissers:** Johan, Claude

## Context
De POC bundelt een legacy Electron `focus-app` (RPM). De productie-wereld draait op de **student-extensie** in Chromium.

## Beslissing
Vers herbouwen vanuit de POC als referentie, maar rond **Chromium + de force-installed productie-extensie**.
De Electron-app wordt gedropt.

## Gevolgen
Geen legacy-last; sluit aan op de productie-Focus-stack. De Chromium-policy/managed-storage is volledig nieuw werk
(de POC heeft het niet).

## Alternatieven
POC verderzetten met Electron — verworpen: legacy, niet de productie-architectuur.
