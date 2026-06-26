#!/usr/bin/env python3
"""OCR-locate voor de e2e-harness (laag D, ADR-0020).

Vindt de pixelpositie van zichtbare tekst in een VM-screenshot, zodat laag D
(QMP virtio-tablet) erop kan klikken — resolutie-onafhankelijk, geen gast-software,
geen fragiele needle-PNG's. tesseract draait in een podman-container (de sudo-constraint
staat enkel passwordless `podman` toe; `tesseract` is niet op de host geïnstalleerd).

Subcommando's:
  find <png> <tekst>     — print {"x":..,"y":..,"w":..,"h":..,"conf":..} van het midden
                           van (de eerste regel die) <tekst> bevat; exit !=0 als niet gevonden.
  dump <png>             — print alle herkende woorden + boxes (debug).

Env: COOLBX_OCR_IMAGE (default localhost/coolbx-ocr), COOLBX_OCR_LANG (default nld+eng).
"""
import json
import os
import shlex
import subprocess
import sys

OCR_IMAGE = os.environ.get("COOLBX_OCR_IMAGE", "localhost/coolbx-ocr")
OCR_LANG = os.environ.get("COOLBX_OCR_LANG", "nld+eng")

# Preprocessing-varianten (schaal, tesseract-PSM, ImageMagick-ops). Meerdere passes vangen
# wat één mist: PSM 11 (sparse) leest verspreide UI-labels; PSM 3 (auto-layout) leest
# knoppen/tekstblokken die sparse mist (bv. de mint-knop); upscalen helpt kleine tekst;
# negate vangt randgevallen. Boxen van opgeschaalde varianten worden terug-geschaald.
VARIANTS = [
    (1, 11, []),  # origineel, sparse → verspreide labels (waybar, losse teksten)
    (2, 3, ["-colorspace", "Gray", "-normalize", "-resize", "200%"]),  # auto-layout → knoppen/blokken
    (3, 12, ["-colorspace", "Gray", "-negate", "-normalize", "-resize", "300%", "-sharpen", "0x1"]),
]


def _tsv_one(png_data, psm, ops):
    """convert (ImageMagick) preprocessing → tesseract, beide in de container via een pipe.
    Tolerant: een falende variant geeft '' i.p.v. een exception."""
    inner = (
        "convert - " + " ".join(shlex.quote(o) for o in ops) + " png:- | "
        f"tesseract - - --psm {int(psm)} -l {shlex.quote(OCR_LANG)} tsv"
    )
    p = subprocess.run(
        ["sudo", "podman", "run", "--rm", "-i", OCR_IMAGE, "sh", "-c", inner],
        input=png_data, capture_output=True, timeout=90,
    )
    if p.returncode != 0:
        sys.stderr.write(p.stderr.decode("utf-8", "replace"))
        return ""
    return p.stdout.decode("utf-8", "replace")


def _words_all(png_path):
    """Verzamel woorden over alle preprocessing-varianten (coords terug-geschaald)."""
    with open(png_path, "rb") as f:
        data = f.read()
    out = []
    for vi, (scale, psm, ops) in enumerate(VARIANTS):
        for w in _words(_tsv_one(data, psm, ops)):
            # Regel-key uniek per variant maken: anders mergen woorden van verschillende
            # varianten met dezelfde (block,par,line) tot één (te brede) frase-box.
            w["line"] = (vi,) + tuple(w["line"])
            if scale != 1:
                for k in ("x", "y", "w", "h"):
                    w[k] = round(w[k] / scale)
            out.append(w)
    return out


def _words(tsv):
    """Parse TSV → lijst van {text,x,y,w,h,conf,line-key}."""
    lines = tsv.splitlines()
    if not lines:
        return []
    header = lines[0].split("\t")
    idx = {k: i for i, k in enumerate(header)}
    out = []
    for ln in lines[1:]:
        c = ln.split("\t")
        if len(c) < len(header):
            continue
        text = c[idx["text"]].strip()
        try:
            conf = float(c[idx["conf"]])
        except ValueError:
            conf = -1
        if not text or conf < 0:
            continue
        left, top = int(c[idx["left"]]), int(c[idx["top"]])
        w, h = int(c[idx["width"]]), int(c[idx["height"]])
        key = (c[idx["block_num"]], c[idx["par_num"]], c[idx["line_num"]])
        out.append({"text": text, "x": left, "y": top, "w": w, "h": h,
                    "conf": conf, "line": key})
    return out


def _find(words, needle):
    """Zoek <needle> (case-insensitive). Eerst per-woord-substring; anders aaneengesloten
    woorden op één regel die samen de zoekterm bevatten → gecombineerde box."""
    nl = needle.lower()
    # 1) los woord / substring
    for w in words:
        if nl in w["text"].lower():
            return _center(w)
    # 2) frase over opeenvolgende woorden op dezelfde regel — kies de KLEINSTE span die
    #    de zoekterm bevat (anders merget de box met buurtekst → verkeerd klikpunt).
    by_line = {}
    for w in words:
        by_line.setdefault(w["line"], []).append(w)
    for line_words in by_line.values():
        lw = sorted(line_words, key=lambda w: w["x"])
        for i in range(len(lw)):
            acc = ""
            for j in range(i, len(lw)):
                acc = (acc + " " + lw[j]["text"]).strip().lower()
                if nl in acc:
                    span = lw[i:j + 1]
                    x1 = min(w["x"] for w in span)
                    y1 = min(w["y"] for w in span)
                    x2 = max(w["x"] + w["w"] for w in span)
                    y2 = max(w["y"] + w["h"] for w in span)
                    box = {"x": x1, "y": y1, "w": x2 - x1, "h": y2 - y1,
                           "conf": min(w["conf"] for w in span)}
                    return _center(box)
    return None


def _center(box):
    return {"x": box["x"] + box["w"] // 2, "y": box["y"] + box["h"] // 2,
            "w": box["w"], "h": box["h"], "conf": round(box["conf"], 1)}


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    cmd, png = sys.argv[1], sys.argv[2]
    words = _words_all(png)
    if cmd == "dump":
        for w in words:
            print(f'{w["conf"]:5.1f}  ({w["x"]:4d},{w["y"]:4d})  {w["text"]!r}')
        return 0
    if cmd == "find":
        if len(sys.argv) < 4:
            print("find vereist een zoektekst", file=sys.stderr)
            return 2
        hit = _find(words, sys.argv[3])
        if not hit:
            print(f"niet gevonden: {sys.argv[3]!r}", file=sys.stderr)
            return 1
        print(json.dumps(hit))
        return 0
    print(f"onbekend commando: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
