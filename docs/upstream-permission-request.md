# Draft request to Gericom

**Unsent.** Intended as a respectful follow-up to the existing licensing
questions, not a claim that permission has been granted. Review the exact
publication scope before posting.

Suggested subject: GBARunner3 / libtwl licensing for a dual-screen Fusion extension

Hello Gericom,

I'm developing a Nintendo DS extension that runs Metroid Fusion through
GBARunner3 on the top screen and renders its live exploration map on the bottom
screen. A local command-line packager combines a user-supplied ROM and GBA BIOS
with the enhanced runtime. Neither ROM nor BIOS would be included in the public
repository or packager download.

Before publishing, could you clarify permission for:

1. Publishing our GBARunner3 modifications as source/patches, including the
   upstream context in those patches.
2. Distributing the compiled modified runtime embedded in a Windows/macOS
   packager and in user-generated NDS packages, with downstream redistribution
   under clearly stated terms.
3. Retaining the existing GBARunner3 splash artwork/logo, or any attribution and
   naming changes you would prefer.
4. Any additional contributor or artwork permissions we should obtain.

Our GBARunner3 base is `ecaa817815d9761745606592f04affe5ee9c3731`.
I saw the existing licensing questions in issues #200 and #208 but did not find
a general license or permission answer for this revision. An explicit open-source
license and any component exceptions would make downstream compliance clear.

The build also pins libtwl `e069645bed14a93e149e873e9273f04851e3a04e`.
I found the zlib license added in `81ad90ceca20be0bdaf5bbfab80b3ad796201510`.
Does that license cover the earlier pinned version, or should we migrate to a
licensed revision before distributing the compiled runtime?

We will preserve required notices and clearly identify the modified project
as independent. Thank you for your work and any guidance on the terms.
