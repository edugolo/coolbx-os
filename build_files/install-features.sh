#!/usr/bin/env bash
set -ouex pipefail

# Modulair feature-mechanisme (ADR-0012). FEATURES = spatie-gescheiden lijst.
# Een Containerfile kan niet loopen → dit script doet het in bash.
FEATURES="${1:-${FEATURES:-}}"
FEATURES_DIR="/ctx/features"

for feat in $FEATURES; do
  fdir="${FEATURES_DIR}/${feat}"
  if [[ ! -d "$fdir" ]]; then
    echo "WARN: feature '${feat}' niet gevonden in ${FEATURES_DIR}" >&2
    continue
  fi
  echo "== feature: ${feat} =="
  # Self-contained: kopieer eventuele system_files en draai install.sh.
  if [[ -d "${fdir}/system_files" ]]; then
    cp -r "${fdir}/system_files/." /
  fi
  if [[ -f "${fdir}/install.sh" ]]; then
    bash "${fdir}/install.sh"
  fi
done