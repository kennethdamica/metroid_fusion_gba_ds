# DSpico / 3DS startup investigation

**Hardware result, 2026-11-21:** the user confirmed Hardware Fix 4 boots and
runs Fusion on their 3DS through DSpico in DSi mode. The ARM interworking fix
is physically confirmed. The subsequent gameplay-framing and sector-map update
was also reported working on that setup; see the [map guide](fusion-map.md).
Earlier pending notes below record the investigation at the time. This is a
single-console report, not a full hardware compatibility test.

Reported 2026-11-21: packaged Fusion extracts, shows the GBARunner3 logo,
then remains on a blank purple background. Only the packaged build has been
tried; ordinary GBARunner3 has not yet been used as a control. Pico Launcher
version is unknown. Hardware test 1 stops at `01 CORE READY`, `MODE DSI`.
That result is ambiguous: test 1 waited for an ARM7 backlight response before
updating every stage label, so a subsequent stage could leave `01` displayed.
Hardware test 2 removes all IPC waits from the stage display and splits the
early initialization path into finer checkpoints. The user confirmed that
tests 2 and 3 both remain at `01 CORE READY`, `MODE DSI`, despite the nonblocking
labels. The user also confirmed that `CORE READY` is fully rendered. The apparent
environment-detection boundary was actually the return from the first
diagnostic draw call; see the Test 4 interworking finding below. Emulator success does not
establish physical compatibility.

## Diagnostic package

Build separately from the working Mac release:

```sh
.venv/bin/python tools/build_dual_screen.py --hardware-diagnostics
.venv/bin/python tools/package_fusion.py \
  --runtime artifacts/hardware-runtime \
  --rom 'Metroid Fusion (USA).gba' --bios gba_bios.zip \
  --output artifacts/my-hardware-build/Fusion.nds
```

Copy that `Fusion.nds` to the flashcart SD root, replacing the previous NDS.
Keep the `_fusion` directory: the diagnostic uses the same verified payloads
and save identity. It does not require a firmware update or SD reformat.
Report the bottom-screen stage **and label**, plus `MODE DS` or `MODE DSI`.
The stage describes the operation being entered, not one already completed.
If startup succeeds, the diagnostic screen is replaced by the normal map.

| Code (hex) | Operation |
|---|---|
| 01 | About to enter environment detection |
| 02 | Mount storage (the package explicitly selects `fat:`) |
| 03 | Read configuration |
| 04 | Read and patch GBA BIOS |
| 05 | Open/read ROM and apply game patches |
| 06 | Initialize/load save |
| 07 | Apply runtime patches |
| 08 | Wait for logo animation |
| 09 | Configure display |
| 0A | Initialize guest memory, dispatch, JIT and audio |
| 0B | Set cache options and ARM9 clock |
| 0C | Initialize geographic map |
| 10 | Environment mode detected; about to select emulator-probe path |
| 11 | Read the no$gba debug identifier register |
| 12 | Select logger |
| 13 | Set ARM7 main-memory bus priority |
| 14 | Set up splash IRQ handler |
| 15 | Enable splash interrupts |
| 16 | Splash interrupt setup returned; about to enter mount stage |
| 17 | Environment function entered; about to clear flags |
| 18 | Flags cleared; about to read the mode register as 16 bits |
| 19 | Mode read completed; about to select DS/DSi detection branch |
| E0 | Filesystem mount returned an error |
| E1 / E2 | BIOS open / read failed |
| E3 / E4 / E5 | ROM open / header read / linear ROM read failed |

The diagnostic adds no per-frame logging or SD log writes. Test 2 performs
only memory/register writes when changing stage: it does not wait for ARM7,
SD, VBlank or interrupt completion. The existing display-configuration
backlight request keeps the bottom screen lit, without adding a roundtrip. It uses the map's
font in VRAM C during startup and adds BIOS/ROM read-result checks. Startup
constant tables from `main.o` move to main RAM to preserve VRAM code capacity;
executable code stays in permitted ARM9 code memory. Normal build outputs are
unchanged. `gFusionBootStage` in main RAM also permits automated verification.

## Leads checked

