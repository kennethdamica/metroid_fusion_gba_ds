# Display work and sound timing

The November 22 sound update addresses choppy sound reported on hardware in
both Zelda and Fusion. ARM7 consumes the emulated GBA sound FIFO while ARM9
supplies samples through GBARunner3's sound DMA handler. Display work runs with
interrupts masked: a large framebuffer copy or inventory redraw can delay a
refill until the FIFO is empty. Zelda's full inventory redraw every fourth
frame made this considerably worse.

## Runtime change

The shared implementation in `runtime/display/` checks for the pending ARM7
sound IRQ between short pieces of display work. It acknowledges only that IRQ
and calls the existing `dma_dmaSound` path for active sound channels, preserving
the original source addressing, repeat behavior and emulated DMA interrupts.
It does not enable nested interrupts or take a hardware DMA channel.

The refill call uses a separate 512-byte aligned stack because the runtime's
288-byte IRQ stack cannot safely hold both rendering and the sound DMA call
chain. `gDisplayAudioDebug` records service calls, each channel's DMA calls,
and a stack-canary failure count. Resolve its address from the current link map;
addresses are build-specific.

Both games check sound requests every 16 rows of the 240×160 top-screen copy
and throughout map work. Zelda also checks between 2 KiB pieces of lower-screen
publication, icon copies and panel rendering. Its complete-frame staging and
early-VBlank publication remain in place. A snapshot of visible inventory/map
state skips unchanged redraws; touch input is still sampled each frame.

Normal builds leave the upstream ARM7 mixer and shared sound structure
unchanged. No ROM, BIOS, extraction path or save format changes are required.
The existing frozen Mac/Windows packager releases are not rebuilt by this work.

## Build and test

Complete [development setup](development.md) first. Use new output paths:

```sh
.venv/bin/python tools/build_dual_screen.py --game alttp --package-template
.venv/bin/python tools/package_alttp.py \
  --rom '/path/to/zelda.gba' --bios '/path/to/bios.bin' \
  --output artifacts/alttp-audio-candidate/Zelda.nds
.venv/bin/python tools/test_alttp.py \
  --package artifacts/alttp-audio-candidate/Zelda.nds --maps --video-stability \
  --video-debug-address 0x0204CEEC --output artifacts/audio/zelda-verified-v3

.venv/bin/python tools/build_dual_screen.py --game fusion --hardware-diagnostics
.venv/bin/python tools/package_fusion.py \
  --rom '/path/to/fusion.gba' --bios '/path/to/bios.bin' \
  --output artifacts/fusion-audio-candidate/Fusion.nds
.venv/bin/python tools/test_packaged_fusion.py \
  --package artifacts/fusion-audio-candidate/Fusion.nds \
  --output artifacts/audio/fusion-verified-v3
```

Use the diagnostic/hardware Fusion configuration, as for the previously working
Hardware Test 5 package. Its standard template has a separately documented boot
problem. Check `gZeldaVideoDebug` in the Zelda link map before reusing the address
above after source changes.

Copy the new file to the flashcart as `Zelda.nds` or `Fusion.nds`, retaining the
existing `_alttp` and `_fusion` folders. Subsequent launches reuse the extracted
files and existing saves.

## Audio evidence and limitations

Final candidates, without ARM7 counters:

| Package | SHA-256 |
| --- | --- |
| `artifacts/alttp-audio-candidate/Zelda.nds` | `77bdf631139fe9954726ebaedf563ee347e41c51c10726d233dcb8705b9b1ea0` |
| `artifacts/fusion-audio-candidate/Fusion.nds` | `811a3fffc1335c14287cef201e26dfb46a548c5c988af3ccf4ea38c0943f71a2` |

Zelda passed all 67 assertions in `artifacts/audio/zelda-verified-v3/result.json`,
including gameplay, real touch input, all 14 dungeon fixtures, map controls,
save preservation and second-launch reuse. The inventory/world/dungeon stable
windows each produced one identical image; publication had zero overruns and
took at most 14 scanlines. Only 31 complete lower-screen publications were needed
throughout the 21,960-frame scripted test.

Fusion passed 87 gameplay/display assertions in
`artifacts/audio/fusion-verified-v3/first-boot/result.json` and all 27 packaging,
save/reuse/recovery checks in `artifacts/audio/fusion-verified-v3/result.json`.
That test used `artifacts/audio/fusion-v3/Fusion.nds`, which is byte-identical to
the final candidate above. All 29 Zelda/package/public host tests and the
repository source/document-link audit passed. Hardware listening confirmation
of these candidates remains outstanding.

