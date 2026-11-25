#!/usr/bin/env python3
"""Bundle a verified local Fusion ROM and BIOS into a bootable extractor NDS."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import zipfile
from fusion_profile import FUSION_SHA1, BIOS_SHA256, ROM_BYTES
from game_profiles import FUSION, ALTTP
from rom_compatibility import validate_rom
from nds_banner import crc16, set_menu_banner, TITLES

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNTIME = ROOT / 'artifacts/hardware-runtime'
DATA_ROOT = Path('_fusion') / FUSION_SHA1
DATA_DIR = DATA_ROOT / 'v1'
CONFIG = b'{}\n'
NAMES = ('manifest.bin', 'rom.gba', 'bios.bin', 'config.json')
MAGIC = b'FUSPKG01'


def verify_melonds_copy(original, copied):
    """Allow the pinned core's DLDI replacement and zero capacity padding only."""
    a, b = original.read_bytes(), copied.read_bytes()
    offset = a.find(bytes.fromhex('eda58dbf') + b' Chishm\0')
    if offset < 0 or offset+16 > len(a):
        return False
    allocated = 1 << a[offset+15]
    capacity = 1 << (len(a)-1).bit_length()
    return (offset+allocated <= len(a) and len(b) == capacity
            and b[:offset] == a[:offset] and b[offset+allocated:len(a)] == a[offset+allocated:]
            and b[offset+16:offset+36] == b'melonDS DLDI driver\0'
            and not any(b[len(a):]))


def read_bios(path):
    if not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError('Choose a 16 KiB GBA BIOS file or a small ZIP containing it')
    data = path.read_bytes()
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            entries = [i for i in archive.infolist() if i.file_size == 16384 and not i.is_dir()]
            if len(entries) != 1:
                raise ValueError('BIOS zip must contain exactly one 16 KiB file')
            data = archive.read(entries[0])
    if hashlib.sha256(data).hexdigest() != BIOS_SHA256:
        raise ValueError('BIOS differs from the verified original GBA BIOS')
    return data


def inspect_package(path, *, profile=FUSION):
    if path.stat().st_size > 16 * 1024 * 1024:
        raise ValueError('File is too large for a Fusion NDS package')
    data = path.read_bytes()
    if len(data) < 0x200 or crc16(data[:0x15E]) != struct.unpack_from('<H', data, 0x15E)[0]:
        raise ValueError('Invalid NDS header checksum')
    fnt, fnt_size, fat, fat_size = struct.unpack_from('<4I', data, 0x40)
    if fat_size != 32 or fnt < 0x200 or fnt + fnt_size > fat or fat + 32 > len(data):
        raise ValueError('Invalid NitroFS tables')
    if data[fnt:fnt+8] != struct.pack('<IHH', 8, 0, 1):
        raise ValueError('Invalid NitroFS root')
    names = b''.join(bytes([len(n)]) + n.encode() for n in NAMES) + b'\0'
    if data[fnt+8:fnt+fnt_size] != names:
        raise ValueError('Unexpected package filenames')
    payloads, previous = {}, fat + 32
    for i, name in enumerate(NAMES):
        start, end = struct.unpack_from('<II', data, fat + 8*i)
        if not previous <= start <= end <= len(data):
            raise ValueError('Invalid payload bounds')
        payloads[name] = data[start:end]
        previous = end
    manifest = payloads['manifest.bin']
    if profile is None:
        profile = next((p for p in (FUSION, ALTTP) if manifest[:8] == p.magic), None)
    if profile is None or len(manifest) not in (76, 80) or manifest[:8] != profile.magic:
        raise ValueError('Unsupported package manifest')
    version, abi = struct.unpack_from('<II', manifest, 8)
    flags = struct.unpack_from('<I', manifest, 76)[0] if len(manifest) == 80 else 0
    if (version, abi, len(manifest)) not in ((1, 1, 76), (2, 2, 80)) or flags & ~1:
        raise ValueError('Unsupported package manifest')
    for i, name in enumerate(NAMES[1:]):
        if hashlib.sha1(payloads[name]).digest() != manifest[16+20*i:36+20*i]:
            raise ValueError(f'Payload hash mismatch: {name}')
    compatibility = validate_rom(payloads['rom.gba'], profile, allow_unsupported=bool(flags & 1))
    if bool(flags & 1) != compatibility['experimental']:
        raise ValueError('ROM compatibility flag disagrees with its identity')
    data_root = Path(profile.directory) / compatibility['rom_sha1']
    if hashlib.sha256(payloads['bios.bin']).hexdigest() != BIOS_SHA256 or payloads['config.json'] != CONFIG:
        raise ValueError('Unsupported BIOS/configuration')
    if struct.unpack_from('<I', data, 0x80)[0] != len(data):
        raise ValueError('NDS used size disagrees with file size')
    return dict(package_sha256=hashlib.sha256(data).hexdigest(), package_bytes=len(data),
                payloads={n: dict(bytes=len(b), sha256=hashlib.sha256(b).hexdigest()) for n,b in payloads.items()},
                game=profile.key, format_version=version, **compatibility,
                data_directory=(data_root / 'v1').as_posix(), save_path=(data_root / 'rom.sav').as_posix())


