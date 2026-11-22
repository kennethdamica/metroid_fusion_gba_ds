fusion-pack 0.1.0 - Windows x64 local preview

Create a dual-screen Fusion NDS using your own game ROM and GBA BIOS.
The executable includes the enhanced GBARunner3 runtime and Python runtime.
You do not need to install Python, Docker, Wine, an emulator, or a compiler.
Everything runs locally and offline.

EXAMPLE (PowerShell, from the extracted folder)

  .\fusion-pack.exe "Metroid Fusion (USA).gba" --bios bios.bin -o Fusion.nds

In Command Prompt, use fusion-pack.exe with the same arguments.

SUPPORTED INPUTS

Metroid Fusion (USA), original revision, 8 MiB.
ROM SHA-1: ca33f4348c2c05dd330d37b97e2c5a69531dfe87
Original 16 KiB GBA BIOS (.bin or ZIP containing exactly one 16 KiB BIOS).
No game ROM or BIOS is included in this download.

OUTPUT

Use -o "C:\Users\YourName\Desktop\Fusion.nds" to choose a destination.
Without -o, Fusion.nds is saved in your current working directory.
Existing files are never overwritten; choose a new output name to rebuild.
Your original ROM and BIOS are never modified.

  .\fusion-pack.exe --help
  .\fusion-pack.exe --list-games
  .\fusion-pack.exe --inspect Fusion.nds

--json prints machine-readable results. --manifest also saves a build report.
Exit codes: 0 success, 1 input/file error, 2 usage error, 130 cancellation.

ON THE DS

Copy the generated file to the flashcart SD root as Fusion.nds. Keep your
existing _fusion folder and saves. First launch extracts the game and BIOS;
later launches reuse them. Leave about 9 MiB free beyond the NDS for extraction.
A compatible DLDI flashcart launcher and writable SD card are required.
The included runtime is Hardware Test 5, briefly identified during startup.
Game saves live on the flashcart SD, separately from the NDS.

PLATFORM AND RELEASE STATUS

This is an x64 Windows executable. The developer's Mac build/test environment
uses Windows CPython under Wine; Wine is not needed by Windows end users.
Native Windows 10/11 validation remains a separate release check.
The executable is not Authenticode-signed; publisher reputation has not been
established.

Public release still requires clarification of GBARunner3/libtwl distribution
terms, a complete dependency notice audit and project licensing. See
THIRD_PARTY_NOTICES.txt. This archive contains no Nintendo ROM or BIOS; do not
add your generated game-containing NDS to the public packager download.
