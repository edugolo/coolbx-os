# ADR-0007: Examenintegriteit op de Focus-server-laag

- **Status:** Aanvaard
- **Datum:** 2026-06-23
- **Beslissers:** Johan, Claude

## Context
Een onbreekbare OS-jail is brittle. De leerling mag bewust kunnen afsluiten (met waarschuwing "ingediend?"), maar
herstarten/herjoinen moet gecontroleerd zijn.

## Beslissing
Integriteit = **detectie + gegate heropstart op de Focus-server** (herjoinen enkel via herneemcode + toestemming
leerkracht; ook bij crash/wifi-verlies), niet een onbreekbare OS-jail. De OS levert de schone, afgeschermde sessie
en een *bewuste* exit.

## Gevolgen
Robuuster dan een fysieke jail. Vereist server-heartbeat-detectie en een goed herneemcode-ontwerp (entropie,
eenmalig, per-leerling, rate-limited) — gedeeld contract met het Focus-team. Offline-gedrag moet fail-closed zijn.

## Alternatieven
Onbreekbare OS-jail met teacher-only unlock — verworpen: brittle, en fysieke/offline-aanvallen blijven toch bestaan.
