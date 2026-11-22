# Troubleshooting

## The packager rejects my input

Only original-revision **Metroid Fusion (USA)** is supported. Its SHA-1 is
`ca33f4348c2c05dd330d37b97e2c5a69531dfe87`; modified ROMs and other revisions
are rejected. The BIOS must match the original 16 KiB GBA BIOS. DS firmware is
not a substitute. A BIOS ZIP must contain exactly one 16 KiB file.

Use quoted paths when filenames contain spaces. `--list-games` lists supported
inputs and `--help` describes the options. Files are processed locally.

## The output already exists

Choose another `-o` filename or move the existing output yourself. The packager
never overwrites an existing NDS. With `--manifest`, the companion report must
also have a new destination. Check available disk space and write access if
creation fails for a new path.

## The console stops at a logo or boot stage

Use the current validated Hardware Test 5 runtime and a writable flashcart SD
with a compatible DLDI launcher. For the fallback launch path, the file must be
named `Fusion.nds` at the SD root. Keep the existing `_fusion` directory.

Record the test label, boot stage, DS/DSi mode, console, flashcart and launcher
version when reporting a problem. The earlier `01 CORE READY` freeze on
3DS/DSpico was fixed by preserving ARM interworking behavior; see the
[hardware investigation](hardware-debug.md).

DSi mode on a DLDI flashcart is distinct from launching through the console's
internal SD. The extractor does not support internal-SD mode.

## melonDS extracts successfully but gameplay is blank

Use the project's patched core. The tested stock interpreter mishandles ARM9
data aborts used by GBARunner3, so extraction can succeed while guest execution
fails. [Developer setup](development.md) explains how to build the patched core.
Also use the locked diagnostic runtime: the separate non-diagnostic template
has its own known execution stall.

## Where is my save?

The console writes a separate file:

```text
/_fusion/ca33f4348c2c05dd330d37b97e2c5a69531dfe87/rom.sav
```

ROM, BIOS and configuration extraction data live in the `v1/` directory under
the same ROM hash. Replacing the NDS preserves that save identity. Two packages
of the same supported ROM intentionally share the save. Keep the entire
`_fusion` directory when moving to another SD card; deleting it also deletes
your save. The save is not written into the NDS or the desktop packager.

## Windows preview status

The x64 executable is standalone and has passed Wine-based CLI tests. Native
Windows 10/11 validation and Authenticode signing remain open. Report the exact
Windows version and error text if it does not start. Wine is a developer build
tool here, not an installation requirement for Windows users.
