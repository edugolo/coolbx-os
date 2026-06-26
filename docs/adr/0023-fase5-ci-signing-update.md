# ADR-0023: Fase 5 — CI-signing, staged auto-update & greenboot

- **Status:** Aanvaard (deels geverifieerd; signing-activatie wacht op cosign-key)
- **Datum:** 2026-06-25
- **Beslissers:** Johan, Claude
- **Bouwt op:** ublue-os-research (image-template build.yml, on-device sigstore), roadmap §Updates/§Fase 5.

## Beslissing / wat er staat
**CI (`.github/workflows/build.yml`):** single image (geen flavor-matrix), bouwt een **PRODUCTIE**-image
(`ENABLE_FIRSTBOOT_USER=0` → geen testuser, mét DevTools/file://-hardening), `FEATURES="kiosk branding fleet"`,
`FEATURES_CACHEBUST=${{ github.sha }}`. PR's bouwen-only; main/cron/dispatch → push naar GHCR + **cosign
sign-by-digest** (`secrets.SIGNING_SECRET`). Dagelijkse cron (04:15 UTC) trekt fedora-bootc-CVE-fixes door.
**Rechunk** (hhd-dev/rechunk) tussen build en push → kleinere `bootc upgrade`-deltas. Actions SHA-gepind.
`bootc container lint` is de laatste Containerfile-laag.

**Staged auto-update (`fleet`-feature, geverifieerd):** de default `bootc-fetch-apply-updates.timer` (kan
op willekeurig moment applyen/rebooten) is **gemaskeerd**; `coolbx-update.timer` draait `bootc upgrade`
**stage-only** (04:00 + `Persistent` + `RandomizedDelaySec=15m`). Reboot = natuurlijk moment → nooit midden
in een toets. (`test_07_fleet.py`: timer masked/enabled, stage-only, geen `--apply`/reboot.)

**greenboot (geverifieerd):** `greenboot` + `greenboot-default-health-checks` (zit in de fedora-bootc-repo)
+ een **lokale** `required.d`-health-check (gdm/chromium/sway/kiosk-launcher/Focus-policy aanwezig). **NOOIT
focus-api** in de check — een externe outage mag de vloot niet doen terugrollen (ADR-0017). Bij N gefaalde
boots → auto-rollback naar de vorige deployment.

**On-device signing-verificatie (scaffold, BEWUST niet actief):** strikte `policy.json`
(`default: reject` + `sigstoreSigned` voor de coolbx-repo, `keyPath` `/etc/pki/containers/coolbx-os.pub`)
+ `registries.d` (`use-sigstore-attachments`) staan als **template** in `/usr/share/coolbx/signing/` met
`docs/SIGNING.md`. Een `default: reject` zónder geldige sleutel/handtekening breekt **álle** updates →
daarom pas activeren na de cosign-opzet. De `fleet`-install.sh bakt `coolbx-os.pub` zodra een echte
`cosign.pub` (geen placeholder) in de repo staat.

## Externe acties (jouw eenmalige opzet — zie docs/SIGNING.md)
1. `cosign generate-key-pair` → private key als repo-secret `SIGNING_SECRET`, `cosign.pub` committen
   (vervangt `features/fleet/cosign.pub`-placeholder).
2. Na de eerste gesigneerde GHCR-push: `policy.json`/`registries.d` met de juiste owner activeren.
3. **Canary:** CI pusht nu `:stable`; promoot een `:testing`-ring later (handmatig) voor ring-uitrol.

## Hoe gevonden / geverifieerd
ublue-os-research (image-template `build.yml`, on-device sigstore-policy), WebSearch (policy.json-formaat),
en e2e-verificatie (`just e2e` = 26/26 vanaf koude boot: update-timer, greenboot, hardening, force-install).
