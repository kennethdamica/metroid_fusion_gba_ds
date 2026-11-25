# A Link to the Past: touch inventory and maps

Implemented prototype, 2026-11-22. The top screen runs the GBA game; the bottom
screen shows a native DS inventory and maps. Tap an owned item to equip it while moving,
then use the game's normal item button. This is one running game, with the DS
interface reading and updating its state. Four Swords is outside this adapter.

The original-art inventory candidate is generated locally at
`artifacts/alttp-native-ui-v2/Zelda.nds`. The previous transition sound-fix build
is preserved at `artifacts/alttp-transition-audio-v2/Zelda.nds`.
The initial inventory prototype is at `artifacts/alttp-candidate/Zelda.nds`.
The first audio fix is preserved at `artifacts/alttp-audio-candidate/Zelda.nds`. The confirmed buffered-display build
is preserved at `artifacts/alttp-flicker-candidate/Zelda.nds`, and the earlier map
build at `artifacts/alttp-maps-candidate/Zelda.nds`.
Copy it to the flashcart SD card as `Zelda.nds`. The user-supplied game and BIOS
are bundled inside, extracted on first launch, and reused on later launches.
The user confirmed the interface, maps and flicker fix on hardware. The original-art
inventory update needs a fresh hardware check; emulator results do not establish
hardware audio quality. See [display/audio timing](display-audio.md).

## Build, package and play

Complete the pinned-toolchain and emulator setup in [Development](development.md)
first. From the repository root:

```sh
.venv/bin/python tools/build_dual_screen.py --game alttp --package-template
.venv/bin/python tools/package_alttp.py \
  --rom '/path/to/your/zelda.gba' --bios '/path/to/your/bios.bin' \
  --output artifacts/alttp-native-ui-v2/Zelda.nds
.venv/bin/python tools/play_alttp.py --package artifacts/alttp-native-ui-v2/Zelda.nds
```

The BIOS argument also accepts the same BIOS ZIP input as the Fusion packager.
Output must be new; the packager refuses to overwrite an existing NDS. Select a
new output path for a subsequent build, and pass it to the launcher with
`--package`. The launcher uses the existing verified patched desktop build and
creates a separate `artifacts/melonds-alttp/` app, SD card and configuration.
Quit that app before rebuilding or replacing its SD-card contents.

Desktop controls: arrow keys move, **X** is GBA A (use equipped item), **Z** is B,
**Backspace** is Select (original inventory), **Enter** is Start (save menu),
**Q/W** are L/R. Click an owned item on the lower screen to equip it. **F** toggles
fast-forward and **P** pauses. A new game initially has no selectable items.

The Zelda packager is currently a Python developer command. The existing frozen
Mac/Windows Fusion executables remain Fusion-only; this work does not silently
change their supported ROM or released runtime.

Supported input is the 8 MiB US GBA release, game code `AZLE`, revision 0:

```text
SHA-1:   a272055abbbf6c26b0cd54c87395d01699589161
SHA-256: f328f8f07d736288a00c80d31cc1630f3aa02aaf20efdcba73d31dae832b5d76
```

Packaging enforces this exact ROM identity. The separate Zelda template and
`ZELPKG01` container signature prevent accidental use of a Fusion template.
The extractor stores files at:

```text
_alttp/a272055abbbf6c26b0cd54c87395d01699589161/v1/rom.gba
_alttp/a272055abbbf6c26b0cd54c87395d01699589161/v1/bios.bin
_alttp/a272055abbbf6c26b0cd54c87395d01699589161/v1/config.json
_alttp/a272055abbbf6c26b0cd54c87395d01699589161/rom.sav
```

The game's separate 8 KiB save is outside the versioned extraction directory.
Fusion's `_fusion/` data and saves are unchanged.

## Display and touch implementation

[The Zelda overlay](../runtime/alttp/FusionScreen.size.cpp) reuses the established
centered 240×160 top-screen capture path. The integration functions retain their
`fusionScreen*` names, but the Zelda build substitutes its own implementation.
The bottom screen uses the original 240×160 inventory layout at its native pixel
size, beneath the DS tab strip. [ZeldaInventory.h](../runtime/alttp/ZeldaInventory.h)
loads the game's original frame tilemap, English menu graphics, item names and
equipment descriptors from the supplied ROM. It draws the original item grid,
green selection brackets, selected item/name, abilities, equipment, pendants or
crystals, and heart-piece or dungeon-item widgets. The inventory's 24-pixel item
spacing replaces the former 40-pixel DS card spacing; touch targets follow it.
The map tab and floor controls remain available, including while the game's own
pause menu is open. Equipping still requires safe live gameplay.

