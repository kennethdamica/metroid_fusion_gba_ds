# GitHub publishing and automated releases

The source repository is
[kennethdamica/metroid_fusion_gba_ds](https://github.com/kennethdamica/metroid_fusion_gba_ds).
The project now supports Fusion and Zelda under the **GBA DS** name; the existing
repository URL is retained.

## Push source changes

From the repository root:

```sh
python3 tools/check_repository.py
python3 -m unittest discover -s tests/public -v
git status --short
git add README.md docs tools runtime patches tests release .github .gitattributes
git diff --cached --stat
git diff --cached --name-only
git commit -m "Describe the change"
git push origin main
```

Review the staged paths. They should contain source, documentation, tests,
patches and notices. Never force-add ignored ROMs, BIOS files, saves, generated
NDS files, `vendor/`, `.tools/`, `.venv/` or `artifacts/`. The checker also flags
private files already tracked despite ignore rules. Keep local input files on
your Mac; neither source CI nor release builds require them.

## What CI does

[Source checks](../.github/workflows/source-checks.yml) runs on pushes and pull
requests. [Build packagers](../.github/workflows/release.yml) runs on `main`,
version tags and manual dispatch:

1. Build pinned upstream GBARunner3 and both enhanced DS runtimes on Ubuntu
   using the pinned devkitARM image.
2. Require exact matches with `release/packager/runtime-lock.json` and verify
   the runtime source hashes. Transfer only the two templates and manifests.
3. Freeze one executable on native Windows x64 and one on Apple Silicon macOS.
4. Run public tests and the actual frozen CLI from an isolated directory with
   an empty PATH. Audit the executable's bundled runtime files.
5. Audit the two ZIPs, provenance and license notices, then generate `SHA256SUMS`.
6. On a version-tag push only, publish the tested ZIPs/checksums as a GitHub
   **prerelease**. Ordinary `main` pushes and manual runs produce Actions
   artifacts without publishing a release.

The `public-release` Actions artifact contains both platform ZIPs and checksums.
Build artifacts expire after 30 days; published release assets remain attached
to their release. No game ROM, BIOS, save, memory dump or game-containing NDS is
uploaded by these workflows.

GitHub supplies the workflow token automatically. Only the publish job has
`contents: write`; build jobs have read-only permissions. No personal token,
ROM secret or signing certificate is required. Actions are pinned by commit SHA.

## Publish a version

Update `VERSION` in `tools/fusion_pack.py`, the version assertion in the public
CLI test, and the usage documents. Update release notes if appropriate. If a
runtime changes, complete local gameplay/save tests before updating its lock;
do not bypass the lock to make CI green.

Commit/push those changes and wait for **Build packagers** to pass on `main`.
Then tag that tested commit, using the exact CLI version (example: `0.2.0`):

```sh
git tag v0.2.0
git push origin v0.2.0
```

The tag workflow rebuilds and retests before publishing. Tag and CLI version
must agree. A failed build never publishes a release. Publication starts with
a draft and only makes it public after uploading all assets. Rerunning a failed
publication may complete that draft; an already published release is never
replaced. Do not move an existing version tag: fix the source and publish a new
version instead.

The outputs are `gba-ds-pack-VERSION-macos-arm64-preview.zip`,
`gba-ds-pack-VERSION-windows-x86_64-preview.zip`, and `SHA256SUMS`. Generated
executables belong in release assets, not Git history.

## Test limits

Hosted CI runs no copyrighted game data. Runtime hash checks connect CI builds
to local gameplay evidence; native CLI smoke tests do not establish Windows
game-package acceptance, DS hardware compatibility or arbitrary hack support.
Executables remain unsigned on Windows and ad-hoc signed, without notarization,
on macOS. See [release readiness](releasing.md) and the
[CLI guide](packager-cli.md).

The maintainer has deferred unresolved upstream-permission questions. Identified
notices remain included; automation does not mark those questions resolved.
See [licensing status](../LICENSING.md).

Workflow behavior follows GitHub's documentation for
[hosted runner platforms](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)
and [artifact transfers](https://github.com/actions/download-artifact).
