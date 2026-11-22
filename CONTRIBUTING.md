# Contributing

Start with the [developer guide](docs/development.md). The current target is
original-revision US Metroid Fusion with a live bottom-screen map; changes for
other games need their own verified adapter and input profile.

## Reporting a problem

Include the packager version, operating system or console model, flashcart and
launcher version, steps to reproduce, expected behavior and exact error text.
For boot failures, include the displayed hardware-test number, boot stage and
DS/DSi mode. For ROM identification, a checksum is enough.

Keep game ROMs, BIOS files, generated NDS files, saves and RAM dumps out of
issues and pull requests. Remove personal paths from logs before sharing them.
The [bug-report template](.github/ISSUE_TEMPLATE/bug_report.md) prompts for the
useful details.

## Making a change

- Keep changes focused and explain their effect on users.
- Preserve the clean pinned checkout in `vendor/`; put runtime changes in
  `runtime/` and integration changes in `patches/`.
- Preserve save identity and no-overwrite behavior unless a migration is
  explicitly designed and documented.
- Keep display code in ARM mode where required by the
  [hardware interworking fix](docs/hardware-debug.md). Emulator success alone
  does not validate physical hardware behavior.
- Match surrounding code. Do not reformat runtime source or patch context as
  part of a documentation change: those bytes are inputs to the release lock.
- Update the relevant docs and report tests actually run, including skips and
  platform limitations.

Run the source-only checks before submitting:

```sh
python3 tools/check_repository.py
python3 -m unittest discover -s tests/public -v
```

These do not use game data or Docker. Changes to runtime, extraction or saves
also need the relevant local tests in the developer guide. Passing public CI
is not a gameplay or hardware certification.

Review [licensing status](LICENSING.md) before contributing third-party code.
Include attribution and provenance; do not add an assumed upstream license.
