export image_name := env("IMAGE_NAME", "coolbx-os")
export default_tag := env("DEFAULT_TAG", "latest")
export base_image := env("BASE_IMAGE", "quay.io/fedora/fedora-bootc:43")
export features := env("FEATURES", "")
export bib_image := env("BIB_IMAGE", "quay.io/centos-bootc/bootc-image-builder:latest")
export rootfs := env("ROOTFS", "btrfs")

default:
    @just --list

# Bouw de container-image (rootless). BASE_IMAGE / FEATURES / DEFAULT_TAG via env.
build tag=default_tag:
    podman build \
      --build-arg BASE_IMAGE="{{ base_image }}" \
      --build-arg FEATURES="{{ features }}" \
      --tag "localhost/{{ image_name }}:{{ tag }}" .

# Prod-build (geen first-boot dev-user / autologin).
build-prod tag=default_tag:
    podman build \
      --build-arg BASE_IMAGE="{{ base_image }}" \
      --build-arg FEATURES="{{ features }}" \
      --build-arg ENABLE_FIRSTBOOT_USER=0 \
      --tag "localhost/{{ image_name }}:{{ tag }}" .

# Bouw een bootable qcow2 via bootc-image-builder.
# Rootless build (heeft netwerk) → image via save|load naar root-storage (rootful build
# heeft hier geen DNS) → BIB leest /var/lib/containers/storage.
build-qcow2 tag=default_tag:
    #!/usr/bin/env bash
    set -euo pipefail
    IMG="localhost/{{ image_name }}:{{ tag }}"
    echo ">> rootless build $IMG (base={{ base_image }}, features='{{ features }}')"
    podman build \
      --build-arg BASE_IMAGE="{{ base_image }}" \
      --build-arg FEATURES="{{ features }}" \
      --tag "$IMG" .
    echo ">> image naar rootful storage (save|load, geen netwerk/rebuild)"
    podman save "$IMG" | sudo podman load
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
    OVMF_CODE=$(ls /usr/share/edk2/ovmf/OVMF_CODE.fd /usr/share/OVMF/OVMF_CODE.fd 2>/dev/null | head -1 || true)
    OVMF_VARS_SRC=$(ls /usr/share/edk2/ovmf/OVMF_VARS.fd /usr/share/OVMF/OVMF_VARS.fd 2>/dev/null | head -1 || true)
    [ -n "$OVMF_CODE" ] || { echo "OVMF niet gevonden — installeer edk2-ovmf"; exit 1; }
    cp -f "$OVMF_VARS_SRC" output/ovmf_vars.fd
    rm -f /tmp/coolbx-mon.sock
    qemu-system-x86_64 \
      -enable-kvm -machine q35 -cpu host -m 4096 -smp 4 \
      -drive if=pflash,format=raw,readonly=on,file="$OVMF_CODE" \
      -drive if=pflash,format=raw,file=output/ovmf_vars.fd \
      -drive file=output/qcow2/disk.qcow2,if=virtio,format=qcow2 \
      -device virtio-vga -display none \
      -monitor unix:/tmp/coolbx-mon.sock,server,nowait \
      -netdev user,id=n0,hostfwd=tcp:127.0.0.1:2222-:22 -device virtio-net-pci,netdev=n0 \
      -serial file:output/serial.log \
      -daemonize -pidfile /tmp/coolbx-vm.pid
    echo "VM gestart (pid $(cat /tmp/coolbx-vm.pid)). 'just vm-shot' voor screenshot, 'just vm-ssh' voor shell."

# Maak een screenshot van de VM (QEMU-monitor screendump → PNG die de agent kan bekijken).
vm-shot out="output/shot.png":
    python3 scripts/vm-shot.py /tmp/coolbx-mon.sock "{{ out }}"

# SSH in de dev-VM (testuser, wachtwoord 'tester').
vm-ssh *args:
    sshpass -p tester ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p 2222 tester@127.0.0.1 {{ args }}

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