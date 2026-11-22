# GBA dual screen on Nintendo DS

> Historical development record. Some status, commands and artifact paths describe
> earlier builds. Start with the [current README](../../README.md) and
> [developer guide](../development.md) for current instructions.

**Standalone packager previews:** Apple Silicon Mac
(`artifacts/packager/macos-arm64/fusion-pack`) and Windows x64
(`artifacts/packager/windows-x86_64/fusion-pack.exe`) bundle the runtime and
create an NDS from a user's Fusion ROM and GBA BIOS, without Python or Docker:

```sh
./fusion-pack "Metroid Fusion (USA).gba" --bios bios.bin -o Fusion.nds
```

Windows PowerShell:

```powershell
.\fusion-pack.exe "Metroid Fusion (USA).gba" --bios bios.bin -o Fusion.nds
```

The Windows preview is built/tested under Wine on this Mac. Native Windows
10/11 testing and Authenticode signing remain release checks.

The output is saved at the chosen path. Existing files and game saves are
preserved. Only the original US Fusion revision is supported. The ROM-free
preview ZIP, build/test commands and remaining public-release licensing/signing
work are documented in [the CLI packager guide](../packager-cli.md).

**Fusion now runs with a geographic exploration map on the bottom screen and gameplay on top.** It uses Fusion's original map artwork, room layout and visited-state data. The current room is gold; Samus's map cell is white. Run [Play Fusion.command](../../Play%20Fusion.command) to open the current single-file package in the patched desktop app.

The original baseline also runs on this Apple Silicon Mac through unmodified GBARunner3 and the patched core. The automated run reaches a new game, moves Samus both ways, crosses a room boundary, jumps, lands, and preserves the ROM while writing a separate save. Those checks use the Python/libretro frontend. A separate patched desktop app is now available for interactive play below.

The original baseline GBARunner3 build remains untouched. Two clean builds produced the identical 205,312-byte NDS binary, SHA-256 `6a3f82c4b998b9e58aadb1c275d03df182cce83994f8691d7843cf622833522d`.

**3DS/DSpico:** the user confirmed Hardware Fix 4 runs on their 3DS in DSi mode. The new `artifacts/hardware-test-5/Fusion.nds` centers the game at its native 240×160 size with black borders and names/tests all six sectors. It passes 87 gameplay/display checks, 27 package/save checks and 35 all-area checks. Copy this file as `Fusion.nds`, keeping `_fusion` and your save. The canonical `artifacts/packages/Fusion.nds` contains the same bytes, and the rebuilt desktop app includes the L4 CPU fix. Test 5's new framing still needs confirmation on the physical console. Details: [map/display design](../fusion-map.md) and [hardware investigation](../hardware-debug.md).

## Play on this Mac

Double-click **[Play Fusion.command](../../Play%20Fusion.command)** in this project folder, or run:

```sh
.venv/bin/python tools/play_fusion.py
```

This selects `artifacts/melonds-desktop/melonDS Fusion.app` and opens the bundled `artifacts/packages/Fusion.nds`. The window title must include **Fusion patched**. The downloaded stock `.tools/melonds/melonDS.app` still has the ARM9 abort bug: extraction succeeds and the grid appears, but the top screen stays white. Changing the game package does not fix that emulator bug.

Controls: **arrows** move, **X** is A/jump/confirm, **Z** is B/fire, **Enter** is Start, **Backspace** is Select, **Q/W** are L/R, **F** toggles fast forward, and **P** pauses. Use View → Screen size to enlarge the window. `WAIT` and `--` are expected during menus and story scenes; live area/room IDs appear during gameplay.

Manual desktop verification of the geographic map reached gameplay at 60/60 fps, crossed from area `00`, room `00` to room `03`, and checked map highlighting plus pause/resume. Details are recorded in `artifacts/map-desktop-evidence/gui-verification.json`.

