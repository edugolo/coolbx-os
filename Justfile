export image_name := env("IMAGE_NAME", "coolbx-os")
export default_tag := env("DEFAULT_TAG", "latest")
export base_image := env("BASE_IMAGE", "quay.io/fedora/fedora-bootc:43")
export features := env("FEATURES", "")
export bib_image := env("BIB_IMAGE", "quay.io/centos-bootc/bootc-image-builder:latest")
export rootfs := env("ROOTFS", "btrfs")

default:
    @just --list

# ─── DEV vs PROD: twee lagen houden dev-tooling uit productie ────────────────────
#  Laag 1 — Devtools (dogtail/a11y, GUI-automation) zitten NOOIT in een image.
#           Ze worden enkel AT-RUNTIME op de dev-VM gezet via `just vm-gui-setup`
#           (bootc usr-overlay, transient — weg bij reboot). Geen build_files/feature
#           installeert ze → per constructie onbereikbaar voor prod.
#  Laag 2 — De enige image-niveau dev-naad (autologin-testuser) hangt aan de build-arg
#           ENABLE_FIRSTBOOT_USER. Default = 0 (prod-veilig). Alleen build-dev/-qcow2
#           zetten 1. build_files/02-config.sh faalt de prod-build als een dev-naad lekt.
# ─────────────────────────────────────────────────────────────────────────────────

# Bouw de container-image (rootless, prod-stijl: ENABLE_FIRSTBOOT_USER default 0).
build tag=default_tag:
    podman build \
      --build-arg BASE_IMAGE="{{ base_image }}" \
      --build-arg FEATURES="{{ features }}" \
      --tag "localhost/{{ image_name }}:{{ tag }}" .

# PRODUCTIE-image (deploybaar): expliciet GEEN autologin/testuser, GEEN dev-tooling.
build-prod tag=default_tag:
    podman build \
      --build-arg BASE_IMAGE="{{ base_image }}" \
      --build-arg FEATURES="{{ features }}" \
      --build-arg ENABLE_FIRSTBOOT_USER=0 \
      --tag "localhost/{{ image_name }}:{{ tag }}" .

# Dev-image MÉT autologin-testuser (tester/tester) — enkel voor de lokale VM-loop, NOOIT prod.
build-dev tag=default_tag:
    podman build \
      --build-arg BASE_IMAGE="{{ base_image }}" \
      --build-arg FEATURES="{{ features }}" \
      --build-arg ENABLE_FIRSTBOOT_USER=1 \
      --tag "localhost/{{ image_name }}:{{ tag }}" .

# Bouw een bootable qcow2 via bootc-image-builder.
# Rootless build (heeft netwerk) → image via save|load naar root-storage (rootful build
# heeft hier geen DNS) → BIB leest /var/lib/containers/storage.
build-qcow2 tag=default_tag:
    #!/usr/bin/env bash
    set -euo pipefail
    # GUARD: weiger te bouwen terwijl een VM output/qcow2/disk.qcow2 open heeft — BIB
    # overschrijft dat bestand en een draaiende qemu erop → corruptie (emergency mode).
    if [ -f /tmp/coolbx-vm.pid ] && kill -0 "$(cat /tmp/coolbx-vm.pid 2>/dev/null)" 2>/dev/null; then
      echo "FOUT: er draait een VM (pid $(cat /tmp/coolbx-vm.pid)) op de qcow2. Doe eerst 'just vm-stop'."; exit 1
    fi
    IMG="localhost/{{ image_name }}:{{ tag }}"
    echo ">> rootful DEV-build $IMG (network=host → DNS; base={{ base_image }}, features='{{ features }}')"
    # Bouw direct in rootful storage (--network=host geeft DNS). Bespaart de dure
    # 'podman save | sudo podman load' (≈2,5 GB stream) én dubbel schijfgebruik;
    # BIB leest dezelfde /var/lib/containers/storage. Laag-cache blijft persistent.
    # FEATURES_CACHEBUST: bust de feature-laag altijd (bind-mount cachet niet op inhoud).
    sudo podman build --network=host \
      --build-arg BASE_IMAGE="{{ base_image }}" \
      --build-arg FEATURES="{{ features }}" \
      --build-arg FEATURES_CACHEBUST="$(date +%s)" \
      --build-arg ENABLE_FIRSTBOOT_USER=1 \
      --tag "$IMG" .
    mkdir -p output
    echo ">> bootc-image-builder → qcow2 (rootfs={{ rootfs }})"
    sudo podman run --rm --privileged --pull=newer \
      --security-opt label=type:unconfined_t \
      -v "$(pwd)/disk_config/disk.toml:/config.toml:ro" \
      -v "$(pwd)/output:/output" \
      -v /var/lib/containers/storage:/var/lib/containers/storage \
      "{{ bib_image }}" \
      --type qcow2 --rootfs "{{ rootfs }}" --use-librepo=True \
      "$IMG"
    # BIB-output is root-owned; sudo is alleen voor podman → fix ownership via een podman-container.
    sudo podman run --rm --security-opt label=disable -v "$(pwd)/output:/output" \
      "{{ base_image }}" chown -R "$(id -u):$(id -g)" /output
    echo ">> klaar: output/qcow2/disk.qcow2"

