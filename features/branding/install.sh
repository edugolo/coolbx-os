#!/usr/bin/env bash
# Coolbx OS — branding feature: Plymouth + GRUB + GDM/desktop + os-release.
set -euo pipefail

echo "::group:: branding: packages (Inter-font + plymouth script-plugin)"
# Inter draagt de volledige Coolbx-identiteit (GNOME-UI + kiosk-HTML).
# plymouth-plugin-script levert script.so — vereist door ons 'script'-thema
# (de base heeft enkel two-step/label/spinner).
dnf5 install -y --setopt=install_weak_deps=False \
    rsms-inter-fonts plymouth-plugin-script glib2-devel
echo "::endgroup::"

echo "::group:: branding: os-release"
# Rebrand os-release (keep Fedora version fields, override identity).
osr=/usr/lib/os-release
sed -i \
    -e 's/^NAME=.*/NAME="Coolbx OS"/' \
    -e 's/^PRETTY_NAME=.*/PRETTY_NAME="Coolbx OS"/' \
    -e 's|^HOME_URL=.*|HOME_URL="https://coolbx.be/"|' \
    -e '/^ANSI_COLOR=/d' \
    -e '/^LOGO=/d' \
    "$osr"
{
    echo 'VARIANT="Coolbx OS"'
    echo 'VARIANT_ID=coolbx-os'
    echo 'ANSI_COLOR="0;38;2;80;206;150"'
    echo 'LOGO=coolbx-logo'
    echo 'LOGO_DARK=coolbx-logo-white'
} >> "$osr"
sed -i -e '/^LOGO_DARK=/d' "$osr"   # voorkom dubbele bij herhaalde run
echo 'LOGO_DARK=coolbx-logo-white' >> "$osr"
echo "::endgroup::"

echo "::group:: branding: plymouth (pulsing splash)"
install -d /etc/plymouth
cat > /etc/plymouth/plymouthd.conf <<'EOF'
[Daemon]
Theme=coolbx
DeviceTimeout=8
EOF
# Make 'coolbx' the active theme. Always set the symlink directly (robust),
# and also call the helper when present.
ln -sf /usr/share/plymouth/themes/coolbx/coolbx.plymouth \
       /usr/share/plymouth/themes/default.plymouth
if command -v plymouth-set-default-theme >/dev/null 2>&1; then
    plymouth-set-default-theme coolbx || true
fi
# Regenerate the image-shipped initramfs so the coolbx theme + script.so land in
# early boot. On bootc the canonical initramfs is /usr/lib/modules/<kver>/initramfs.img
# (ostree copies it to /boot at deploy) — write THERE explicitly, not dracut's
# default /boot path (which isn't part of the image). Theme is already set above,
# so dracut's plymouth module pulls coolbx in.
kver=$(ls /usr/lib/modules 2>/dev/null | head -n1)
if command -v dracut >/dev/null 2>&1 && [ -n "${kver:-}" ] \
   && [ -f "/usr/lib/modules/${kver}/initramfs.img" ]; then
    echo "dracut: regenereer initramfs voor ${kver} (incl. plymouth/coolbx)"
    # Laptops booten van lokale schijf → netwerk/SAN-storage-init weglaten.
    # Krimpt de initramfs en verkort het GRUB→Plymouth-laadmoment (zwarte flits).
    # Lokale drivers (nvme/ahci/sd/mmc/virtio/btrfs/ext4) blijven via kernel-modules.
    dracut --force --no-hostonly --add plymouth \
        --omit "nfs nbd cifs iscsi fcoe fcoe-uefi multipath nvmf" \
        "/usr/lib/modules/${kver}/initramfs.img" "${kver}"
    lsinitrd "/usr/lib/modules/${kver}/initramfs.img" 2>/dev/null \
        | grep -qi 'themes/coolbx' \
        && echo "dracut: coolbx-thema zit in initramfs ✓" \
        || echo "warn: coolbx-thema NIET in initramfs"
else
    echo "warn: dracut/initramfs niet gevonden (kver=${kver:-?})"
fi
echo "::endgroup::"

echo "::group:: branding: grub2 theme (first-boot installer)"
# On bootc /boot lives outside the image, so the stock CoreOS grub.cfg (static,
# not regenerated from /etc/default/grub) can't be themed at build time. A
# first-boot oneshot copies the theme into /boot/grub2 and writes custom.cfg,
# which the stock grub.cfg sources via its 41_custom.cfg hook.
chmod 0755 /usr/libexec/coolbx-grub-theme
systemctl enable coolbx-grub-theme.service
echo "::endgroup::"

echo "::group:: branding: dconf (desktop + gdm defaults)"
if command -v dconf >/dev/null 2>&1; then
    dconf update || echo "warn: dconf update failed (db compiles at boot)"
fi
echo "::endgroup::"

echo "::group:: branding: GDM greeter backdrop (#141210)"
# De login/lock-greeter negeert de desktop-achtergrond; z'n backdrop-kleur komt uit
# het gnome-shell-thema (gresource). We herpakken die met #lockDialogGroup op
# Focus-dark. Bij een GNOME-update herbouwen we de image → opnieuw toegepast.
gres=/usr/share/gnome-shell/gnome-shell-theme.gresource
if [ -f "$gres" ] && command -v glib-compile-resources >/dev/null 2>&1; then
    wd=$(mktemp -d); prefix=/org/gnome/shell/theme
    files=""
    for res in $(gresource list "$gres"); do
        rel="${res#"$prefix"/}"
        mkdir -p "$wd/$(dirname "$rel")"
        gresource extract "$gres" "$res" > "$wd/$rel"
        files="$files    <file>$rel</file>\n"
    done
    # Quick-settings/systeemmenu blijven GNOME-DEFAULT (eerder geprobeerd: blauwgrijs/
    # bruin/licht/mint — telkens niet goed; reset naar default, herbekijken we later).
    # ENKEL het rechtsklik-/context-menu krijgt een lichte hairline (box-shadow, zoals
    # de vensters) zodat het loskomt van het donkere bureaublad.
    if [ -f "$wd/gnome-shell-dark.css" ]; then
        cat >> "$wd/gnome-shell-dark.css" <<'CSS'