The patched app uses its own `artifacts/melonds-desktop/portable/` profile and virtual SD. On first setup, the launcher copies an existing package save from the stock app's configured SD folder if present; it never overwrites a save already in the new profile. Subsequent play uses the new profile's save. Quit the emulator normally so its virtual SD synchronizes to `portable/sdcard/`. The stock app, settings and original save remain untouched.

The desktop build uses the same pinned engine and `patches/melonds-arm9-data-abort.patch` as the passing automated tests, with JIT compiled out. Build provenance is in `artifacts/melonds-desktop/manifest.json`. Rebuild on this Mac with `.venv/bin/python tools/build_melonds_gui.py`. Prerequisites already installed here are the project-local Qt 6.8.3 SDK (`.tools/qt-sdk/6.8.3/macos`), FAAD 2.11.4 static library (`.tools/gui-deps`), and Homebrew SDL2, ENet, libarchive and zstd. Qt frameworks and shared dependencies are bundled with `macdeployqt`, then the generated app is locally signed. This build targets this Apple Silicon Mac; other Macs and macOS versions have not been tested.

## Geographic map renderer

The lower screen shows the current area's real 32×32 map through a 32×20-cell viewport. It scrolls vertically with Samus, preserves Fusion's exploration/download rules, and includes the original walls, doors and station/item icons. Gold marks visible cells in the current room and white marks Samus's current map cell. Main Deck and sectors 1–6 use the same adapter. Gameplay verification currently covers Main Deck rooms `00` and `03`, not a complete playthrough of every area.

Menus and transitions keep the last map visible but remove live highlighting and show `WAIT`/`--`. Before gameplay the map is blank. Active demo detection uses `0x03001242`; the previous flag at `0x0300001F` stayed set after an attract-mode demo and incorrectly hid the display during subsequent normal play.

Engine A renders the 240×160 GBA viewport directly on top. Engine B uses VRAM C for the map and labels. A small ITCM gate checks for changes every eighth VBlank (up to 7.5 updates/second). It reads guest memory without changing it, and skips full map work when Samus's room/cell and current map tile are unchanged. Asset loading happens once before the game starts; there is no SD access or allocation in the display IRQ. The stationary regression advances exactly 2,000 guest frames over 2,000 emulated frames.

Implementation, memory addresses, bounds, and build commands are documented in [docs/fusion-map.md](../fusion-map.md). Sources are in [runtime/dual_screen](../../runtime/dual_screen), with the [integration/linker patch](../../patches/gbarunner3-dual-screen.patch). The original GBARunner3 baseline remains untouched. The previous numeric-grid package is preserved in `artifacts/packages/room-id-grid-backup/`.

The centered-screen release passes **87/87** gameplay/map/framing/frame-budget checks in `artifacts/screen-framing-dev/test2/first-boot/result.json`, **27/27** package/save checks in `artifacts/screen-framing-dev/test2/result.json`, and **35/35** sector checks in `artifacts/screen-framing-dev/sectors-verified/result.json`. The sector run uses emulator-only warps after normal gameplay begins, allowing Fusion's own room loader to load each sector. It covers real rooms and map artwork, not a full-game playthrough. Stationary gameplay advances 2,000/2,000 frames. Seven packaging unit tests also pass. The original ARM interworking fix is physically confirmed on the user's 3DS; new display changes still need hardware playtesting.

The external-data prototype can still be built and tested separately:

```sh
.venv/bin/python tools/build_dual_screen.py --clean
.venv/bin/python tools/test_fusion.py --dual-screen --output artifacts/my-dual-test
```

Use `artifacts/packages/Fusion.nds` for the current single-file package. Earlier `fusion-dual-verified` reports and the existing external-data artifact describe the previous numeric-grid prototype; rebuild it before using the current map checks.

## Generate and test one bundled NDS

