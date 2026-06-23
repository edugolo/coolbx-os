# ADR-0005: Beheerde laptop die op aanvraag vergrendelt

- **Status:** Aanvaard
- **Datum:** 2026-06-23
- **Beslissers:** Johan, Claude

## Context
Het toestel is niet enkel een toets-toestel: het moet ook in een vrije ("play") modus bruikbaar zijn, én tijdens
toetsen vergrendelen ("focus").

## Beslissing
Een **beheerde GNOME-laptop** die op aanvraag in een **vergrendelde kiosk-sessie** schakelt (aparte Wayland-sessie
op een eigen VT), en bij afsluiten terugkeert naar GNOME.

## Gevolgen
Dubbele bruikbaarheid (gewoon toestel + toets-kiosk). Groter aanvalsoppervlak dan een pure kiosk → de GNOME-laag
moet beheerd zijn en mag tijdens een kiosk niet bereikbaar zijn.

## Alternatieven
- Pure kiosk (alleen Chromium, altijd): verworpen — geen vrije modus.
- Per-rol-image-varianten: deels via ansible-rollen i.p.v. aparte images.
