#!/usr/bin/env bash
# Coolbx OS — greenboot required health-check (Fase 5). Bij N gefaalde boots rolt bootc/ostree
# automatisch terug naar de vorige deployment. LOKAAL ONLY: we checken nooit focus-api-bereik —
# een externe outage zou anders de hele vloot doen terugrollen (ADR-0017, roadmap §Updates).
set -uo pipefail

fail=0
chk() { if eval "$2" >/dev/null 2>&1; then echo "OK   $1"; else echo "FAIL $1"; fail=1; fi; }

# De grafische laag + de bouwstenen die de kiosk-sessie nodig heeft om te KUNNEN starten.
chk "gdm actief"                 'systemctl is-active --quiet gdm'
chk "chromium aanwezig"          'command -v chromium-browser || command -v chromium'
chk "kiosk-launcher aanwezig"    'test -x /usr/bin/coolbx-kiosk-start'
chk "sway aanwezig"              'command -v sway'
chk "Focus-policy aanwezig"      'test -f /etc/chromium/policies/managed/coolbx-managed.json'
chk "geen kritieke failed units" 'test "$(systemctl --failed --no-legend --plain | wc -l)" -lt 3'

[ "$fail" -eq 0 ] && echo "coolbx-kiosk-health: GROEN" || echo "coolbx-kiosk-health: ROOD"
exit "$fail"
