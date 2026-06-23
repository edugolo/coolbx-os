# ADR-0006: sway + waybar als kiosk-compositor

- **Status:** Aanvaard
- **Datum:** 2026-06-23
- **Beslissers:** Johan, Claude

## Context
De kiosk moet één fullscreen Chromium tonen én een **minimale systeem-UI** (wifi/batterij/klok). cage kan geen
statusbalk tonen; gnome-kiosk sleept de hele GNOME-stack mee.

## Beslissing
**sway** (gestripte config) + **waybar** als kiosk-sessie, met Chromium in `--kiosk`.

## Gevolgen
Statusbalk mogelijk; lichte stack. **Hardening-last is groter dan bij cage:** VT-switch dood op logind-niveau
(niet door sway), alle keybinds unbinden, `SWAYSOCK` afschermen, externe monitors mirrorren — moet in VM bewezen
(zie spike S3). Bij tegenvallende hardening blijft cage een terugvaloptie.

## Alternatieven
- cage: blokkeert VT-switch by design, maar geen statusbalk.
- gnome-kiosk: officieel maar zwaar.
- labwc: project raadt zelf cage aan voor kiosk.
