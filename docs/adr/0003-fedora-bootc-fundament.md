# ADR-0003: Fedora bootc als OS-fundament

- **Status:** Aanvaard
- **Datum:** 2026-06-23
- **Beslissers:** Johan, Claude

## Context
We willen een immutable, image-gebaseerd, atomisch-updatebaar OS met OTA, signing en rollback — de "managed Chromebook"-ervaring.

## Beslissing
Bouw op **Fedora bootc** (containers/bootc, GA, wekelijkse releases). Podman-build vanuit een Containerfile,
bootc-image-builder voor disk-images, GHCR + cosign, bootc OTA-updates.

## Gevolgen
Immutable basis met atomische updates/rollback; sluit aan op de POC-toolchain. De *concrete* base-image (kaal
fedora-bootc vs Universal Blue) is een aparte keuze — zie [ADR-0004](0004-base-image-via-spike.md).

## Alternatieven
Klassiek mutable Fedora/Debian, of rpm-ostree zonder bootc — verworpen: minder image-native, bootc is de opvolgrichting.
