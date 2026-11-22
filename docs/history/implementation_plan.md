# GBA Dual Screen implementation and Mac testing plan

> Historical development record. Some status, commands and artifact paths describe
> earlier builds. Start with the [current README](../../README.md) and
> [developer guide](../development.md) for current instructions.

Implementation update, November 21, 2026: the baseline builds reproducibly and patched melonDS runs Fusion. A separate enhanced runtime now displays gameplay on top and live hexadecimal area/room IDs with a room-ID grid below. The user selected a single `.nds` package with first-run extraction as the eventual output; see [packaging_plan.md](packaging_plan.md). See [README.md](../../README.md) for build/test commands. The research below predates these experiments; physical hardware testing remains outstanding.

Research date: November 19, 2026. Based on `project_summary.md` and the upstream sources linked below.

Build a small GBARunner3 extension for Metroid Fusion on an original DS or DS Lite with DSPico. Preserve the existing game execution path, read a bounded snapshot of game state, and draw a tile-based display on the other screen. Prove display coexistence and performance before implementing complete maps or a general adapter framework.

**Mac testing now covers the complete GBARunner3 → Fusion stack using the local melonDS interpreter corrections and launcher arguments.** Physical DS testing remains necessary for timing, audio, flashcart behavior, and acceptance.

The inspected Mac is Apple Silicon, running macOS 14.4. Homebrew, Clang, and CMake are available. No devkitARM compiler was found on PATH or at the usual `/opt/devkitpro` location; melonDS and RetroArch were not present in `/Applications`.

## Findings that affect the design

