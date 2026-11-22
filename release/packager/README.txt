fusion-pack 0.1.0 — local preview

Create a dual-screen Fusion NDS using your own game ROM and GBA BIOS.
The executable includes the enhanced GBARunner3 runtime. It works offline;
you do not need Python, Docker, an emulator, or a compiler.

Supported game: Metroid Fusion (USA), original revision, 8 MiB.
ROM SHA-1: ca33f4348c2c05dd330d37b97e2c5a69531dfe87
BIOS: original 16 KiB GBA BIOS, either .bin or a ZIP containing one such file.
No game ROM or BIOS is distributed with this tool.

USAGE

  ./fusion-pack "Metroid Fusion (USA).gba" --bios bios.bin -o Fusion.nds

Choose any destination folder with -o, including paths containing spaces.
Without -o, the file is saved as Fusion.nds in your current directory.
Existing files are never overwritten. Choose another output name to rebuild.
The original ROM and BIOS are only read, never modified.
The included runtime is the validated Hardware Test 5 build; that name briefly
appears during DS startup before the game and map.

  ./fusion-pack --help
  ./fusion-pack --list-games
  ./fusion-pack --inspect Fusion.nds

Use --json for machine-readable output, or --manifest to also save a build
report alongside the NDS. Exit codes: 0 success, 1 validation/file error,
2 command-line usage error, 130 cancellation.

ON THE DS

Copy the generated file to the flashcart SD root as Fusion.nds. A compatible
DLDI flashcart launcher and writable SD card are required. Leave about 9 MiB
free beyond the NDS itself for extraction. The first launch extracts the game
and BIOS; later launches reuse them. Keep the _fusion folder and existing
saves when replacing the NDS. Saves stay on the flashcart SD, separate from
the generated NDS. No emulator is needed on the Mac to create the package.

PLATFORM AND RELEASE STATUS

This build targets Apple Silicon macOS. It has an ad-hoc code signature for
local testing; it is not Developer ID signed or Apple-notarized. Intel Macs,
Windows and Linux need separate builds and validation.

This is a local preview, not a cleared public release. GBARunner3/libtwl
redistribution terms, remaining runtime dependency notices, project licensing,
and Apple signing/notarization must be resolved before public distribution.
See THIRD_PARTY_NOTICES.txt. Do not redistribute an NDS containing your ROM
and BIOS as part of the packager release.