# Start de dev-VM headless (qemu-direct, UEFI). SSH op :2222, monitor-socket voor screenshots.
dev-vm:
    #!/usr/bin/env bash
    set -euo pipefail
    test -f output/qcow2/disk.qcow2 || { echo "Bouw eerst: just build-qcow2"; exit 1; }
    if [ -f /tmp/coolbx-vm.pid ] && kill -0 "$(cat /tmp/coolbx-vm.pid 2>/dev/null)" 2>/dev/null; then
      echo "VM draait al (pid $(cat /tmp/coolbx-vm.pid)). Doe eerst 'just vm-stop'."; exit 1
    fi
    OVMF_CODE=$(ls /usr/share/edk2/ovmf/OVMF_CODE.fd /usr/share/OVMF/OVMF_CODE.fd 2>/dev/null | head -1 || true)
    OVMF_VARS_SRC=$(ls /usr/share/edk2/ovmf/OVMF_VARS.fd /usr/share/OVMF/OVMF_VARS.fd 2>/dev/null | head -1 || true)
    [ -n "$OVMF_CODE" ] || { echo "OVMF niet gevonden — installeer edk2-ovmf"; exit 1; }
    cp -f "$OVMF_VARS_SRC" output/ovmf_vars.fd
    rm -f /tmp/coolbx-mon.sock /tmp/coolbx-qmp.sock
    # Headless maar volledig automatiseerbaar (CI-vriendelijk): screendump via de monitor,
    # input via QMP+virtio-tablet, SSH op :2222, CDP via SSH-tunnel. Geen host-display nodig.
    qemu-system-x86_64 \
      -enable-kvm -machine q35 -cpu host -m 4096 -smp 4 \
      -drive if=pflash,format=raw,readonly=on,file="$OVMF_CODE" \
      -drive if=pflash,format=raw,file=output/ovmf_vars.fd \
      -drive file=output/qcow2/disk.qcow2,if=virtio,format=qcow2 \
      -device virtio-vga,xres=1280,yres=800 -display none \
      -device virtio-tablet-pci \
      -monitor unix:/tmp/coolbx-mon.sock,server,nowait \
      -qmp unix:/tmp/coolbx-qmp.sock,server,nowait \
      -netdev user,id=n0,hostfwd=tcp:127.0.0.1:2222-:22 -device virtio-net-pci,netdev=n0 \
      -serial file:output/serial.log \
      -daemonize -pidfile /tmp/coolbx-vm.pid
    echo "VM gestart (pid $(cat /tmp/coolbx-vm.pid)). 'just vm-shot' voor screenshot, 'just vm-ssh' voor shell."

