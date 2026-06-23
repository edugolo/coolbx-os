# ADR-0012: Coolbx OS is een standalone distro; Focus-integratie is een optionele feature-laag

- **Status:** Aanvaard
- **Datum:** 2026-06-23
- **Beslissers:** Johan, Claude

## Context
Coolbx OS heeft waarde op zich: een generieke, vergrendelde bootc "device floor" / kiosk-distro voor scholen
(bruikbaar voor beheerde laptops of andere kiosk-apps, niet enkel toetsen). Coolbx Focus is één gebruiker ervan.

## Beslissing
De **kern van Coolbx OS staat volledig los van Focus**. Alle Focus-binding — force-installed extensie,
managed-storage, en de device-auth/anti-spoofing ([ADR-0013](0013-anti-spoofing-hmac-per-device.md)) — zit in een
**optionele build-time feature** (`FEATURES=`). Een "kale" Coolbx OS bevat die feature niet en heeft geen Focus-afhankelijkheid of -secrets.

## Gevolgen
Versterkt aparte repos ([ADR-0001](0001-aparte-repo.md)) en het feature-model. Bredere inzetbaarheid. Vereist een
schoon **integratiecontract** + een **release-compatibiliteits**-naad (welke OS-versie ↔ welke Focus-server-versie)
i.p.v. tight coupling of een gedeelde build-pijplijn. **Geen Focus-secrets in de OS-kern.**

## Alternatieven
- OS+Focus tight gekoppeld / monorepo / gedeelde build-time secret — verworpen: koppelt de OS aan Focus, beperkt
  inzetbaarheid, en het gedeelde secret is zwakker (zie ADR-0013).
