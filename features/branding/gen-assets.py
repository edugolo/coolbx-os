#!/usr/bin/env python3
"""Genereer de Coolbx OS-brandingassets (Plymouth/GRUB/wallpaper) in de feature.
Reproduceerbaar: draai vanuit de repo-root om de PNG's te herbouwen."""
import os
from PIL import Image, ImageDraw, ImageFont

SF = os.path.join(os.path.dirname(__file__), "system_files")
FD = "/usr/share/fonts/rsms-inter-fonts/"
MINT = (80, 206, 150); PAPER = (250, 248, 243); BG = (20, 18, 16); SUB = (150, 142, 130)


def f(n, s):
    return ImageFont.truetype(FD + n, s)


def ensure(p):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def wordmark(size, accent=MINT, cool=PAPER):
    b = f("InterDisplay-Black.ttf", size); l = f("InterDisplay-Light.ttf", size)
    tmp = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    w1 = tmp.textbbox((0, 0), "coolbx", font=b)[2]; gap = int(size * 0.30)
    w2 = tmp.textbbox((0, 0), "os", font=l)[2]
    W = w1 + gap + w2; H = int(size * 1.4)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.text((0, 0), "coolbx", font=b, fill=cool)
    d.text((w1 + gap, 0), "os", font=l, fill=accent)
    return img.crop(img.getbbox())


# Plymouth: logo + pulserende dot
logo = wordmark(120)
logo.save(ensure(f"{SF}/usr/share/plymouth/themes/coolbx/logo.png"))
dot = Image.new("RGBA", (28, 28), (0, 0, 0, 0))
ImageDraw.Draw(dot).ellipse([0, 0, 27, 27], fill=MINT)
dot.save(ensure(f"{SF}/usr/share/plymouth/themes/coolbx/dot.png"))

# GRUB-achtergrond 1920x1080: vlak #141210 + enkel de wordmark bovenaan
gb = Image.new("RGB", (1920, 1080), BG)
wm = wordmark(76)
gb.paste(wm, (1920 // 2 - wm.width // 2, 150), wm)
gb.save(ensure(f"{SF}/usr/share/grub/themes/coolbx/background.png"))
# Geen spinner/terminal-box meer: het zwarte laad-vlak is opgelost door in theme.txt
# géén terminal-box te definiëren (transparante terminal, Pop!_OS-aanpak).

# GNOME "Over"-logo (os-release LOGO=coolbx-logo): in LICHTE modus toont GNOME dit
# op een paper-achtergrond → "coolbx" in INK (anders onzichtbaar). Vierkant canvas
# voor de icon-theme-lookup; GNOME schaalt op hoogte.
about = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
awm = wordmark(48, cool=BG)            # ink "coolbx" + mint "os"
awm.thumbnail((224, 224))
about.paste(awm, (128 - awm.width // 2, 128 - awm.height // 2), awm)
about.save(ensure(f"{SF}/usr/share/icons/hicolor/256x256/apps/coolbx-logo.png"))

# Witte wordmark (paper "coolbx" + mint "os") voor DONKERE achtergronden:
# GDM-greeter + de donkere-modus 'Over'-pagina (vervangt het Fedora-asset).
white_wm = wordmark(120, cool=PAPER)   # PNG, brede wordmark
white_wm.save(ensure(f"{SF}/usr/share/coolbx/branding/coolbx-wordmark-white.png"))
# vierkant-canvas variant (256²) voor icon-theme-namen die de shell/greeter vragen
sq = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
w2 = white_wm.copy(); w2.thumbnail((224, 224))
sq.paste(w2, (128 - w2.width // 2, 128 - w2.height // 2), w2)
sq.save(ensure(f"{SF}/usr/share/coolbx/branding/coolbx-logo-white.png"))
# GNOME 'Over' zoekt in DONKERE modus naar de icoon-variant <LOGO>-dark
# (= coolbx-logo-dark). os-release LOGO_DARK is géén standaard → dit is de juiste weg.
sq.save(ensure(f"{SF}/usr/share/icons/hicolor/256x256/apps/coolbx-logo-dark.png"))
# SVG met ingebedde PNG (om Fedora's SVG-logo-assets te vervangen, formaat-veilig)
import base64
b64 = base64.b64encode(open(f"{SF}/usr/share/coolbx/branding/coolbx-wordmark-white.png", "rb").read()).decode()
svg = ('<?xml version="1.0" encoding="UTF-8"?>\n'
       f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
       f'width="{white_wm.width}" height="{white_wm.height}" viewBox="0 0 {white_wm.width} {white_wm.height}">\n'
       f'  <image width="{white_wm.width}" height="{white_wm.height}" xlink:href="data:image/png;base64,{b64}"/>\n'
       '</svg>\n')
open(ensure(f"{SF}/usr/share/coolbx/branding/coolbx-wordmark-white.svg"), "w").write(svg)


def embed_svg(png_path, w, h):
    b = base64.b64encode(open(png_path, "rb").read()).decode()
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{w}" height="{h}" viewBox="0 0 {w} {h}">\n'
            f'  <image width="{w}" height="{h}" xlink:href="data:image/png;base64,{b}"/>\n</svg>\n')


# Ink wordmark (paper-achtergrond / LICHTE modus) — PNG + SVG, om Fedora's
# "lightbackground"-logo te vervangen (de blauwe/donkere variant).
ink_wm = wordmark(120, cool=BG)
ink_png = f"{SF}/usr/share/coolbx/branding/coolbx-wordmark-ink.png"
ink_wm.save(ensure(ink_png))
open(ensure(f"{SF}/usr/share/coolbx/branding/coolbx-wordmark-ink.svg"), "w").write(
    embed_svg(ink_png, ink_wm.width, ink_wm.height))

# Wallpaper (optie C): vlak #141210 + subtiele wordmark net onder het midden.
# 4K-bron zodat GNOME's zoom naar elke resolutie schaalt; gecentreerd-horizontaal
# + binnen de centrale veilige zone zodat geen enkel crop hem wegsnijdt.
WPW, WPH = 3840, 2160
wp = Image.new("RGB", (WPW, WPH), BG)
mark = wordmark(220)
a = mark.split()[3].point(lambda p: int(p * 0.12))
mark.putalpha(a)
wp.paste(mark, (WPW // 2 - mark.width // 2, int(WPH * 0.72) - mark.height // 2), mark)
wp.save(ensure(f"{SF}/usr/share/backgrounds/coolbx/coolbx-dark.png"))

# GDM/login-achtergrond (zelfde vlak, met subtiele wordmark onderaan)
gdm = Image.new("RGB", (1920, 1080), BG)
wm2 = wordmark(48)
gdm.paste(wm2, (1920 // 2 - wm2.width // 2, 1080 - 140), wm2)
gdm.save(ensure(f"{SF}/usr/share/backgrounds/coolbx/coolbx-login.png"))

print("branding-assets gegenereerd in", SF)
