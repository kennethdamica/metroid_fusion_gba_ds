#!/usr/bin/env python3
"""Bounded, isolated melonDS DS runs with screenshots and optional assertions."""
import argparse
import hashlib
import json
import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
import traceback
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CORE = ROOT / ".tools/melonds/melondsds_libretro-macos-arm64-Release/cores/melondsds_libretro.dylib"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def worker(args):
    os.environ["MELONDSDS_SKIP_ERROR_SCREEN"] = "1"
    os.environ["TZ"] = "UTC"
    time.tzset()
    from libretro import Session, ExplicitPathDriver, ArrayVideoDriver, JoypadState, RETRO_MEMORY_SYSTEM_RAM, UnformattedLogDriver
    from PIL import Image

    root = args.output.resolve()
    if args.fusion_state or args.assert_fusion or args.assert_fusion_screen:
        from fusion_checks import FUSION_SHA1
        if args.wait_package:
            from package_fusion import inspect_package
            inspect_package(args.rom)
        elif not args.sd_dir or hashlib.sha1((args.sd_dir / 'rom.gba').read_bytes()).hexdigest() != FUSION_SHA1:
            raise ValueError('Fusion checks require the verified US ROM at SD /rom.gba')
    save = root / "state/save"
    system = root / "state/system"
    sd = save / "melonDS DS/dldi_sd_card"
    sd.mkdir(parents=True)
    if args.sd_dir:
        shutil.copytree(args.sd_dir, sd, dirs_exist_ok=True)
    if args.assert_probe:
        (sd / "probe.txt").write_text("DS_STORAGE_PROBE\n")
    options = {
        "melonds_console_mode": "ds", "melonds_boot_mode": "direct",
        "melonds_sysfile_mode": "builtin", "melonds_render_mode": "software",
        "melonds_jit_enable": "enabled" if args.jit else "disabled",
        "melonds_homebrew_sdcard": "enabled",
        "melonds_homebrew_sync_sdcard_to_host": "enabled",
        "melonds_homebrew_readonly": "disabled",
        "melonds_screen_layout1": "top-bottom", "melonds_screen_gap": "0",
        "melonds_show_cursor": "disabled", "melonds_start_time_mode": "absolute",
        "melonds_network_mode": "disabled",
    }
    scripted_inputs = json.loads(args.input_script.read_text()) if args.input_script else None
    # Test-only fault/transition injection into this isolated emulator process.
    memory_events = json.loads(args.memory_script.read_text()) if args.memory_script else []
    for event in memory_events:
        if not 1 <= event['frame'] <= args.frames or event['region'] not in ('main', 'shared'):
            raise ValueError('Invalid memory test event')
        data = bytes.fromhex(event['hex'])
        limit = 0x400000 if event['region'] == 'main' else 0x8000
        if not 0 <= event['offset'] <= limit - len(data):
            raise ValueError('Memory test event outside guest memory')
    if scripted_inputs is not None:
        for event in scripted_inputs:
            if not 0 <= event['start'] < event['end'] <= args.frames:
                raise ValueError('Input interval outside frame range')
            JoypadState(**{button: True for button in event['buttons']})
    booting = args.wait_package
    def inputs():
        frame = 0
        while True:
            if booting:
                yield JoypadState()
                continue
            if scripted_inputs is None:
                yield JoypadState(a=args.press_a_start <= frame < args.press_a_end)
            else:
                yield JoypadState(**{button: True for event in scripted_inputs
                                    if event['start'] <= frame < event['end']
                                    for button in event['buttons']})
            frame += 1

    result = {"rom": str(args.rom.resolve()), "rom_sha256": sha256(args.rom),
              "core_sha256": sha256(args.core), "options": options,
              "frames_requested": args.frames, "frames_completed": 0,
              "assertions": [], "captures": [], "status": "running", "input_script": scripted_inputs,
              "memory_test_events": memory_events,
              "sd_inputs": {str(p.relative_to(args.sd_dir)): sha256(p)
                            for p in sorted(args.sd_dir.rglob('*')) if p.is_file()} if args.sd_dir else {}}
    (root / "result.json").write_text(json.dumps(result, indent=2))
    images = {}
    capture_frames = {int(n) for n in args.capture.split(",")} | {args.frames}
    start = time.monotonic()
    # Passing our own logger avoids libretro.py retaining every LogRecord in RAM.
    logger = logging.getLogger('emulator-test')
    logger.setLevel(logging.WARNING)
    logger.addHandler(logging.StreamHandler())
    repeated = {}
    class BoundRepeatedMessages(logging.Filter):
        def filter(self, record):
            message = record.getMessage()
            for prefix in ('[melonDS] undefined ARM', '[melonDS] undefined THUMB', '[melonDS] ARM9: prefetch abort', '[melonDS] ARM9: data abort'):
                if message.startswith(prefix):
                    repeated[prefix] = repeated.get(prefix, 0) + 1
                    count = repeated[prefix]
                    return count <= 16 or count & (count - 1) == 0
            return True
    logger.addFilter(BoundRepeatedMessages())
    with Session(args.core.resolve(), args.rom.resolve(), video=ArrayVideoDriver,
                 options=options, input=inputs, log=UnformattedLogDriver(logger),
                 path=ExplicitPathDriver(args.core, system=system, save=save,
                                         assets=root / "state/assets")) as emu:
        if args.gba_rom_arg or args.nds_launch_path:
            # Model a flashcart launcher passing argv[1], before startup runs.
            # melonDS already supplies argv[0] in the libnds command-line block.
            memory = emu.core.get_memory(RETRO_MEMORY_SYSTEM_RAM)
            if memory is None or len(memory) != 0x400000:
                raise RuntimeError("DS main RAM unavailable for launcher arguments")
            memory = memory.cast('B')
            argv_header = 0x3FFE70  # 0x02FFFE70 mirrored into 4 MiB DS RAM
            if int.from_bytes(memory[argv_header:argv_header+4], 'little') != 0x5F617267:
                raise RuntimeError("melonDS did not provide the libnds argv header")
            pointer = int.from_bytes(memory[argv_header+4:argv_header+8], 'little')
            length = int.from_bytes(memory[argv_header+8:argv_header+12], 'little')
            offset = pointer - 0x02000000
            if not 0 <= offset < len(memory) or not 0 < length < 256:
                raise RuntimeError("Unexpected launcher command-line location")
            argv0 = args.nds_launch_path.encode() if args.nds_launch_path else bytes(memory[offset:offset+length]).split(b'\0')[0]
            command = argv0 + b'\0'
            if args.gba_rom_arg:
                command += args.gba_rom_arg.encode() + b'\0'
            if len(command) > 512 or offset + len(command) > len(memory):
                raise RuntimeError("Launcher command line too long")
            memory[offset:offset+len(command)] = command
            memory[argv_header+8:argv_header+12] = len(command).to_bytes(4, 'little')
            result['launcher_gba_argument'] = args.gba_rom_arg
            result['launcher_nds_path'] = argv0.decode()
        info = emu.core.get_system_info()
        result["core"] = info.library_name.decode() + " " + info.library_version.decode()
        if args.wait_package:
            for boot_frame in range(1, args.package_boot_frames + 1):
                emu.run()
                memory = emu.core.get_memory(RETRO_MEMORY_SYSTEM_RAM).cast('B')
                marker = bytes(memory[0x3E000:0x3E010])
                if marker[:8] in (b'PKGREADY', b'PKGERROR'):
                    result['package_boot'] = dict(frames=boot_frame, marker=marker[:8].decode())
                    if marker[:8] == b'PKGERROR':
                        result['package_boot']['error_code'] = int.from_bytes(marker[8:12], 'little')
                        # Let the LCD finish drawing the actionable error text.
                        emu.run()
                        emu.run()
                    else:
                        result['package_boot'].update(extracted=int.from_bytes(marker[8:12], 'little'),
                                                      reused=int.from_bytes(marker[12:16], 'little'))
                    shot = emu.video.screenshot()
                    if shot:
                        Image.frombytes('RGBA', (shot.width, shot.height), bytes(shot.data)).save(root/'package-startup.png')
                    (root/'result.json').write_text(json.dumps(result, indent=2))
                    if marker[:8] == b'PKGERROR':
                        raise RuntimeError(f"Package startup error {result['package_boot']['error_code']}")
                    break
            else:
                shot = emu.video.screenshot()
                if shot:
                    Image.frombytes('RGBA', (shot.width, shot.height), bytes(shot.data)).save(root/'package-timeout.png')
                raise RuntimeError('Package did not finish startup within frame budget')
            booting = False
            print(f"Package ready after {boot_frame} frames: {result['package_boot']}", flush=True)
        for frame in range(1, args.frames + 1):
            for event in memory_events:
                if event['frame'] == frame:
                    if event['region'] == 'main':
                        target = emu.core.get_memory(RETRO_MEMORY_SYSTEM_RAM).cast('B')
                    else:
                        descriptor, offset = emu.memory_maps.find(0x0F000000)
                        target = descriptor.view[offset:offset + 0x8000].cast('B')
                    data = bytes.fromhex(event['hex'])
                    target[event['offset']:event['offset']+len(data)] = data
            emu.run()
            result["frames_completed"] = frame
            if frame in capture_frames:
                shot = emu.video.screenshot()
                if shot is None:
                    raise RuntimeError(f"No framebuffer at frame {frame}")
                image = Image.frombytes("RGBA", (shot.width, shot.height), bytes(shot.data)).convert("RGB")
                filename = f"frame-{frame:06d}.png"
                image.save(root / filename)
                if image.size == (256, 384):
                    image.crop((0, 0, 256, 192)).save(root / f"top-{frame:06d}.png")
                    image.crop((0, 192, 256, 384)).save(root / f"bottom-{frame:06d}.png")
                images[frame] = image
                memory = emu.core.get_memory(RETRO_MEMORY_SYSTEM_RAM)
                if memory is not None:
                    (root / f"ram-{frame:06d}.bin").write_bytes(bytes(memory))
                shared = emu.memory_maps.find(0x0F000000) if emu.memory_maps else None
                if shared is not None:
                    descriptor, offset = shared
                    data = bytes(descriptor.view[offset:offset + 0x8000])
                    (root / f"shared-wram-{frame:06d}.bin").write_bytes(data)
                    # GBARunner3 assigns all physical shared WRAM to ARM9 and
                    # maps GBA IWRAM here. Decode only when explicitly requested.
                    if args.fusion_state or args.assert_fusion or args.assert_fusion_screen:
                        from fusion_checks import decode
                        result.setdefault('fusion_states', []).append(dict(frame=frame, **decode(data)))
                result["captures"].append({"frame": frame, "file": filename,
                                           "pixel_sha256": hashlib.sha256(image.tobytes()).hexdigest()})
                (root / "result.json").write_text(json.dumps(result, indent=2))
                print(f"Captured frame {frame}: {image.size}", flush=True)
    def check(name, condition):
        result["assertions"].append({"name": name, "passed": bool(condition)})
    if args.assert_probe:
        # Pinned melonDS software output expands maximum DS channels to 251.
        for frame, color in ((120, (251, 0, 0)), (180, (251, 251, 0)), (240, (251, 0, 0))):
            image = images.get(frame)
            check(f"input_at_{frame}", image is not None and image.getpixel((8, 8)) == color)
            check(f"bottom_screen_at_{frame}", image is not None and image.getpixel((8, 200)) == (0, 0, 251))
            check(f"storage_at_{frame}", image is not None and image.getpixel((200, 8)) == (0, 251, 0))
        written = sd / "probe-result.txt"
        check("DLDI_write_synced_to_host", written.exists() and written.read_text() == "DS_STORAGE_OK\n")
    for spec in args.expect_pixel:
        frame, x, y, r, g, b = map(int, spec.split(","))
        check(f"pixel_{spec}", frame in images and images[frame].getpixel((x, y)) == (r, g, b))
    if args.force_failure:
        check("intentional_failure_to_validate_runner", False)
    if args.assert_fusion:
        from fusion_checks import verify
        if args.wait_package:
            from package_fusion import DATA_DIR, DATA_ROOT
            verify(root, sd / DATA_DIR, check, save_path=sd / DATA_ROOT / 'rom.sav')
        else:
            verify(root, sd, check)
    if args.assert_fusion_screen:
        from fusion_screen_checks import verify
        verify(root, check)
    if args.sd_dir:
        result['rom_integrity'] = {}
        for original in [p for p in args.sd_dir.rglob('*') if p.suffix.lower() in ('.gba', '.nds')]:
            relative = original.relative_to(args.sd_dir)
            copied = sd / relative
            unchanged = copied.is_file() and sha256(copied) == sha256(original)
            if original.suffix.lower() == '.nds' and args.wait_package and copied.is_file():
                from package_fusion import verify_melonds_copy
                valid = unchanged or verify_melonds_copy(original, copied)
                check(f'NDS_only_expected_loader_changes:{relative}', valid)
                result.setdefault('nds_loader_transforms', {})[str(relative)] = dict(
                    byte_identical=unchanged, allowed_dldi_and_zero_padding=valid,
                    original_sha256=sha256(original), sd_copy_sha256=sha256(copied))
                continue
            result['rom_integrity'][str(relative)] = unchanged
            if not unchanged:
                check(f'SD_ROM_must_not_change:{relative}', False)
    if args.assert_gba_probe:
        markers = []
        for frame in sorted(capture_frames):
            path = root / f"ram-{frame:06d}.bin"
            if path.exists():
                data = path.read_bytes()[:12]
                marker = int.from_bytes(data[:4], "little")
                counter = int.from_bytes(data[4:8], "little")
                markers.append((marker, counter))
        check("GBA_guest_executed", bool(markers) and all(m == 0x47424150 for m, _ in markers))
        check("GBA_guest_frames_advance", len(markers) > 1 and all(b[1] > a[1] for a, b in zip(markers, markers[1:])))
    result["elapsed_seconds"] = round(time.monotonic() - start, 3)
    result['repeated_log_counts'] = repeated
    result["status"] = ("passed" if all(a["passed"] for a in result["assertions"]) else "failed") if result["assertions"] else "observed"
    (root / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return 1 if result["status"] == "failed" else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rom", type=Path, required=True)
    parser.add_argument("--core", type=Path, default=DEFAULT_CORE)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sd-dir", type=Path)
    parser.add_argument("--gba-rom-arg", help="Pass an SD path as libnds argv[1], e.g. fat:/rom.gba")
    parser.add_argument("--nds-launch-path", help="Model the launcher's actual SD argv[0], e.g. fat:/Fusion.nds")
    parser.add_argument("--wait-package", action='store_true', help='Wait for bootstrap handoff before the gameplay input/capture timeline')
    parser.add_argument("--package-boot-frames", type=int, default=30000)
    parser.add_argument("--input-script", type=Path, help='JSON array of {start,end,buttons} frame intervals')
    parser.add_argument('--memory-script', type=Path, help='Test-only JSON writes to isolated emulator RAM at specified frames')
    parser.add_argument("--fusion-state", action='store_true', help='Decode US Fusion IWRAM using the patched diagnostic core')
    parser.add_argument("--assert-fusion", action='store_true', help='Verify the full scripted Fusion new-game/movement run')
    parser.add_argument("--assert-fusion-screen", action='store_true', help='Check rendered bottom-screen IDs/grid against guest RAM')
    parser.add_argument("--frames", type=int, default=240)
    parser.add_argument("--capture", default="60,120,180,240")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--press-a-start", type=int, default=150)
    parser.add_argument("--press-a-end", type=int, default=210)
    parser.add_argument("--jit", action="store_true")
    parser.add_argument("--assert-probe", action="store_true")
    parser.add_argument("--assert-gba-probe", action="store_true", help="Assert original GBA probe marker and increasing frame count in DS main RAM")
    parser.add_argument("--expect-pixel", action="append", default=[], metavar="FRAME,X,Y,R,G,B")
    parser.add_argument("--force-failure", action="store_true")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.frames <= 0 or args.timeout <= 0:
        parser.error("Frame and timeout limits must be positive")
    if args.worker:
        return worker(args)
    if args.output.exists():
        parser.error("Output directory must be new, to prevent reusing writable emulator state")
    args.output.mkdir(parents=True)
    start = time.monotonic()
    with (args.output / "emulator.log").open("wb") as log:
        proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), *sys.argv[1:], "--worker"],
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        def capture_log():
            # Native emulation errors can repeat millions of times. Drain the pipe
            # while bounding disk use, retaining the beginning and end of the log.
            budget, skipped, tail = 1024 * 1024, 0, b""
            while chunk := proc.stdout.read(65536):
                take = min(len(chunk), budget)
                log.write(chunk[:take])
                budget -= take
                skipped += len(chunk) - take
                tail = (tail + chunk)[-16384:]
            if skipped:
                log.write(f"\n[Omitted {skipped} bytes of repeated output; final tail follows]\n".encode())
                log.write(tail)
        thread = threading.Thread(target=capture_log, daemon=True)
        thread.start()
        try:
            code = proc.wait(timeout=args.timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            code = 124
        thread.join()
    report = args.output / "result.json"
    result = json.loads(report.read_text()) if report.exists() else {}
    if code and result.get("status") != "failed":
        result.update(status="timeout" if code == 124 else "error", exit_code=code)
    result["process_elapsed_seconds"] = round(time.monotonic() - start, 3)
    report.write_text(json.dumps(result, indent=2) + "\n")
    suite = ET.Element("testsuite", name="melonDS", tests="1", failures=str(int(code != 0)))
    case = ET.SubElement(suite, "testcase", name=args.output.name, time=str(result["process_elapsed_seconds"]))
    if code:
        ET.SubElement(case, "failure", message=result["status"]).text = "See emulator.log and result.json"
    elif result.get("status") == "observed":
        ET.SubElement(case, "skipped", message="Observation only; no boot assertion supplied")
    ET.ElementTree(suite).write(args.output / "junit.xml", encoding="utf-8", xml_declaration=True)
    print(f"{result.get('status', 'error')}: {report}")
    if code:
        print((args.output / "emulator.log").read_text()[-3000:])
    return code if code >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())
