#!/usr/bin/env python3
"""CDP-client voor de Coolbx OS e2e-harness (laag C uit ADR-0020).

Spreekt het Chrome DevTools Protocol tegen een Chromium die met
`--remote-debugging-port=9222` draait in de dev-VM, bereikt via een SSH
local-forward (`-L 9222:localhost:9222`). Leest ECHTE browserstaat (geen pixels):
page-titel/DOM, `chrome://policy`, en `chrome.storage.managed` van de
force-installed Focus-extensie via diens service-worker-target.

Draait OP DE HOST (niet in de gast). Vereist alleen `websocket-client` (stdlib + urllib
voor discovery). Verzin geen waarden — faalt luid als een target/sessie ontbreekt.

Subcommando's:
  targets                  — lijst alle CDP-targets (page + service_worker + ...)
  title                    — page-titel van de eerste page-target
  eval <js>                — evalueer JS in de eerste page-target (returnByValue)
  managed [ext-id]         — lees chrome.storage.managed.get(null) via de extensie-SW
  policy                   — dump de toegepaste policies (chrome://policy → listPolicies JSON)
  wait-page [timeout]      — wacht tot er een page-target met een niet-lege URL is

Env:
  CDP_HOST (default 127.0.0.1), CDP_PORT (default 9222), CDP_TIMEOUT (default 10s)
  FOCUS_EXT_ID (default makdakigkdbicdljgdclgnejachcohag — het integratiecontract)
"""
import json
import os
import sys
import time
import urllib.request
from urllib.parse import urlsplit

import websocket  # websocket-client (sync)

HOST = os.environ.get("CDP_HOST", "127.0.0.1")
PORT = int(os.environ.get("CDP_PORT", "9222"))
TIMEOUT = float(os.environ.get("CDP_TIMEOUT", "10"))
EXT_ID = os.environ.get("FOCUS_EXT_ID", "makdakigkdbicdljgdclgnejachcohag")


