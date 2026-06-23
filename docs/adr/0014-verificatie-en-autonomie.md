# ADR-0014: Verificatie- & autonomie-aanpak tijdens de bouw

- **Status:** Aanvaard
- **Datum:** 2026-06-23
- **Beslissers:** Johan, Claude

## Context
De bouw gebeurt grotendeels **autonoom** in deze sessie. Doel: hoge grondigheid, een auditeerbaar verificatiespoor,
en doorwerken zonder onnodig te stoppen — tot een in-VM geverifieerde pilot-build.

## Beslissing
Per fase:
1. **Machine-leesbare VM-verificatie** door Claude zelf: SSH-CLI-checks (`bootc status`, `systemctl`, journald,
   policy-files) + **QEMU-monitor `screendump`**-PNG's (qemu-direct, rootless). Geen browser-VNC (onbruikbaar voor een agent).
2. **Zware multi-agent adversariële review op elke fase-grens** (meerdere lenzen) + verificatie van elke niet-triviale claim.
3. **Elke spike-uitkomst + architectuurkeuze → ADR.**

Echte **externe blockers** (Focus `.crx`/`update.xml`, echte hardware, openstaande productkeuzes) worden **gebundeld en
aan Johan voorgelegd**, niet als stop-momenten. De bouw loopt in deze sessie; `docs/ROADMAP.md` + ADRs + memory
garanderen continuïteit voor een latere sessie.

## Gevolgen
Hoge grondigheid en auditeerbaarheid; bewust hogere token-/tijdskost. Verificatieresultaten worden vastgelegd.

## Alternatieven
- Lichte zelf-verificatie zonder agents — verworpen (minder onafhankelijke tegenspraak).
- Verificatie achteraf i.p.v. per fase — verworpen (gaten ontdek je dan te laat).
