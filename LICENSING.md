# Licensing status

The [November 21, 2026 review](docs/licensing-review.md) distinguishes publishing
this source tree from distributing standalone packager executables. The
maintainer has chosen to defer unresolved upstream-permission questions and
retain identified third-party notices. This records that decision; it does
not establish permission where no applicable license has been identified.

Known license texts are collected under `licenses/`, and the melonDS patches
have scoped GPL attribution and modification dates in [patches/README.md](patches/README.md).
Packager builds and automated release ZIPs include the collected texts.
The original notice-only refresh is retained locally under
`artifacts/packager-with-notices/` for historical reference.

## Source publication

- **GBARunner3:** no general license was found at our pinned revision or in the
  current upstream tree reviewed. Our patches include upstream code/context.
  Clarify publication and redistribution permission; excluding `vendor/` alone
  does not resolve this. Existing upstream licensing issues remain unanswered
  on the pages reviewed.
- **Original project code:** no license selected. MIT is proposed for independent
  original material we have rights to license, with explicit third-party scope
  exceptions. No license is granted by this proposal.
- **melonDS patches:** upstream source and these modifications are
  GPL-3.0-or-later. Scoped attribution and modification-date notices accompany
  the patches, together with the full [GPL text](licenses/GPL-3.0.txt).
- **Diagnostic build templates:** copied devkitPro example files need applicable
  terms confirmed or replacement with independently authored build files.

## Binary distribution

**Correction to the earlier review:** current libtwl has a zlib license, added
in commit `81ad90ceca20be0bdaf5bbfab80b3ad796201510`. Our older pinned version
predates it. Confirm coverage of the old pin or deliberately migrate and retest.
See the [reference notice](licenses/libtwl-zlib.txt) and detailed review.

The executables also embed GBARunner3 code/artwork and other linked components.
Collected notices now cover libnds, TLSF, mini-printf, ArduinoJson, FatFs,
SD/MMC and identified host-library license texts. The full dependency audit
remains incomplete for linked toolchain runtime code, exact native-library
coverage and applicable Microsoft runtime conditions. Known source obligations
and remaining items are listed in the review. PyInstaller's bootloader exception
does not remove separate dependency obligations.

The original local preview ZIPs remain unchanged. Current builds collect the
known notices alongside the executable and provenance report. Remaining audit
gaps are documented rather than marked complete.

## Scope and next steps

- [Detailed evidence and resolution plan](docs/licensing-review.md)
- [Unsent upstream permission request](docs/upstream-permission-request.md)
- [Collected reference license texts](licenses/README.md)
- [Existing packager notices](release/packager/THIRD_PARTY_NOTICES.txt)
- [Release checklist](docs/releasing.md)

ROMs, BIOS files, extracted graphics, generated game-containing NDS files,
saves and memory dumps remain local inputs/outputs. Third-party license files
do not license Nintendo game data. Repository visibility itself does not grant
rights to upstream material, and this project assigns no blanket license to it.
