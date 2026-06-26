#!/usr/bin/env python3
"""Betrouwbare GUI-automation in de dev-VM via AT-SPI/dogtail (resolutie-onafhankelijk,
géén pixels). Draait ON the VM (in de grafische sessie); wordt door de Justfile-recepten
via SSH aangeroepen met de juiste sessie-env.

Acties:
  apps                         — lijst draaiende AT-SPI-apps
  launch <appcmd...>           — start een GUI-app (zet XDG_CURRENT_DESKTOP=GNOME)
  dump <app>                   — toon de widget-boom (rol + naam) van een app
  find <app> <tekst>           — toon widgets waarvan de naam <tekst> bevat
  click <app> <naam>           — klik de widget met die naam (button/label/row…)
  type <app> <naam> <tekst>    — vul tekst in het veld met die naam
  read <app> <rol>             — lees alle namen van widgets met die rol (bv. label)

Vereist (op de VM): python3-dogtail, gnome-ponytail-daemon, a11y aan
(`gsettings set org.gnome.desktop.interface toolkit-accessibility true`).
"""
import os
import sys
import subprocess
import time


def _env():
    os.environ.setdefault("XDG_CURRENT_DESKTOP", "GNOME")
    os.environ.setdefault("XDG_RUNTIME_DIR", "/run/user/1000")
    os.environ.setdefault("WAYLAND_DISPLAY", "wayland-0")
    os.environ.setdefault("DBUS_SESSION_BUS_ADDRESS", "unix:path=/run/user/1000/bus")


def _root():
    from dogtail import tree
    from dogtail.config import config
    config.searchCutoffCount = 8
    config.actionDelay = 0.4
    config.logDebugToFile = False
    config.logDebugToStdOut = False
    return tree.root


def _app(name):
    return _root().application(name)


def main():
    _env()
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    cmd = sys.argv[1]
    a = sys.argv[2:]

    if cmd == "launch":
        subprocess.Popen(["setsid"] + a, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
                         start_new_session=True)
        time.sleep(4)
        print("launched:", " ".join(a))
        return 0

    if cmd == "apps":
        print([x.name for x in _root().applications()])
        return 0

    app = _app(a[0])

    if cmd == "dump":
        def walk(node, depth=0):
            if depth > 12:
                return
            nm = (node.name or "")[:40]
            print("  " * depth + f"[{node.roleName}] {nm}")
            for c in node.children:
                walk(c, depth + 1)
        walk(app)
        return 0

    if cmd == "find":
        needle = a[1].lower()
        for n in app.findChildren(lambda x: x.name and needle in x.name.lower()):
            print(f"[{n.roleName}] {n.name!r}")
        return 0

    if cmd == "read":
        role = a[1]
        names = [n.name for n in app.findChildren(lambda x: x.roleName == role) if n.name]
        print(names)
        return 0

    if cmd == "click":
        target = a[1]
        # prefereer een klikbare rol (button/row/...) boven een naamgelijke label
        actionable = ("push button", "button", "list item", "table cell",
                      "toggle button", "radio button", "check box", "menu item")
        cands = app.findChildren(lambda x: x.name == target)
        node = next((c for c in cands if c.roleName in actionable), None) or \
               (cands[0] if cands else app.child(name=target))
        # AdwActionRow e.d. reageren op 'activate', niet op een synthetische klik.
        for how in ("activate", "click", "return"):
            try:
                if how == "activate":
                    node.doActionNamed("activate")
                elif how == "click":
                    node.click()
                else:
                    node.grabFocus(); node.keyCombo("<Return>")
                print(f"clicked: {target!r} [{node.roleName}] via {how}")
                return 0
            except Exception:
                continue
        print(f"FAIL klikken: {target!r}")
        return 1

    if cmd == "type":
        target, text = a[1], a[2]
        node = app.child(name=target)
        node.click()
        node.typeText(text)
        print(f"typed into {target!r}: {text}")
        return 0

    print("onbekende actie:", cmd)
    return 2


if __name__ == "__main__":
    sys.exit(main())
