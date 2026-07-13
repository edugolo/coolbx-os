# Bijdragen aan Coolbx — licentie & Developer Certificate of Origin

**Versie 1.0 · 2026-07-13 · geldt voor alle Coolbx-repositories (coolbx-focus, coolbx-os, coolbx-ansible)**

## Kort samengevat

- Alle Coolbx-software is gelicentieerd onder de **GNU Affero General Public License v3.0 (AGPL-3.0)**.
- Door bij te dragen ga je ermee akkoord dat jouw bijdrage **onder diezelfde AGPL-3.0** wordt
  uitgebracht. Je **behoudt zelf het auteursrecht** op je bijdrage — je draagt niets over aan de vzw.
- We vragen géén ondertekende copyright-assignment-CLA. In de plaats gebruiken we het
  **Developer Certificate of Origin (DCO)**: je bevestigt per commit, met een `Signed-off-by`-regel,
  dat je het recht hebt om je bijdrage onder deze licentie in te dienen.

## Waarom DCO in plaats van een copyright-assignment-CLA?

Dit is een bewuste keuze:

1. **Community-vriendelijk en licht.** Geen juridisch document ondertekenen en opsturen vóór je
   eerste pull request; één regel in je commit-message volstaat. Dezelfde aanpak als o.a. de
   Linux-kernel en GitLab (voor community-bijdragen).
2. **De vzw hoeft geen copyright te verzamelen.** Coolbx heeft besloten dat *alles* open is onder
   AGPL-3.0, zonder `ee/`-split en zonder dual-licensing-verdienmodel. Een vzw die geen proprietary
   herlicentiëring plant, heeft geen reden om auteursrechten van bijdragers te centraliseren — en
   het níet vragen ervan is een geloofwaardigheidssignaal: de open belofte kan niet stilletjes
   worden teruggedraaid.
3. **De eerlijke trade-off, expliciet benoemd:** doordat elke contributor auteursrecht op zijn
   eigen bijdrage behoudt, kan het project **later alleen van licentie veranderen met instemming
   van alle betrokken contributors** (of door hun code te vervangen). Dat maakt her-licentiëren
   praktisch zeer moeilijk. Wij zien dat niet als een risico maar als een **feature**: het verankert
   de AGPL-3.0-belofte structureel, ook tegen een toekomstig bestuur van de vzw in.

## Wat je bevestigt: het Developer Certificate of Origin

Met de `Signed-off-by`-regel in je commit bevestig je het **Developer Certificate of Origin 1.1**
(zie de originele Engelse tekst hieronder — die is juridisch leidend). In gewone taal bevestig je
dat één van deze situaties geldt:

- **(a)** je hebt de bijdrage zelf geschreven en mag ze onder de open-source-licentie van dit
  project (AGPL-3.0) indienen; of
- **(b)** je bijdrage bouwt op bestaand werk dat onder een geschikte open-source-licentie valt,
  en die licentie staat je toe het (al dan niet gewijzigd) onder AGPL-3.0 in te dienen; of
- **(c)** iemand anders die (a) of (b) bevestigde heeft je de bijdrage bezorgd en jij hebt ze
  niet gewijzigd;
- **(d)** en je begrijpt dat het project en je bijdrage publiek zijn, en dat je bijdrage —
  inclusief je sign-off — blijvend bewaard en herverdeeld wordt, in lijn met de projectlicentie.

Let daarbij in het bijzonder op:
- **Werkgever:** als je bijdraagt in het kader van je job (bv. als ICT-medewerker van een school
  of bedrijf), zorg dat je werkgever daarmee instemt — check je arbeidscontract.
- **Code van derden / AI-gegenereerde code:** dien niets in waarvan je de herkomst of licentie
  niet kunt verantwoorden.

### Developer Certificate of Origin 1.1 (originele tekst, juridisch leidend)

```
Developer Certificate of Origin
Version 1.1

Copyright (C) 2004, 2006 The Linux Foundation and its contributors.

Everyone is permitted to copy and distribute verbatim copies of this
license document, but changing it is not allowed.


Developer's Certificate of Origin 1.1

By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I
    have the right to submit it under the open source license
    indicated in the file; or

(b) The contribution is based upon previous work that, to the best
    of my knowledge, is covered under an appropriate open source
    license and I have the right under that license to submit that
    work with modifications, whether created in whole or in part
    by me, under the same open source license (unless I am
    permitted to submit under a different license), as indicated
    in the file; or

(c) The contribution was provided directly to me by some other
    person who certified (a), (b) or (c) and I have not modified
    it.

(d) I understand and agree that this project and the contribution
    are public and that a record of the contribution (including all
    personal information I submit with it, including my sign-off) is
    maintained indefinitely and may be redistributed consistent with
    this project or the open source license(s) involved.
```

## Praktisch: zo signeer je je commits

Voeg aan elke commit een sign-off-regel toe met je echte naam en een werkend e-mailadres:

```
Signed-off-by: Voornaam Achternaam <jij@example.be>
```

Dat hoeft niet met de hand:

```bash
# per commit
git commit -s -m "fix: beschrijving van je wijziging"

# vergeten? voeg toe aan je laatste commit
git commit --amend -s --no-edit

# voor een reeks commits op je branch (rebase met sign-off)
git rebase --signoff main
```

Stel eenmalig je identiteit in als dat nog niet gebeurd is:

```bash
git config --global user.name  "Voornaam Achternaam"
git config --global user.email "jij@example.be"
```

**Richtlijnen:**
- Gebruik je **echte naam** (geen pseudoniem) — het DCO is een verklaring, die moet herleidbaar zijn.
- Elke commit in een pull request moet gesigneerd zijn; de CI controleert dit (DCO-check) en een
  PR met niet-gesigneerde commits wordt niet gemerged tot dat rechtgezet is (zie `git rebase --signoff`).
- Een sign-off is géén `GPG`-handtekening (`-S`); cryptografisch signeren mag extra, maar vereist
  is alleen de `-s`-sign-off-regel.

## Licentie van niet-code-bijdragen

Documentatie in de repositories valt onder dezelfde AGPL-3.0, tenzij een map of bestand expliciet
anders vermeldt. (Gedeelde *lesinhoud* in de latere community-bibliotheek krijgt een eigen
content-licentie — zie het ontwerp daarvoor in `governance/design/`.)

## Vragen

Twijfel je of je iets mag bijdragen (werkgever, herkomst, licentie van een dependency)? Open een
issue of contacteer de maintainers vóór je de code indient — dat voorkomt werk dat we niet kunnen
aanvaarden.