def publish_new(source, destination):
    """Atomically publish a complete file without replacing an existing path."""
    if sys.platform == 'darwin':
        import ctypes
        libc = ctypes.CDLL(None, use_errno=True)
        rename = libc.renamex_np
        rename.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint)
        rename.restype = ctypes.c_int
        if rename(os.fsencode(source), os.fsencode(destination), 4):  # RENAME_EXCL
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error), str(destination))
    elif os.name == 'nt':
        os.rename(source, destination)  # Windows rename refuses replacement.
    else:
        os.link(source, destination)  # Same-directory temporary, no overwrite.
        source.unlink()


def stage_file(destination, data):
    fd, name = tempfile.mkstemp(prefix='.'+destination.name+'.', suffix='.tmp', dir=destination.parent)
    path = Path(name)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return path


def build(runtime_dir, rom_path, bios_path, output, *, write_manifest=True, profile=FUSION, allow_unsupported_rom=False):
    sidecar = output.with_suffix('.manifest.json')
    if os.path.lexists(output) or (write_manifest and os.path.lexists(sidecar)):
        raise ValueError('Output must be new; existing packages are never overwritten')
    if not rom_path.is_file() or rom_path.stat().st_size != ROM_BYTES:
        raise ValueError(f'Only the verified US {profile.title} ROM is supported (8 MiB, original revision)')
    rom, bios = rom_path.read_bytes(), read_bios(bios_path)
    compatibility = validate_rom(rom, profile, allow_unsupported=allow_unsupported_rom)
    template = runtime_dir / 'sdcard' / profile.template
    build_manifest = json.loads((runtime_dir / 'manifest.json').read_text())
    if build_manifest.get('game', 'fusion') != profile.key:
        raise ValueError('Runtime template belongs to another game')
    data = bytearray(template.read_bytes())
    abi = build_manifest.get('package_abi')
    if abi not in (1, 2) or hashlib.sha256(data).hexdigest() != build_manifest['rom_sha256']:
        raise ValueError('Runtime template does not match its build manifest/ABI')
    if compatibility['experimental'] and abi != 2:
        raise ValueError('Experimental ROMs require a rebuilt ABI 2 runtime template')
    if len(data) < 0x200 or crc16(data[:0x15E]) != struct.unpack_from('<H', data, 0x15E)[0]:
        raise ValueError('Invalid template header')
    set_menu_banner(data, profile.key)
    # Preserve both executable load segments and DLDI patch space. The game is
    # NitroFS data, outside the ARM9 segment, never an 8 MiB RAM load.
    def align(n):
        data.extend(b'\0' * (-len(data) % n))
    align(512)
    fnt = len(data)
    names = b''.join(bytes([len(n)]) + n.encode() for n in NAMES) + b'\0'
    data.extend(struct.pack('<IHH', 8, 0, 1) + names)
    fnt_size = len(data)-fnt
    align(4)
    fat = len(data)
    data.extend(b'\0'*32)
    manifest = profile.magic + struct.pack('<II', abi, abi) + b''.join(hashlib.sha1(b).digest() for b in (rom,bios,CONFIG))
    if abi == 2:
        manifest += struct.pack('<I', int(compatibility['experimental']))
    for i, payload in enumerate((manifest,rom,bios,CONFIG)):
        align(512)
        start = len(data)
        data.extend(payload)
        struct.pack_into('<II',data,fat+8*i,start,len(data))
    align(512)
    struct.pack_into('<4I',data,0x40,fnt,fnt_size,fat,32)
    struct.pack_into('<I',data,0x80,len(data))
    capacity = 0
    while (128*1024 << capacity) < len(data):
        capacity += 1
    data[0x14] = capacity
    data[:12] = profile.nds_title
    struct.pack_into('<H',data,0x15E,crc16(data[:0x15E]))
    output.parent.mkdir(parents=True,exist_ok=True)
    staged = stage_file(output, data)
    staged_report = None
    published_report = False
    try:
        report = inspect_package(staged, profile=profile)
        report.update(runtime=build_manifest, menu_title=TITLES[profile.key],
                      launch_without_argv=f'Place the file at SD root as {profile.filename}',
                      first_launch='Extracts verified ROM/BIOS/config. Existing saves are never replaced.')
        if write_manifest:
            staged_report = stage_file(sidecar, (json.dumps(report, indent=2)+'\n').encode())
            report_identity = staged_report.stat()
            publish_new(staged_report, sidecar)
            published_report = True
        publish_new(staged, output)
        return report
    except BaseException:
        # Only remove our own newly published report, never a preexisting file.
        if published_report and sidecar.exists() and os.path.samestat(sidecar.stat(), report_identity):
            sidecar.unlink()
        raise
    finally:
        staged.unlink(missing_ok=True)
        if staged_report:
            staged_report.unlink(missing_ok=True)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runtime',type=Path,default=DEFAULT_RUNTIME)
    p.add_argument('--rom',type=Path)
    p.add_argument('--bios',type=Path)
    p.add_argument('--output',type=Path)
    p.add_argument('--inspect',type=Path)
    args=p.parse_args()
    try:
        if args.inspect:
            report=inspect_package(args.inspect)
        else:
            if not all((args.rom,args.bios,args.output)):
                p.error('--rom, --bios and --output are required')
            report=build(args.runtime,args.rom,args.bios,args.output)
        print(json.dumps(report,indent=2))
    except (ValueError,OSError,KeyError) as e:
        p.exit(1,f'{e}\n')


if __name__=='__main__':
    main()
