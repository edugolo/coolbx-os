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
| [0004](0004-base-image-via-spike.md) | Concrete base-image beslist via spike | Voorgesteld |
| [0005](0005-toestelmodel-beheerd-vergrendelt.md) | Beheerde laptop die op aanvraag vergrendelt | Aanvaard |
| [0006](0006-kiosk-sway-waybar.md) | sway + waybar als kiosk-compositor | Aanvaard |
| [0007](0007-integriteit-op-focus-laag.md) | Examenintegriteit op de Focus-server-laag | Aanvaard |
| [0008](0008-account-pilot-autologin-gast.md) | Pilot-accountmodel: gedeeld + autologin-gast | Voorgesteld |
| [0009](0009-security-scope-pilot-eerlijk.md) | Security-scope v1: pilot-eerlijk, hardening fast-follow | Aanvaard |
| [0010](0010-branding-play-focus.md) | Branding: play↔focus-dualiteit, geen schild | Aanvaard |
| [0011](0011-chromium-rpm-policy-in-image.md) | RPM-Chromium + policy in het image (geen Flatpak/ansible) | Aanvaard |
| [0012](0012-standalone-os-focus-optioneel.md) | Coolbx OS standalone; Focus-integratie = optionele feature-laag | Aanvaard |
| [0013](0013-anti-spoofing-hmac-per-device.md) | Anti-spoofing via HMAC-handshake + per-toestel-secret | Aanvaard (richting) |
