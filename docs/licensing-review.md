# Licensing and provenance review

**Follow-up:** the maintainer chose to defer unresolved upstream-permission
questions and proceed with known-license notices. The original review and its
recommendation below remain an evidence record. Collected notices now accompany
refreshed preview archives, and scoped GPL patch attribution/change dates are
in `patches/README.md`. The full binary dependency audit is still incomplete.

Reviewed November 21, 2026 against the pinned source, the actual preview
executables, linker maps, the pinned toolchain image and current upstream pages.
This is a technical license/provenance review, not legal clearance. Where the
scope of a permission is unclear, obtain confirmation from the relevant rights
holders or qualified counsel before relying on it.

**Recommendation:** do not publish the complete current tree or packager
binaries yet. The main unresolved item is permission for GBARunner3-derived
source and compiled runtime distribution. There are also scoped notice and
source-provenance tasks below. Choosing our own license does not grant rights
to upstream material.

## 1. Source repository: actions before publication

| Item | Evidence | Resolution |
| --- | --- | --- |
| GBARunner3 patches | Three `gbarunner3-*.patch` files contain upstream source/context. No repository-wide license at our pin or in the current upstream tree reviewed. | Obtain a license or written permission covering publication of modifications/patches and redistribution; otherwise withhold affected material or design a separately reviewed publication scope. |
| Original additions | No project license selected. | Choose a license for material we have rights to license; identify exceptions by path. MIT is a reasonable permissive default for independent tools/docs. It cannot override upstream terms. |
| melonDS patches | Both emulator patches modify GPL-3.0-or-later source. | Preserve attribution, clearly identify modification dates and GPL scope, and accompany the patches with the GPL text. Do not mark these patches as MIT-only. |
| Diagnostic build templates | `tests/nds_probe/Makefile` matches devkitPro's installed ARM9 template except for adding `-lfat`; its `template.prj` matches exactly. `tests/nds_mpu_probe/Makefile` has the same template structure. | Establish applicable example-file terms and retain attribution, or replace the template build files with independently authored minimal build rules and remove unused IDE templates. Do not assume libnds's license covers examples. |
| Game-derived references/assets | Map graphics are loaded from the user's ROM; no ROM/BIOS/graphics binaries occur in the candidate source tree. Original glyphs are documented in the renderer. Addresses/layouts reference metroidret/mf. | Keep proprietary inputs/outputs excluded. Retain reference provenance; any copied substantial reference code must receive its applicable notice. Review final index/history before publication. |

The earlier check found 85 source candidates and no private binaries. It checks
filenames/content patterns and links, not copyright ownership or all secrets.
The root currently has no Git repository/history; any later imported history
needs separate review. Ignoring `vendor/` does not erase the upstream portions
of a patch, nor establish rights to a potentially derived replacement file.

GitHub distinguishes the limited platform ability to view/fork a public
repository from a general open-source license. An absent license is not a
blanket permission to redistribute modified source or binaries.
[GitHub licensing guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)

## 2. GBARunner3: the principal permission question