# Start de dev-VM met een ZICHTBAAR venster (gtk op de wayland-sessie) i.p.v. headless.
# Je ziet de VM live draaien; screenshots/SSH blijven werken via de monitor-socket en :2222.
dev-vm-gui:
    #!/usr/bin/env bash
    set -euo pipefail
    test -f output/qcow2/disk.qcow2 || { echo "Bouw eerst: just build-qcow2"; exit 1; }
    if [ -f /tmp/coolbx-vm.pid ] && kill -0 "$(cat /tmp/coolbx-vm.pid 2>/dev/null)" 2>/dev/null; then
      echo "VM draait al (pid $(cat /tmp/coolbx-vm.pid)). Doe eerst 'just vm-stop'."; exit 1
    fi
    OVMF_CODE=$(ls /usr/share/edk2/ovmf/OVMF_CODE.fd /usr/share/OVMF/OVMF_CODE.fd 2>/dev/null | head -1 || true)
    OVMF_VARS_SRC=$(ls /usr/share/edk2/ovmf/OVMF_VARS.fd /usr/share/OVMF/OVMF_VARS.fd 2>/dev/null | head -1 || true)
    [ -n "$OVMF_CODE" ] || { echo "OVMF niet gevonden — installeer edk2-ovmf"; exit 1; }
    cp -f "$OVMF_VARS_SRC" output/ovmf_vars.fd
    rm -f /tmp/coolbx-mon.sock
    export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
    export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/1000}"
    qemu-system-x86_64 \
      -enable-kvm -machine q35 -cpu host -m 4096 -smp 4 \
      -drive if=pflash,format=raw,readonly=on,file="$OVMF_CODE" \
      -drive if=pflash,format=raw,file=output/ovmf_vars.fd \
      -drive file=output/qcow2/disk.qcow2,if=virtio,format=qcow2 \
      -device virtio-vga,xres=1280,yres=800 -display gtk,show-cursor=on,zoom-to-fit=on \
      -device virtio-tablet-pci \
      -monitor unix:/tmp/coolbx-mon.sock,server,nowait \
      -qmp unix:/tmp/coolbx-qmp.sock,server,nowait \
      -netdev user,id=n0,hostfwd=tcp:127.0.0.1:2222-:22 -device virtio-net-pci,netdev=n0 \
      -serial file:output/serial.log \
      -name "Coolbx OS — dev-VM" \
      -pidfile /tmp/coolbx-vm.pid

# Maak een screenshot van de VM (QEMU-monitor screendump → PNG die de agent kan bekijken).
vm-shot out="output/shot.png":
    python3 scripts/vm-shot.py /tmp/coolbx-mon.sock "{{ out }}"

# Muisklik op pixel (X,Y) in de grafische VM (via virtio-tablet + QMP, absoluut).
vm-click x y:
    python3 scripts/vm-input.py click {{ x }} {{ y }}

# Dubbelklik op pixel (X,Y).
vm-dblclick x y:
    python3 scripts/vm-input.py dblclick {{ x }} {{ y }}

# Stuur toetsen naar de VM (bv. `just vm-key ret` of `just vm-key ctrl-alt-f3`).
vm-key *keys:
    python3 scripts/vm-input.py key {{ keys }}

# Tik letterlijke tekst in de VM (us-layout qcodes).
vm-type text:
    python3 scripts/vm-input.py type "{{ text }}"

# SSH in de dev-VM (testuser, wachtwoord 'tester').
vm-ssh *args:
    sshpass -p tester ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p 2222 tester@127.0.0.1 {{ args }}

# Wacht tot de VM via SSH bereikbaar is (default 120s). Exit !=0 bij timeout.
vm-wait timeout="120":
    #!/usr/bin/env bash
    set -uo pipefail
    for i in $(seq 1 {{ timeout }}); do
      if sshpass -p tester ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=2 -p 2222 tester@127.0.0.1 true 2>/dev/null; then
        echo "VM up na ${i}s"; exit 0
      fi; sleep 1
    done
    echo "VM kwam niet up binnen {{ timeout }}s — zie output/serial.log"; exit 1

# Machine-leesbare smoke-test tegen de draaiende VM. Exit !=0 bij falen (voor de autonome loop).
check:
    #!/usr/bin/env bash
    set -uo pipefail
    vssh(){ sshpass -p tester ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=4 -p 2222 tester@127.0.0.1 "$@"; }
    fail=0
    chk(){ if vssh "$2" >/dev/null 2>&1; then echo "OK   $1"; else echo "FAIL $1"; fail=1; fi; }
    chk "gdm actief"             'systemctl is-active --quiet gdm'
    chk "NetworkManager actief"  'systemctl is-active --quiet NetworkManager'
    chk "default=graphical"      'test "$(systemctl get-default)" = graphical.target'
    chk "gnome-shell draait"     'pgrep -x gnome-shell'
    chk "geen failed units"      'test "$(systemctl --failed --no-legend | wc -l)" -eq 0'
    chk "nl_BE locale"           'grep -q nl_BE /etc/locale.conf'
    [ $fail -eq 0 ] && echo "ALLE CHECKS OK" || echo "ER ZIJN CHECKS GEFAALD"
    exit $fail