```sh
# Build the extractor/runtime template once (Docker required).
.venv/bin/python tools/build_dual_screen.py --hardware-diagnostics --clean

# Bundle locally supplied data; no Docker or compiler needed for this step.
.venv/bin/python tools/package_fusion.py \
  --rom 'Metroid Fusion (USA).gba' --bios gba_bios.zip \
  --output artifacts/my-package-build/Fusion.nds

# Inspect a package or run its acceptance suite. Output folders must be new.
.venv/bin/python tools/package_fusion.py --inspect artifacts/my-package-build/Fusion.nds
.venv/bin/python tools/test_packaged_fusion.py \
  --package artifacts/my-package-build/Fusion.nds --output artifacts/my-package-test
.venv/bin/python -m unittest discover -s tests/package -v
```

**Copy only `Fusion.nds` to the SD card.** The adjacent Mac manifest is for provenance and is not required on the DS. The generated NDS bundles the verified US Fusion ROM, GBA BIOS and default configuration as NitroFS data. First launch validates and extracts them; future launches hash-check and reuse them. Saves are kept outside the versioned extracted-data directory:

```text
/_fusion/ca33f4348c2c05dd330d37b97e2c5a69531dfe87/v1/rom.gba
/_fusion/ca33f4348c2c05dd330d37b97e2c5a69531dfe87/v1/bios.bin
/_fusion/ca33f4348c2c05dd330d37b97e2c5a69531dfe87/v1/config.json
/_fusion/ca33f4348c2c05dd330d37b97e2c5a69531dfe87/rom.sav
```

A launcher supplying `argv[0]` may launch a renamed/moved file using a `fat:/` path of at most 127 bytes. Without usable launcher arguments, the fallback is `/Fusion.nds` at the SD root. Leave approximately 9 MiB free for extraction in addition to the NDS itself. The runtime template targets DS/DS Lite flashcart DLDI storage; this extractor does not support DSi internal-SD mode. The user confirmed the ARM interworking fix runs on a 3DS with DSpico in DSi mode. The current `artifacts/hardware-test-5/Fusion.nds` adds centered framing and sector validation; see [the startup investigation](../hardware-debug.md).

The current diagnostic package is 8,743,424 bytes (about 8.34 MiB). It contains native DS runtime/renderer code and the original GBA game data; GBARunner3 continues to execute the game. The host tool refuses unknown ROM/BIOS hashes, mismatched runtime templates, or existing output paths. Extraction uses temporary files, checks the stored bytes before installation, retries interrupted extraction, and never opens the save for replacement. Two packages of this same Fusion ROM intentionally share its ROM-hash save identity.

The test starts from an SD containing only the NDS, waits for the bootstrap handoff, then runs the complete gameplay/grid regression. Repeat-boot checks distinguish exact save preservation at handoff from Fusion's own startup backup maintenance: the primary save slots must remain unchanged. The suite also checks partial extraction recovery, the no-argv filename fallback, damaged payload rejection and invalid file-table bounds.

Earlier map-release evidence: **75/75** full packaged gameplay/map checks, **27/27** package acceptance checks, **17/17** demo/save-load/pause/resume checks, and **7/7** host packaging tests pass. The acceptance suite freshly tests first extraction, repeat boot, exact save preservation at handoff, primary-slot preservation after game startup, interrupted extraction recovery and corrupt-package rejection. Reports are listed above.

The current `artifacts/packages/Fusion.nds` SHA-256 is `245d9b92dffb48f854a9e2bd0f466c03b3f217c4f540950a5a284a6d12fd8505`. It contains the original unchanged Fusion/BIOS payloads and uses the same extracted-data directory and save identity as the previous grid build.

melonDS automatically installs a DLDI-patched, capacity-padded copy of the launched NDS on its virtual SD. The integrity assertion allows changes only within the original reserved DLDI slot plus zero padding, requires the expected melonDS driver name, and checks all other bytes unchanged. The original Mac NDS and bundled game/BIOS remain unchanged. The added bootstrap marker is only a test synchronization point; it does not edit guest game memory.

