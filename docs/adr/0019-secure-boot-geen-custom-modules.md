# ADR-0019: Secure Boot zonder eigen MOK-key — geen out-of-tree kernelmodules

- **Status:** Aanvaard (richting)
- **Datum:** 2026-06-25
- **Beslissers:** Johan, Claude
- **Bron:** ublue-os-onderzoek (Bazzite/Bluefin akmods-signing) — zie ROADMAP §Security fast-follow.

## Context
Voor de "anti-live-USB/fysiek"-hardening (fast-follow) willen we **UEFI Secure Boot AAN**. De vraag is of Coolbx OS
daarvoor een **eigen signing-key + MOK-enrollment** nodig heeft, zoals Universal Blue doet.

UBlue signt zijn **custom kernelmodules** (akmods, nvidia, …) met een eigen key (`/etc/pki/akmods/certs/akmods-ublue.der`)
en laat de gebruiker die als **MOK** enrollen (`mokutil --import`, wachtwoord, reboot → blauwe MOKManager → "Enroll MOK").
Shim, bootloader en kernel zelf zijn Fedora-gesigned; **alleen de eigen modules** vereisen de MOK-key.

## Beslissing
**Coolbx OS bouwt géén out-of-tree kernelmodules.** We draaien puur userspace (Chromium, sway, GNOME, waybar) op de
**stock fedora-bootc kernel**. Daardoor:

- **Geen eigen Secure-Boot-key en geen MOK-enrollment nodig** — Fedora's gesigneerde shim + kernel blijven geldig,
  Secure Boot werkt out-of-the-box.
- We **vermijden custom modules bewust**, omdat `mokutil`-MOK-enrollment **fysiek/interactief per toestel** is
  (firmware-prompt bij de eerste boot) en dus **niet schaalt** in de FOG-massauitrol ([ADR-0017](0017-s4-update-rollback-powerwash.md), ROADMAP §5b).

## Gevolgen
- Secure-Boot-hardening = **firmware-wachtwoord + bootmenu-lock + GRUB-wachtwoord** (de échte fysieke verdediging),
  niet een eigen key-infrastructuur. Zie ROADMAP §Security fast-follow.
- **Als** later tóch een out-of-tree module nodig blijkt (exotische laptop-hardware/wifi/touchpad): kopieer letterlijk
  het ublue-patroon (akmods-key + cert in `/etc/pki/akmods/certs/` + `mokutil --import`), maar weet dat de FOG-flow dan
  een **handmatige MOK-enroll-stap per toestel** krijgt — dat is een bewuste kostenafweging, geen default.
- Sluit aan bij de "zo clean mogelijk / minimale base"-richting (ROADMAP, ADR-0004).

## Alternatieven
- **Eigen akmods-key + MOK (UBlue-aanpak)** — nodig zodra je modules signt; verworpen zolang we geen modules bouwen
  (per-toestel fysieke enrollment botst met massauitrol).
- **Secure Boot uit** — verworpen: zonder Secure Boot + firmware-pw is de live-USB/fysieke aanval triviaal.
