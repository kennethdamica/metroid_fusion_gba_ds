# Historical baseline experiments — superseded

> Historical development record. Some status, commands and artifact paths describe
> earlier builds. Start with the [current README](../../README.md) and
> [developer guide](../development.md) for current instructions.

These notes record the initial stock-emulator failure. See [README.md](../../README.md) for the working patched-core setup. Do not follow the old direct-boot hardware instructions below: games with saves must receive a writable ROM path through `argv[1]` to avoid overwriting the ROM via the fallback path.

See [project_summary.md](project_summary.md) for the product and [implementation_plan.md](implementation_plan.md) for the staged implementation plan.

## Baseline status — November 19, 2026

The **unmodified GBARunner3 build works on this Apple Silicon Mac** using Docker Desktop and the upstream devkitARM r65 container. Two clean builds produced the same 205,312-byte NDS file:

`6a3f82c4b998b9e58aadb1c275d03df182cce83994f8691d7843cf622833522d`

**Mac DS automation works, but GBARunner3 gameplay in melonDS is not working yet.** The original DS diagnostic passes ten checks covering two screens, press/release input, DLDI file reads, writes, and host synchronization. GBARunner3 displays its splash screen, then fails to reach the expected GBA diagnostic display or Fusion gameplay. Standalone melonDS 1.1 also showed a splash followed by two black screens. No physical DS has been tested.

| Experiment | Result | Local evidence |
|---|---|---|
| Two clean upstream builds | Identical binary hashes | `artifacts/baseline/{first-build-manifest,manifest}.json` |
| Native melonDS DS 1.4.0, DS diagnostic | Ten assertions pass | `artifacts/nds-probe-final/` |
| Deliberately incorrect assertion | Ten real assertions pass; intentional failure returns exit 1 | `artifacts/nds-probe-final-negative/` |
| GBARunner3 + original GBA probe, interpreter | Blank display; guest marker absent at frames 600, 750, 900; four assertions fail | `artifacts/gbar3-probe-assert/` |
| GBARunner3 + Fusion, interpreter | Black screens through frame 1200; observation only | `artifacts/gbar3-fusion-interpreter/` |
| Fusion, interpreter, BIOS intro skipped | Black screens through frame 1200; observation only | `artifacts/gbar3-fusion-skip/` |
| Fusion, JIT | Execution-error loop; 45-second timeout, last captured frame 600 | `artifacts/gbar3-fusion-jit/` |
| Original GBA probe, BIOS intro skipped | Repeated abort at guest code `0x0220013C`; 45-second timeout | `artifacts/gbar3-probe-skip/` |
| Standalone melonDS 1.1, interpreter | Splash then black screens, observed in GUI; stopped after test | `artifacts/standalone-fusion/` (SD data) |

