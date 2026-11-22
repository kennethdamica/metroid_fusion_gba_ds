# Single-file DS package: agreed output and feasibility

> Historical development record. Some status, commands and artifact paths describe
> earlier builds. Start with the [current README](../../README.md) and
> [developer guide](../development.md) for current instructions.

## Standalone CLI update — November 21, 2026

The first end-user interface is now a standalone command-line executable,
`fusion-pack`, built for Apple Silicon macOS. It embeds a prebuilt enhanced
runtime and its own interpreter, accepts the user's ROM and BIOS, and writes
one NDS to a user-chosen filesystem path. No Python, Docker or project checkout
is required by the end user. A build report is optional. See
[the CLI guide](../packager-cli.md) for usage, output safety, validation and
the remaining licensing/signing work before public distribution.

The earlier implementation notes below describe the developer packaging
workflow and historical milestones.

Decision: November 21, 2026. The user selected one `.nds` file with first-run extraction. The host packager and bootstrap extractor are now implemented. `artifacts/packages/Fusion.nds` is the generated single-file package; the earlier dual-screen prototype remains available separately. See README.md for commands and current validation results.

## User-facing contract

1. On the Mac, select a supported GBA ROM, GBA BIOS and a versioned enhanced-runtime package.
2. The tool verifies their identities and produces a game-specific file such as `Metroid Fusion DS.nds`, plus an optional build manifest on the Mac.
3. Copy that single `.nds` to a compatible flashcart SD card and launch it normally.
4. First launch validates and extracts the bundled ROM, BIOS and required configuration into a private, versioned per-game directory. Show progress and an actionable error if there is insufficient space or extraction fails.
5. Subsequent launches reuse verified extracted data. Store saves separately from versioned runtime/configuration data so rebuilding or replacing the `.nds` does not reset progress.

The `.nds` contains native DS ARM9/ARM7 code, the enhancement renderer, and original GBA data. GBARunner3 remains the GBA execution runtime. Packaging does not turn the GBA game's instructions and assets into a rewritten DS game. Writable SD storage and a compatible DLDI launcher are still needed. The selected approach stores the game both inside the `.nds` and as an extracted SD file (roughly another 8 MiB for this Fusion ROM); only the existing runtime/cache working set occupies RAM.

The tool should be a local bundler: use a prebuilt versioned runtime template, embed the user's inputs, update DS filesystem/header metadata, and verify the result. End users should not need to build GBARunner3 for each game. Package manifests should include format version, runtime/adapter version, original ROM and BIOS hashes, lengths, payload paths, configuration and save identity.

## Why this fits the code we tested

- GBARunner3's loader uses FatFs `FIL` handles, reads the first 2 MiB into its linear ROM mapping, and streams the remainder. Fusion is 8 MiB, while an original DS has 4 MiB main RAM. The payload belongs in the `.nds` data section, not in an ARM9 load segment.
- `SdCache.c` derives physical SD sectors from the open file's FAT cluster table, reading 4 KiB blocks directly through ARM7. Merely replacing a path with `nitro:/rom.gba` will not satisfy that cache. Extraction preserves its existing file/sector assumptions.
- Save tag scanning and save-patch routines also seek/read the ROM's FatFs handle. First-run extraction lets these continue unchanged.
- The enhanced build now derives a save filename in separate writable memory. It does not mutate the ROM argument or the VRAM fallback literal. Direct fallback boot is part of the enhanced regression.
- DS files can contain a NitroFS data tree: `ndstool` supports `-d directory`. The upstream bootstrap Makefile even has an `GBAR3_ISNITRO` branch using `nitrofiles` and `FatInNitroFS.dldi`. That special emulator/debug route is evidence of data embedding, not a tested DSPico save/extraction implementation.