Pinned revision: `ecaa817815d9761745606592f04affe5ee9c3731`.
The pinned root lists no project license; individual incorporated components
have separate notices. The current upstream tree reviewed also lacks a
repository-wide license. Existing issues
[#200](https://github.com/Gericom/GBARunner3/issues/200) and
[#208](https://github.com/Gericom/GBARunner3/issues/208) ask about licensing and
modified-source/binary permission. Neither page returned a maintainer grant
in this review; the questions themselves are not permission.

Affected local files include:

- `patches/gbarunner3-dual-screen.patch`
- `patches/gbarunner3-package.patch`
- `patches/gbarunner3-hardware-diagnostics.patch`
- Runtime integration files, especially code modeled on upstream interfaces or
  implementation, require provenance review alongside the patches.

The executable also embeds modified GBARunner3 machine code and its startup
artwork. The linker map includes `runner.o`, `splashBg.o`, `three.o` and
`threeGlow.o`. Ask about those assets, not just C/C++ source. A ROM-free runtime
is still a distribution of upstream code and artwork.

Preferred resolution: a clear upstream license and any component exceptions,
or a written grant covering the pinned revisions, modifications, source/patch
publication, compiled runtime embedding in a packager, and downstream users'
redistribution rights. Ask whether additional contributors or asset owners
must consent. A grant from one person only covers rights they can grant.
An [unsent request draft](upstream-permission-request.md) is ready for review.

## 3. libtwl: a narrower issue than previously recorded

Our runtime pins `e069645bed14a93e149e873e9273f04851e3a04e`, which has no license
file. However, Gericom added a zlib license at
[`81ad90ceca20be0bdaf5bbfab80b3ad796201510`](https://github.com/Gericom/libtwl/commit/81ad90ceca20be0bdaf5bbfab80b3ad796201510)
on September 25, 2024. The [current license](https://github.com/Gericom/libtwl/blob/develop/LICENSE.txt)
permits use, modification and redistribution with origin, modification and
notice conditions. A verbatim copy is in `licenses/libtwl-zlib.txt`.

It would be incorrect to keep describing all of libtwl as unlicensed. The open
question is the older pin. Comparing it with the license-adding revision shows
three changed code files, in addition to the new license:

- `libtwl7/include/libtwl/sys/swi.h`
- `libtwl7/source/sys/swi.s`
- `libtwl7/source/sio/sioRtc.c`

Two practical routes are confirmation that the grant covers our earlier pin,
or a deliberate move to a licensed revision with rebuilds and full regression
checks. Do not assume retroactive coverage, and do not silently change the
hardware-tested dependency to close a paperwork item.

## 4. melonDS: known license, compliance work

The pinned melonDS engine is `16f127dbb587a73371827ce79689c5d237c4b59b`;
the melonDS DS frontend is `f394adbacb5722ee97c1b37c8064da9a25818310`.
The modified engine files carry the melonDS team notice; the frontend
`src/libretro/core/core.cpp` carries Jesse Talavera-Greenberg's notice. Their
headers specify GPL version 3 or later.

The relevant paths are `patches/melonds-arm9-data-abort.patch` and
`patches/melonds-ds-shared-wram.patch`. The full GPL text has been collected in
`licenses/GPL-3.0.txt`; a per-patch attribution/modification-date notice remains
an action before publishing the patches. GPL section 5 explicitly covers
source modifications. [GPLv3 terms](https://www.gnu.org/licenses/gpl-3.0.html)

The standalone packager does not contain melonDS. Its license obligations
should not be confused with distribution of our separate patched emulator.
If distributing an emulator core/app, provide the complete corresponding
source for that binary, including applicable dependencies and build scripts,
with the required notices. A loose link to an upstream homepage is not our
release source-delivery plan. Qt, FAAD, SDL, ENet and other GUI dependencies
need their own review at that point; the patched GUI is outside this proposed
packager release. [GNU distribution guidance](https://www.gnu.org/licenses/gpl-faq.html#SourceAndBinaryOnDifferentSites)

## 5. Additional obligations for packager executables

The original preview ZIPs are unchanged. They contain some notices, but the
notice collection is not complete. Rebuild or repackage only after completing
the applicable inventory and permissions; regenerate checksums and verify the
final release artifacts.

| Included material | What was established | Remaining action |
| --- | --- | --- |
| GBARunner3 and splash artwork | Embedded in the NDS template; no general license found | Permission as above |
| libtwl | Embedded; later revision has zlib license | Resolve the older pin and include correct notice |
| libnds 1.8.3-1 | Pinned image provides a zlib-style `libnds_license.txt`; `libnds7.a`/`libnds9.a` appear in maps | Retain notice and finish per-file/library exceptions check |
| FatFs R0.13c | Permissive retained-notice terms; notice already in `THIRD_PARTY_NOTICES.txt` | Retain notice in final distribution |
| TLSF 3.1 | Matthew Conte, BSD-3-Clause-style terms in `tlsf.h`; `tlsf.o` linked | Add full copyright/conditions/disclaimer to binary notices |
| mini-printf | Michal Ludvig, BSD-3-Clause-style terms; `mini-printf.o` linked | Add full notice |
| ArduinoJson 6.20.1 | Benoit Blanchon, MIT header; included by runtime settings code | Include exact-version MIT notice and copyright |
| DSi SD/MMC code | profi200, MIT license; `sdmmc.o`/`tmio.o` linked | Add full notice; reference text collected in `licenses/sdmmc-mit.txt` |
| GCC/newlib/startup/sysbase | Maps reference `libstdc++`, `libgcc`, `libc`, `libm`, `libg`, `libsysbase`, startup objects | Inventory linked members, versions, notices and runtime exceptions. Toolchain GPL alone does not determine the output's license. |
| CPython 3.13.7 | PSF/historical notices included; extra Windows notices also present | Check embedded standard-library/native dependencies against actual distribution |
| PyInstaller 6.22.3 | Bootloader exception permits independently licensed application bundles, subject to dependency terms | Retain chosen attribution; no need to GPL our independent packager merely because it is frozen |
| Native host libraries | Archive audit finds OpenSSL on both platforms, liblzma/libmpdec on Mac, libffi and `VCRUNTIME140.dll` on Windows; Python extensions include further code | Match exact binary versions to notices; complete gaps, including applicable Microsoft redistribution conditions |

The build maps establish linked archive/object involvement, not that every
object offered to the linker survives garbage collection. Scope any exclusions
using the final linked sections before dropping an identified dependency from
the audit. The release does not distribute the Docker image, Wine, compiler,
or all PyInstaller build dependencies merely because they were used to build.

Primary terms:
[PyInstaller exception](https://pyinstaller.org/en/stable/license.html),
[Python licensing](https://docs.python.org/3.13/license.html),
[Microsoft redistribution guidance](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files).
The actual Windows Python license includes additional distribution conditions;
review that exact bundled text and the applicable grant rather than assuming
that every DLL has Python's PSF license. Local archive inventory is recorded at
`artifacts/licensing-review/inventory.json`.

## 6. Project license and suggested order

A practical proposal is MIT for independently authored packager/tools/docs and
other original material we have rights to license, GPL-3.0-or-later for the
melonDS-derived patches, and explicit scope/terms for GBARunner3-derived work
once permission is settled. This is a proposal, not a license grant applied
by this review. If upstream selects incompatible terms, revisit the plan.
[MIT terms](https://choosealicense.com/licenses/mit/)

Selecting a license for our own original material is a project policy decision
to enable reuse, not a claim that publishing one's own code always requires
an open-source license. Permission to redistribute other people's material is
a separate question and cannot be solved with our license choice.

Proceed in this order:

1. Seek GBARunner3 permission, including patches, binaries and splash artwork;
   include the older libtwl pin question in the same request.
2. Resolve or replace the copied diagnostic build templates; retain any
   required upstream notices and audit the other source additions' provenance.
3. Select the original-code license, add precise path exceptions and complete
   melonDS patch notices/change dates. Keep third-party terms intact.
4. Review the final source index and any history, then publish the source when
   those issues are resolved. A reduced source-only release would require an
   explicitly reviewed file list; omitting binaries alone is insufficient.
5. Finish linked/bundled dependency notices, source-delivery requirements where
   applicable, and platform release checks before publishing executable ZIPs.

Signing/notarization and native Windows smoke tests are release-quality tasks,
not prerequisites for publishing otherwise properly licensed source.
No maintainer has been contacted, no license has been selected on the user's
behalf, and no permission is inferred from silence.