Across 116 Zelda and 12 Fusion RAM captures, the refill-stack canary recorded
zero failures; both builds exercised the new refill path. Final stereo recordings
are `artifacts/audio/zelda-audio-v3/audio.wav` (23.5 seconds) and
`artifacts/audio/fusion-audio-v3/audio.wav` (33.5 seconds), sampled at 32,728 Hz.
Their scripted scenes match the earlier `zelda-baseline` and `fusion-baseline`
recordings. `artifacts/audio/validation-summary.json` records candidate hashes,
stack checks and recording metadata. Recording valid PCM alone does not prove
the absence of audible glitches.

The instrumented Zelda comparison used identical file-menu frames 600–1200:

| Build | FIFO A misses / requests | FIFO B misses / requests |
| --- | --- | --- |
| Control: refills and redraw caching disabled | 7,248 / 105,600 (6.86%) | 7,248 / 105,600 (6.86%) |
| Sound fix | 50 / 105,601 (0.047%) | 51 / 105,601 (0.048%) |

This is approximately a 99.3% reduction in missed samples in that emulator
window. It is not a hardware measurement or a guarantee of perfect sound in
every scene. The instrumented full Zelda gameplay/map test passed all 67 checks
and recorded no lower-screen publication overruns. Its captures are under
`artifacts/audio/zelda-verified-v2/`; the comparison captures are under
`artifacts/audio/zelda-control-boot/` and `artifacts/audio/zelda-audio-v2/`.

For reproduction, `--audio-counters` applies the experimental ARM7 counter
patch in a separate build directory ending in `-audio-counters`.
`--audio-baseline` disables the cooperative refill calls and Zelda redraw
caching in a separate directory ending in `-audio-baseline`; combine both flags
for an instrumented control. Counter offsets are 96 bytes beyond
`gGbaSoundShared`: two underrun counts followed by two sample-request counts.
Subtract two captured snapshots within one continuous sound scene; resets and
32-bit wraparound must be considered in longer recordings.

The counters themselves reproduced a Fusion startup freeze even with the
original display code. Removing the counter patch restored guest progress.
The builder therefore restricts them to Zelda, and neither final candidate
includes them. Failed instrumented Fusion runs are not evidence of gameplay or
audio quality.

`tools/emulator_test.py` accepts `--audio-start FRAME --audio-end FRAME` to
record an inclusive gameplay-timeline window as stereo 16-bit `audio.wav` at
the core's reported sample rate. It drains the core's audio buffer every frame
even when recording is disabled. Compare recordings from the same scripted
scene; stretches of silence or a sample-plateau heuristic alone cannot reliably
identify underruns after the mixer's filtering.

## Follow-up: scratch on item and map changes

Hardware feedback confirmed the first audio update was substantially better,
with a remaining scratch on touches and occasional stutter following floor
changes. The follow-up separates two sources of delay:

