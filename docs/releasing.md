# Release readiness

For the actual upload steps, use [GitHub setup](github-setup.md). The maintainer
has chosen to defer unresolved upstream-permission questions; those findings
remain recorded below. Known notices and GPL patch attribution have been added.
This checklist is an inventory of release considerations, not an approval flow.

The repository is public. The release workflow builds platform ZIPs on `main`
and publishes prereleases on version-tag pushes after all checks pass. A local
build alone does not publish anything. See [GitHub automation](github-setup.md).

The [licensing review](licensing-review.md) identifies the specific open items:
GBARunner3 permission, older-pinned libtwl coverage, GPL patch notices, copied
diagnostic templates, and binary dependency notices. Current libtwl has a zlib
license; the question is coverage of our older pin, not absence of any license.

## Source publication checks

- [ ] Choose a license for original project contributions and review the
  provenance/terms of patches derived from upstream code. See
  [licensing status](../LICENSING.md).
- [ ] Review the exact Git index and any existing history for private data.
  `.gitignore` does not remove files already committed.
- [ ] Run `python3 tools/check_repository.py` and the public test suite.
- [ ] Ensure the README describes actual compatibility, test limits and
  availability; add download links only once real releases exist.

The source checker catches excluded directories, common private/generated file
types, non-text files, personal home paths and broken local Markdown links in
the candidate source tree. It is not a comprehensive secret or history scanner.

## Before publishing a packager binary

- [ ] Resolve GBARunner3/libtwl distribution terms and finish runtime/host
  dependency notices and any required source distribution.
- [ ] Build from reviewed source with the validated runtime lock.
- [ ] Run the frozen-executable suite and inspect its bundled-file audit.
- [ ] Run local package/emulator acceptance on the generated NDS, including
  extraction, subsequent launch and save preservation.
- [ ] Test the Windows executable on native Windows 10/11, including paths,
  output publication and NTFS symlink behavior. Wine coverage is recorded
  separately.
- [ ] Complete intended Authenticode and macOS Developer ID/notarization flows;
  test final signed artifacts and regenerate their checksums.
- [ ] Record console/flashcart/launcher versions and hardware results without
  presenting emulator coverage as a full hardware compatibility matrix.
- [ ] Review each final ZIP. Ship the packager, notices and provenance only;
  exclude game inputs, generated game-containing NDS files, saves and dumps.

Build commands and artifact layout are in the [CLI guide](packager-cli.md).
Use release assets for executable ZIPs and checksums, not Git history. Do not
upload the whole local `artifacts/` directory: it contains private game data.

## Current evidence

Local Mac and Windows packagers generate the same validated NDS bytes. The
0.2.0 preview passed 81 standalone CLI assertions per platform (Windows under
Wine), 88 Zelda gameplay/inventory/map assertions, Fusion gameplay and save
acceptance, and 34 experimental-variant extraction/isolation checks in patched
melonDS. Both templates reproduce their tested hashes from clean builds.
Hosted CI additionally runs a ROM-free native executable test on Windows and
macOS; native Windows packaging with real game inputs remains a separate check.
Raw private-input gameplay reports are not included in a fresh clone.