See [packaging_plan.md](packaging_plan.md) for the format, memory/storage handoff and remaining hardware checks. The built `artifacts/dual-screen/sdcard/FusionDual.nds` remains an external-data prototype; use `artifacts/packages/Fusion.nds` for the single-file package.

## Run the working Fusion test

From this project folder, with Docker Desktop running and native Python 3.13+, Git, CMake and Xcode command-line tools installed:

```sh
python3.13 tools/setup_emulator.py
.venv/bin/python tools/build_baseline.py --clean
.venv/bin/python tools/build_patched_emulator.py
.venv/bin/python tools/build_probes.py
```

On this Mac these builds and dependencies are already present. The supplied BIOS and US Fusion ROM have already been prepared in `fixtures/local/fusion`. To create a fresh fixture elsewhere:

```sh
.venv/bin/python tools/prepare_sd.py \
  --bios gba_bios.zip --rom 'Metroid Fusion (USA).gba' \
  --output fixtures/local/fusion-new
```

Run the full regression, choosing a new output directory each time:

```sh
.venv/bin/python tools/test_fusion.py --output artifacts/my-fusion-test
```

Use `--sd-dir fixtures/local/fusion-new` to select a different fixture. The runner starts with clean emulator state and a copy of that SD folder. The script simulates 30,000 DS frames, including Fusion's opening story, and has a 240-second wall-clock timeout. The exploratory run completed in about 134 seconds; emulated throughput is not a measurement of physical DS performance.

Each run produces `result.json`, `junit.xml`, bounded logs, screenshots of both screens, DS main RAM, and shared-WRAM snapshots. Passing requires thirteen checks: all checkpoints, file-select mode, playable non-demo state, advancing game frames, right/left input and movement, a room transition, jump input and jump/landing, an unchanged Fusion ROM, and a separate 32 KiB save. Exit 0 means all requested checks passed; a failed check returns 1 and timeout returns 124.

## Why stock melonDS failed

Two independent problems were found:

