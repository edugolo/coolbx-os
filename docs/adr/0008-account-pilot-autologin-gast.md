# ADR-0008: Pilot-accountmodel — gedeeld toestel + autologin-gast

- **Status:** Voorgesteld (breed model beslist na pilot)
- **Datum:** 2026-06-23
- **Beslissers:** Johan, Claude

## Context
Het account-/identiteitsmodel (wie logt in op de GNOME-laag) bepaalt enrollment, ephemeral-strategie, privacy en
reset. Lokale accounts en SSO brengen elk grote complexiteit (wachtwoordbeheer / OIDC + home-provisioning).

## Beslissing
**Pilot:** gedeeld toestel met **GDM-autologin naar een beheerd gastprofiel** dat bij logout/reboot reset. Lost
"wie logt in" én "reset tussen leerlingen" op zonder wachtwoord-/SSO-moeras. Het brede model wordt **na pilot-feedback** beslist.

## Gevolgen
Simpel, privacy-vriendelijk (geen carryover), sluit aan op de ephemeral-filosofie. Geen persistente persoonlijke
data/voorkeuren in de pilot (uitz.: a11y-voorkeuren moeten persistent).

## Alternatieven
- Persoonlijk lokaal account: wachtwoord-/resetlast over de vloot.
- Centrale SSO (Entra/Google/LDAP): krachtigst maar zwaarste engineering — kandidaat voor breed model.
