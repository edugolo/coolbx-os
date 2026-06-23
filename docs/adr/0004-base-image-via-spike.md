# ADR-0004: Base-image — fedora-bootc (voorkeursrichting via spike S1; hardware-gate openstaand)

- **Status:** Aanvaard — **voorkeursrichting**; hardware-validatie is een **openstaande gate vóór pilot**.
- **Datum:** 2026-06-23
- **Beslissers:** Johan, Claude
- (Vervangt de eerdere "Voorgesteld"-versie.)

## Context
"Zo clean mogelijk" pleit voor kaal `quay.io/fedora/fedora-bootc`; `ghcr.io/ublue-os/base-main` levert
hardware/firmware batteries-included maar koppelt aan Universal Blue. Beslist via een spike: beide bouwen + in VM booten.

## Beslissing
**`quay.io/fedora/fedora-bootc:43`** als base — als **voorkeursrichting**, met `ublue-os/base-main` als gevalideerde fallback.

Spike-bewijs (S1, machine-leesbaar in een qemu-direct VM):

| | fedora-bootc | ublue base-main |
|---|---|---|
| build (`bootc container lint`) | 10/10 (11/11 na /var-cleanup) | 10/10 |
| boot → GNOME (nl_BE, autologin, SSH) | ✅ | ✅ |
| image-grootte | **3.86 GB** | 7.22 GB |
| **finale image mét firmware** (`linux-firmware` + `alsa-sof-firmware`) | **3.85 GB** | — |

> De firmware-laag bleek vrijwel **gratis** (zat al grotendeels in de fedora-bootc-base): finale image 3.85 GB,
> ~ongewijzigd. De size-vergelijking met ublue (7.22 GB) houdt dus stand mét firmware.

## Wat S1 NIET kon testen — hardware-gate vóór pilot
Een qemu-VM presenteert virtio/geïdealiseerde devices → het **énige reële base-onderscheid (hardware) is niet gemeten**:
- echte wifi/GPU/audio-DSP/touchpad/NVMe op heterogene schoollaptops; Secure Boot / shim-keten;
- suspend/resume, lid-switch, batterij/thermal; GPU-accelerated rendering (sway draait in VM op llvmpipe);
- updates/rollback op het bootc-pad (S4).

`linux-firmware` + `alsa-sof-firmware` dekken firmware-blobs + audio-DSP, **niet** out-of-tree drivers/akmods.
**Echte hardware-validatie op ≥2 representatieve schoollaptops is een gate vóór pilot.** Faalt fedora-bootc daar
(wifi/gpu/audio/suspend) → **ublue base-main** als fallback (die brengt akmods/codecs/extra enablement mee).

## Gevolgen
Lean (~half zo groot), clean, standalone ([ADR-0012](0012-standalone-os-focus-optioneel.md)). De `bootc lint`-score
is hygiëne (beide 10/10), niet hardware-bewijs. De definitieve base-bevestiging gebeurt op echte hardware (gate), niet in de VM.

## Alternatieven
- ublue base-main: pragmatisch (akmods/firmware/codecs) maar ~2× zo groot + UB-koppeling → gevalideerde fallback.
- BlueBuild: verworpen (zie [ADR-0003](0003-fedora-bootc-fundament.md)).
