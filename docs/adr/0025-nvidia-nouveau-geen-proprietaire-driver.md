# ADR-0025: nvidia — nouveau + firmware, géén proprietaire driver

- **Status:** Aanvaard (richting)
- **Datum:** 2026-06-26
- **Beslissers:** Johan, Claude
- **Bron:** ublue-os-onderzoek (Bazzite's akmods/nvidia-pijplijn) + hardware-firmware-werk (zie ROADMAP §Fase 4 / `build_files/01-packages.sh`).

## Context
Bij het breed-werkend maken van de image op willekeurige schoollaptops kwam de nvidia-vraag op. **Bazzite** — een
gaming-distro — levert de **proprietaire nvidia-driver** mee, gebouwd als out-of-tree kernelmodule via de
`ublue-os/akmods`-pijplijn (kernel-gematchte, gesigneerde `kmod-nvidia` + versionlock). Dat is precies waar Bazzite
voor gemaakt is: 3D-performance, CUDA, DLSS.

Twee dingen worden vaak verward:
- **`nvidia-gpu-firmware`** — firmware-blobs (o.a. GSP) voor de **open** in-kernel driver `nouveau`. Puur firmware.
- **De proprietaire driver** (`kmod-nvidia`) — een **out-of-tree kernelmodule**.

## Beslissing
**Coolbx OS levert `nvidia-gpu-firmware` (voor nouveau) maar NIET de proprietaire nvidia-driver.**

- We draaien een **Chromium-examenkiosk**: we hebben **beeld** nodig, geen GPU-rekenkracht (geen gaming/CUDA).
- `nouveau` + de GSP-firmware geeft werkend beeld op nvidia-laptops, ruim voldoende voor een Wayland/sway-kiosk.
- Schoollaptops met nvidia zijn bijna altijd **hybride** (Intel/AMD-iGPU stuurt het paneel, de dGPU ligt stil) → nvidia
  raakt meestal niet eens het kritieke pad.

De doorslaggevende reden is consistentie met **[ADR-0019](0019-secure-boot-geen-custom-modules.md)**: de proprietaire
nvidia-kmod is een **out-of-tree module**. Die meeleveren zou óf Secure Boot breken, óf een **MOK-enrollment per toestel**
vereisen (fysiek/interactief, firmware-prompt) — wat **niet schaalt in de FOG-massauitrol**. Bazzite accepteert die prijs
voor performance; voor een examenkiosk is hij onnodig en onwenselijk.

## Gevolgen
- **Eén universele image** blijft geldig (zie ROADMAP §Fase 4, firmware-set): nvidia-laptops booten op nouveau zonder
  per-toestel-stappen. Geen akmods-build-complexiteit, geen versionlock-breuk bij kernel-updates, geen Secure-Boot-gedoe.
- `nvidia-gpu-firmware` zit in de expliciete firmware-lijst (`build_files/01-packages.sh`), naast amd/intel-gpu-firmware.
- **Als** een specifieke nvidia-only laptop ooit echt slecht presteert op nouveau: dat is een **gerichte uitzondering**
  (eventueel akmods + MOK-enroll, conform de ADR-0019-kostenafweging) — geen vlootbrede default.

## Alternatieven
- **Proprietaire nvidia via akmods (Bazzite-aanpak)** — verworpen: out-of-tree module → botst met ADR-0019 (Secure Boot
  zonder MOK), onnodige akmods-complexiteit, geen performancebehoefte voor een Chromium-kiosk.
- **Helemaal géén nvidia-firmware** — verworpen: dan geen (versneld) beeld op nvidia-hardware; de firmware is goedkoop
  en hoort bij de "boot op elk toestel"-doelstelling.
