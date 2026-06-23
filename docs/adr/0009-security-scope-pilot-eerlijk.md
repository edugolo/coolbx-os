# ADR-0009: Security-scope v1 — pilot-eerlijk, hardening als fast-follow

- **Status:** Aanvaard
- **Datum:** 2026-06-23
- **Beslissers:** Johan, Claude

## Context
`kioskMode=true` dwingt niets af (cosmetisch). Echte enforcement = Chromium-policy-set + kiosk-jail. Anti-spoofing
en fysieke hardening (Secure Boot, firmware-pw, enrollment-credential) zijn serieus werk en deels afhankelijk van het Focus-team.

## Beslissing
**v1 = pilot-eerlijk:** kiosk-jail + Chromium-enforcement-policy nu (Fase 2), integriteit op de Focus-laag +
leerkracht-aanwezigheid. De harde hardening (Secure Boot + firmware-wachtwoord + niet-kopieerbaar enrollment-credential
+ anti-live-USB) komt als **fast-follow** vóór de "waterdicht"-claim.

## Gevolgen
Sneller naar een werkende, **eerlijk geframede** pilot. "Waterdichte toetsafname" wordt pas geclaimd na de fast-follow.
Tot dan is de OS-laag spoofbaar vanaf een gewone laptop — expliciet erkend.

## Alternatieven
- Waterdicht-eerst: trager, deels Focus-afhankelijk.
- Minimaal (enkel afleiding-preventie): kan "waterdicht" nooit waarmaken.
