# Standalone command-line packager

`gba-ds-pack` includes both enhanced runtimes in one executable per platform.
It creates an NDS from the user's ROM and original GBA BIOS, entirely offline.
End users do not need Python, Docker, Wine, a compiler or an emulator.
No game ROM, game graphics or BIOS is bundled in the executable.

```sh
./gba-ds-pack "Metroid Fusion (USA).gba" --bios bios.bin -o Fusion.nds
./gba-ds-pack "Zelda ALttP (USA).gba" --bios bios.bin -o Zelda.nds
```

On Windows PowerShell, use `.\gba-ds-pack.exe` with the same arguments.
`--bios` accepts a raw 16 KiB BIOS or a ZIP containing exactly one such file.
The BIOS must match the supported original; the ROM override does not bypass
BIOS validation.

## Game selection and experimental variants

Known originals are detected by SHA-1:

| Adapter | Supported original | SHA-1 |
| --- | --- | --- |
| `fusion` | Metroid Fusion, USA revision 0, 8 MiB | `ca33f4348c2c05dd330d37b97e2c5a69531dfe87` |
| `alttp` | A Link to the Past & Four Swords, USA revision 0, 8 MiB; ALttP adventure | `a272055abbbf6c26b0cd54c87395d01699589161` |

An unknown hash fails by default. To try a variant, explicitly select its adapter:

```sh
./gba-ds-pack "Zelda variant.gba" --bios bios.bin --game alttp \
  --allow-unsupported-rom -o Zelda.nds --manifest
```

Use `--game fusion` for Fusion. The override requires `--game`; the packager
does not guess an unknown ROM's adapter from its filename. An explicit adapter
that conflicts with a known ROM is rejected.

The override relaxes **only the full-ROM identity requirement**. It still
requires the supported game code, region, revision, exact 8 MiB size, valid GBA
header and matching protected code/data ranges. Zelda's adapter graphics also
undergo compressed-stream bounds and map palette-index checks. The protected
range offsets and SHA-256 digests live in `tools/rom_compatibility.json`; no
reference ROM bytes are distributed.

These checks are conservative: engine changes, other regions/revisions and
expanded ROMs remain rejected. Some cosmetic or text variants may pass.
Passing preflight does not establish that a modified ROM plays correctly or
that its maps and touch controls remain compatible. Synthetic padding changes
are used to test the override; they are not evidence of arbitrary hack support.

Experimental builds and inspections print a warning to stderr, including in
JSON mode. Reports identify the actual ROM SHA-1, game, experimental status,
checks performed, extracted-data directory and save path.

## Output and save behavior

`-o` selects any new `.nds` path, creating parent directories if needed. The
default is `Fusion.nds` or `Zelda.nds` in the current directory. Inputs are only
read. Existing packages, companion reports and dangling output symlinks are
never overwritten. `--manifest` adds a companion report; otherwise only the NDS
is created.

```sh
./gba-ds-pack --version
./gba-ds-pack --list-games --json
./gba-ds-pack --inspect Zelda.nds --json
```

Exit codes: 0 success, 1 validation/file error, 2 command usage error,
130 cancellation. Inspection auto-detects either game's package and is read-only.

Copy the output to the flashcart SD root as `Fusion.nds` or `Zelda.nds`.
These names support launchers that supply no launch path. Keep the existing
`_fusion` and `_alttp` directories. A writable DLDI flashcart and about 9 MiB
free beyond each package are required for extraction.

Each ROM has a separate identity:

```text
_fusion/<actual ROM SHA-1>/v1/{rom.gba,bios.bin,config.json}
_fusion/<actual ROM SHA-1>/rom.sav
_alttp/<actual ROM SHA-1>/v1/{rom.gba,bios.bin,config.json}
_alttp/<actual ROM SHA-1>/rom.sav
```

Known originals keep their existing paths. Different variants get distinct
save folders; saves are never automatically copied between them. A second
launch verifies and reuses the extracted files. Replacing an NDS does not
replace its save. Do not distribute a generated NDS containing your ROM/BIOS.

## Manifest and integrity

New templates use manifest ABI 2: the original 76-byte identity record plus a
32-bit flags field. Bit 0 declares an experimental ROM; other bits are rejected.
Manifest version/ABI/length must agree. Actual ROM, BIOS and config SHA-1s are
stored in the manifest. BIOS/config remain pinned; a nonexperimental ROM must
match the selected adapter's known hash.

The extractor derives paths from the manifest's ROM digest, verifies extraction
against that digest, then re-reads the stored bytes before publishing the file.
Later launches hash existing files before reusing them. The override never
suppresses payload integrity checks. A corrupted package still fails. Saves
are outside the extraction replacement paths. These checks detect corruption;
the manifest is not a cryptographic signature or an anti-tampering boundary.

