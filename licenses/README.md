# Reference license texts

These are verbatim copies of identified third-party license texts. They do not
assign a license to this project's original contributions or resolve the
GBARunner3 permission question. See the [review](../docs/licensing-review.md)
for scope, remaining actions and the difference between source and binary
publication. The original ZIPs are preserved; refreshed ZIPs under
`artifacts/packager-with-notices/` include these texts alongside the unchanged
executables and a packaging-update record.

| File | Source and scope |
| --- | --- |
| [GPL-3.0.txt](GPL-3.0.txt) | melonDS DS `f394adbacb5722ee97c1b37c8064da9a25818310`, root `LICENSE`; upstream melonDS/melonDS DS source headers specify GPL-3.0-or-later |
| [libtwl-zlib.txt](libtwl-zlib.txt) | libtwl `81ad90ceca20be0bdaf5bbfab80b3ad796201510`, `LICENSE.txt`; later than our runtime pin |
| [metroidret-mit.txt](metroidret-mit.txt) | metroidret/mf `8614cc3eec194092cd756d6382c879b4c2ab4967`, root `LICENSE`; does not license Nintendo ROM data |
| [sdmmc-mit.txt](sdmmc-mit.txt) | GBARunner3 `ecaa817815d9761745606592f04affe5ee9c3731`, `code/core/arm7/source/mmc/LICENSE.txt` |

## Additional collected notices

| File | Source and scope |
| --- | --- |
| [libnds-zlib.txt](libnds-zlib.txt) | libnds 1.8.3-1, `/opt/devkitpro/libnds/libnds_license.txt` in the pinned devkitARM image; the modified touch driver also retains its per-file notice |
| [fatfs.txt](fatfs.txt) | FatFs R0.13c notice from pinned GBARunner3 `code/core/arm9/source/Fat/ff.c` |
| [tlsf-bsd.txt](tlsf-bsd.txt) | TLSF 3.1 notice block from pinned GBARunner3 `code/core/arm9/source/Core/Heap/tlsf.h` |
| [mini-printf-bsd.txt](mini-printf-bsd.txt) | Copyright/conditions/disclaimer from pinned GBARunner3 `code/libs/mini-printf/mini-printf.c` |
| [arduinojson-mit.txt](arduinojson-mit.txt) | [ArduinoJson v6.20.1 LICENSE.txt](https://github.com/bblanchon/ArduinoJson/blob/v6.20.1/LICENSE.txt), matching the runtime header version |
| [openssl-apache-2.0.txt](openssl-apache-2.0.txt) | OpenSSL 3.6.0 `LICENSE.txt` from the local Homebrew installation; Apache 2.0 license text |
| [xz-copying.txt](xz-copying.txt) | XZ Utils 5.8.1 `COPYING`; distinguishes liblzma's 0BSD terms from other tools in the source package |
| [mpdecimal-bsd.txt](mpdecimal-bsd.txt) | mpdecimal 4.0.1 `COPYRIGHT.txt` from the local Homebrew installation |

The packager build copies the collected `.txt` notices into its distribution
alongside Python and installed build-package notices. Exact native dependency
coverage and toolchain-runtime exceptions remain an incomplete audit; collecting
these texts does not assert that every obligation has been resolved. The GPL
text concerns the separate emulator patches; melonDS is not embedded in the
packager. See [patch attribution](../patches/README.md).