- The package flushes its argv handoff before entering the core.
- The packaged argv starts with `fat:`, so `shouldMountDsiSd` chooses flashcart
  storage even in DSi mode. The historical upstream
  [DSpico / console-SD issue](https://github.com/Gericom/GBARunner3/issues/172)
  is not established as the cause of this failure.
- Bootstrap extraction and core file access use different IPC/cache paths.
  Successful extraction does not establish that subsequent core reads work.
- The official [DSpico DLDI implementation](https://github.com/LNH-team/dspico-dldi/blob/develop/source/iointerface.c)
  reads sectors in a loop and polls for completion. Inspection alone does not
  establish a transfer-size limit or demonstrate a driver fault.
- The automated emulator uses a melonDS DLDI driver and DS mode. It does not
  emulate the physical DSpico transport or prove 3DS/DSi-mode compatibility.

Next investigation depends on the observed stage. A storage-stage failure
calls for checking the core IPC/cache path against the working extractor and
a stock GBARunner3 control; a later stage points to cache/clock, map or guest
startup. No hardware fix is claimed until the user confirms it on the 3DS.

## Emulator validation of hardware test 1

`artifacts/hardware-test/Fusion.nds` is 8,741,376 bytes, SHA-256
`92d7de986e3b714fc816ac525e9780aa45e46d32951cdc9e1e00459c2cacbc9c`.
Patched melonDS passes all 75 gameplay/map assertions and all 27 package
acceptance checks, including first extraction, repeat-launch reuse, exact
save preservation at handoff, primary save-slot preservation after game
startup, and recovery/rejection cases. The seven host packaging tests pass.
Reports are in `artifacts/hardware-test-verified/`. The startup label was
visually verified in `artifacts/hardware-trace-screen/frame-000020.png`;
RAM stage samples and linker bounds are recorded alongside it in
`trace-verification.json`. The original Mac release hash is unchanged.
The remaining confirmation is the diagnostic result on the user's 3DS.

## Hardware test 2

The new package is `artifacts/hardware-test-2/Fusion.nds`, SHA-256
`933ed4992b5f62db5bf9be861befa59725e4b6c337e62e54e3a6e41c505f1f48`.
Its screen reads `FUSION HARDWARE TEST 2`. It preserves the normal environment
probe and interrupt setup behavior so the hardware report can identify the
actual blocking operation. No DSi-mode fix is claimed yet.

A separate, deliberately broken copy was tested only in melonDS: replacing
its debug-register read with an infinite loop leaves `11 DEBUG PROBE` clearly
visible, with RAM stage `0x11` at both 60 and 180 frames. The fault address,
original opcode and package hash are recorded in
`artifacts/hardware-test-2-fault/fault.json`, and the screenshot is
`artifacts/hardware-test-2-fault/run/frame-000180.png`. **Do not copy that
fault-injection package to the flashcart.** The normal package is unaffected.

The unmodified test-2 package passes **75/75 gameplay/map assertions** and
**27/27 package assertions**, including repeat launch, save preservation,
interrupted extraction recovery and malformed-package rejection. Reports:
`artifacts/hardware-test-2-verified/{first-boot/result.json,result.json}`.
`artifacts/hardware-test-2/diagnostic-validation.json` records the fault-test
result and checks that the compiled stage renderer calls only its text/hex
helpers. The Mac release package remains unchanged.

## Hardware test 3: mode-register read candidate

The mode label successfully reads `0x04004000` as a 16-bit value, while the
original `Environment::Initialize()` read it as 32 bits. Test 3 changes that
one runtime read to 16 bits and adds checkpoints 17/18/19 to distinguish
function entry, flags initialization and the register read. It retains the
original mode flags, emulator probes, clock selection and file-loading path.
This is a **candidate**, not a confirmed explanation of the 3DS stall.
[GBATEK's DSi I/O map and SCFG documentation](https://problemkaputt.de/gbatek.htm#dsicontrolregistersscfg)
identify SCFG_A9ROM at `0x04004000`; the documentation alone does not prove
that the original 32-bit access causes this failure.

Package: `artifacts/hardware-test-3/Fusion.nds`, SHA-256
`086b2a418f9176780afd16b10834243f311a4ab778f24d03ce841194d51e84ed`.
The compiled code was inspected: `0x068057c0` executes `LDRH r4, [r3]`,
between the calls displaying 18 and 19. The build input hashes and linker
capacity were checked and recorded in `artifacts/hardware-test-3/build-validation.json`.
The screen identifies itself as `FUSION HARDWARE TEST 3`.

A separate emulator-only fault injection replaces the mode-register `LDRH`
with an infinite loop. The screen correctly remains at `18 READ MODE`, and
RAM stage samples at frames 60 and 180 both equal `0x18`. Details and screenshot
are in `artifacts/hardware-test-3-fault/`; that deliberately broken copy is
not the hardware-test package.

Test 3 passes **75/75 gameplay/map assertions** and **27/27 package
assertions**, including repeat-launch reuse, save preservation and extraction
recovery. Reports are in `artifacts/hardware-test-3-verified/`. The remaining
check is the user's 3DS; these are DS-mode emulator results.

## Hardware fix 4: ARM/Thumb return mismatch reproduced

The earlier mode-register-width change did not resolve the hardware report.
Inspection of the return immediately after drawing `01 CORE READY` found the
actual incompatible instruction: Test 3's Thumb renderer ends with `POP {pc}`.
GBARunner's CRT0 writes CP15 control `0x0005D07D`, setting L4 (bit 15) to
preserve ARMv4T load-to-PC behavior for the GBA guest. With L4 set, that POP
cannot return to an ARM caller in the required instruction-set state.
The [ARM assembler guide, POP/interworking](https://documentation-service.arm.com/static/5e9831ef9931941038dd07ba?token=)
explicitly documents that L4 disables the state change on loads to PC.

The prior melonDS interpreter ignored L4 for LDR/LDM/POP-to-PC. The local CPU
patch now respects it in all three load paths, retaining explicit BX/BLX
state changes and CPSR-restoring exception returns. JIT remains disabled.
Corrected libretro core SHA-256:
`4000f5b6035046f2e21b4128fd1ab6e921f79ef796f744ffc3d25071e8e24c43`.
The previous core is archived under `.tools/melonds-custom/before-l4/`.
The desktop GUI source has the same updated patch; its installed app binary
has not yet been rebuilt, and the existing Mac release remains unchanged.

**Reproduction:** the unchanged Test 3 package stalls at `01 CORE READY` in
this corrected emulator (`artifacts/hardware-l4-repro/frame-000180.png`). RAM
stage samples at frames 60 and 180 both remain 1. The previous emulator let
this same package boot. This reproduces the user's startup symptom even in
DS mode, showing that the incompatible return does not require DSi mode.

**Fix:** compile `FusionScreen.size.cpp`, including its startup diagnostics,
in ARM mode with `-Os`, matching the runtime functions it calls. Fixing only
Thumb return epilogues is insufficient because ARM runtime functions also
return to the Thumb caller with LDM/POP. An intermediate Thumb-only attempt
is retained as failed evidence in `artifacts/hardware-test-4-verified/`; do
not use its package. No exception handler change or CPU-compatibility-mode
change is needed for this fix.

To fit the ARM code, startup JSON-parser and save-signature constant tables
join the existing startup constants in main RAM. Diagnostic VRAM allocation
ends at `0x0681FDFC` (516 bytes spare), ITCM at `0x7D60` (672 bytes spare),
and main-RAM allocation at `0x021EF000` (68 KiB heap). The Thumb/ARM build rule
also depends on its Makefile so changed compile flags trigger recompilation.

The deliverable is **`artifacts/hardware-fix-4/Fusion.nds`**, 8,742,912 bytes,
SHA-256 `e472392c3b548f2b861f104fcb661ed0acf0b2d9a45f45f1a0f21c320f2a1fa4`.
It identifies itself as `FUSION HARDWARE TEST 4`. The original Fusion/BIOS
payloads, extraction format and save identity remain unchanged.

Repeat the before/after regression with:

```sh
.venv/bin/python tools/test_interworking_regression.py \
  --broken-package artifacts/hardware-test-3/Fusion.nds \
  --fixed-package artifacts/hardware-fix-4/Fusion.nds \
  --fixed-map artifacts/hardware-runtime/debug/code_core_arm9_build_arm9.map \
  --output artifacts/interworking-recheck
```

The initial passing result is `artifacts/hardware-interworking-regression/result.json`:
old build stays at stage 1; fixed build reaches stage 12 and the guest frame
counter advances. This is emulator evidence for the software defect and fix;
confirmation on the user's physical 3DS is still pending.

The final ARM-state package passes **75/75 gameplay/map checks**, **27/27
package/reuse/save/recovery checks**, and **5/5 before/after interworking
checks** on the L4-corrected interpreter. Full evidence is in
`artifacts/hardware-fix-4-verified/` and
`artifacts/hardware-interworking-regression/`. Physical 3DS confirmation
is the remaining step.
