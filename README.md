# GBA DS

Play **Metroid Fusion** on the top screen of a Nintendo DS-family system, with
its live exploration map on the bottom screen. A command-line packager combines
your own GBA ROM and BIOS with an enhanced GBARunner3 runtime to create one
`Fusion.nds` file. Zelda: A Link to the Past is also supported, with a live
touch inventory and world/dungeon maps on the bottom screen in `Zelda.nds`.

The map follows Samus across Main Deck and all six sectors. Gold highlights the
current room; white marks Samus. Gameplay is centered at the original 240×160
resolution, with black borders.

> **Preview status:** packagers target Apple Silicon macOS and Windows x64.
> [Downloads and releases](https://github.com/kennethdamica/metroid_fusion_gba_ds/releases). Licensing status and platform-test limits are documented in
> [release readiness](docs/releasing.md). This repository
> contains source and build instructions, not a game ROM, BIOS, or generated NDS.

## Create the NDS ROM

Use a standalone `gba-ds-pack` build for your platform. End users do not need
Python, Docker, Wine, a compiler, or an emulator. To build the tool yourself,
follow the [developer guide](docs/development.md). Each executable supports both
games; download the ZIP for your operating system and extract it first.

You provide:

- **Metroid Fusion (USA), original revision**, 8 MiB; ROM SHA-1
  `ca33f4348c2c05dd330d37b97e2c5a69531dfe87`.
- Or **A Link to the Past & Four Swords (USA), revision 0**, 8 MiB; ROM SHA-1
  `a272055abbbf6c26b0cd54c87395d01699589161` (ALttP adventure).
- The original **16 KiB GBA BIOS**, as `bios.bin` or a ZIP containing that file.

Windows PowerShell:

```powershell
.\gba-ds-pack.exe "Metroid Fusion (USA).gba" --bios bios.bin -o Fusion.nds
```

macOS Terminal:

```sh
./gba-ds-pack "Metroid Fusion (USA).gba" --bios bios.bin -o Fusion.nds
```

The game is detected automatically. `-o` selects a destination; it defaults to
`Fusion.nds` or `Zelda.nds` in the current directory. Existing output files are
refused and inputs are left unchanged. Unknown hashes are rejected by default.
To try a variant, use `--game fusion` or `--game alttp` together with
`--allow-unsupported-rom`. Compatibility checks still apply; passing them does
not guarantee a modified ROM works. Each ROM hash gets a separate save folder.

Use `--help`, `--list-games`, or `--inspect Fusion.nds` for more information.
The [CLI guide](docs/packager-cli.md) covers JSON output, optional manifests,
build provenance and validation.

## Run on your console

1. Copy the generated file to the flashcart SD root as **`Fusion.nds`** or **`Zelda.nds`**.
2. Keep any existing **`_fusion`** and **`_alttp`** folders and saves. Leave about **9 MiB** free
   beyond the NDS file for extraction.
3. Launch through a compatible DLDI flashcart launcher. First launch extracts
   the bundled data; subsequent launches verify and reuse it.

Saves are separate files on the SD card, so replacing the NDS does not replace
your save. The current runtime identifies itself as **Hardware Test 5** during
startup. See [troubleshooting](docs/troubleshooting.md) for boot and save details.

## Compatibility and testing

| Component | Current evidence |
| --- | --- |
| 3DS with DSpico, DSi mode | Boot fix and subsequent display/map changes reported working on the maintainer's console |
| Original DS / DS Lite | Intended flashcart targets; physical acceptance testing remains open |
| Apple Silicon macOS packager | Native executable tested on macOS 14.4 |
| Windows x64 packager | Both-game local checks under Wine; CI tests the ROM-free CLI natively on Windows |
| Patched melonDS on macOS | Gameplay, maps, package extraction, repeat launch and save checks pass |
| Stock melonDS | The tested stock build fails this runtime path; use the project's patched core |

Sector tests use controlled emulator warps after gameplay begins. They do not
establish full-game compatibility or physical-console performance. DSi internal
SD launching is not supported by the extractor. Preview executables are not
Developer ID/notarized or Authenticode-signed releases.

## Development

The DS runtime is ARM C/C++ and assembly layered over pinned GBARunner3 sources.
Python provides packaging, builds and local emulator automation. Windows builds
use Windows Python/PyInstaller under Wine; the finished `.exe` is self-contained.

| Location | Contents |
| --- | --- |
| [`runtime/`](runtime/) | Map renderer, first-launch extraction and boot diagnostics |
| [`patches/`](patches/) | GBARunner3 integration and melonDS fixes |
| [`tools/`](tools/) | Build, packaging and emulator scripts |
| [`tests/`](tests/) | Original diagnostic programs, input scripts and host tests |
| [`release/packager/`](release/packager/) | Runtime/dependency locks and distribution notices |
| [`docs/`](docs/README.md) | Setup, architecture, validation and historical research |

Start with [development setup](docs/development.md) and
[contribution guidelines](CONTRIBUTING.md). Downloaded dependencies, local game
fixtures, saves and generated artifacts are ignored. Public CI checks source
files and the CLI without game data; gameplay tests run locally with supplied
inputs. Pushes to `main` also build tested packager artifacts; version tags
automatically publish prereleases. See [GitHub and release automation](docs/github-setup.md).

## Credits and licensing

Built on [GBARunner3](https://github.com/Gericom/GBARunner3),
[libtwl](https://github.com/Gericom/libtwl), devkitARM/libnds and FatFs. Emulator
work uses [melonDS DS](https://github.com/JesseTG/melonds-ds) and
[melonDS](https://github.com/melonDS-emu/melonDS). The adapter references pinned
[Metroid Fusion decompilation definitions](https://github.com/metroidret/mf/tree/8614cc3eec194092cd756d6382c879b4c2ab4967);
map graphics are read from the user's ROM at runtime.

See [licensing status](LICENSING.md) and
[third-party notices](release/packager/THIRD_PARTY_NOTICES.txt). No project
license has been selected yet; a public repository is not itself a grant of
redistribution rights. This project is independent of Nintendo.
