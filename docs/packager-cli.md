# Standalone command-line packager

`fusion-pack` creates a dual-screen Fusion `.nds` using a local, user-supplied
ROM and BIOS. The executable includes the prebuilt enhanced runtime and its
own Python interpreter. End users need no project checkout, Python, Docker,
compiler or emulator. It performs no network requests.

```sh
./fusion-pack "Metroid Fusion (USA).gba" --bios bios.bin -o Fusion.nds
```

On Windows x64, extract the Windows ZIP and run this in PowerShell:

```powershell
.\fusion-pack.exe "Metroid Fusion (USA).gba" --bios bios.bin -o Fusion.nds
```

Only the executable and your own inputs are needed. Python, Wine and Docker
are not Windows end-user requirements. The output can be any new `.nds` path
on your filesystem, for example `-o "C:\Users\You\Desktop\Fusion.nds"`.

`--bios` also accepts a ZIP containing exactly one 16 KiB BIOS file. The only
supported game is the original US Fusion revision, SHA-1
`ca33f4348c2c05dd330d37b97e2c5a69531dfe87`. Other games, revisions and modified
ROMs are rejected. The BIOS is also verified. These identities are centralized
in `tools/fusion_profile.py`, rather than imported from emulator test code.

The `-o` path selects where the finished NDS is saved on the user's filesystem.
Its default is `Fusion.nds` in the current working directory. Parent folders
are created as needed. The program generates only one NDS unless `--manifest`
is requested. Existing output files, report files and dangling output symlinks
are refused. The input ROM and BIOS are never modified.

```sh
./fusion-pack --version
./fusion-pack --list-games
./fusion-pack --inspect Fusion.nds
./fusion-pack "Metroid Fusion (USA).gba" --bios gba_bios.zip \
  -o "My games/Fusion.nds" --manifest --json
```

Success is exit 0; input/file errors are exit 1, usage errors 2, cancellation
130. `--json` prints structured results, while ordinary output gives the saved
path, size, checksum and flashcart instructions. Inspection does not change
the file.

The DS package format, extraction directory and save identity are unchanged.
Copy the finished NDS to the flashcart SD root as `Fusion.nds`, retaining the
existing `_fusion` directory. Game saves are written on the flashcart SD by
the runtime; they are not written into the host executable or NDS.

## Safe output publication

The builder writes to a unique temporary file in the destination directory,
flushes/syncs it, and validates the completed NDS before publishing its final
name. macOS uses `renamex_np(RENAME_EXCL)` so a destination created concurrently
cannot be overwritten. Windows uses non-replacing rename; the Linux path uses
a same-directory hard link and therefore requires a filesystem supporting it.
Unsupported filesystems fail safely rather than falling back to overwriting.

Optional manifests are staged before publication as well. A failed NDS
publication removes the newly created manifest only if its file identity still
matches. Handled write failures/cancellation remove temporary files. A sudden
process kill or power loss can leave a hidden temporary file or a report
without its NDS; no claim of multi-file or power-loss atomicity is made.

## Build

For a fresh clone, first follow [developer setup](development.md) to create the
Python environment and fetch/build the pinned baseline. Paths under `artifacts/`
below are local outputs, not files shipped in the source repository.

```sh
.venv/bin/python -m pip install -r requirements-packager.txt
.venv/bin/python tools/build_dual_screen.py --hardware-diagnostics
.venv/bin/python tools/build_packager.py
```

