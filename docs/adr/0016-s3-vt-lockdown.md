# ADR-0016: S3 — VT-lockdown via VT_LOCKSWITCH

- **Status:** Aanvaard
- **Datum:** 2026-06-23
- **Beslissers:** Johan, Claude

## Context
De kiosk draait op een eigen VT (tty3) naast de GNOME-gast (tty2). Sway geeft `Ctrl+Alt+Fn` door aan de
**kernel-VT-laag** (niet via sway-keybinds — vandaar dat cage dit "by design" blokkeert en sway niet). Een leerling
kon dus midden in een toets naar GNOME terugschakelen.

## Beslissing
VT-switching wordt **op kernel-niveau geblokkeerd** via de **`VT_LOCKSWITCH`-ioctl** (`/usr/bin/coolbx-vt-lock`,
op `/dev/tty0`). `coolbx-kiosk-start` zet de lock ná `chvt` naar de kiosk-VT; de `ExecStopPost`
(`coolbx-kiosk-return`) **ontgrendelt eerst** (anders weigert `chvt`) en keert terug naar de GNOME-VT.

## Bevinding (bewezen in VM)
- VT vóór: `tty3`. Na `Ctrl+Alt+F2` (via QEMU-sendkey): **`tty3` — bleef** (switch geblokkeerd). ✅
- Na exit (`systemctl stop coolbx-kiosk` → ExecStopPost): **`tty2`** (GNOME) — unlock + terugkeer werkt. ✅

## Gevolgen
De kiosk is escape-resistant tegen VT-switching. De unlock zit in `ExecStopPost`, dus ook bij een sway-crash
ontgrendelt het systeem (geen permanent-locked toestel).

**Restpunten (fast-follow hardening, Fase 4 / [te bevestigen]):** boot-time escape (GRUB-wachtwoord, `kernel.sysrq=0`,
anti-live-USB via Secure Boot + firmware-pw), **sway-IPC afschermen** (`swaymsg exit`/`exec` — al beperkt want geen
terminal in de kiosk), en de overige Chromium-enforcement-policy (devtools/downloads/file:// — in `--app`-modus).

## Alternatieven
- cage (blokkeert VT-switch by design) — verworpen: geen statusbalk mogelijk (ADR-0006); we hielden sway voor de waybar.
