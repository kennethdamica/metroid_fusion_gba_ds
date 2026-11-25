One standalone packager per platform, supporting **Metroid Fusion** and
**Zelda: A Link to the Past**. Supply your own supported GBA ROM and BIOS;
no Python, Docker or emulator installation is required.

- Windows x64: extract the Windows ZIP and run `gba-ds-pack.exe`.
- Apple Silicon macOS: extract the Mac ZIP and run `./gba-ds-pack`.
- Run `--help` for commands or `--list-games` for supported ROM identities.
- Experimental variants require `--game` plus `--allow-unsupported-rom`.
  Compatibility checks still apply; each ROM hash has separate saves.

These archives contain the executable, usage guide, build provenance and
third-party notices. `SHA256SUMS` covers both downloads. **Do not upload your
ROM, BIOS, saves or generated game-containing NDS files to this release.**

CI rebuilds the DS runtimes and requires the locally gameplay-tested template
hashes. It tests the standalone CLI natively on Windows and macOS without game
data. Gameplay, touch controls, maps and save tests use private local inputs;
they are not run on GitHub. Synthetic variant tests do not establish general
ROM-hack compatibility.

Preview builds are unsigned on Windows and ad-hoc signed on macOS, without
Apple notarization. Physical-console and full native-Windows game-package
acceptance remain separate checks. Existing licensing findings and known
notices are retained in the source repository; this prerelease does not resolve
the documented upstream-permission questions.