The first delivered build is Apple Silicon macOS, tested on macOS 14.4. The
build refuses an existing destination; use `--output artifacts/packager-next`
for another build. Build dependencies are pinned separately from emulator
dependencies. PyInstaller creates an executable specific to the host OS and
architecture; Intel macOS and Linux still need their own builds and tests.
See [PyInstaller's platform model](https://pyinstaller.org/en/stable/operating-mode.html).

### Windows x64

The Windows executable is frozen by Windows CPython 3.13.7 and Windows
PyInstaller 6.22.3. On this Mac they run under Wine 10 in a Linux amd64
container; the result is a Windows PE executable, not a script or Wine wrapper.
The developer helper downloads official CPython NuGet and PyPI wheels,
verifies the hashes in `release/packager/windows-downloads.json`, and uses
`release/packager/windows.Dockerfile` with a pinned Debian base. Debian apt
packages are not snapshot-pinned; this records a repeatable workflow rather
than promising bit-identical host executables across future rebuilds.

With Docker running and the validated hardware runtime already built:

```sh
.venv/bin/python tools/build_windows_packager.py \
  --output artifacts/packager-next \
  --test-output artifacts/packager-next-windows-test
```

The image build context contains only allowlisted Python/build wheels. The
freezer and tests run locally with container networking disabled. Tests require
the local ROM/BIOS; neither input is embedded in the executable or release ZIP.
`--test-output` is optional when building without those inputs.

A developer on native Windows can instead use 64-bit Python 3.13, install
`requirements-packager.txt`, and run `tools/build_packager.py` followed by
`tools/test_packager_cli.py`. Supply the exact runtime and its manifest at
`artifacts/hardware-runtime`; the checksum/source-input checks still apply.
That native workflow needs no Docker or Wine. Native Windows 10/11 testing is
still required before calling this preview Windows-release-ready.

Windows outputs:

- `artifacts/packager/windows-x86_64/fusion-pack.exe`: standalone executable.
- `artifacts/packager/fusion-pack-0.1.0-windows-x86_64-preview.zip`: executable,
  Windows usage guide, provenance and available license notices.
- `artifacts/packager/windows-x86_64/build.json`: input/output hashes and build
  environment. The executable is unsigned; Authenticode is a release task.

Mac outputs:

- `artifacts/packager/macos-arm64/fusion-pack`: standalone executable.
- `artifacts/packager/fusion-pack-0.1.0-macos-arm64-preview.zip`: executable,
  usage guide, provenance, available license notices and build manifest.
- `artifacts/packager/macos-arm64/build.json`: source/template/executable hashes.

The freezer has an explicit data allowlist: the runtime-only
`FusionTemplate.nds` and its manifest. It does not recursively collect
`artifacts`, `fixtures`, game packages, ROMs or BIOS files. The build rejects a
template with populated NitroFS, a mismatched checksum or stale source inputs.
The template must also match `release/packager/runtime-lock.json`, which pins
the fully tested Hardware Test 5 runtime. The startup diagnostic label is kept.

The initial packaging test exposed a stall in the separate non-diagnostic
`artifacts/package-runtime` template. Container checks and its earlier border
smoke test passed, but guest execution did not advance. That template is not
used by this release. Its failed full run is retained under
`artifacts/packager-emulator-test`, and the rejected executable under
`artifacts/packager-rejected-standard`. The CLI and developer packager now
default to `artifacts/hardware-runtime`.

## Validation

```sh
.venv/bin/python -m unittest discover -s tests/package -v
.venv/bin/python tools/test_packager_cli.py \
  --executable artifacts/packager/macos-arm64/fusion-pack \
  --output artifacts/my-packager-test
.venv/bin/python tools/test_packaged_fusion.py \
  --package artifacts/my-packager-test/Fusion.nds \
  --output artifacts/my-packager-emulator-test
```

The executable test copies only the binary and explicitly supplied input files
to a fresh temporary folder outside the checkout, empties `PATH`, and exercises
paths with spaces/Unicode, raw/ZIP BIOS, default/custom output, JSON, optional
reports, inspection, invalid inputs, filesystem failures and existing-file
protection. Its NDS must match the reference builder exactly. It also opens
the frozen archive and audits its runtime files and proprietary-payload hashes.

Builder tests cover write/sync failure cleanup, a destination created during
publication, dangling symlinks, runtime tampering, format corruption and
reproducibility. Emulator acceptance uses the NDS produced by the actual
standalone binary, including first extraction and repeat-launch save checks.

Current preview evidence:

- `artifacts/packager-cli-verified/result.json`: 44/44 standalone CLI and
  frozen-content assertions. The binary runs with an empty `PATH` outside
  the checkout and produces Hardware Test 5 byte for byte.
- `tests/package/test_builder.py`: 12/12 builder tests, including failed writes
  and a concurrent destination-file race.
- `artifacts/packager-verified/result.json`: package acceptance on the generated
  NDS. Its 30,000-frame first-boot evidence is reused from the exact same NDS
  and core hashes in `artifacts/screen-framing-dev/test2/first-boot`; subsequent
  launch, save and recovery/rejection checks run again.
- The final executable passes `codesign --verify --strict`; this confirms the
  local ad-hoc signature, not Developer ID signing or notarization.

Windows preview evidence:

- `artifacts/packager-windows-cli-verified/result.json`: 47/47 assertions on
  the actual `.exe` under Wine 10, running from an isolated Unicode directory
  with an empty PATH. It generates the exact gameplay-validated NDS hash
  `245d9b92dffb48f854a9e2bd0f466c03b3f217c4f540950a5a284a6d12fd8505`.
- The frozen archive contains Windows Python and its required DLLs plus the
  two allowlisted runtime data files. Its proprietary-payload audit passes.
  The PE header identifies a Windows x86-64 console executable.
- Windows builder suite: 11 passed, one explicitly skipped because Wine's
  symlink API reports success without creating a link. Atomic no-overwrite
  races and failed-write cleanup pass. All 12 tests pass on native macOS.
- `artifacts/packager-windows-emulator-verified/result.json`: acceptance on the
  Windows-generated NDS using the patched Mac melonDS core. First-boot gameplay
  evidence is reused only after exact package/core/input hash checks; repeat
  launch, save preservation and recovery/rejection checks execute again.
- `artifacts/packager/validation-windows.json`: consolidated evidence and
  artifact hashes. These are Wine tests, not native Windows tests; Windows
  10/11, NTFS symlink behavior and signed-download validation remain pending.

## Before public distribution

This is a working local preview, not a cleared public release. No project-wide
redistribution license was found in the pinned GBARunner3/libtwl checkouts;
their terms need clarification, and the remaining runtime dependency notice
audit and this project's licensing need completion. The provenance file names
these open issues rather than assigning an invented license to upstream code.

The Mac executable currently has an ad-hoc signature. A public Mac download
needs the intended Developer ID signing/notarization workflow and testing with
Gatekeeper enabled. See [Apple's distribution guidance](https://developer.apple.com/documentation/security/notarizing-macos-software-before-distribution).
No account credentials, signing identity, upload or public publication have
been used for this preview.