Before a single-player game is loaded, the bottom screen is black and ignores
all touches. A held touch from the title/file screens is consumed, so it cannot
activate a control when gameplay starts. Returning to the outer game menus hides
and resets the interface again. During ordinary dialogue or pause menus, the
loaded inventory stays visible; unsafe item changes are rejected.

Menu assets are decoded once at startup into a 16,260-byte runtime RAM cache.
HUD/icon pixels and palettes come from the running game. All artwork remains
local to the user-supplied ROM; none is embedded in public source. Display interrupts perform no allocation or filesystem access. The
map cache occupies 20,206 bytes in the unused 32 KiB tail of VRAM D. The
256×192 capture must not be enlarged into that region. A temporary 4 KiB heap
buffer is freed before gameplay. Display code executes in privileged runtime
RAM with explicit data-cache publication; guest permissions and instruction-cache
policy remain unchanged. Word-sized map flags are required because VRAM ignores
byte stores.

The renderer composes a complete 32 KiB lower-screen image in the unused tail
of VRAM C (`0x06858000`) and stages its palette at `0x0687F000`, beyond D's map
cache. Visible VRAM H is never cleared or drawn into during composition. At the
next early VBlank an ITCM block-copy routine publishes the image, palette and
background mode together, before copying the top screen. A late interrupt keeps
the previous complete image. DMA remains available to guest emulation. This adds
one display frame of presentation latency without allocating another RAM buffer.
Neither C nor D's 256×192 framebuffer/capture area may extend into these tails.

The earlier inventory redraw spilled into visible scanout, producing a damaged
frame every fourth frame in the emulator reproduction. Consecutive-frame tests
now cover the inventory and both kinds of map; single screenshots did not expose
that defect. `gZeldaVideoDebug` records publish/defer counts, start/end scanlines,
overruns, maximum publication duration, and composition timing. Its address is
listed in the runtime link map and can be passed to the test runner with
`--video-debug-address` to check the publication window.

[The ARM7 patch](../patches/gbarunner3-alttp-touch.patch) samples calibrated touch
once per frame and publishes an aligned atomic 32-bit packet with coordinates,
press state and sequence number. ARM9 polls without waiting on IPC. A press
produces one request; holding or dragging does not repeatedly equip. Invalid or
unsafe requests are discarded rather than queued for later.

Calibration must be initialized immediately after `readUserSettings()` on ARM7,
before ARM9 reuses that firmware-settings RAM for its ROM cache. Initializing
it later produced incorrect coordinates in melonDS. The corrected diagnostic
reads a requested `(68,48)` touch as `(68,48)`. SPI access is serialized with an
RTOS mutex shared by touch sampling and the backlight service. The project's
modified libnds touch driver leaves audio interrupts enabled during sampling;
see [display/audio timing](display-audio.md). Both the outer application IRQ
mask and the driver's full-read critical section had to be removed.

## Map controls and coverage

Tap **MAP** or **INVENTORY** in the top row of the bottom screen. Gameplay keeps
running. Map controls never write to the game's equipment or progress fields.

- Outside, the map follows the Light World or Dark World and marks Link's position.
  Ordinary houses show the last outside position; after an indoor cold boot the
  position appears once Link goes outside.
- Inside a main dungeon, the display selects its layout and current floor, colors
  the current room gold, and shows visited rooms. Finding the dungeon map reveals
  its other rooms.
- Tap **UP** or **DOWN** to inspect another floor. **FOLLOW LINK** returns to the
  current floor. A dungeon/floor transition resumes following automatically.

Both world maps use the original ROM artwork, cropped to the playable central
region and sampled to 128×128. Dungeon rooms use original room shapes, arranged
in their original floor layouts, with a DS-specific palette. The 14 main dungeon
layouts (including Sewers and Hyrule Castle) contain 59 floors. The Four Swords
bonus dungeon is not supported. Room exploration is shown at room granularity;
individual quadrants, chests, boss markers and compass indicators are not yet
reproduced. No dungeon artwork is redrawn while its room/exploration state is
unchanged; Link's small marker updates separately.

[ZeldaMap.h](../runtime/alttp/ZeldaMap.h) reads and decodes map assets once during
startup. These are private reads from the supplied game; no map assets are
committed to the repository.

## Verified game state

