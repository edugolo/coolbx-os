"""Laag D — OCR-locate + QMP-klik (pixels als laatste redmiddel).

Bewijst de volledige laag-D-keten tegen de LIVE kiosk: screendump → tesseract → pixelbox.
Vereist de OCR-container (`just ocr-build`). Slaat over als die ontbreekt.
"""
import subprocess

import pytest

W, H = 1280, 800  # dev-VM is op deze resolutie gepind


def _ocr_available():
    p = subprocess.run(
        ["sudo", "podman", "image", "exists", "localhost/coolbx-ocr"],
        capture_output=True,
    )
    return p.returncode == 0


pytestmark = pytest.mark.skipif(
    not _ocr_available(), reason="OCR-container ontbreekt (just ocr-build)"
)


def test_ocr_finds_kiosk_text(kiosk):
    # De kiosk staat op het actieve VT → screendump toont 'm. Zoek de placeholder-tekst.
    pos = kiosk.find_text("Toetsmodus")
    assert pos is not None, "OCR vond 'Toetsmodus' niet op het scherm"
    x, y = pos
    assert 0 <= x <= W and 0 <= y <= H, f"coördinaat buiten scherm: {pos}"


def test_ocr_finds_exit_button(kiosk):
    # De waybar 'Sessie afsluiten'-knop moet vindbaar zijn (frase over meerdere woorden).
    pos = kiosk.find_text("Sessie afsluiten")
    assert pos is not None, "OCR vond de 'Sessie afsluiten'-knop niet"
    x, y = pos
    # de knop zit rechtsboven in de waybar
    assert y < 80, f"exit-knop niet in de bovenbalk: {pos}"
