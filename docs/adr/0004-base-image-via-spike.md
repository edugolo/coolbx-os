# ADR-0004: Base-image — fedora-bootc (beslist via spike S1)

- **Status:** Aanvaard
- **Datum:** 2026-06-23
- **Beslissers:** Johan, Claude
- (Vervangt de eerdere "Voorgesteld"-versie.)

## Context
"Zo clean mogelijk" pleit voor kaal `quay.io/fedora/fedora-bootc`; `ghcr.io/ublue-os/base-main` levert
hardware/firmware batteries-included maar koppelt aan Universal Blue. Beslist via een spike: beide bouwen + in VM booten.

## Beslissing
**`quay.io/fedora/fedora-bootc:43`** als base-image.

Spike-bewijs (S1, machine-leesbaar in een qemu-direct VM):

| | fedora-bootc | ublue base-main |
|---|---|---|
| build (`bootc container lint`) | 10/10 | 10/10 |
| boot → GNOME (nl_BE, autologin, SSH) | ✅ | ✅ |
| image-grootte | **3.86 GB** | 7.22 GB |
| base-grootte | 1.94 GB | 6.12 GB |
| standalone ([ADR-0012](0012-standalone-os-focus-optioneel.md)) | ✅ | koppelt aan UB |

Beide booten identiek in de VM; fedora-bootc is ~half zo groot, bootc-native en standalone. We voegen
**`linux-firmware`** toe voor hardware-support (geleerd van UB) — blijft leaner dan base-main.

## Gevolgen
Lean, clean, standalone. **Hardware-support op echte heterogene schoollaptops = fast-follow** (enkel op echte
hardware testbaar; voeg gerichte drivers/firmware toe waar nodig, met UB's `build_files` als referentie).
`ublue-os/base-main` blijft de gedocumenteerde fallback als hardware tegenvalt.

## Alternatieven
- ublue base-main: pragmatisch (firmware) maar ~2× zo groot + UB-koppeling → fallback.
- BlueBuild: verworpen (zie [ADR-0003](0003-fedora-bootc-fundament.md)).
