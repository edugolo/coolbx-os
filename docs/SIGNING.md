# Image-signing & on-device verificatie (Fase 5)

De "managed Chromebook"-vertrouwensgarantie: schooltoestellen weigeren elke niet-gesigneerde of
getamperde OS-image. De CI signt met **cosign (sign-by-digest)**; het toestel verifieert tegen een
ingebakken publieke sleutel.

> **Status (B3.d, 2026-07-12):** de CI signt elke push nu VERPLICHT **keyless**
> (Fulcio/Rekor via GitHub-OIDC — faalt de signing, dan faalt de build): publieke
> transparantie zonder sleutelbeheer, verifieerbaar met
> `cosign verify --certificate-identity-regexp 'github.com/edugolo/coolbx-os' --certificate-oidc-issuer https://token.actions.githubusercontent.com <image>@<digest>`.
> **On-device enforcement** (bootc/policy.json) kan keyless-identiteiten van GitHub
> Actions echter NIET verifiëren (containers-policy fulcio ondersteunt alleen
> `subjectEmail`, geen URI-SAN's) — het toestel-verify-pad is daarom de
> **cosign-keypair** (register-fallback F-03-008). Die policy is bewust nog niet
> actief (een `default: reject` zónder geldige sleutel/handtekening breekt álle
> updates). Activeer pas na de stappen hieronder — sleutel-custody ligt bij de
> beheerder ([extern]): private key in het `SIGNING_SECRET`-repo-secret ÉN offline
> back-up (Vaultwarden — les van F-05-007).

## Eenmalige opzet

1. **Genereer een wachtwoordloze cosign-keypair** (CI-vereiste):
   ```bash
   COSIGN_PASSWORD="" cosign generate-key-pair
   ```
2. **Private key → GitHub repo-secret** `SIGNING_SECRET` (inhoud van `cosign.key`).
   De workflow `.github/workflows/build.yml` gebruikt die al (`secrets.SIGNING_SECRET`).
3. **Public key → repo + image:** commit `cosign.pub` in de repo-root, en bak 'm in het image als
   `/etc/pki/containers/coolbx-os.pub` (zie `features/fleet/install.sh` — de gate activeert dit zodra
   een echte `cosign.pub` aanwezig is i.p.v. de placeholder).
4. **Bevestig dat de CI gesigneerde images pusht** (main/cron → `cosign sign -y --key … @<digest>`).

## On-device activeren (na stap 1-4)

`REPLACE_OWNER` = je GitHub-owner. De templates staan in `/usr/share/coolbx/signing/`:
```bash
sudo sed "s/REPLACE_OWNER/<owner>/" /usr/share/coolbx/signing/policy.json  > /etc/containers/policy.json
sudo sed "s/REPLACE_OWNER/<owner>/" /usr/share/coolbx/signing/coolbx-os.yaml > /etc/containers/registries.d/coolbx-os.yaml
# /etc/pki/containers/coolbx-os.pub is al gebakken (stap 3).
sudo bootc upgrade --check   # moet de gesigneerde image accepteren; een niet-gesigneerde → reject
```
Beter nog: bak deze drie bestanden in het image (zodat verificatie vanaf de eerste boot geldt) — doe dit
in `features/fleet/install.sh` achter dezelfde cosign.pub-gate.

## Sleutelrotatie

`policy.json` ondersteunt **meerdere `keyPath`-entries** (twee sleutels): voeg de nieuwe sleutel toe
naast de oude, rol uit, en verwijder de oude pas als de hele vloot de nieuwe policy heeft. Bewaar een
**back-up van de private key** (totaalverlies → de vloot kan niet meer updaten).

## Verificatie

- CI: de `Sign by digest`-stap slaagt en `cosign verify --key cosign.pub <ref>` lukt.
- Toestel: `bootc upgrade` accepteert de gesigneerde image; een ongetekende/getamperde push → `reject`.
