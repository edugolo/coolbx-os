# Features — optionele, modulaire lagen (ADR-0012)

Elke feature is een self-contained map die via de build-arg `FEATURES="naam1 naam2"` wordt geactiveerd
(zie `build_files/install-features.sh`). Een kale Coolbx OS (geen `FEATURES`) bevat geen enkele feature en
heeft geen Focus-afhankelijkheid.

```
features/<naam>/
  install.sh        # optioneel: pakketten/config voor deze feature
  system_files/     # optioneel: bestanden die in / worden gekopieerd
```

Geplande features: `kiosk` (sway+waybar+chromium kiosk-sessie), `focus` (force-installed extensie +
HMAC device-auth, ADR-0013), `branding` (play↔focus assets).
