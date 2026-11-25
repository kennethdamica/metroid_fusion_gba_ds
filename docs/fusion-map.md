# Fusion live map adapter

The adapter renders Fusion's own exploration map on the lower DS screen. It uses original 8×8 map tiles, walls, hatches and station/item symbols, with a 32×20-cell viewport that follows Samus vertically. Gold marks the visible cells in the current room; white marks Samus's current map cell. Gray, pink and green retain Fusion's unexplored, visited and hidden-room colors. Undownloaded/unvisited cells stay hidden as in the game. This is a geographic map of the current area, not the former numeric room grid.

The map remains visible during menus and transitions, but live highlighting and IDs are removed (`WAIT`). Before the first valid gameplay state it stays blank. The reader supports Main Deck and sectors 1–6, with named sector labels and a loaded-area guard. Automated sector coverage uses controlled warps after normal gameplay begins; it is not a full-game playthrough.

## Verified data sources

Only the verified US revision is supported: SHA-1 `ca33f4348c2c05dd330d37b97e2c5a69531dfe87`. Definitions were checked against [metroidret/mf at 8614cc3](https://github.com/metroidret/mf/tree/8614cc3eec194092cd756d6382c879b4c2ab4967): `database.json`, `linker.ld`, `src/minimap.c`, `src/menus/pause_screen_map.c`, and the room/background structures. The renderer is independently implemented; graphics and palette are read from the user's original local ROM, not committed as assets.

| Address/offset | Meaning |
| --- | --- |
| ROM `0x561FA8`, `0x3800` bytes | 448 original 4bpp map tiles |
| ROM `0x5657A8`, `0x60` bytes | Three map palette banks |
| RAM `0x02034000` | Current 32×32 map, filtered for exploration and collected items |
| RAM `0x02034800` | Unfiltered current-area map for room connectivity |
| RAM `0x0300002C/2D` | Area and room IDs |
| RAM `0x03001242` | Active demo state (zero during normal play) |
| RAM `0x03000031/32` | Samus's map cell |
| RAM `0x030000B2/B3` | Current room's map origin |
| RAM `0x030000A0/A2` | Clipdata width/height, including two blocks of padding on each edge |

Room extents derive from clipdata dimensions (15 blocks per map column, 10 per row). The highlight flood-fills from Samus through interior ink on touching tile edges, respecting horizontal/vertical tile flips and the room's bounds. Walls and hatches stop it, preventing a rectangular highlight from filling adjacent rooms inside an irregular room's bounds. It recomputes when the area/room changes, after a menu, or when Samus enters another connected component. Only already visible map cells are recolored.

## DS resources and update budget

Engine A renders the GBA scene into a capture in VRAM D. The top screen displays
VRAM C, containing the previous captured frame cropped to 240×160 and centered
at (8,16). All surrounding pixels remain black. This preserves GBA windows,
sprites, affine transforms and blending without borrowing guest graphics
resources, and adds one frame of presentation latency. It fixes the exposed
right/bottom graphics from the earlier direct-display implementation.

During VBlank, an ARM block-transfer loop copies 160 rows of 120 words from D
to C. It uses no DMA channel. Engine A's display-register translation retains
VRAM-display mode across guest mode changes; its rendering/capture continues
normally. This follows the [DS capture/display separation documented in GBATEK](https://mgba-emu.github.io/gbatek/#ds-video-capture-and-main-memory-display-mode).

Engine B renders the bottom map using 32 KiB VRAM H: original tiles at
`0x06200000`, font at `0x06204000`, world tilemap at `0x06206000`, labels at
`0x06206800`. The BIOS moves to executable VRAM I (`0x068A0000`); the 32 KiB ROM
cache lookup table moves to runtime main RAM. Neither overlaps the map or
capture buffers. The diagnostic build leaves 36 KiB of heap, 248 bytes at the
end of ITCM and roughly 0.5 KiB at the end of VRAM A. The display-register
handler is outside the linker's fixed early ITCM slot. Display code remains
ARM throughout to preserve CP15.L4 compatibility.

Map tiles/palettes load once from the user's ROM before guest execution. The
map IRQ allocates nothing and performs no SD access. Every eighth VBlank
checks state and only refreshes on a relevant change. A stationary map returns
immediately. Menus retain the previous valid map without a live highlight.
During area transitions, the adapter waits until the game's loaded-map area
(`gPreviousArea`, `0x03000B86`) matches the current area. Labels name Main Deck,
SRX, TRO, PYR, AQA, ARC and NOC. All areas use the game's exploration/item
buffers, preserving discovery, collected icons and late-game map changes.

## Reproduce

```sh
.venv/bin/python tools/build_dual_screen.py --hardware-diagnostics
.venv/bin/python tools/package_fusion.py \
  --rom 'Metroid Fusion (USA).gba' --bios gba_bios.zip \
  --output artifacts/my-map-package/Fusion.nds
.venv/bin/python tools/test_packaged_fusion.py \
  --package artifacts/my-map-package/Fusion.nds --output artifacts/my-map-test
.venv/bin/python tools/play_fusion.py --package artifacts/my-map-package/Fusion.nds
```

Package/output paths must be new. The original ROM, BIOS, package payload format, extracted-data paths and save identity are unchanged. Expected map screenshots are reconstructed independently from guest RAM and the original ROM graphics, with explicit room-cell fixtures for rooms 00 and 03 rather than reimplementing the runtime flood fill. Main Deck room 00 occupies `(19,13)` and `(20,13)`; room 03 occupies `(17,13)` and `(18,13)`.

The former `0x0300001F` demo guard was sticky after an attract-mode demo. The adapter now reads active demo state at `0x03001242`, matching the game’s input/demo handler. This permits loaded saves and normal play after a demo while still excluding attract-mode gameplay.

## Current validation

The subsequent sound update services pending audio refills during the top-screen
copy and map work. See [display/audio timing](display-audio.md) for the candidate
build and its validation. The hardware-confirmed package below is preserved.

Hardware Test 5 (`artifacts/hardware-test-5/Fusion.nds`) and the canonical
`artifacts/packages/Fusion.nds` are identical: SHA-256
`245d9b92dffb48f854a9e2bd0f466c03b3f217c4f540950a5a284a6d12fd8505`,
8,743,424 bytes. The runtime remains compatible with the existing extracted
files and save path. The maintainer reported the ARM fix and subsequent framing
and map update working on their 3DS/DSpico setup. Broader hardware coverage and
full-game playtesting remain open.

- `artifacts/screen-framing-dev/test2/first-boot/result.json`: 87/87, including
  exact maps, native-size black borders, movement/room change/jump and
  2,000/2,000 stationary guest frames.
- `artifacts/screen-framing-dev/test2/result.json`: 27/27 extraction, repeat
  launch, save preservation, recovery and malformed-package rejection.
- `artifacts/screen-framing-dev/sectors-verified/result.json`: 35/35 for Main
  Deck and all six sectors. Evidence is the matching run under `sectors/run`.
- Seven packaging unit tests pass.
- The rebuilt native patched app was checked at 60/60 fps: BIOS/title/file
  selection, briefing, gameplay, pause retaining the map without a live
  highlight, and resume restoring it. All displayed a stable centered frame.
- Follow-up packaging tests found the standard non-diagnostic template stalls
  at guest frame 1. Its earlier 1,200-frame border smoke test was insufficient
  to establish gameplay. Use the pinned Hardware Test 5 template; see
  [the packager guide](packager-cli.md).

Sector coverage uses isolated emulator-only memory writes to request real
room transitions after the scripted new game reaches normal gameplay. It
sets test health and map-download flags, then lets Fusion load the room,
backgrounds, exploration buffers and fade-in itself. No test writes exist in
the shipped runtime, and the user's actual save is never used. This is not a
full-game playthrough. Fixtures explicitly exclude the ARC room-00 cutout
and the neighboring NOC recharge room inside room 00's bounding box.

```sh
.venv/bin/python tools/test_fusion_sectors.py \
  --package artifacts/packages/Fusion.nds --output artifacts/my-sector-test
```

The earlier demo/save-load regression is documented under
`artifacts/map-resume-verified`; it tested the previous display path. Its test
script remains available as `tools/test_fusion_map_resume.py`.

## Hardware interworking correction

The display module now compiles as ARM code, matching the GBARunner runtime.
CP15.L4 is enabled for GBA-compatible load-to-PC semantics, so ARMv5-style
ARM/Thumb return interworking is unavailable. The previous Thumb compilation
worked only because the older emulator ignored L4. Startup JSON-parser and
save-signature constants also move to main RAM to make room for the ARM code.
Current memory bounds and test evidence appear above. The original interworking
reproduction is recorded in [hardware-debug.md](hardware-debug.md).