/* Coolbx OS — hairline op het rechtsklik-/context-menu (scheiding van donker bureaublad) */
.popup-menu-content {
  box-shadow: 0 0 0 1px rgba(250,248,243,0.16),
              0 8px 24px rgba(0,0,0,0.40);
}
CSS
    fi
    for css in "$wd"/gnome-shell.css "$wd"/gnome-shell-dark.css "$wd"/gnome-shell-light.css; do
        [ -f "$css" ] || continue
        printf '\n/* Coolbx OS — login/lock backdrop = Focus-dark */\n#lockDialogGroup { background-color: #141210; background-image: none; }\n' >> "$css"
    done
    printf '<?xml version="1.0" encoding="UTF-8"?>\n<gresources>\n  <gresource prefix="%s">\n%b  </gresource>\n</gresources>\n' \
        "$prefix" "$files" > "$wd/coolbx-theme.gresource.xml"
    if glib-compile-resources --sourcedir="$wd" --target="$gres" "$wd/coolbx-theme.gresource.xml" 2>/dev/null; then
        echo "GDM-backdrop herpakt → #141210"
    else
        echo "warn: gresource herpakken mislukt (backdrop blijft default)"
    fi
    rm -rf "$wd"
else
    echo "warn: gnome-shell-theme.gresource of glib-compile-resources ontbreekt"
fi
echo "::endgroup::"

echo "::group:: branding: Fedora-logo-assets vervangen door wordmark"
# GNOME's 'Over'-pagina toont (via Fedora-branding) het fedora-logo i.p.v. de
# os-release LOGO. Voor een volledig gerebrand OS overschrijven we de brede
# Fedora-logo-assets met onze wordmark.
wl=/usr/share/coolbx/branding/coolbx-wordmark-white.png   # voor DONKERE bg
wsvg=/usr/share/coolbx/branding/coolbx-wordmark-white.svg
il=/usr/share/coolbx/branding/coolbx-wordmark-ink.png     # voor LICHTE bg
isvg=/usr/share/coolbx/branding/coolbx-wordmark-ink.svg
# coolbx-logo-white als themed icon (legacy/GDM).
cp -f /usr/share/coolbx/branding/coolbx-logo-white.png \
      /usr/share/icons/hicolor/256x256/apps/coolbx-logo-white.png 2>/dev/null || true
# GNOME 'Over' (control-center) gebruikt een aparte logo voor LICHTE vs DONKERE modus.
# AUTORITATIEF (Fedora gnome-control-center.spec): het is gecompileerd met
#   -Ddistributor_logo=/usr/share/pixmaps/fedora_logo_med.png        (LICHT)
#   -Ddark_mode_distributor_logo=/usr/share/pixmaps/fedora_whitelogo_med.png (DONKER)
# → die twee PNG's zijn de échte bron; mode-correct vervangen (licht=ink, donker=wit).
if [ -f "$wl" ] && [ -f "$il" ]; then
    # >>> de compile-tijd 'Over'-logo's (de doorslaggevende) <<<
    [ -e /usr/share/pixmaps/fedora_logo_med.png ]      && cp -f "$il" /usr/share/pixmaps/fedora_logo_med.png       # LICHT → ink
    [ -e /usr/share/pixmaps/fedora_whitelogo_med.png ] && cp -f "$wl" /usr/share/pixmaps/fedora_whitelogo_med.png  # DONKER → wit
    # Overige lichte-bg-assets → INK
    for f in /usr/share/fedora-logos/fedora_lightbackground.svg \
             /usr/share/fedora-logos/fedora_logo.svg \
             /usr/share/pixmaps/fedora-logo.png /usr/share/pixmaps/fedora-logo-small.png; do
        [ -e "$f" ] && cp -f "$(echo "$f" | grep -q '\.svg$' && echo "$isvg" || echo "$il")" "$f"
    done
    # Overige donkere-bg-assets → WIT
    for f in /usr/share/fedora-logos/fedora_darkbackground.svg \
             /usr/share/fedora-logos/fedora_logo_darkbackground.svg \
             /usr/share/pixmaps/fedora_whitelogo.svg \
             /usr/share/pixmaps/fedora-logo-sprite.svg \
             /usr/share/pixmaps/fedora-gdm-logo.png \
             $(find /usr/share/icons -iname "fedora-logo-icon.png" 2>/dev/null); do
        [ -e "$f" ] && cp -f "$(echo "$f" | grep -q '\.svg$' && echo "$wsvg" || echo "$wl")" "$f"
    done
    echo "Fedora-logo-assets vervangen (licht=ink, donker=wit; compile-tijd-paden incl.)"
fi
echo "::endgroup::"

echo "::group:: branding: icon cache (About-logo + dock-icoon)"
# coolbx-logo (os-release LOGO=, GNOME 'Over') + coolbx-focus (toetsmodus-launcher).
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -f /usr/share/icons/hicolor 2>/dev/null \
        || echo "warn: icon-cache update overgeslagen"
fi
echo "::endgroup::"

echo "branding feature installed"
