# Developer setup

Run commands from the repository root. The complete build/emulator workflow
has been exercised on Apple Silicon macOS with Python 3.13, Git, Docker Desktop,
CMake and Xcode command-line tools. End users of the frozen packager do not need
these dependencies.

## Source-only checks

With Python 3.13 and Git installed:

```sh
python3 tools/check_repository.py
python3 -m unittest discover -s tests/public -v
```

These check public source contents, Python/JSON syntax, local Markdown links
and CLI behavior without game inputs. The GitHub workflow runs the same checks
on Ubuntu and Windows. It does not build the DS runtime or test gameplay.

## Build the validated runtime

Start Docker Desktop, then create a local environment:

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements-packager.txt
.venv/bin/python tools/build_baseline.py --clean
.venv/bin/python tools/build_dual_screen.py --hardware-diagnostics --clean
```

The baseline script fetches the pinned GBARunner3 checkout and its submodule.
The enhanced build applies patches to a separate working copy. Docker provides
the pinned devkitARM toolchain; neither build needs a game ROM or BIOS.

The validated template is
`artifacts/hardware-runtime/sdcard/FusionTemplate.nds`. Use
`--hardware-diagnostics`: the separate non-diagnostic package template has a
known execution stall and is not the release template. The
[runtime lock](../release/packager/runtime-lock.json) pins Hardware Test 5.
Do not update that lock just to make a changed build pass.

## Build standalone packagers

For a native Apple Silicon Mac executable:

```sh
.venv/bin/python tools/build_packager.py
```

For a Windows x64 executable built locally on the Mac:

```sh
.venv/bin/python tools/build_windows_packager.py --output artifacts/packager
```

Both use the validated runtime above. Outputs are placed under
`artifacts/packager/macos-arm64/` and `artifacts/packager/windows-x86_64/`, with
platform-specific preview ZIPs beside them. Existing platform output directories
are refused; use `--output artifacts/packager-next` for a subsequent build.

The Windows helper verifies downloaded Windows Python and wheel hashes, builds
an isolated Wine image, then freezes the executable with networking disabled.
The resulting executable requires neither Python nor Wine on Windows.
[The CLI guide](packager-cli.md) also covers native Windows freezing with an
already-built template and the limits of Wine-based testing.

## Generate a local game package

Supply your own original US Fusion ROM and original GBA BIOS. The end-user CLI
accepts explicit input paths; local regression scripts expect
`Metroid Fusion (USA).gba` and `gba_bios.zip` at the repository root.
All game/firmware inputs and generated binaries are ignored.

```sh
.venv/bin/python tools/fusion_pack.py "Metroid Fusion (USA).gba" \
  --bios gba_bios.zip -o artifacts/my-package/Fusion.nds
.venv/bin/python tools/fusion_pack.py --inspect artifacts/my-package/Fusion.nds
.venv/bin/python -m unittest discover -s tests/package -v
```

The package suite explicitly skips when its local game inputs/runtime are
absent. Do not describe that skip as a successful game-packaging test.

Test the actual frozen Mac executable outside the checkout with an empty PATH:

```sh
.venv/bin/python tools/test_packager_cli.py \
  --executable artifacts/packager/macos-arm64/fusion-pack \
  --output artifacts/my-cli-test
```

For Windows, add `--test-output artifacts/my-windows-cli-test` to the Windows
build helper. Both test suites require the local game inputs above and a fresh
output directory. Full generated NDS files stay local.

## Patched emulator acceptance on macOS

Install the emulator dependencies and build the patched interpreter:

```sh
python3.13 tools/setup_emulator.py
.venv/bin/python tools/build_patched_emulator.py
.venv/bin/python tools/test_packaged_fusion.py \
  --package artifacts/my-package/Fusion.nds \
  --output artifacts/my-package-test
```

The setup script is Apple Silicon-specific. The tests use the patched libretro
core, not a downloaded stock melonDS app. Acceptance covers first extraction,
gameplay/map checks, subsequent launches, save preservation, interrupted
extraction and corrupt-package rejection. Every test output directory must be
new. Reports, screenshots, saves and memory snapshots stay under ignored local
artifact directories.

Only reuse a previous first-boot report with `--reuse-first-run` when the script
accepts its exact package, core and input hashes. Report that reuse explicitly.
For sector and display tests, see the [map guide](fusion-map.md). Interactive
macOS app setup and original probe commands remain in the
[development record](history/development-log.md); the GUI requires additional
local Qt and library dependencies and is not needed for CLI packaging.

## Runtime changes

The renderer reads original map assets from the supplied ROM at runtime.
Runtime files and integration patches are hashed into the template manifest.
Changing their content requires rebuilding and running relevant gameplay,
package/save and hardware tests before deliberately updating the release lock.
The tight ARM/ITCM/VRAM constraints are documented in the map and hardware guides.