def _http_json(path):
    url = f"http://{HOST}:{PORT}{path}"
    # Host-header = localhost slaagt voor Chrome's Host-check; via de SSH-tunnel
    # resolvet 127.0.0.1 op de VM naar Chromium's loopback-listener.
    req = urllib.request.Request(url, headers={"Host": "localhost"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.load(r)


def _ws_url(raw):
    """Herbouw de ws-URL met HOST:PORT. Chromium zet de Host uit onze HTTP-Host-header
    (= 'localhost', poortloos) in webSocketDebuggerUrl → 'ws://localhost/devtools/...'
    zonder poort → websocket-client zou naar :80 gaan. We nemen alleen het pad over."""
    path = urlsplit(raw).path
    return f"ws://{HOST}:{PORT}{path}"


class CDP:
    """Browser-level CDP-verbinding; attacht flat op elk target (sessionId)."""

    def __init__(self):
        ver = _http_json("/json/version")
        self.ws = websocket.create_connection(
            _ws_url(ver["webSocketDebuggerUrl"]),
            timeout=TIMEOUT,
            # Origin moet in de --remote-allow-origins-allowlist zitten (Chrome 111+).
            header=[f"Origin: http://{HOST}:{PORT}"],
            suppress_origin=True,
        )
        self._id = 0

    def send(self, method, params=None, session_id=None):
        self._id += 1
        mid = self._id
        msg = {"id": mid, "method": method, "params": params or {}}
        if session_id:
            msg["sessionId"] = session_id
        self.ws.send(json.dumps(msg))
        deadline = time.time() + TIMEOUT
        while time.time() < deadline:
            self.ws.settimeout(max(0.1, deadline - time.time()))
            raw = self.ws.recv()
            if not raw:
                continue
            data = json.loads(raw)
            if data.get("id") == mid:  # negeer protocol-events
                if "error" in data:
                    raise RuntimeError(f"{method}: {data['error']}")
                return data.get("result", {})
        raise TimeoutError(f"geen antwoord op {method} binnen {TIMEOUT}s")

    def targets(self):
        return self.send("Target.getTargets")["targetInfos"]

    def attach(self, target_id):
        return self.send(
            "Target.attachToTarget", {"targetId": target_id, "flatten": True}
        )["sessionId"]

    def evaluate(self, expression, session_id, await_promise=False):
        res = self.send(
            "Runtime.evaluate",
            {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": await_promise,
            },
            session_id=session_id,
        )
        if res.get("exceptionDetails"):
            raise RuntimeError(json.dumps(res["exceptionDetails"]))
        return res["result"].get("value")

    def first_page(self):
        pages = [t for t in self.targets() if t["type"] == "page"]
        if not pages:
            raise RuntimeError("geen page-target gevonden")
        # Prefereer de echte content-page (de kiosk-URL) boven de instabiele extensie-eigen
        # pagina's: de force-installed Focus-extensie opent in kioskMode z'n chrome-extension://
        # index.html, die zichzelf sluit/herlaadt → 'Session not found' als we die pakken.
        stable = [
            t for t in pages
            if not t.get("url", "").startswith(("chrome-extension://", "devtools://",
                                                "chrome://"))
        ]
        return (stable or pages)[0]

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass


def cmd_targets(_):
    for t in CDP().targets():
        print(f'[{t["type"]:>14}] {t.get("url", "")[:80]}')
    return 0


def cmd_title(_):
    c = CDP()
    page = c.first_page()
    sid = c.attach(page["targetId"])
    print(c.evaluate("document.title", sid))
    return 0


def cmd_eval(args):
    # JS via arg, of via stdin als arg ontbreekt of '-' is (omzeilt shell-quoting).
    expr = sys.stdin.read() if not args or args[0] == "-" else args[0]
    c = CDP()
    sid = c.attach(c.first_page()["targetId"])
    print(json.dumps(c.evaluate(expr, sid, await_promise=True)))
    return 0


_MANAGED_EXPR = (
    "new Promise((res, rej) => chrome.storage.managed.get(null, items => {"
    " const e = chrome.runtime.lastError; e ? rej(new Error(e.message)) : res(items); }))"
)


def cmd_managed(args):
    """Lees chrome.storage.managed van de extensie. Robuust tegen de slapende MV3-SW:
    open een VERS extensie-page-target (privileged context) en lees daarin, alles in
    één CDP-verbinding (geen gat waarin de SW/page weer kan inslapen)."""
    ext = args[0] if args else EXT_ID
    c = CDP()
    # Vers extensie-eigen page-target openen (chrome.storage werkt in elke extensie-context).
    tid = c.send("Target.createTarget",
                 {"url": f"chrome-extension://{ext}/index.html"}).get("targetId")
    if not tid:
        print(f"FAIL: kon geen extensie-target openen voor {ext} (geïnstalleerd?)",
              file=sys.stderr)
        return 3
    try:
        sid = c.attach(tid)
        # korte poll: wacht tot de extensie-context geladen is en chrome.storage bestaat
        deadline = time.time() + 8
        last = None
        while time.time() < deadline:
            try:
                ready = c.evaluate("typeof chrome !== 'undefined' && !!chrome.storage", sid)
                if ready:
                    print(json.dumps(c.evaluate(_MANAGED_EXPR, sid, await_promise=True)))
                    return 0
            except RuntimeError as e:
                last = e  # context nog niet klaar / target wisselt — opnieuw
            time.sleep(0.5)
        print(f"FAIL: extensie-context niet klaar binnen 8s ({last})", file=sys.stderr)
        return 3
    finally:
        try:
            c.send("Target.closeTarget", {"targetId": tid})
        except Exception:
            pass


def cmd_policy(_):
    c = CDP()
    # Eigen VERSE chrome://policy-tab (los van de — soms instabiele — kiosk-page).
    tid = c.send("Target.createTarget", {"url": "chrome://policy"}).get("targetId")
    sid = c.attach(tid)
    try:
        # Versie-robuust: moderne chrome://policy heeft geen cr.sendWithPromise meer.
        # Elke <policy-row> draagt z'n data als JS-property `.policy`; we piercen door alle
        # shadow-roots en lezen die rechtstreeks — inclusief de 3rdparty-EXTENSIEpolicies
        # (serverUrl/kioskMode, met isExtension:true). Filter op enkel de gezette rijen.
        expr = (
            "(() => { const out = []; const walk = r => {"
            " r.querySelectorAll('*').forEach(el => {"
            "  if (el.tagName === 'POLICY-ROW' && el.policy &&"
            "      (el.policy.value !== undefined || el.policy.status || el.policy.level))"
            "    out.push(el.policy);"
            "  if (el.shadowRoot) walk(el.shadowRoot); }); };"
            " walk(document); return out; })()"
        )
        # POLL tot de Lit-componenten gerenderd zijn (vaste sleep was flaky → soms leeg).
        pols = []
        deadline = time.time() + 12
        while time.time() < deadline:
            try:
                pols = c.evaluate(expr, sid, await_promise=False) or []
            except RuntimeError:
                pols = []
            if pols:
                break
            time.sleep(0.5)
        print(json.dumps(pols, indent=2))
    finally:
        try:
            c.send("Target.closeTarget", {"targetId": tid})
        except Exception:
            pass
    print(f"# {len(pols)} gezette policy/policies", file=sys.stderr)
    return 0


def cmd_fill(args):
    """Vul een invoerveld (CSS-selector) met een waarde — React/Vue-proof via de native
    value-setter + input/change-events. Het robuuste 'fill'-paradigma (à la Playwright)."""
    if len(args) < 2:
        print("fill vereist <selector> <waarde>", file=sys.stderr)
        return 2
    selector, value = args[0], args[1]
    c = CDP()
    sid = c.attach(c.first_page()["targetId"])
    js = (
        "(() => { const el = document.querySelector(%s);"
        " if (!el) return {ok:false, err:'selector niet gevonden'};"
        " el.focus();"
        " const proto = el instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;"
        " const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;"
        " setter.call(el, %s);"
        " el.dispatchEvent(new Event('input', {bubbles:true}));"
        " el.dispatchEvent(new Event('change', {bubbles:true}));"
        " return {ok:true, value: el.value}; })()"
    ) % (json.dumps(selector), json.dumps(value))
    print(json.dumps(c.evaluate(js, sid)))
    return 0


def cmd_cdptype(args):
    """Typ tekst in het gefocuste element via Input.insertText (alsof getypt)."""
    if not args:
        print("type vereist tekst", file=sys.stderr)
        return 2
    c = CDP()
    sid = c.attach(c.first_page()["targetId"])
    c.send("Input.insertText", {"text": args[0]}, session_id=sid)
    print("ok")
    return 0


def cmd_wait_page(args):
    timeout = float(args[0]) if args else 30.0
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            pages = [
                t
                for t in CDP().targets()
                if t["type"] == "page" and t.get("url")
            ]
            if pages:
                print(f'page klaar: {pages[0]["url"][:80]}')
                return 0
        except Exception:
            pass
        time.sleep(1)
    print(f"FAIL: geen page-target binnen {timeout}s", file=sys.stderr)
    return 1


CMDS = {
    "targets": cmd_targets,
    "title": cmd_title,
    "eval": cmd_eval,
    "managed": cmd_managed,
    "policy": cmd_policy,
    "fill": cmd_fill,
    "type": cmd_cdptype,
    "wait-page": cmd_wait_page,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in CMDS:
        print(__doc__)
        return 2
    try:
        return CMDS[sys.argv[1]](sys.argv[2:])
    except (ConnectionRefusedError, urllib.error.URLError) as e:
        print(
            f"FAIL: geen CDP-endpoint op {HOST}:{PORT} ({e}). "
            "Draait Chromium met --remote-debugging-port en staat de SSH-tunnel "
            "(`just vm-cdp-tunnel`) open?",
            file=sys.stderr,
        )
        return 4


if __name__ == "__main__":
    sys.exit(main())