# Push een feature's system_files LIVE in de draaiende VM via `bootc usr-overlay` (geen herbouw/reboot).
# Snelle iteratie: bewerk features/<feat>/system_files -> `just vm-sync <feat>` -> `just vm-kiosk`.
vm-sync feat="kiosk":
    #!/usr/bin/env bash
    set -euo pipefail
    sshc(){ sshpass -p tester ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p 2222 tester@127.0.0.1 "$@"; }
    echo ">> usr-overlay activeren + '{{ feat }}' live syncen naar /usr+/etc"
    sshc 'echo tester | sudo -S bootc usr-overlay >/dev/null 2>&1 || true'
    ( cd "features/{{ feat }}/system_files" && tar -cf - -- * ) | sshc 'cat > /tmp/coolbx-sync.tar'
    sshc 'echo tester | sudo -S tar -C / --no-same-owner --no-overwrite-dir -xf /tmp/coolbx-sync.tar && echo "OK: {{ feat }} live (transient tot reboot)"'
    # vm-sync is een DEV-tool → simuleer de dev-build-gate: verwijder prod-only policies die
    # de dev-tooling breken (DeveloperToolsAvailability:2 blokkeert Runtime.evaluate/CDP). ADR-0022.
    sshc 'echo tester | sudo -S rm -f /etc/chromium/policies/managed/coolbx-hardening-prod.json'

# Start de kiosk in de draaiende VM (na vm-sync). Stop een lopende kiosk eerst.
vm-kiosk url="file:///usr/share/coolbx/kiosk/placeholder.html":
    sshpass -p tester ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p 2222 tester@127.0.0.1 \
      "echo tester | sudo -S sh -c 'systemctl stop coolbx-kiosk 2>/dev/null; systemctl reset-failed coolbx-kiosk 2>/dev/null; umount -l /var/lib/coolbx-kiosk 2>/dev/null; coolbx-vt-lock unlock 2>/dev/null; sleep 2; env COOLBX_KIOSK_URL={{ url }} /usr/bin/coolbx-kiosk-start'"

# DEV-ONLY (ADR-0020): start de kiosk MÉT CDP-debugpoort 9222 (COOLBX_KIOSK_DEBUG=1) voor de e2e-harness.
# Vereist eerst `just vm-sync kiosk` (de debug-gate zit in chromium-kiosk.sh). Nooit in prod.
vm-kiosk-debug url="file:///usr/share/coolbx/kiosk/placeholder.html":
    sshpass -p tester ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p 2222 tester@127.0.0.1 \
      "echo tester | sudo -S sh -c 'systemctl stop coolbx-kiosk 2>/dev/null; systemctl reset-failed coolbx-kiosk 2>/dev/null; umount -l /var/lib/coolbx-kiosk 2>/dev/null; coolbx-vt-lock unlock 2>/dev/null; sleep 2; env COOLBX_KIOSK_DEBUG=1 COOLBX_KIOSK_URL={{ url }} /usr/bin/coolbx-kiosk-start'"

# Spreek het Chrome DevTools Protocol tegen de kiosk-Chromium in de VM (laag C, ADR-0020).
# Opent een ephemere SSH local-forward (-L 9222) via een ControlMaster en draait scripts/vm-cdp.py.
# Bv.: `just vm-cdp targets` · `just vm-cdp title` · `just vm-cdp managed` · `just vm-cdp policy`
vm-cdp *args:
    #!/usr/bin/env bash
    set -uo pipefail
    CTL=/tmp/coolbx-cdp-ssh.sock
    cleanup(){ sshpass -p tester ssh -S "$CTL" -O exit -p 2222 tester@127.0.0.1 2>/dev/null || true; }
    trap cleanup EXIT
    sshpass -p tester ssh -MNfT -S "$CTL" \
      -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ExitOnForwardFailure=yes \
      -L 9222:localhost:9222 -p 2222 tester@127.0.0.1 || { echo "tunnel faalde (poort 9222 bezet of geen CDP?)"; exit 1; }
    python3 scripts/vm-cdp.py {{ args }}

# Bouw de host-side OCR-container (tesseract + NL/EN) voor laag D van de e2e-harness.
# --network=host geeft DNS in de build (anders kan dnf de Fedora-mirrors niet resolven).
ocr-build:
    sudo podman build --network=host -t localhost/coolbx-ocr -f tools/ocr/Containerfile tools/ocr

