# ADR-0013: Anti-spoofing via hergebruikt HMAC-handshake + per-toestel-secret

- **Status:** Aanvaard (ontwerprichting; implementatiedetails + Focus-contract open)
- **Datum:** 2026-06-23
- **Beslissers:** Johan, Claude

## Context
`kioskMode`/managed-storage is zelf-gerapporteerd → zwak (een vervalste client liegt). Focus heeft al een
**HMAC-SHA256 handshake**: de extensie signt `clientId:sessionCode:ts` met `VITE_EXTENSION_HMAC_SECRET`
(`apps/student-extension/src/background/handshake.ts`); de server verifieert met `EXTENSION_HMAC_SECRET` + een
replay-venster (`apps/server/src/socket/handshake.ts`). Maar dat is **één globaal secret**, op build-time in de
publiek-installeerbare `.crx` geïnlined → **extraheerbaar** → geen toestelbewijs.

## Beslissing
Hergebruik het HMAC-**schema** (gedeeld als **gedocumenteerd integratiecontract** + test-vectors; de ~10 regels code
worden gedupliceerd, géén gedeelde package/repo). Voeg een **tweede handshake** toe, gesigneerd door een **OS-agent**
(native-messaging-host) met een **per-toestel-secret** dat bij **enrollment** wordt uitgedeeld en **root-only**
(`/etc/coolbx/…`, `0600 root`, onbereikbaar voor leerling/extensie) bewaard. De **Focus-server** is de enige verifier
en houdt een **allowlist** van enrolled toestellen (met **revocatie**). **Geen gedeeld build-time secret.** Dit zit in
de optionele Focus-feature ([ADR-0012](0012-standalone-os-focus-optioneel.md)).

## Gevolgen
Echt toestelbewijs t.o.v. een gewone laptop met de (kopieerbare) extensie, **zonder TPM/PKI-complexiteit** — past bij
pilot-eerlijk ([ADR-0009](0009-security-scope-pilot-eerlijk.md)). Het "één geheel" zit op de **server** (runtime-verifier),
niet in een gefuseerde build/deploy. Open punten: enrollment-/provisioning-flow, het Focus-server-contract, en de
native-host `allowed_origins` exact op `makdakigkdbicdljgdclgnejachcohag`.

**Restrisico → fast-follow:** een root-only secret op een onversleutelde schijf is met fysieke toegang te stelen →
**TPM-sealing/FDE** als fast-follow. Diepe remote-attestatie (TPM-quote/measured boot) = v2-visie.

## Alternatieven
- Globaal gedeeld secret (ook cross-repo/build) — verworpen: extraheerbaar, per-toestel-loos, niet te revoken, koppelt OS↔Focus.
- Volledige TPM-/asymmetrische attestatie nu — verworpen: te zwaar voor v1.