Primary references: [ndstool's create/data options](https://github.com/devkitPro/ndstool/blob/master/source/ndstool.cpp), [devkitPro NitroFS initialization and self-file fallback](https://github.com/devkitPro/libfilesystem/blob/master/source/nitrofs.c), [pinned GBARunner3 bootstrap](https://github.com/Gericom/GBARunner3/blob/ecaa817815d9761745606592f04affe5ee9c3731/code/bootstrap/Makefile), [pinned SD cache](https://github.com/Gericom/GBARunner3/blob/ecaa817815d9761745606592f04affe5ee9c3731/code/core/arm9/source/SdCache/SdCache.c). These establish the packaging primitives and constraints. The implemented package now boots and extracts through patched melonDS.

## Implementation sequence

1. **Define the package and extraction layout.** For example, bundle `/package/manifest.json`, `/package/game.gba`, `/package/bios.bin` and configuration; extract under a directory keyed by original ROM hash. Keep a stable save path independent of the runtime version. Reject unsupported ROM hashes even when a hack keeps the `AMTE` header.
2. **Build the host bundler.** Use the pinned `ndstool` toolchain or a validated NDS container writer; preserve entrypoints, ARM7/ARM9 binaries, DLDI patch space and launcher argv support. Verify payload bytes, offsets, lengths, header checksums and output hashes. Use only user-supplied game/BIOS data.
3. **Implement a startup extractor before guest execution.** Resolve the launched `.nds` through the flashcart's `argv[0]` and access its embedded data through the SD-backed self-file path. Explicitly test a loader without usable argv and choose a fallback discovery/error behavior. Do not assume raw cartridge reads behave the same on all flashcarts. Stream through a small buffer; verify hashes, write temporary files, and rename only after successful completion. Resume/retry cleanly after power loss. Never overwrite an existing save.
4. **Hand off explicit paths.** Make BIOS/config/ROM/save paths explicit instead of depending on the global `/_gba/bios.bin` and mutable extensions. Reuse the current FatFs ROM/cache path after extraction. Audit bootstrap/ARM7 storage ownership: GBARunner3 moves the DLDI driver to ARM7, so a generic ARM9 libfat initializer cannot simply be inserted without checking that handoff.
5. **Automate package acceptance in patched melonDS.** Start with an SD containing only the generated `.nds`; model its actual launch path. Verify first extraction, the full 73-check dual-screen gameplay run, unchanged packaged/extracted ROM, separate save creation, second launch without re-extraction, persistence of a real saved game, interrupted extraction recovery, insufficient space, invalid payloads and two packages with independent saves. Current tests verify a 32 KiB save file, not a save-station/reload round trip.
6. **Test on DS/DS Lite and DSPico.** Verify DLDI patching, launcher path, first/repeat boot, writes/power interruption, save reload, controls, audio and frame timing. The Mac interpreter cannot establish physical performance or flashcart compatibility.

## Resource constraint to address before adding the extractor

The external-data enhanced core ends at `0x0681FD74` (652 bytes free); explicit package paths move the packaged core end to `0x0681FDC4` (572 bytes free). The compact renderer uses 12 bytes of additional explicit main-RAM state, maps VRAM C to Engine B, and uses about 10 KiB of its tile/map address space. Future maps and packaging code need a deliberate code/data placement plan. Prefer transient extraction work in the bootstrap before the VM takes over, with an audited filesystem handoff; do not keep growing the core's VRAM A text section. This does not prevent single-file packaging, but it is a concrete implementation constraint.

Reading directly from an embedded ROM could be a later optimization. It would require a bounded ROM-file abstraction, offset-aware cache sector translation, compatible save-tag scanning and independent save storage. It is not needed for the selected first-run extraction workflow.


## Implemented format and bootstrap

`tools/package_fusion.py` builds a standard NitroFS root with four entries in a fixed order: `manifest.bin`, `rom.gba`, `bios.bin`, `config.json`. The 76-byte binary manifest contains `FUSPKG01`, little-endian format/ABI version 1, and three SHA-1 payload digests. The runtime also pins all three expected digests and sizes; the host independently checks the BIOS SHA-256 and Fusion SHA-1. Payloads are sector-aligned, outside executable load segments. The host updates the NDS filesystem pointers, used size, device capacity, title and header CRC. ARM7/ARM9 load segments and reserved DLDI space stay unchanged. A companion JSON manifest records template source pins, patch hashes, template hash, payload SHA-256 hashes and output SHA-256.

The bootstrap reuses upstream FatFs with RAM copy helpers. It runs after the existing ARM7 DLDI setup and uses two bootstrap-only IPC commands that return the storage driver's success status. An aligned 8 KiB bounce buffer maintains ARM9 cache coherence. All files are closed and FatFs is unmounted before the core mounts the filesystem afresh. After the core image is copied to VRAM, explicit ROM/BIOS/config/save paths are copied below its BSS into `0x0203F000`; the synchronization marker occupies `0x0203E000`. The core consumes the paths before clearing its guest EWRAM. The verified bootstrap executable text ends below these handoff addresses.

On first launch, three files are extracted using `.part` temporary names, checked while streaming, synced/closed, re-read and hashed, then renamed into place. Existing valid files are rehashed and reused. An interrupted `.part` is replaced on retry. A damaged installed file is replaced only after a valid temporary replacement is available. Existing save files are untouched by this process. This is retryable filesystem sequencing, not a claim that FAT is power-loss-proof.

Remaining limits: physical flashcart/storage timing, actual power-loss testing, forced disk-full/device-write failures, DSi internal SD, and a save-station/gameplay reload round trip are not validated by the current suite. The recovery test simulates a partially extracted BIOS file. The full game boot may create a redundant save backup; preservation checks therefore include both byte equality before guest execution and unchanged primary save-slot data after guest startup. Pinned save layout references: [Fusion save-file structure](https://github.com/metroidret/mf/blob/8614cc3eec194092cd756d6382c879b4c2ab4967/include/structs/save_file.h) and [primary/backup pointers](https://github.com/metroidret/mf/blob/8614cc3eec194092cd756d6382c879b4c2ab4967/src/data/sram_pointers.c).


## Geographic map update — November 21, 2026

Implemented the current-area geographic exploration map using Fusion's original ROM tiles and live map RAM. Visible current-room cells are gold, Samus's cell is white, and the map follows vertically. The adapter accepts Main Deck and sectors 1–6; gameplay coverage currently exercises Main Deck rooms 00 and 03. Pause/resume and loaded saves work, including returning from an attract-mode demo (active demo state is at `0x03001242`, unlike the sticky old flag).

The default `artifacts/packages/Fusion.nds` is updated without changing payload format or save identity. Its SHA-256 is `a042536916f7a5ed25a89070719c543e00ad2d1ba46aeb479362eab524cbbde8`, size 8,740,352 bytes. The previous grid package is backed up in `artifacts/packages/room-id-grid-backup/`.

Validation: 75/75 full gameplay/map/frame-budget checks, 27/27 package checks (including repeat launch and save preservation), 17/17 demo-exit/save-load/pause/resume checks, and 7/7 packaging unit tests pass. A second build reproduces the NDS exactly. The native patched melonDS app also passed visual gameplay, room transition and pause/resume checks. Test reports are in `artifacts/map-release-verified/`, `artifacts/map-resume-verified/` and `artifacts/map-desktop-evidence/`. See [map implementation notes](../fusion-map.md). Hardware performance, area transitions, other room shapes and full-game testing remain outstanding.


## CLI acceptance and runtime pinning — November 21, 2026

The CLI build is self-contained and embeds only a runtime template and manifest.
It accepts a positional ROM path, mandatory `--bios`, optional `-o` output path,
`--manifest`, `--json`, `--inspect`, `--list-games` and `--version`. No Nintendo
ROM/BIOS is included. The native Mac preview passed 44 standalone assertions
with an empty PATH outside the checkout, plus 12 builder tests.

End-to-end packaging validation discovered that the separate non-diagnostic
template stalls at guest frame 1 despite producing a valid container. The
release therefore pins the exact Hardware Test 5 template and generated-NDS
checksum in `release/packager/runtime-lock.json`. Both host CLI defaults now
use `artifacts/hardware-runtime`; a different template is refused by the
release builder until the lock is deliberately updated after gameplay tests.
Public distribution remains pending upstream/runtime license clarification
and notices, project licensing, and macOS signing/notarization.

## Windows command-line preview — November 21, 2026

Added a standalone x64 `fusion-pack.exe` using Windows CPython/PyInstaller,
built locally under Wine 10. End users supply the original US Fusion ROM and
GBA BIOS, choose an output path, and need no Python, Docker or Wine installation.
The Windows download includes no game or BIOS data. Its generated NDS exactly
matches the Hardware Test 5 package, preserving the existing extraction and
save identity.

`tools/build_windows_packager.py` verifies downloaded build dependencies,
builds in a ROM-free image context, freezes offline and optionally runs the
isolated executable suite. Windows paths and legacy console encodings are
handled, and DS save paths in reports consistently use forward slashes.

The executable passes 47 acceptance assertions under Wine. Builder tests pass
11 checks there, with the unsupported symlink-creation case explicitly skipped;
macOS passes all 12. The generated NDS also has a dedicated patched-emulator
acceptance report. See `docs/packager-cli.md` for commands and evidence.
Native Windows validation, Authenticode and the existing public-distribution
licensing/notices work remain open.
