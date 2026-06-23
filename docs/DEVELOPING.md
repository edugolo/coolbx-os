# Lokaal ontwikkelen — Coolbx OS

Autonome, machine-leesbare build→VM-loop (geen browser-VNC). Zie ook `docs/ROADMAP.md` en `docs/adr/`.

## Vereisten (dev-machine, Fedora)
`podman`, `just`, `qemu-system-x86_64` + `/dev/kvm`, `edk2-ovmf`, `jq`, `python3-pillow`, `sshpass`.
Passwordless `sudo podman` staat ingesteld (`/etc/sudoers.d/coolbx-os-dev`) voor bootc-image-builder.

## Inner loop
```bash
just build                 # rootless container-build (snel, voor lint/iteratie)
just build-qcow2           # rootful build + bootc-image-builder → output/qcow2/disk.qcow2
just dev-vm                # start headless qemu (UEFI), SSH op :2222, monitor-socket
just vm-shot               # screenshot → output/shot.png  (agent bekijkt dit)
just vm-ssh 'bootc status' # CLI-check in de VM
just vm-stop
```

### Base / features kiezen (env)
```bash
BASE_IMAGE=ghcr.io/ublue-os/base-main:43 just build-qcow2   # base-spike (S1)
FEATURES="kiosk focus" just build                            # optionele features (ADR-0012)
ROOTFS=ext4 just build-qcow2                                 # FOG-vriendelijke rootfs
```

## Verificatie (machine-leesbaar)
- **Visueel:** `just vm-shot` → PNG.
- **CLI:** `just vm-ssh '<cmd>'` (bv. `systemctl is-active gdm`, `bootc status`, `cat /etc/os-release`).
- **Serieel logboek:** `output/serial.log`.

## Dev vs prod
Dev-builds zetten een autologin-testuser (`tester`/`tester`). Prod: `just build-prod` (`ENABLE_FIRSTBOOT_USER=0`)
→ geen testuser, geen autologin. CI moet falen als een prod-build de dev-user bevat.
