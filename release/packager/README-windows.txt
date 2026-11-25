gba-ds-pack 0.2.0 — preview

On Windows, no Wine installation is needed.
One executable creates DS packages for Metroid Fusion and Zelda: A Link to
the Past & Four Swords (ALttP adventure). Supply your own ROM and GBA BIOS.
No Python, Docker, emulator or compiler installation is needed. Works offline.
No game ROM, game graphics or BIOS is included.

USAGE (Windows x64, PowerShell)

  .\gba-ds-pack.exe "Metroid Fusion (USA).gba" --bios bios.bin -o Fusion.nds
  .\gba-ds-pack.exe "Zelda ALttP (USA).gba" --bios bios.bin -o Zelda.nds

The game is detected by SHA-1. Both supported originals are US revision 0,
8 MiB. Run --list-games to see the exact hashes. The original 16 KiB GBA BIOS
can be a .bin or ZIP containing exactly one such file.

EXPERIMENTAL VARIANTS

  .\gba-ds-pack.exe "Zelda variant.gba" --bios bios.bin --game alttp --allow-unsupported-rom -o Zelda.nds

Use --game fusion for Fusion variants. Unknown hashes are rejected by default.
The override still checks game, region, revision, size, header and protected
adapter code/data. Zelda graphics used by the adapter also have bounds checks.
It does not support arbitrary hacks, expanded ROMs, other regions or revisions.
Passing these checks is not a compatibility guarantee. Some cosmetic or text
variants may work; engine/inventory changes are deliberately rejected.

Each distinct ROM SHA-1 has separate extracted files and saves. An experimental
variant never automatically imports the original game's save. Integrity checks
still verify the actual supplied ROM during extraction and on subsequent boots.

OUTPUT AND DS USE

Use -o to choose any destination. Defaults are Fusion.nds or Zelda.nds in your
current directory. Existing output files are never overwritten; inputs are read
only. --manifest writes a build report; --json prints machine-readable results.
--inspect FILE.nds verifies a package. --help lists all options.
Exit codes: 0 success, 1 input/file error, 2 usage error, 130 cancellation.

Copy the generated NDS to the flashcart SD root as Fusion.nds or Zelda.nds.
A compatible DLDI launcher and writable SD are required. Leave about 9 MiB extra
free for extraction. Later launches verify and reuse the extracted files.
Keep _fusion and _alttp when replacing packages. Saves live at:

  _fusion/<actual ROM SHA-1>/rom.sav
  _alttp/<actual ROM SHA-1>/rom.sav

Verified originals retain their previous save paths. Do not redistribute your
generated NDS; it contains your game and BIOS.

RELEASE STATUS

Apple Silicon build: ad-hoc signed, not Developer ID signed or notarized.
Windows x64 has a separate executable. Local packaging tests run under Wine;
CI tests the ROM-free CLI on native Windows. Game-package acceptance with user
inputs and Authenticode signing remain outstanding.
Redistribution terms and project licensing remain unresolved as described in
THIRD_PARTY_NOTICES.txt. This is a preview; the documented licensing findings remain unresolved.
