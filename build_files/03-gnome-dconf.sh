#!/usr/bin/env bash
set -ouex pipefail

# Compileer GSettings-schemas/overrides (coolbx-defaults komen later via system_files).
if command -v glib-compile-schemas >/dev/null 2>&1; then
  glib-compile-schemas /usr/share/glib-2.0/schemas || true
fi