The new inspector/extractor also accept verified ABI 1 manifests. The source
builder can package a known original with an older ABI 1 template, but refuses
experimental variants unless the runtime supports ABI 2. The `v1` data folder
name is retained because the extracted-file layout is unchanged.

On the host, output is staged, flushed and inspected before non-overwriting
publication: macOS `renamex_np(RENAME_EXCL)`, Windows non-replacing rename,
Linux same-directory hard link. Handled failures clean up temporary files.
Power loss can leave a hidden temporary or companion report; multi-file
power-loss atomicity is not promised.

## Automated builds and releases

Pushes to `main` build both native platform executables and retain tested ZIPs
as Actions artifacts. Pushing a matching version tag, such as `v0.2.0`, rebuilds
and publishes a GitHub prerelease with both ZIPs and checksums.
[GitHub publishing](github-setup.md) describes the workflow and release steps.
CI uses no game data; it verifies templates against locally validated hashes.

## Developer builds

Start with [development setup](development.md). Build both runtimes:

```sh
.venv/bin/python -m pip install -r requirements-packager.txt
.venv/bin/python tools/build_dual_screen.py --hardware-diagnostics
.venv/bin/python tools/build_dual_screen.py --game alttp --package-template
.venv/bin/python tools/build_packager.py --output artifacts/packager-0.2.0
```

The freezer checks each template against its build manifest, source hashes and
`release/packager/runtime-lock.json`. Update that lock only after validating the
new packages in patched melonDS. Fusion uses the working hardware-diagnostic
runtime; Zelda uses `artifacts/alttp-package-runtime`.

The explicit data allowlist contains two runtime-only NDS templates, their two
manifests, and the compatibility digest JSON. The freezer does not recursively
collect artifacts, ROMs, BIOS files, saves or generated game packages.
Templates with populated NitroFS or mismatched checksums are rejected.

Windows x64 can be built on this Mac with the pinned Windows CPython/PyInstaller
under Wine in Docker:

```sh
.venv/bin/python tools/build_windows_packager.py \
  --output artifacts/packager-0.2.0 \
  --test-output artifacts/packager-0.2.0-windows-test
```

The helper verifies cached/downloaded Python and wheel checksums; its Docker
build context is allowlisted. Freezing/testing run with networking disabled.
Windows users receive a real standalone PE executable and need none of these
developer dependencies. Native Windows developers can instead run
`tools/build_packager.py` with the same runtime artifacts and pinned Python
requirements. Wine testing does not replace native Windows testing.

Outputs under the chosen build directory:

- `macos-arm64/gba-ds-pack` and `windows-x86_64/gba-ds-pack.exe`.
- `gba-ds-pack-0.2.0-<platform>-preview.zip`, including usage and license notices.
- Per-platform `build.json`, recording executable, runtime and source hashes.

Generated files are ignored and are not in Git. Publish only the intended
ROM-free platform ZIPs as release assets when ready; do not add artifacts to
source control. Existing output directories are refused.

## Validation

```sh
.venv/bin/python -m unittest discover -s tests/public -v
.venv/bin/python -m unittest discover -s tests/package -v
.venv/bin/python -m unittest discover -s tests/alttp -v
.venv/bin/python tools/test_package_variants.py --output artifacts/variant-test-new
.venv/bin/python tools/test_packager_cli.py \
  --executable artifacts/packager-0.2.0/macos-arm64/gba-ds-pack \
  --output artifacts/packager-0.2.0-macos-test
```

Local tests require user-supplied game/BIOS files. The executable test runs the
actual binary from an isolated Unicode directory with an empty PATH. It tests
both games, the experimental override, save paths, compatibility rejection,
JSON output, read-only inspection, existing-file protection and the frozen data
allowlist. Generated packages must match the gameplay-tested release hashes.

`tools/test_packaged_fusion.py` exercises full gameplay, first extraction,
second launch, save preservation, interrupted extraction recovery and corrupted
payload/bounds rejection. `tools/test_alttp.py` exercises gameplay, inventory,
maps and repeat launch. `tools/test_package_variants.py` tests extraction/reuse,
variant/original save isolation, payload corruption and manifest opt-in checks
for both games. It uses synthetic identity changes, not third-party hacks.

## Menu banners and release status

Both packages have original code-drawn icons and game-specific titles:
**Metroid Fusion / DS** and **The Legend of Zelda / A Link to the Past / DS**.
`tools/nds_banner.py` updates all six language titles and CRC, rejecting overlap
with executable or filesystem data.

This remains a local preview. macOS has an ad-hoc signature, not Developer ID
signing/notarization. Windows is unsigned; native Windows game-package acceptance is
outstanding (CI covers the ROM-free executable). See [release readiness](releasing.md) and
[third-party notices](../release/packager/THIRD_PARTY_NOTICES.txt) for unresolved
redistribution terms and project licensing. No publication occurs during a build.
