# Architecture Decision Records (ADR)

Bevroren, genummerde beslissingen met hun *waarom*. Aanvulling op `docs/ROADMAP.md` (het levende plan).
Formaat: MADR-lite — zie `0000-template.md`. Een ADR wordt **niet herschreven** maar *vervangen* (nieuwe ADR,
oude op status "Vervangen door ADR-XXXX").

**Wanneer een ADR?** Elke niet-triviale architectuur-/productkeuze en **elke spike-uitkomst** tijdens uitvoering.

| # | Titel | Status |
|---|---|---|
| [0001](0001-aparte-repo.md) | Aparte repo, los van de Focus-monorepo | Aanvaard |
| [0002](0002-vers-herbouwen-geen-electron.md) | Vers herbouwen rond de productie-extensie, geen Electron | Aanvaard |
| [0003](0003-fedora-bootc-fundament.md) | Fedora bootc als OS-fundament | Aanvaard |
| [0004](0004-base-image-via-spike.md) | Base-image: fedora-bootc (beslist via spike S1) | Aanvaard |
| [0005](0005-toestelmodel-beheerd-vergrendelt.md) | Beheerde laptop die op aanvraag vergrendelt | Aanvaard |
| [0006](0006-kiosk-sway-waybar.md) | sway + waybar als kiosk-compositor | Aanvaard |
| [0007](0007-integriteit-op-focus-laag.md) | Examenintegriteit op de Focus-server-laag | Aanvaard |
| [0008](0008-account-pilot-autologin-gast.md) | Pilot-accountmodel: gedeeld + autologin-gast | Voorgesteld |
| [0009](0009-security-scope-pilot-eerlijk.md) | Security-scope v1: pilot-eerlijk, hardening fast-follow | Aanvaard |
| [0010](0010-branding-play-focus.md) | Branding: play↔focus-dualiteit, geen schild | Aanvaard |
| [0011](0011-chromium-rpm-policy-in-image.md) | RPM-Chromium + policy in het image (geen Flatpak/ansible) | Aanvaard |
| [0012](0012-standalone-os-focus-optioneel.md) | Coolbx OS standalone; Focus-integratie = optionele feature-laag | Aanvaard |
| [0013](0013-anti-spoofing-hmac-per-device.md) | Anti-spoofing via HMAC-handshake + per-toestel-secret | Aanvaard (richting) |
| [0014](0014-verificatie-en-autonomie.md) | Verificatie- & autonomie-aanpak tijdens de bouw | Aanvaard |
| [0015](0015-s2-chromium-managed-storage.md) | S2: Chromium managed-storage + enforcement op Fedora (bevestigd) | Aanvaard |
| [0016](0016-s3-vt-lockdown.md) | S3: VT-lockdown via VT_LOCKSWITCH (kiosk escape-resistant) | Aanvaard |
| [0017](0017-s4-update-rollback-powerwash.md) | S4: bootc update/rollback/powerwash haalbaarheid | Aanvaard |
| [0018](0018-logo-rebranding-generic-logos.md) | Logo-rebranding: Fedora-trademark eruit via generic-logos (ublue-os) | Aanvaard (richting) |
| [0019](0019-secure-boot-geen-custom-modules.md) | Secure Boot zonder eigen MOK-key — geen out-of-tree kernelmodules | Aanvaard (richting) |
| [0020](0020-e2e-dev-automation-harness.md) | e2e dev-automation-harness — host-gedreven (QMP+CDP+OCR+pytest) | Aanvaard (gebouwd) |
| [0021](0021-fase2-force-install-geverifieerd.md) | Fase 2 — force-install + managed-storage geverifieerd tegen productie | Aanvaard (geverifieerd) |
| [0022](0022-fase4-devtools-dev-prod-gating.md) | Fase 4 — DevTools-hardening via dev/prod-gating (DevTools:2 breekt CDP) | Aanvaard (geverifieerd) |
| [0023](0023-fase5-ci-signing-update.md) | Fase 5 — CI-signing (cosign), staged auto-update & greenboot | Aanvaard (deels geverifieerd) |
| [0024](0024-attest-hmac-implementatie.md) | Toestel-attestatie HMAC-scaffold — implementatie (ADR-0013) | Aanvaard (geverifieerd) |
| [0025](0025-nvidia-nouveau-geen-proprietaire-driver.md) | nvidia: nouveau + firmware, géén proprietaire driver (ADR-0019) | Aanvaard (richting) |
| [0026](0026-surface-camera-niet-ondersteund.md) | Surface-camera (IPU3) niet ondersteund — vereist linux-surface-kernel (ADR-0019) | Aanvaard (richting) |
| [0027](0027-media-nonfree-optionele-feature.md) | Nonfree media (codecs + VAAPI + Widevine) als optionele feature | Aanvaard (richting) |
