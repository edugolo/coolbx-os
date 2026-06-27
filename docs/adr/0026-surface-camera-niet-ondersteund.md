# ADR-0026: Surface-camera (IPU3) niet ondersteund — vereist linux-surface-kernel

- **Status:** Aanvaard (richting)
- **Datum:** 2026-06-27
- **Beslissers:** Johan, Claude
- **Bron:** code-onderzoek `github.com/linux-surface` (kernel-patches + afwezige userspace-code) + live test op Surface Go 2.

## Context
De pilotvloot bevat ~25 **Microsoft Surface Go 2**'s (Windows-vervanging). Alles werkt op de stock
fedora-bootc-kernel — wifi, touchpad ([ADR-0019](0019-secure-boot-geen-custom-modules.md)-conform via
`usbcore.quirks`), audio, scherm — **behalve de camera's** (Intel IPU3: ov5693/ov8865/ov7251).

We hebben de camera grondig onderzocht en live getest:
- **Kernel-kant lijkt OK:** `ipu3-cio2` meldt "Connected 3 cameras", IPU3+sensor-modules laden,
  `/dev/media*`/`/dev/video*` + tps68470-stroomchip aanwezig.
- **Maar `libcamera` (0.5.2) vindt NUL camera's**, óók als root. Beide media-devices worden
  geënumereerd en de IPU3-pipeline-handler is geladen, maar produceert geen camera → `"Skip
  ipu3-csi2: no device node"`, slechts 2 v4l-subdevs. De sensor-subdevs *probe-en* niet volledig.

**Code-onderzoek bij linux-surface** wees de oorzaak ondubbelzinnig aan: de hele organisatie levert
**nul userspace-/libcamera-bestanden** (geen fork, geen tuning-YAML's, geen scripts) — ze draaien
**kale upstream-libcamera**. Alle camera-enablement zit **100% in hun kernel-patch**
(`patches/6.x/0013-cameras.patch`): ACPI-`_DEP`-enumeratievertraging tot de INT3472/tps68470-PMIC
klaar is, INT3472-I2C-daisy-chain, een dw9719-probe-delay specifiek voor de Go 2, en IPU3-IOMMU-
passthrough. Dit zijn **in-tree kernelwijzigingen** (geen ladbare modules → geen akmods), nog **niet
in mainline**. Zonder die glue probe-en de sensoren niet → libcamera ziet niets. Het is dus een
**kernel-probe-probleem, geen userspace-gat**: er valt niets te kopiëren (tuning raakt alleen
beeldkwaliteit, niet enumeratie).

> De linux-surface-**wiki** (noot 26) suggereert "werkt op mainline ≥6.14 zonder Surface-kernel", maar
> de **code + de live test** weerleggen dat. De wiki was te optimistisch.

## Beslissing
**Coolbx OS ondersteunt de Surface-IPU3-camera NIET.** De enige werkende route is de
**linux-surface-kernel** (of die patches zelf bouwen) — d.w.z. een **eigen kernel**, wat we bewust
níét doen ([ADR-0019](0019-secure-boot-geen-custom-modules.md)). De afweging:

- **Kosten van een eigen kernel:** Secure Boot vereist dan **MOK-enrollment per toestel** (fysieke
  firmware-prompt, niet FOG-kloonbaar → schaalt niet) óf Secure Boot uit (verlies van fysieke
  hardening); **kernel-onderhoudslast** (zelf herbouwen per Fedora-update + CVE, óf afhankelijk van de
  linux-surface-COPR-cadans); botst met **één-universele-image** (Surface-kernel op álle toestellen,
  of een apart image-variant met dubbel onderhoud); zwakker "het is gewoon gesigneerde Fedora"-verhaal.
- **Baat:** enkel de camera op de Surface-subset. **Niet examen-kritisch** — proctoring leunt op het
  sessie-signaal (`session=kiosk`, [ADR-0024](0024-attest-hmac-implementatie.md)), niet op camera.

Brede, structurele kosten vs. smalle baat → de camera rechtvaardigt geen eigen kernel.

## Gevolgen
- **Scope: dit raakt enkel de Surface-IPU3-camera.** De generieke `libcamera`/pipewire-camerastack
  BLIJFT in de basis — die is geen Surface-ding maar algemene modernisering: nieuwere laptops (2021+)
  met Intel **IPU6**-MIPI-camera's vereisen libcamera (en IPU6 werkt wél op de stock kernel), UVC-
  webcams werken sowieso, en het is de Fedora/ublue-richting. Alleen de **oude IPU3** van de Go 2 mist
  de kernel-probe-glue.
- "Surface-camera werkt niet" is een **gedocumenteerde, bewuste beperking** met de reden hierboven —
  voor de directie te kaderen als beveiligingsafweging (alles werkt, behalve de camera).
- **Heropenbaar** zodra (a) de camera-probe-glue mainline wordt (dan werkt het vanzelf op de stock
  kernel + libcamera), of (b) de "geen eigen kernel"-beslissing om andere redenen herzien wordt.

## Alternatieven
- **linux-surface-kernel draaien** — verworpen: botst met ADR-0019 (Secure Boot zonder MOK + FOG) en
  voegt kernel-onderhoud + image-complexiteit toe voor enkel de camera.
- **libcamera-tuning-bestanden toevoegen** — verworpen: lost niets op; het probleem is enumeratie
  (kernel-probe), niet beeldkwaliteit (tuning). linux-surface heeft die bestanden zelf niet eens.
- **Apart Surface-image op de surface-kernel** — als optie benoemd voor als de Surfaces zwaarder gaan
  wegen; nu niet gekozen wegens dubbel onderhoud + de Secure-Boot-afweging.