Research used the matching GBA-specific
[reference checksum and disassembly](https://github.com/camthesaxman/zeldaalttp/tree/d3802f5bc354e4e70309bb5f6c606e8c4b731317).
These are GBA guest addresses, not SNES addresses. Live tests checked selection,
HUD state, movement and subsequent item actions:

| Address | Use |
| --- | --- |
| `0x02002320`–`0x02002337` | 24 inventory entries; quantities, upgrades and bottle contents are not Boolean flags |
| `0x03002C7E` | Selected inventory slot, one-based; high byte at `0x03002C7F` is cleared when equipping |
| `0x030039BC` | Equipped item type consumed by the item dispatcher |
| `0x030039BD` | In-use item latch; left to the game to update |
| `0x0200B1F8`, `0x0200B1FA`, `0x0200B238`, `0x0200B23A` | Four selected-item HUD tile words |
| `0x03002BDE` | Game's HUD upload flag |
| `0x03006D10` | Main game state; adapter requires single-player state 13 |
| `0x03002BDC`, `0x03002BDD` | Game module/submodule; adapter requires normal indoor/overworld state |
| `0x03002CE2`, `0x03002C0E`, `0x03002C0A` | Dungeon identity, signed floor and current room |
| `0x030038F4`, `0x030038F0`, `0x03002BF6` | Link position and overworld identity |
| `0x02002000`, `0x02002348` | Visited room flags and owned dungeon maps |
| ROM `0x16B62C`, `0x16B5A8` | Slot-to-type mapping and icon descriptor pointer table |

The earlier candidate `0x03003D12` is not the live equipped-item field and is
not written by this implementation.

Equipping updates slot, type and HUD together while the guest is stopped in the
runtime IRQ. Ownership and variant are checked again before writing. The
adapter checks normal gameplay, menu state, item-use/effect state, action flags,
control lock and agreement between equipped and in-use types. It never grants
items or changes quantities/progression. The selected brackets follow game RAM.

## Repeatable tests and coverage

```sh
.venv/bin/python -m unittest discover -s tests/alttp -v
.venv/bin/python tools/test_alttp.py \
  --package artifacts/alttp-flicker-candidate/Zelda.nds \
  --maps --video-stability --output artifacts/alttp-display-verified
```

Use a new output directory each run. The integration suite uses the pinned
patched libretro melonDS core with JIT disabled, starts from a fresh SD card,
and performs a full boot. It creates a game file and tests:

- Three payloads extracted with hashes matching the bundle.
- Touch switching between boomerang and lamp, including while Link moves.
- Correct equipped slot, dispatcher type, game HUD and lower-screen highlight.
- Actual lamp use consuming magic and a boomerang projectile appearing/retiring.
- Empty-slot taps and taps in the original inventory being ignored.
- Item ownership remaining unchanged by equipping/using those two items.
- Switching to the original Light World map without changing the equipped item.
- With `--maps`, current-room highlights for all 14 main dungeon identities and
  actual touch input for floor up/down/follow controls.
- A separate save, second-launch payload reuse, byte-identical save preservation,
  and an unchanged source NDS.

The buffered-display candidate passed **67 assertions** in
`artifacts/alttp-flicker/verified-v1/result.json`, including all prior gameplay,
map and save checks. Its SHA-256 is `9a73e2d765799d27c313f8b0ee2f1c129c94fcdff380ed82caa6c82dcc2734b8`.
The old build showed a partial inventory redraw in 8 of 33 consecutive frames.
The fixed build produced one identical image across each stable test window:
33 inventory frames, 33 world-map frames and 14 dungeon-map frames. Publication
took at most 12 scanlines, with zero overruns; 16 late publications were deferred
while retaining the previous image. The supplied NDS is byte-identical to the
package used in that run. Real DS confirmation remains necessary.

To include timing assertions, add `--video-debug-address 0x0204CCCC` for this
build; verify the `gZeldaVideoDebug` symbol in the link map after changing the
runtime. Host renderer tests additionally guard the visible lower framebuffer,
its palette, and the top framebuffer against writes during composition.

The earlier map candidate passed all **62 integration assertions** in
`artifacts/alttp-maps-verified/result.json`: 21,960 frames on first launch and
1,200 on second launch. The delivered `artifacts/alttp-maps-candidate/Zelda.nds`
was used in that run, SHA-256
`b4cbfb0732814492452c897361cc017a7034161be4173927d4d5d20d6578383a`.
All six Zelda unit tests and the 23 package/public tests passed. The source and
local documentation-link audit also passed. The original inventory candidate
was preserved. These results cover emulation and the explicitly described RAM
fixtures; real hardware qualification of the new map UI remains outstanding.

The earlier inventory-only `artifacts/alttp-verified/result.json` run passed
all 25 assertions on the original candidate NDS (SHA-256
`161a0ed0d2fbb6a903ad712132e8ea0e3f84da05b135fa38aad4e4b0bf9f8e8b`).
It completed 21,400 gameplay-timeline frames on first launch and 1,200 on the
second. The five Zelda unit tests and 23 existing package/public checks also
passed. These local reports and screenshots are ignored build artifacts.

A separate native Mac desktop smoke test reached normal gameplay, acquired the
house chest's lamp through ordinary play, displayed it in the lower inventory,
and exercised the lamp after a bottom-screen click. The desktop profile is
isolated from Fusion and from the automated fixture. A second native desktop
smoke test of the redesigned interface switched between inventory and map during
play and walked from the house into the overworld; the position marker followed
Link and the application continued reporting 60/60 frames.

The fixture seeds boomerang/lamp ownership and magic **only in emulator RAM** to
avoid making the test depend on a long playthrough. Touch and subsequent item
use are real emulated inputs. Shipping packages contain no item-granting code.
The optional map fixture also changes dungeon/floor/room identity and map
ownership in isolated emulator RAM. It uses short idle scenes before the
intro's next timed dialogue, not a natural playthrough of those dungeons. The
shipping host renderer test separately decodes both worlds and all 59 floors,
checks map pixels against the ROM, and guards capture/cache/image boundaries.
This does not prove naturally acquiring every item or preserving later-game
quest progression. The second launch checks startup/save bytes, not a full
resume-and-play sequence. Savestate restoration is not used: a GBARunner3
restore experiment froze, so the suite uses full boots.

The generic harness accepts `touch: [x,y]` in bottom-screen DS pixels alongside
joypad buttons. Its unit checks cover coordinate conversion, bounds and
simultaneous pointer/joypad state. Full runs record frames, guest memory, package
markers and assertions in their output directory. Expected melonDS DLDI patching
and capacity padding are checked separately from payload/save integrity.

Remaining qualification: redesigned UI/map performance on 3DS/Pico; bottles and
upgraded items; all special item actions; dialogue, transitions, death, minigames
and long save/reload sessions. The guards are conservative, but these cases have
not all been exercised. The adapter is a playable prototype, not yet a Zelda
binary release with exhaustive compatibility coverage.

## Original-art inventory validation (earlier build)

`artifacts/alttp-native-ui-v2/Zelda.nds` has SHA-256
`b6d88b3772eed22496b194764671f8b9a44cb604f133b19e208a2e51790a3782`.
The prior audio/touch runtime remains unchanged. Copy this NDS to the flashcart
as `Zelda.nds`, keeping `_alttp` and its existing save.

The patched melonDS suite passed **82 checks** in
`artifacts/alttp-native-ui-v2-test/result.json`: 22,650 frames of gameplay,
real touch equipping, every main dungeon fixture, repeated/rapid map transitions,
blank startup, original-art comparison, extraction, and second-launch save reuse.
Inventory/world/dungeon stability windows each contained one identical image.
There were zero publication overruns; maximum publication was 13 scanlines and
maximum composition slice was 26. Startup touch attempts registered no UI actions;
the second-launch file screen also had a black bottom screen. Captured audio
refill-stack canaries were intact. These are emulator checks, not hardware audio
qualification.

The original-art comparison checks at least 99% pixel agreement, with a small
color tolerance, against the game's own inventory in the same run. The original
menu body is translated down eight pixels to accommodate the DS tab strip.
The original green selection brackets replace the prior gold-card assertion.
The first dungeon fixture opens the map before changing dungeon identity, allowing
its complete image to settle. No pause-menu restriction is imposed on read-only
map navigation; item equipping retains its original safety checks.

All **30 host tests** passed. The new sanitizer-backed inventory renderer test
checks 61 item/bottle variants, their original name tables, progression widgets,
and memory boundaries. Neither the tab graphics nor visible display memory is
used as temporary drawing space. Game assets are read from local ROM inputs.

Run the current full regression with a fresh output directory:

```sh
.venv/bin/python tools/test_alttp.py \
  --package artifacts/alttp-world-map-v2/Zelda.nds \
  --maps --video-stability --transitions --record-audio \
  --video-debug-address 0x02051E98 --render-debug-address 0x02051E78 \
  --output artifacts/my-native-ui-test
```

Addresses are specific to this build; resolve them from the link map after any
runtime changes. Hardware validation of the imported inventory and later-game
progression is still needed. Existing map artwork and supported dungeon coverage
remain as documented above.

## Outdoor map timing and quest markers

The outdoor map uses a perspective effect that writes BG2X, BG2Y and BG2PA
on each HBlank. The generic guest handler performs several trapped I/O accesses;
late writes can restart the affine background during visible scanout. The Zelda
build now handles this specific effect directly in the host HBlank IRQ, using
the game's active scale table and signed camera coordinates. It suppresses only
that effect's guest HBlank notification, retaining DMA and sound processing and
all other guest effects. Capture dimensions, centering and the audio mixer are
unchanged. The new hook is in `runtime/alttp/ZeldaWorldMap.s` and
`patches/gbarunner3-alttp-world-map.patch`.

The lower outdoor map includes the original objective X, pendant/crystal and
other story-objective sprites, plus the light-world return portal. Coordinates,
art and collection masks come from the user's ROM. Obtained pendants/crystals
are hidden; objectives follow the current quest stage and world. Markers use a
steady original frame instead of flashing, and the existing Link diamond stays
above them. This change does not add dungeon compass/boss markers or alternate
crystal-number animation. No game artwork is embedded in public source.

Marker sprites and tables occupy 2,548 additional bytes in the unused VRAM D
tail. Total map cache use is 22,754 bytes, below its 28 KiB bound and outside the
96 KiB capture. Marker rows are composed in bounded units and only invalidated
when their relevant state changes. The startup menu decoder now uses 2 KiB of
scratch instead of 8 KiB: the verified compressed layout/font consume only
362/1,583 bytes. This avoids exhausting the small remaining runtime heap as
code grows. Both decoders keep explicit input/output bounds.

The candidate is `artifacts/alttp-world-map-v2/Zelda.nds`. Keep `_alttp` when
replacing the NDS; its ROM identity, extraction format and save path are unchanged.
The play/test helpers now default to this candidate. Earlier packages remain in
their own artifact directories.

A separate full-boot test uses a **copy** of a house-start save, walks outdoors,
opens the original map, zooms out/in, scrolls and closes it. Its input sequence is
`tests/alttp/world-map-input.json`. The verifier compares rendered background
pixels to the ROM and the game's active scanline table, allowing small sprite
occlusions. Run it after capturing the frames named by `verify_perspective`:

```sh
.venv/bin/python tools/alttp_world_checks.py \
  --captures artifacts/alttp-world-map-v2-test \
  --rom "Legend of Zelda, The - A Link to the Past & Four Swords (USA).gba" \
  --debug-address 0x02051E70
```

The 11 map frames matched **99.43–99.94%** of predicted background pixels.
During the measured 900-frame map interval, 144,003 native scanline updates
completed with no additional crossed-scanline updates. Two were recorded during
entry, before this stable interval. Both zoom levels and returning to gameplay
passed. The severe hardware-only banding was not reproduced in melonDS, so the
3DS/Pico confirmation of this timing fix remains necessary.

The sanitizer-backed map test checks original marker pixels for all nine stages
in both worlds, collection masks, portal visibility, invalid stages and image
boundaries, alongside all 59 dungeon floors. Additional emulator marker captures
use `tests/alttp/world-marker-states.json` to seed quest/collection/world state in
isolated RAM; these are rendering tests, not a natural late-game playthrough.

The four additional marker captures (pendants present/collected, crystals
present/collected) matched the independent ROM oracle with **zero pixel
mismatches**, excluding Link's separate foreground diamond. Validate them with:

```sh
.venv/bin/python tools/alttp_world_checks.py --markers \
  --captures artifacts/alttp-world-markers-test \
  --rom "Legend of Zelda, The - A Link to the Past & Four Swords (USA).gba"
```

The full map regression now captures dense floors 32 frames after a touch rather
than 20, and gives the first sewer fixture 32 frames to settle. It also asserts
that composition has finished at those captures. The per-frame drawing budget
is unchanged; publishing an incomplete image to satisfy a capture deadline would
reintroduce tearing. Inventory/world/dungeon stability checks remain strict.

The final package has SHA-256 `196c0d149964b4da34b821aa99269d9b82df4ba92a07087622f92544ceb30b70`. The final
full-boot suite passed **88 checks**, including extraction, touch equipping,
all dungeon fixtures, strict frame stability and second-launch save preservation.
See `artifacts/alttp-world-map-v2-regression-final/result.json`; the package
folder also contains `validation.json` and `Zelda.nds.sha256`. All **30 host
tests** and the public-source checks passed.
