# Feature: `branding`

Coolbx OS-merkidentiteit, end-to-end door de bootketen. Tekst-wordmark (geen grafisch
logo) — `coolbx` (InterDisplay-Black, paper) + `os` (InterDisplay-Light, mint).

## Palet

| Rol | Hex |
|---|---|
| Achtergrond (Focus-dark) | `#141210` |
| Surface | `#2B2620` |
| Tekst (paper) | `#FAF8F3` |
| OS-accent (mint) | `#50CE96` |
| Focus/toetsmodus (amber) | `#E8902A` |

Mint = OS-accent. Amber blijft **gereserveerd voor Coolbx Focus / toetsmodus**.

## Wat het levert

- **GRUB2-thema** (`/usr/share/grub/themes/coolbx`) — vlak `#141210`, wordmark-achtergrond,
  mint geselecteerd-item + mint voortgangsbalk tijdens de timeout.
- **Plymouth-splash** (`script`-thema `coolbx`) — wordmark op `#141210` met zacht pulserende
  mint-dot; ondersteunt boodschappen + wachtwoordprompt.
- **GDM-greeter** — donker, mint-accent, login-achtergrond met wordmark (via `gdm` dconf-db).
- **GNOME-desktop** — `prefer-dark`, mint-accent, vlakke `#141210` wallpaper, Inter-UI-font,
  dock-favorieten: Chromium · Bestanden · Rekenmachine · Toetsmodus.
- **os-release** — `Coolbx OS`, mint ANSI-kleur.
- **Inter-font** (`rsms-inter-fonts`) — draagt de hele typografie (UI + kiosk-HTML).

De kiosk-wachtpagina (toetsmodus-A, viewfinder + amber) leeft in de `kiosk`-feature.

## Assets herbouwen

```sh
python3 features/branding/gen-assets.py   # regenereert de PNG's in system_files/
```

De PNG's zijn ingecheckt (reproduceerbaar via het script). Fonts: `rsms-inter-fonts`.