# OCR-locate op een screenshot: `just vm-ocr find output/shot.png "Toetsmodus"` → {x,y,...}.
vm-ocr cmd png text="":
    python3 scripts/vm-ocr.py {{ cmd }} {{ png }} "{{ text }}"

# Vind tekst op het scherm via OCR en klik erop (screendump → tesseract → QMP-klik).
vm-find-click text:
    #!/usr/bin/env bash
    set -uo pipefail
    python3 scripts/vm-shot.py /tmp/coolbx-mon.sock /tmp/coolbx-fc.png
    pos=$(python3 scripts/vm-ocr.py find /tmp/coolbx-fc.png "{{ text }}") || { echo "tekst niet gevonden: {{ text }}"; exit 1; }
    x=$(echo "$pos" | python3 -c "import sys,json;print(json.load(sys.stdin)['x'])")
    y=$(echo "$pos" | python3 -c "import sys,json;print(json.load(sys.stdin)['y'])")
    echo "klik op '{{ text }}' @ ($x,$y)"
    python3 scripts/vm-input.py click "$x" "$y"

# Draai de volledige e2e-suite tegen de VM (start 'm headless als hij nog niet draait).
# Lagen A/B/C/D uit ADR-0020. Vereist: just dev-vm (qcow2) + 'just ocr-build' (eenmalig).
e2e *pytest_args:
    #!/usr/bin/env bash
    set -uo pipefail
    if ! { [ -f /tmp/coolbx-vm.pid ] && kill -0 "$(cat /tmp/coolbx-vm.pid 2>/dev/null)" 2>/dev/null; }; then
      echo ">> geen VM actief — start headless dev-vm"; just dev-vm; just vm-wait 180
    fi
    python3 -m pytest tests/ -v {{ pytest_args }}

# Stop de dev-VM.
vm-stop:
    -kill "$(cat /tmp/coolbx-vm.pid 2>/dev/null)" 2>/dev/null || true
    -rm -f /tmp/coolbx-vm.pid /tmp/coolbx-mon.sock

# Shellcheck op alle build-scripts.
lint:
    #!/usr/bin/env bash
    set -euo pipefail
    if command -v shellcheck >/dev/null 2>&1; then
      find build_files features system_files scripts -name '*.sh' -type f -exec shellcheck {} + 2>/dev/null || true
    else
      echo "shellcheck niet geïnstalleerd — overgeslagen"
    fi
# Ruim podman-opslag op (voorkomt dat dangling build-lagen de schijf vullen).
# Rootless wordt niet meer gebruikt sinds we rootful bouwen → mag volledig leeg.
clean-images:
    -podman system prune -af
    -sudo podman image prune -f
    @echo "schijf nu:"; df -h / | tail -1

# Eenmalige setup voor GUI-automation: installeer dogtail + a11y in de DRAAIENDE VM
# (usr-overlay, transient — weg bij reboot). Daarna werkt `just vm-gui ...`.
vm-gui-setup:
    sshpass -p tester ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p 2222 tester@127.0.0.1 \
      'echo tester | sudo -S bootc usr-overlay 2>/dev/null; echo tester | sudo -S dnf5 install -y --setopt=install_weak_deps=False python3-dogtail gnome-ponytail-daemon python3-pyatspi; \
       export XDG_RUNTIME_DIR=/run/user/1000 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus; \
       gsettings set org.gnome.desktop.interface toolkit-accessibility true; echo "GUI-automation klaar"'

# Betrouwbare GUI-automation via AT-SPI/dogtail (geen pixels). Voorbeelden:
#   just vm-gui apps
#   just vm-gui launch "gnome-control-center system"
#   just vm-gui find gnome-control-center Coolbx
#   just vm-gui click gnome-control-center Systeem
#   just vm-gui type gnome-control-center Apparaatnaam coolbx-laptop
vm-gui *args:
    #!/usr/bin/env bash
    set -euo pipefail
    sshpass -p tester scp -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -P 2222 \
      scripts/vm-dogtail.py tester@127.0.0.1:/tmp/vm-dogtail.py >/dev/null 2>&1
    sshpass -p tester ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p 2222 tester@127.0.0.1 \
      "export XDG_CURRENT_DESKTOP=GNOME XDG_RUNTIME_DIR=/run/user/1000 WAYLAND_DISPLAY=wayland-0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus; python3 /tmp/vm-dogtail.py {{ args }}" 2>/dev/null
