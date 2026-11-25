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

The `gbarunner3-*.patch` files modify GBARunner3 revision
`ecaa817815d9761745606592f04affe5ee9c3731`, by Gericom and contributors.
No general license for that revision was identified in the review. No license
is assigned to those upstream portions by this document. Their status is
recorded in [LICENSING.md](../LICENSING.md).

`gbarunner3-alttp-touch.patch` adds an optional calibrated touch mailbox for the
Zelda build. It uses the libnds touch API and caches calibration before
the runtime reuses firmware-settings memory for ROM data. It does not copy the
Zelda disassembly or game artwork into this repository. The map UI code is
relocated to privileged executable runtime RAM with a data-cache clean during
startup; the GBA instruction-cache policy remains unchanged.
Touch and backlight transactions now share an RTOS mutex, allowing the sound
thread to preempt SPI sampling. `runtime/alttp/arm7/ZeldaTouch.c` is a modified
libnds v1.8.3 driver, retaining its original notice; its read wrappers no longer
mask audio interrupts. This change is Zelda-specific.

`gbarunner3-audio-counters.patch` is an optional Zelda-only diagnostic that
counts ARM7 sound FIFO underruns. Normal builds do not apply it. Instrumentation
itself disrupted Fusion startup, so the builder rejects that combination.
See [display/audio timing](../docs/display-audio.md) for the control comparison
and the separate runtime fix, which uses the existing sound DMA path.

`gbarunner3-alttp-world-map.patch` connects the Zelda-only native perspective
handler to HBlank. It uses the game's scanline scale table for outdoor-map
BG2X/BG2Y/BG2PA updates and consumes that effect's guest interrupt to avoid doing
the same work twice. Other effects, DMA, audio and Fusion retain their existing
paths. See [Zelda inventory and maps](../docs/alttp-inventory.md) for validation
and the remaining hardware check.
