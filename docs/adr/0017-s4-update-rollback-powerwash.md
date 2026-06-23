# ADR-0017: S4 — bootc update / rollback / powerwash haalbaarheid (fedora-bootc:43)

- **Status:** Aanvaard
- **Datum:** 2026-06-23
- **Beslissers:** Johan, Claude

## Context
Spike S4: zijn de bouwstenen voor onzichtbare updates, auto-rollback en een ChromeOS-stijl powerwash beschikbaar
op de gekozen base? Live geverifieerd via SSH in een draaiende VM (geen herbouw).

## Bevindingen (fedora-bootc:43, bootc 1.15.2, systemd 258)
- **Updates:** `bootc upgrade` = A/B staged (nondestructief; queue't een nieuwe image voor next boot). ✅
- **Powerwash:** **`bootc install reset` bestaat** ("nondestructively create a fresh installation state inside an
  existing bootc system") → primaire ChromeOS-stijl reset. ✅ Bovendien is **systemd `factory-reset.target`**
  aanwezig (systemd 258 levert `systemd-factory-reset@.service`, `factory-reset.target`, `factory-reset-now.target`,
  `systemd-factory-reset.socket`) — een tweede, native mechanisme. ✅
- **Auto-rollback:** **greenboot is NIET geïnstalleerd** (zoals voorzien) → `greenboot`/greenboot-rs moet als pakket
  toegevoegd worden (Fase 5) voor health-check-gebaseerde auto-rollback.

## Gevolgen
De update-, rollback- en powerwash-primitieven zijn beschikbaar op de base (geen blocker). De eindgebruiker-knoppen
(Fase 5: `coolbx-update`/`coolbx-rollback`/`coolbx-powerwash` achter een polkit `manage-units`-rule) kunnen hierop bouwen.
greenboot + lokale `required.d`-checks zijn het enige toe te voegen stuk.

## Alternatieven
n.v.t. — spike-bevinding.
