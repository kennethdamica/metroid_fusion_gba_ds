# Patch provenance and licensing

## melonDS interpreter and diagnostic patches

The following patches are distributed under **GNU GPL version 3 or later**,
consistent with the upstream files they modify. The full license is provided
in [GPL-3.0.txt](../licenses/GPL-3.0.txt).

| Patch | Upstream / attribution | Changes |
| --- | --- | --- |
| [melonds-arm9-data-abort.patch](melonds-arm9-data-abort.patch) | melonDS `16f127dbb587a73371827ce79689c5d237c4b59b`; Copyright 2016–2026 melonDS team | Modified by the Fusion DS project, November 19–21, 2026: ARM9 data-abort handling and ARM946 interworking behavior |
| [melonds-ds-shared-wram.patch](melonds-ds-shared-wram.patch) | melonDS DS `f394adbacb5722ee97c1b37c8064da9a25818310`; Copyright 2023 Jesse Talavera-Greenberg | Modified by the Fusion DS project, November 19, 2026: frontend-only physical shared-WRAM diagnostic mapping |

These modifications are not upstream releases. They are provided without any
warranty, including the implied warranties of merchantability or fitness for
a particular purpose; see the GPL for the full terms. Retain this attribution,
change description, license notice and license text when redistributing the
patches. Distribution of a compiled modified emulator also requires satisfying
the applicable corresponding-source obligations and dependency terms.

These emulator patches are separate from the NDS runtime embedded in the
standalone packager. Their GPL scope does not assign a blanket license to the
other independent files in this repository.

## GBARunner3 integration patches

The three `gbarunner3-*.patch` files modify GBARunner3 revision
`ecaa817815d9761745606592f04affe5ee9c3731`, by Gericom and contributors.
No general license for that revision was identified in the review. No license
is assigned to those upstream portions by this document. Their status is
recorded in [LICENSING.md](../LICENSING.md).