Data abort messages alone are not evidence of a defect: GBARunner3 deliberately uses MPU abort handlers to emulate GBA memory accesses. The failed guest assertions, unchanged output, and timeouts establish the failure. An emulator CPU/MPU/cache interaction is a hypothesis, not a diagnosed root cause. See the [upstream technical manual](https://github.com/Gericom/GBARunner3/blob/ecaa817815d9761745606592f04affe5ee9c3731/docs/Technical%20Reference%20Manual/main.tex).

## Build on this Mac

Prerequisites: Docker Desktop running, Git, native Python 3.13+, and network access for initial downloads. Run these commands from this folder:

```sh
python3.13 tools/setup_emulator.py
.venv/bin/python tools/build_baseline.py --clean
.venv/bin/python tools/build_probes.py
```

The setup script downloads the official [melonDS DS v1.4.0 ARM64 release](https://github.com/JesseTG/melonds-ds/releases/tag/v1.4.0), verifies its SHA-256, and installs pinned Python dependencies into `.venv`. It does not install software globally. Standalone melonDS is optional; the downloaded copy is `.tools/melonds/melonDS.app`.

The build script checks out GBARunner3 commit `ecaa817815d9761745606592f04affe5ee9c3731` and libtwl `e069645bed14a93e149e873e9273f04851e3a04e`. It refuses tracked source changes or a different checkout. It runs serial `make`, matching the [upstream workflow](https://github.com/Gericom/GBARunner3/blob/ecaa817815d9761745606592f04affe5ee9c3731/.github/workflows/nightly.yml); parallel recursive make failed due to shared outputs in this checkout.

The toolchain is pinned to `devkitpro/devkitarm@sha256:a998edf6b06416b5c053edbcd879abfa22b1b88e9cd3f267f5c4ee9fec71a93a`, `linux/amd64` under Docker Desktop's emulation. Inspected versions: devkitARM r65, GCC 14.2.0, libnds 1.8.3, ndstool 2.3.1. Container builds have networking disabled and mount only the relevant source directory.

Outputs:

- `artifacts/baseline/sdcard/GBARunner3.nds` and `_gba/configs/`: deployable baseline.
- `artifacts/baseline/debug/`: ELF and map files.
- `artifacts/baseline/build.log` and `manifest.json`: build evidence.
- `tests/nds_probe/probe.nds` and `tests/gba_probe/probe.gba`: original diagnostic programs.

## Prepare local BIOS and ROM

The supplied Fusion ROM is the US release, SHA-1 `ca33f4348c2c05dd330d37b97e2c5a69531dfe87`. The supplied GBA BIOS is 16 KiB, SHA-256 `fd2547724b505f487e6dcb29ec2ecff3af35a841a77ab2e85fd87350abd36570`. Input files are preserved; extracted copies and emulator saves stay local and ignored.

```sh
.venv/bin/python tools/prepare_sd.py \
  --bios gba_bios.zip --rom 'Metroid Fusion (USA).gba' \
  --output fixtures/local/fusion-new

.venv/bin/python tools/prepare_sd.py \
  --bios gba_bios.zip --rom tests/gba_probe/probe.gba \
  --probe --output fixtures/local/probe-new
```

Each destination must be new to protect existing saves. `--skip-intro` creates an explicit GBARunner3 setting for the BIOS-intro experiment. The GBA probe uses `--probe` to disable capture/centering and saving. Fusion otherwise uses upstream defaults.

The prepared hardware folder is already at `artifacts/hardware-fusion/sdcard/`. Its contents are `GBARunner3.nds`, `rom.gba`, and `_gba/` with BIOS/configs. Copy those contents to the flashcart SD root, preserving any existing saves, then launch the NDS executable. This is a deployment package, **not hardware validation**.

## Run automated tests

Use a fresh output directory for every invocation:

```sh
.venv/bin/python tools/emulator_test.py \
  --rom tests/nds_probe/probe.nds \
  --output artifacts/my-ds-test --assert-probe

.venv/bin/python tools/emulator_test.py \
  --rom artifacts/baseline/sdcard/GBARunner3.nds \
  --sd-dir fixtures/local/probe-new --output artifacts/my-gba-test \
  --frames 900 --capture 600,750,900 --timeout 45 \
  --press-a-start 650 --press-a-end 800 --assert-gba-probe \
  --expect-pixel 600,8,8,251,0,0 --expect-pixel 750,8,8,251,251,0

.venv/bin/python tools/emulator_test.py \
  --rom artifacts/baseline/sdcard/GBARunner3.nds \
  --sd-dir fixtures/local/fusion-new --output artifacts/my-fusion-test \
  --frames 1200 --capture 60,240,600,1200 --timeout 45
```

The GBA test currently **fails**; keep it as a regression target. The Fusion command collects evidence and reports `observed`, not `passed`. Add `--jit` to compare the emulated CPU recompiler. `--force-failure` verifies failure reporting. Input intervals use zero-based frame indices; screenshot names use completed frame counts starting at one.

Each run copies its SD fixture, creates isolated writable state, and writes PNG screenshots (combined and individual screens), main-RAM snapshots, bounded native logs, `result.json`, and `junit.xml`. Snapshots map DS main RAM starting at `0x02000000`; they do not directly represent every GBA memory region. The GBA probe's marker and frame counter are at offsets 0 and 4. Pixel comparisons use 251 for maximum channels because that is the pinned software renderer's observed output.

Exit codes: 0 for passed assertions or an explicitly marked observation, 1 for failed assertions/errors, 124 for timeout. Observation-only JUnit cases are skipped. An emulator crash or timeout is never a pass. Logs retain the first 1 MiB and last 16 KiB so a native error loop cannot fill the disk. RAM/SD artifacts can contain the local ROM and BIOS; they are excluded from version control.

Inside Codex's macOS sandbox, Docker access and melonDS shared-memory creation require the normal execution approval path. A sandbox `shm_open` failure is distinct from a GBARunner3 compatibility failure.

## Next implementation gate

1. Run this exact baseline package on DS/DS Lite with DSPico and record Fusion boot/gameplay. This separates a build/runtime failure from emulator compatibility.
2. Investigate the minimal GBA probe with a debugger-enabled melonDS build: trace the BIOS-to-ROM handoff, MPU exception return, instruction cache behavior, and the stalled guest load. Keep upstream GBARunner3 unchanged for comparisons.
3. Require a passing guest marker, advancing frame counter, and input response before using melonDS to gate GBARunner3 changes.
4. Then implement static secondary-screen rendering and the Fusion memory adapter from the implementation plan, measuring on real hardware. The current DS diagnostic can already test renderer/input/storage behavior independently.

No dual-screen runtime feature has been added yet. Upstream source remains unmodified, and no ROM, BIOS, build, or report has been uploaded.
