# ADR-0018: Logo-rebranding — Fedora-trademark eruit via generic-logos

- **Status:** Aanvaard (richting); huidige implementatie = interim
- **Datum:** 2026-06-25
- **Beslissers:** Johan, Claude

## Context
Coolbx OS is een Fedora-bootc-derivaat. Het volledig rebranden van het 'Over'-logo (GNOME Settings ▸ Info)
bleek niet-triviaal: **gnome-control-center is op Fedora gecompileerd met vaste logo-paden** (uit
`gnome-control-center.spec`):

- `-Ddistributor_logo=/usr/share/pixmaps/fedora_logo_med.png` (LICHTE modus)
- `-Ddark_mode_distributor_logo=/usr/share/pixmaps/fedora_whitelogo_med.png` (DONKERE modus)

Het leest dus **niet** os-release `LOGO`/`{logo}-dark`-iconen noch de `fedora-logos`-SVG's — enkel die twee PNG's.
Bovendien is er een **juridisch** punt: een derivaat mag Fedora's trademark-artwork (`fedora-logos`-package) niet
zomaar mee shippen.

## Beslissing
**Doel (productie): de ublue-os-aanpak (Bluefin/Aurora).** Verwijder Fedora's trademark-artwork volledig en overlay
onze eigen logo's:

```bash
dnf -y swap fedora-logos generic-logos        # Fedora-artwork → neutrale GNOME-logo's (zelfde paden)
rpm --erase --nodeps --nodb generic-logos     # uit RPM-DB, BESTANDEN blijven → virtuele provide blijft voldaan
                                              #   ("Keep *-logos in RPM DB for downstream package installations")
# daarna: onze coolbx-wordmark-PNG's overlayen op de control-center-paden:
#   /usr/share/pixmaps/fedora_logo_med.png       → ink-wordmark   (licht)
#   /usr/share/pixmaps/fedora_whitelogo_med.png  → witte wordmark (donker)
```

**Interim (huidig, feature `branding`/install.sh):** we **overschrijven** de Fedora-logo-bestanden direct met onze
wordmark (licht=ink, donker=wit), inclusief de twee doorslaggevende compile-tijd-PNG's. Dit werkt functioneel
(geverifieerd: licht=ink, donker=wit op de Info-pagina) maar shipt de `fedora-logos`-package nog mét z'n naam en
eventuele niet-aangeraakte artwork.

## Gevolgen
- **Productie-TODO:** stap over op `swap fedora-logos generic-logos` + `rpm --erase --nodeps --nodb generic-logos`
  in de pakketlaag, en verplaats de twee wordmark-PNG-overlays naar `system_files` (of houd de install.sh-cp).
  **Verifiëren** dat na de swap de paden `/usr/share/pixmaps/fedora_logo_med.png` + `fedora_whitelogo_med.png`
  nog bestaan zodat de control-center-overlay blijft werken (generic-logos levert generieke varianten op dezelfde
  paden; anders aanmaken).
- ⚠️ **Kanttekening (ublue-os-onderzoek, jun 2026):** op **Fedora 43 / bootc-LTS** zit `generic-logos` **niet** in de
  standaard-repo. Bluefin-LTS installeert het daarom handmatig via een **kojipkgs-URL** (zie
  `ublue-os/bluefin-lts:build_scripts/overrides/base/10-packages-image-base.sh`). De productie-stap moet dus óf die
  kojipkgs-URL meenemen, óf — eenvoudiger — bij onze huidige **directe-overlay**-aanpak blijven (geen package-swap, gewoon
  de Fedora-logo-bestanden overschrijven) en enkel het trademark-net oplossen door `fedora-logos` niet te shippen waar mogelijk.
- Trademark-net: geen Fedora-merkartwork meer in de image.

## Hoe gevonden
`strace` op control-center (welk bestand opent het), de Fedora `gnome-control-center.spec` (de compile-flags),
en `gh search code --owner ublue-os` (Bluefin/Aurora's `dnf swap fedora-logos generic-logos`).

## Alternatieven
- **os-release `LOGO` + `{logo}-dark`-iconen** — werkt enkel als control-center NIET compile-tijd-`DISTRIBUTOR_LOGO`
  heeft; Fedora heeft die wél → genegeerd. `LOGO_DARK` is geen standaard os-release-veld.
- **Alleen de `fedora-logos`-SVG's vervangen** — control-center laadt die niet voor 'Over'; geen effect.