- ARM7 touch sampling previously masked all interrupts, both in the application
  wrapper and inside libnds `touchReadXY`. Touch and backlight transactions now
  share an RTOS mutex, allowing the sound timer and mixer thread to preempt the
  sampling operation. Calibration, filtering and DS/DSi dispatch remain from
  [libnds v1.8.3's touch driver](https://github.com/devkitPro/libnds/blob/v1.8.3/source/arm7/touch.c).
  The modified source is `runtime/alttp/arm7/ZeldaTouch.c`, with the upstream
  copyright/license notice retained and changes marked. Startup initialization
  and the standalone ADC helper retain their original critical sections.
- ARM9 refilling the FIFO cannot make the paused guest generate new music.
  Composition now runs in slices, returning to gameplay between them. Each
  slice has a 16-scanline budget plus its final small work unit. The old complete
  lower-screen image stays visible until composition finishes and an early
  VBlank publishes the replacement. No partial image is displayed.

World tiles use aligned word copies from the existing cache. Dungeon rendering
works a row at a time, decodes tile attributes once per row, and skips empty or
concealed cells. The packed room-sheet cache is only halfword-aligned, so its
row decoder combines two halfwords. Host tests compare the resulting pixels
with the original per-pixel decoder across all 59 floors and 186 room cells.

An item-only change reuses the inventory image, updating selection borders,
the name and enlarged icon. The icon expansion computes each source pixel once
instead of four times. Inventory values are snapshotted for a complete redraw.
Tab/floor changes cancel incompatible unfinished work; movement queues another
refresh instead of continually restarting an image. Touch equipping remains
immediate while composition proceeds.

`gZeldaRenderDebug` records slices, longest slice in scanlines, images started,
completed and cancelled, longest individual work unit, and current phase/step.
The experimental `--audio-counters` build also records the maximum ARM7 mixer
backlog and batches at least half a sound ring late, after the four existing
FIFO counters (offsets 112 and 116 from `gGbaSoundShared`). These counters remain
excluded from normal builds.

The isolated diagnostic holds a touch in an inactive corner, avoiding any
redraw or equip action. Over the same window, maximum mixer backlog was 16
samples in the previous build and 8 with the new sampling path (normal wakeups
process 4 samples). Neither run exhausted the 64-sample lead in the 128-sample
output ring. FIFO misses in that short test were low in both runs and did not
improve (42 per channel versus 51/53); this measurement alone does not establish
that the scratch is gone. Hardware listening remains necessary.

Evidence is under `artifacts/audio/zelda-touch-timing-control/` and
`artifacts/audio/zelda-touch-timing-fixed/`; test-only counter resets happen at
frame 600, the held touch spans frames 700–999, and captures include frames
650, 1000 and 1200. Original game data and saves are untouched.

To exercise repeated item/tab/floor changes, a held touch, and cancellation by
rapid tab switches, add these options to `tools/test_alttp.py`:

```sh
--maps --video-stability --transitions --record-audio \
--video-debug-address 0x0204CF0C --render-debug-address 0x0204CEEC
```

Verify addresses against the build's link map. The transition suite runs 22,650
frames, records sound from frame 20,000 onward, checks complete final images and
bounds the longest composition slice to 40 scanlines. As in the map suite,
dungeon locations and owned items are seeded only in isolated emulator RAM.

The four small pixel routines occupy 1,580 bytes in the remaining executable
VRAM A, while the rest of the UI stays in main RAM. The linker leaves 1,228 bytes
free at the end of VRAM A and 160 bytes at the end of ITCM in this build. This
speeds up composition without changing the guest MPU or instruction-cache
policy. Moving those routines was necessary to keep floor changes responsive
under a short per-frame budget.

The asynchronous renderer intentionally keeps the old complete map while a new
one is being prepared. Tests give item feedback 18 frames and full floor changes
32 frames to settle; separate rapid-switch tests cancel unfinished work. The
last dungeon fixture is established before the consecutive-frame stability
window begins. The opening game's tutorial can open its own inventory during
the longer stress run, in which case touch equipping must remain guarded.

Use `tools/check_alttp_audio.py` to compare instrumented captures. For the matched
transition recordings (before the later fixture-settling adjustment):

```sh
.venv/bin/python tools/check_alttp_audio.py \
  --before artifacts/audio/zelda-transitions-control/first \
  --after artifacts/audio/zelda-transitions-counters-v4/first \
  --before-shared-address 0x020F8060 --after-shared-address 0x020F8080 \
  --start 20010 --end 21960 --require-no-misses
```

Both channels consumed 343,200 samples in that window. The previous build missed
602 samples per channel; the follow-up missed zero. The report is
`artifacts/audio/transition-comparison-v4.json`. This is controlled emulator
telemetry, not a claim of glitch-free sound in every hardware/game situation.

### Follow-up candidate validation

The delivered follow-up is `artifacts/alttp-transition-audio-v2/Zelda.nds`,
SHA-256 `1d16d7b4f899628d656b078c335ff524bb9dbdd6ffbabf170d18f1e02197c0ca`.
It excludes experimental ARM7 counters. Existing `_alttp` files and saves are
reused; the original sound-fix candidate remains preserved.

`artifacts/audio/zelda-transitions-verified-v5/result.json` passed all **80**
checks: gameplay/touch, all dungeon fixtures, floor controls, repeated and rapid
transitions, consecutive-frame stability, first extraction and second-launch
save preservation. The main run completed 22,650 frames and the second launch
1,200 frames. Results include:

- Stable inventory/world/dungeon windows each contained exactly one image.
- No publication overruns; longest publication was 14 scanlines.
- Longest composition slice was 27 scanlines (about 1.7 ms); longest unit was
  12. There were 46 complete compositions and 8 cancelled unfinished images.
- All sampled refill-stack canaries were intact. The new refill path ran 5,203
  times by the last capture.
- Four settled inventory/map screenshots matched the prior audio build pixel
  for pixel, including enlarged item icons and dungeon graphics.
- All 29 host tests and the repository source/document-link audit passed.

The recorded transition audio is under that run's `first/audio.wav`. The final
binary is the same one used in the earlier `verified-v4` run; the v5 rerun adjusts
only fixture settling time for asynchronous rendering and the longer stress
schedule. The v4 audio-counter comparison used the matched original schedule.
Hardware confirmation of the remaining scratch/stutter fix is still required.


### Subsequent hardware feedback

The user confirmed the touch-related scratch was gone, then reported general
clicking on one boot. On a subsequent boot the sound was normal, and the user
asked to defer further audio work. A UI instruction-cache experiment was tested
locally and reverted before the original-art inventory update. That update keeps
the ARM7 sound/touch code, cooperative audio refill code and MPU cache policy
identical to the transition sound-fix build. Its changed rendering still requires
hardware listening qualification.