| Finding | Implementation consequence |
|---|---|
| GBARunner3's inspected `develop` commit is `ecaa817815d9761745606592f04affe5ee9c3731`. Its workflow uses `devkitpro/devkitarm:20241104`, recursive submodules, and `make -C code`. | Reproduce this baseline before changing SDKs. Record the image digest and the `libtwl` submodule commit. An open report describes a boot failure with devkitARM r66, so a successful compilation alone is insufficient. [Build workflow](https://github.com/Gericom/GBARunner3/blob/ecaa817815d9761745606592f04affe5ee9c3731/.github/workflows/nightly.yml), [r66 report](https://github.com/Gericom/GBARunner3/issues/199). |
| Centering and masking are enabled by default. This uses display capture and the sub engine; VBlank code alternates VRAM C/D. | Initially disable centering/capture, put the main engine on the top LCD, and reserve the sub engine for the map. This changes framing, so compare against an unenhanced baseline with the same settings. [Display defaults](https://github.com/Gericom/GBARunner3/blob/ecaa817815d9761745606592f04affe5ee9c3731/code/core/arm9/source/Application/Settings/DisplaySettings.h), [display setup](https://github.com/Gericom/GBARunner3/blob/ecaa817815d9761745606592f04affe5ee9c3731/code/core/arm9/source/Application/GbaDisplayConfigurationService.cpp), [VBlank handler](https://github.com/Gericom/GBARunner3/blob/ecaa817815d9761745606592f04affe5ee9c3731/code/core/arm9/source/Emulator/VBlankIrq.s). |
| The linker places runtime sections in VRAM A and H/I; other banks serve GBA graphics and capture. The unused LCD is also darkened and its backlight disabled. | A blank screen does not mean its usual VRAM allocation is free. Audit all banks and linker sections before assigning a tile buffer. Enable both the bottom backlight and its display brightness. [Linker script](https://github.com/Gericom/GBARunner3/blob/ecaa817815d9761745606592f04affe5ee9c3731/code/core/arm9/gbarunner9.ld), [display setup](https://github.com/Gericom/GBARunner3/blob/ecaa817815d9761745606592f04affe5ee9c3731/code/core/arm9/source/Application/GbaDisplayConfigurationService.cpp). |
| GBA EWRAM/IWRAM have explicit MPU regions. The first 2 MiB of ROM are mapped from GBA `0x08000000` to DS `0x02200000`; other ROM reads use runtime machinery. | Separate RAM snapshots from ROM asset reads. Do not cast arbitrary GBA ROM addresses to DS pointers or trigger SD-cache reads inside the display interrupt. [MPU configuration](https://github.com/Gericom/GBARunner3/blob/ecaa817815d9761745606592f04affe5ee9c3731/code/core/arm9/source/MemoryProtectionConfiguration.cpp), [ROM mapping](https://github.com/Gericom/GBARunner3/blob/ecaa817815d9761745606592f04affe5ee9c3731/code/core/arm9/source/MemoryEmulator/RomDefs.h). |
| The startup code loads a GBA BIOS from `/_gba/bios.bin`, accepts a ROM argument, and otherwise opens `/rom.gba`. | Use these paths for the first reproducible boot. Supplying an NDS BIOS to melonDS does not satisfy GBARunner3's separate GBA BIOS requirement. [Runtime startup](https://github.com/Gericom/GBARunner3/blob/ecaa817815d9761745606592f04affe5ee9c3731/code/core/arm9/source/main.cpp). |
| GBA DS identifies Fusion as `AMTE` and uses `0x03000BDE` to distinguish gameplay and the map screen. The Fusion decompilation documents substantially more state. | Reuse verified facts and presentation references. Implement a direct memory decoder; the existing pause-screen capture profile is not a complete map adapter. [GBA DS profiles](https://github.com/kyannon/gba-ds/blob/main/src/profiles.c), [Fusion symbols](https://github.com/metroidret/mf/blob/main/linker.ld). |
| GBARunner3 has an unresolved missing-license issue. | Resolve reuse and redistribution terms before a public derivative release. Track licenses for every reused component and keep ROM/BIOS assets outside public artifacts. [Upstream issue](https://github.com/Gericom/GBARunner3/issues/200). |

## Step by step implementation

### 1. Freeze the first target and reproduce the build

Target original DS/DS Lite in DS mode, DSPico, and one verified US Metroid Fusion ROM. Defer DSi-specific memory or clock advantages. Keep game files unchanged on disk; GBARunner3's own in-memory compatibility patches are part of its existing runtime.

Create an upstream checkout pinned to the commit above, including submodules. Reproduce the upstream container build. On Apple Silicon, inspect the container's supported platforms; use Docker's Linux AMD64 emulation if the pinned image lacks ARM64. If the historical image is unavailable, reconstruct and record its package versions before changing runtime code.

Add build and packaging scripts that produce `GBARunner3.nds`, `/_gba/configs/`, a build manifest, and a checksum. Retain ELF and linker-map files for diagnostics. Use the existing GBARunner3/libtwl environment for core code; do not replace it with a generic libnds application skeleton.

**Done when:** a clean checkout produces a bootable baseline, dependencies are recorded, and a second build is checked for reproducibility. Investigate timestamp-only binary differences rather than silently calling builds reproducible.

### 2. Establish physical hardware and storage baselines

Prepare a separate test microSD layout containing the built executable, configs, the user's GBA BIOS, `/rom.gba`, and a disposable copy of a save. Record DSPico firmware, launcher, loader, DS model, and SD card. DSPico has distinct firmware, bootloader, DLDI, launcher, and loader components; pin the actual combination used. [DSPico component index](https://github.com/LNH-team/dspico).

First boot the runtime directly with its fallback ROM path. Then verify the intended launcher passes the selected ROM argument correctly. Confirm gameplay, room transitions, audio, saving, and loading without enhancement code. Capture repeatable scenes from a fixed save and button sequence, including movement, combat, a door transition, and a busy scene.

**Done when:** unmodified GBARunner3 works on DS/DS Lite with this storage setup. Any existing Fusion issue is documented separately from enhancement regressions. Do not build features on a failing baseline.

### 3. Prove the Mac testing route

Use the emulator experiment described below before depending on full-system automation. Start with a tiny DS test application, then a self-authored GBA diagnostic loaded through GBARunner3, and finally the verified Fusion ROM.

Test boot, DLDI reads, a save write/read, button input, and screenshots from both LCDs. Compare emulator interpreter and JIT modes if needed; keep GBARunner3's own JIT settings distinct from the DS emulator's JIT settings.

**Done when:** either the complete runtime has a repeatable automated boot/input/capture test, or the emulator limitation is recorded and the project explicitly proceeds with native adapter tests, a separate DS renderer test, and hardware integration tests. Time-box this investigation to roughly two engineering days initially; avoid turning emulator repair into the main project.

### 4. Audit resources and display ownership

Produce a bank-by-bank VRAM table and a memory map covering runtime code/data, GBA graphics, capture, border/color-correction features, heap, stacks, and ARM7 sharing. Check the pinned source, linked output, and runtime register values. Audit DMA, timers, interrupt vectors, and cache ownership as well.

For the prototype, disable center-and-mask capture and borders, route main-engine gameplay to the top LCD, and enable the bottom LCD. **VRAM C mapped to sub backgrounds is a candidate**, contingent on confirming no remaining runtime owner. Do not repurpose H/I: the linker already allocates runtime storage there. Keep the original display path for unsupported games or when enhancements are disabled.

Start with one 4-bit tile background, a compact font, a 32-by-32 tilemap, and a small palette. Avoid a full framebuffer. Proposed initial incremental targets are at most 16 KiB of tile/map data and 16 KiB of ordinary RAM, subject to the actual linker headroom. A bank reservation can be larger than the bytes stored in it.

**Done when:** a static title and grid appear on the bottom LCD during gameplay, without primary-screen corruption, runtime memory overlap, or save/audio regressions. This is the first architectural go/no-go gate.

### 5. Add a bounded snapshot hook

Inspect the runtime's assembly IRQ entry/exit path before adding a C/C++ call. The existing VBlank handler already performs capture, DMA, and save work; it is not a normal application callback. Preserve guest registers, flags, stack alignment, interrupt state, and runtime return behavior. Size the dedicated stack from measured usage.

Start with a few RAM bytes sampled once every six DS VBlanks, approximately ten updates per second. Capture on ARM9 while guest execution is suspended in a known runtime context. Account for its active MPU and cache settings; `volatile` alone is not a cache-coherency solution. Copy into fixed-size host-owned storage. Validate mode, area, room, and coordinate ranges; reject transitional or invalid samples.

Keep the first callback extremely small. Do no allocation, filesystem access, decompression, ROM-cache lookup, or formatted logging there. Preload data before entering the VM. Update only dirty tilemap entries within a measured budget, and skip optional work when the budget is exhausted. More expensive preparation needs a separately verified safe runtime scheduling point.

**Done when:** title, area ID, and room ID update through room transitions while the snapshot path is demonstrably read-only with respect to guest memory.

### 6. Implement the first Fusion adapter

Detect header code and revision, then validate a full ROM digest once during load. A four-character game code alone does not reject hacks or revisions with different layouts. The decompilation's US reference SHA-1 is `CA33F4348C2C05DD330D37B97E2C5A69531DFE87`; verify the local ROM against it before enabling this layout. Record a SHA-256 in the local test manifest too. [Reference ROM hash](https://github.com/metroidret/mf/blob/main/mf_us.sha1).

These are **GBA guest addresses from the US decompilation**, to validate against the running game before treating them as supported:

| State | Address | Width |
|---|---|---|
| Current area | `0x0300002C` | 8 bits |
| Current room | `0x0300002D` | 8 bits |
| Map X / Y | `0x03000031` / `0x03000032` | 8 bits each |
| Main game mode | `0x03000BDE` | signed 16 bits |
| First submode | `0x03000BE0` | signed 16 bits |

The linker establishes the addresses; declarations and game-mode enums establish interpretation. Gameplay is main mode 1, but submodes must also be checked to avoid displaying half-complete room transitions. [Linker](https://github.com/metroidret/mf/blob/main/linker.ld), [global declarations](https://github.com/metroidret/mf/blob/main/include/globals.h), [area and room declarations](https://github.com/metroidret/mf/blob/main/include/structs/connection.h).

Use a narrow read-only memory interface, an immutable snapshot, a pure state decoder, and a renderer consuming that decoded state. The first adapter can remain specific to Fusion. Give unknown ROMs no adapter and no enhancement-side memory reads.

**Done when:** the documented proof of concept works: gameplay on top; title, area/room identifiers, and a small grid with a moving highlight below. Clearly distinguish this diagnostic grid from a geographically accurate room map.

### 7. Build one accurate area map

Use the decompilation's minimap implementation and room metadata to decode area tiles, room/map coordinates, visited tiles, and map-download flags. Fusion already tracks visited minimap cells; use that data so exploration survives save loading. Do not infer map geometry from room number order or equate downloaded maps with visited rooms. [Minimap implementation](https://github.com/metroidret/mf/blob/main/src/minimap.c).

Extract required art and map data from the user's verified ROM during loading or a reproducible local preparation step. Read original bytes through a bounded asset reader, independently of patched executable ROM caches. Convert assets into DS tile/palette formats and preload a compact working set. Do not copy full game assets into the distributable source tree.

Support one area first, with current position, explored cells, and the game's intended undiscovered-area behavior. Rebuild static map layers only when necessary and update the marker independently.

**Done when:** screenshots and state fixtures agree with Fusion's own map for the selected area, including a save reload and an area transition.

### 8. Complete Fusion and meet the hardware performance gate

Expand to every area and relevant icons. Cover pause/menu transitions, elevators, death, new game, save loading, soft reset, and gameplay modes where map state is temporarily invalid. Freeze or hide the marker during those states and resynchronize afterward.

Compare three configurations: original default GBARunner3, baseline with the prototype's display settings, and the same settings with enhancements enabled. This separates the effect of removing capture from the cost of adding the map. Measure callback duration and stack high-water marks using instrumentation that does not claim timers or DMA channels already owned by the runtime. Record gameplay cadence, transition duration, audio glitches, and SD/save behavior on actual hardware.

Proposed acceptance criteria: map updates within 150 ms after a stable room transition; no new audio glitches, crashes, or missed frames in the fixed baseline scenes; less than 1% sustained gameplay-speed regression beyond measurement noise; and a 30-minute hardware soak with save/reload checks. These are engineering targets, not measured results. Reduce map refresh rate or redraw work if needed, preserving game performance first.

**Done when:** Fusion passes on DS and DS Lite before DSi/3DS-specific improvements are considered.

### 9. Generalize and package

Only after Fusion is stable, formalize the adapter registry and reusable map renderer. Add Zero Mission next to test shared concepts without assuming identical addresses or map formats. Then evaluate Aria of Sorrow as an independent adapter.

Package the `.nds`, necessary configs, installation instructions, supported ROM hashes/revisions, hardware/launcher combinations, known issues, and exact build provenance. Document which tests were native, emulated, or physical. Resolve upstream licensing and attribution requirements before public distribution; do not bundle commercial ROMs or BIOS files.

**Done when:** a clean installation on the documented DSPico setup automatically selects verified adapters, and unsupported games retain baseline runtime behavior.

## Mac emulation and automation strategy

| Route | Evidence and purpose | Limitation |
|---|---|---|
| Standalone melonDS | Official Mac builds include ARM64/universal options. Use for interactive debugging and inspecting both screens. [Downloads](https://melonds.kuribo64.net/downloadlist.php). | Its inspected command-line interface launches ROMs but does not provide a complete scripted test runner. [CLI source](https://github.com/melonDS-emu/melonDS/blob/master/src/frontend/qt_sdl/CLI.cpp). |
| melonDS DS core plus `libretro.py` | Both document macOS support; the core explicitly supports ARM64. Python bindings expose frame execution, input, video/audio callbacks, and test drivers. This is the recommended automation prototype. [Core README](https://github.com/JesseTG/melonds-ds), [Python binding](https://github.com/JesseTG/libretro.py), [API documentation](https://libretropy.readthedocs.io/en/latest/). | Validate the exact versions together, storage emulation, and GBARunner3 boot. macOS support does not prove this particular hypervisor works. |
| RetroArch with melonDS DS | Provides a Mac CLI, config selection, and source-supported frame-limit/screenshot options for a basic smoke test. [CLI documentation](https://docs.libretro.com/guides/cli-intro/), [option implementation](https://github.com/libretro/RetroArch/blob/master/retroarch.c). | A process exit or a screenshot alone is not a gameplay assertion. Input scripts, state isolation, and result checking are still needed. |
| DeSmuME | A possible second emulator for cross-checking rendering. | Its FAQ lists Lua scripting among features missing from the Mac port. Do not base the Mac automation plan on Windows Lua tutorials. [FAQ](https://wiki.desmume.org/?title=Faq). |

An upstream GBARunner3 issue contains a June 2025 report of a freeze in melonDS on Android. That is a concrete reason to require the boot experiment, but it neither establishes failure nor guarantees success on current desktop macOS builds. [Compatibility report](https://github.com/Gericom/GBARunner3/issues/179).

The desired full test stack is **Mac → DS emulator → GBARunner3.nds → Fusion loaded from emulated storage**. Loading Fusion directly in a GBA emulator tests game-state interpretation but bypasses GBARunner3, DS rendering, and its memory mapping. Likewise, melonDS's GBA Slot-2 feature is not a GBA execution mode. [Core documentation](https://docs.libretro.com/library/melonds_ds/).

Use four test layers:

1. **Native Mac tests on every change.** Compile the pure decoder and map logic with Clang, use sanitizers, and supply synthetic snapshots for valid rooms, transitions, invalid coordinates, unsupported revisions, and save-state changes. Assert decoded state and tilemap output.
2. **DS renderer tests.** Build a small `.nds` application that exercises the same renderer with scripted snapshots. Capture both screens at fixed frame counts and compare tilemap state and screenshots. This proves DS rendering, not resource coexistence with GBARunner3.
3. **Full runtime tests after the boot gate passes.** Load the real runtime and fixtures through a fresh emulated DLDI filesystem image. Replay button inputs frame by frame; assert room transitions, marker position, save persistence, and no unintended changes to the primary screen. Use a fixed RTC, firmware settings, core version, renderer, and initial save. Start with software rendering and interpreter execution for reproducibility, then evaluate JIT separately. Emulated DLDI storage is not DSPico firmware emulation.
4. **Physical DS acceptance at each integration milestone.** Check boot/launcher behavior, SD reads, saves, sound, performance, and the long-running session. An emulator cannot certify microSD latency or the actual flashcart path.

The automated runner should create an isolated temporary filesystem per case; load the ARM64 core; configure DS mode and software rendering; run a frame-indexed input sequence; collect top/bottom images and structured state where available; enforce both frame and wall-clock timeouts; and emit JSON/JUnit results with nonzero exit status on failure. Include one deliberately failing assertion to prove that failures reach CI. Avoid shared writable saves and avoid savestates as the only starting point for boot tests.

If stock core memory access does not expose a needed region, use test-build telemetry or a narrowly scoped emulator hook rather than guessing that a pointer maps to guest IWRAM. A custom melonDS frontend is a later fallback: its core exposes `RunFrame`, `SetKeyMask`, and touch methods, but a frontend still needs platform services and storage handling. [Core interface](https://github.com/melonDS-emu/melonDS/blob/master/src/NDS.h).

Public CI can build the project and run synthetic native/DS diagnostics. Full Fusion integration tests need locally supplied ROM, BIOS, and save fixtures on a private runner. Keep those files out of logs, published test artifacts, and source control. Emulator DS BIOS replacements and the GBA BIOS needed by GBARunner3 are separate inputs.

## Proposed implementation layout and first milestone

Keep upstream GBARunner3 in a pinned checkout with a small, reviewable patch series. Add project-owned directories for `enhancement/core`, `enhancement/adapters/fusion`, `enhancement/render`, `tests/native`, `tests/nds_renderer`, `tests/integration`, and `tools`. Store personal game files in an ignored local fixtures directory. Keep snapshot acquisition and display setup changes localized in the upstream runtime.

The first milestone is steps 1 through 6: **a reproducible baseline, an emulator feasibility result, and the minimal Fusion title/area/room/grid display working on physical DS hardware**. Full maps and further games depend on that milestone. Toolchain repair, display ownership, and emulator boot are the main schedule uncertainties; a firm total estimate should follow those experiments.
# Implementation status

The baseline build and Mac automation are implemented. Two clean, unmodified GBARunner3 builds match byte for byte. DS diagnostics pass screen, input, storage and ARM9 abort checks. With the local melonDS interpreter fixes and a writable launcher argument, Fusion reaches gameplay and responds to movement, room transitions, jumping and landing. See [README.md](../../README.md) for reproducible commands and exact assertions. The minimal secondary-screen renderer and Fusion adapter are now implemented in a separate build. The first-run extraction packager is implemented; physical DS testing and geographic map rendering remain outstanding.



## Completed Mac dual-screen milestone — November 21, 2026

The separate enhanced runtime displays Fusion gameplay on the top LCD and a read-only area/room monitor with a 16×16 ID grid on the bottom LCD. It refreshes every four VBlanks, hides IDs outside active gameplay, and follows room `00` to `03` during the scripted run. Its direct-boot save-path construction is fixed. The final patched-melonDS test passes 73 checks; an unsupported-game probe passes 6 checks. No physical hardware testing or geographic map rendering has been performed.

The user confirmed the eventual output: one locally generated `.nds`, with embedded ROM/BIOS/configuration extracted on first boot and separate persistent saves. The packager and startup extraction are now implemented and tested in patched melonDS. [packaging_plan.md](packaging_plan.md) records the data format, cache/filesystem constraints, startup placement, failure recovery and acceptance steps. The current core has only 652 bytes free in VRAM A, so larger enhancements must plan code placement explicitly.


## Completed single-file packaging milestone — November 21, 2026

`tools/package_fusion.py` now produces one `Fusion.nds` containing the verified local Fusion ROM, BIOS and configuration. `tools/build_dual_screen.py --package-template` builds a separate bootstrap extractor/runtime template. The host packaging step itself uses Python only. The extractor runs through ARM7 DLDI storage, verifies temporary files before installation, and hands explicit paths to the core. Persistent saves are outside the versioned data directory.

The complete packaged first boot passes 74 gameplay/display/integrity checks. Repeat-boot tests verify that all three installed files are reused, the entire save is unchanged at handoff, and all primary save slots survive full Fusion startup. Fusion creates a matching redundant A backup during that startup. Recovery from a partial BIOS extraction, fallback filename launch, corrupt payload rejection and invalid bounds rejection are covered. Seven host packaging tests cover repeatable output, preserved executable segments, payloads, input rejection and malformed containers. See README.md and packaging_plan.md for output paths, commands, limits and test evidence.


## Geographic map update — November 21, 2026

Implemented the current-area geographic exploration map using Fusion's original ROM tiles and live map RAM. Visible current-room cells are gold, Samus's cell is white, and the map follows vertically. The adapter accepts Main Deck and sectors 1–6; gameplay coverage currently exercises Main Deck rooms 00 and 03. Pause/resume and loaded saves work, including returning from an attract-mode demo (active demo state is at `0x03001242`, unlike the sticky old flag).

The default `artifacts/packages/Fusion.nds` is updated without changing payload format or save identity. Its SHA-256 is `a042536916f7a5ed25a89070719c543e00ad2d1ba46aeb479362eab524cbbde8`, size 8,740,352 bytes. The previous grid package is backed up in `artifacts/packages/room-id-grid-backup/`.

Validation: 75/75 full gameplay/map/frame-budget checks, 27/27 package checks (including repeat launch and save preservation), 17/17 demo-exit/save-load/pause/resume checks, and 7/7 packaging unit tests pass. A second build reproduces the NDS exactly. The native patched melonDS app also passed visual gameplay, room transition and pause/resume checks. Test reports are in `artifacts/map-release-verified/`, `artifacts/map-resume-verified/` and `artifacts/map-desktop-evidence/`. See [map implementation notes](../fusion-map.md). Hardware performance, area transitions, other room shapes and full-game testing remain outstanding.

## Hardware confirmation, centered display and sectors — November 21, 2026

The user confirmed Hardware Fix 4 runs on 3DS/DSpico in DSi mode. Hardware
Test 5 now captures/crops/centers a native 240×160 top image with black borders,
uses VRAM H for the lower map, names all six sectors, and waits for each area's
map to finish loading before displaying live state. The BIOS and ROM cache
table have separate memory allocations. Test 5 passes 87 gameplay/display
checks, 27 package/save checks and 35 checks covering all seven areas via
emulator-assisted real room loads. The native Mac app shows centered gameplay
and pause/resume at 60/60 fps. Physical validation of the new framing and a
full-game performance/playthrough pass remain outstanding. See
[map/display notes](../fusion-map.md).