1. **ARM9 data-abort handling:** the interpreter continued a faulting memory instruction after entering its abort handler. This could assign an unset load result or apply writeback. GBARunner3 uses MPU faults to implement GBA memory accesses, so this broke guest execution. The local patch stops those instructions, restores the base register, handles temporarily selected user registers, and checks sequential accesses. The [ARM946E-S manual](https://documentation-service.arm.com/static/5e8e3ee588295d1e18d3aa82) specifies the base-restored abort model.
2. **Default ROM/save path:** GBARunner3 changes the supplied ROM extension in place to `.sav`. With no ROM argument, it uses the literal `/rom.gba`, stored in VRAM in this build. Its byte-wise edit does not change that path, so saves can overwrite the copied ROM. The harness now supplies `fat:/rom.gba` as writable libnds `argv[1]`, matching a flashcart launcher. It does not modify the NDS or GBA ROM. The behavior comes from [GBARunner3 startup](https://github.com/Gericom/GBARunner3/blob/ecaa817815d9761745606592f04affe5ee9c3731/code/core/arm9/source/main.cpp).

Your original ROM and BIOS are unchanged. Failed experiments affected only disposable per-run SD copies. **Do not directly launch this baseline with the fallback `/rom.gba` path for games with saves.** Use a launcher that supplies the ROM argument. The earlier `artifacts/hardware-fusion/sdcard/` package has not been hardware-tested and needs such a launcher.

## Reproducibility and evidence

| Check | Result | Evidence |
|---|---|---|
| Original DS screen/input/storage diagnostic | 10 checks pass with packaged core | `artifacts/nds-packaged/` |
| Independent ARM9 abort diagnostic | Stock core fails; patched core passes 5 checks | `artifacts/mpu-stock-02/`, `artifacts/mpu-packaged/` |
| Original GBA diagnostic inside GBARunner3 | Guest frames and A press/release work | `artifacts/gba-probe-packaged/` |
| Same GBA diagnostic on stock core with ROM argument | Guest-execution checks fail | `artifacts/gba-probe-stock-control/` |
| Fusion exploratory full run | 30,000 frames; gameplay, room transition, jump, separate save | `artifacts/fusion-clean-long/` |
| Final scripted Fusion regression | All 13 checks pass; 30,000 frames in 133.8 seconds | `artifacts/fusion-verified/` |

The baseline script pins GBARunner3, libtwl and the upstream devkitARM r65 Docker image. Builds run serially because the upstream recursive Makefiles share outputs. The emulator script pins every fetched dependency in [tools/melonds-lock.json](../../tools/melonds-lock.json), checks the exact local patches, and produces `.tools/melonds-custom/fixed/melondsds_libretro.dylib`. Versions, patch hashes, compiler information and the binary hash are in `artifacts/melonds-patched/manifest.json`.

The patches are [ARM9 abort handling](../../patches/melonds-arm9-data-abort.patch) and [shared-WRAM diagnostic access](../../patches/melonds-ds-shared-wram.patch). The latter exposes physical shared WRAM at the frontend-only pseudo-address `0x0F000000`; it is not a DS bus mapping. GBARunner3 assigns this RAM to ARM9 as GBA IWRAM. The harness only reads it. Fusion assertions use the verified US ROM and [pinned decompilation definitions](https://github.com/metroidret/mf/tree/8614cc3eec194092cd756d6382c879b4c2ab4967): `linker.ld`, `include/globals.h`, and `include/structs/samus.h`.

The CPU patch is local and experimental, built with **JIT disabled**. It has not been submitted upstream or validated across a broad DS game suite. The tests prove this Fusion path; they do not establish full-game compatibility, audio accuracy, or hardware timing. Original DS/DS Lite acceptance testing remains necessary later.

## Individual diagnostic commands

```sh
.venv/bin/python tools/emulator_test.py \
  --core .tools/melonds-custom/fixed/melondsds_libretro.dylib \
  --rom tests/nds_probe/probe.nds \
  --output artifacts/my-ds-test --assert-probe

.venv/bin/python tools/emulator_test.py \
  --core .tools/melonds-custom/fixed/melondsds_libretro.dylib \
  --rom tests/nds_mpu_probe/probe.nds --frames 60 --capture 60 \
  --output artifacts/my-mpu-test \
  --expect-pixel 60,8,8,0,251,0 --expect-pixel 60,8,48,0,251,0 \
  --expect-pixel 60,8,88,0,251,0 --expect-pixel 60,8,128,0,251,0 \
  --expect-pixel 60,8,168,0,251,0
```

For custom Fusion observations, use `tools/emulator_test.py` with the patched core, `--sd-dir`, `--gba-rom-arg fat:/rom.gba`, and optionally `--input-script` and `--fusion-state`. Without boot assertions the result is `observed` and JUnit marks it skipped. Any detected change to an SD `.gba` file fails the run. Each input event is `{ "start": 500, "end": 515, "buttons": ["start"] }`, using zero-based frame indices. Captures use completed frame counts starting at one.

All downloaded tools, local BIOS/ROM fixtures, RAM dumps, SD images, saves and build artifacts are ignored. RAM dumps can contain game data; no files have been uploaded. Codex's macOS sandbox requires its normal execution approval path for Docker and emulator shared memory.

## Continue implementation

The minimal second-screen renderer and read-only Fusion adapter are implemented. The single-file packaging/extraction flow is implemented. Next steps are a real map for one area and hardware acceptance. Physical DS/DS Lite boot, save, audio and performance testing remain required.

See [project_summary.md](project_summary.md), [implementation_plan.md](implementation_plan.md), and the historical [baseline experiment notes](BASELINE_NOTES.md).
