"""ROM-free runtime validation shared by developer builds and release CI."""
import hashlib
import json
import struct
from package_fusion import ROOT, crc16
from fusion_pack import PROFILES, runtime_directory


def validated_runtimes():
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    runtime_lock = json.loads((ROOT/'release/packager/runtime-lock.json').read_text())
    bundled = {}
    runtimes = {}
    for profile in PROFILES.values():
        runtime = runtime_directory(profile)
        manifest_path = runtime/'manifest.json'
        template = runtime/'sdcard'/profile.template
        manifest = json.loads(manifest_path.read_text())
        data = template.read_bytes()
        locked = runtime_lock['games'][profile.key]
        if sha(template) != locked['template_sha256'] or locked['package_abi'] != 2:
            raise ValueError('Runtime is not the validated release template; update runtime-lock.json only after gameplay tests')
        fnt, fnt_size, fat, fat_size = struct.unpack_from('<4I', data, 0x40)
        if (manifest.get('package_abi') != 2 or sha(template) != manifest['rom_sha256'] or
                manifest.get('game', 'fusion') != profile.key or
                not 0x200 <= len(data) < 1024*1024 or fat_size != 0 or fnt_size != 9 or
                data[fnt:fnt+fnt_size] != struct.pack('<IHHB', 8, 0, 1, 0) or
                crc16(data[:0x15e]) != int.from_bytes(data[0x15e:0x160], 'little')):
            raise ValueError('Expected runtime-only NDS templates without NitroFS payloads')
        for path, expected in manifest['inputs'].items():
            if sha(ROOT/path) != expected:
                raise ValueError(f'Runtime source changed since its build: {path}')
        bundled[f'runtime/{profile.key}/sdcard/{profile.template}'] = template
        bundled[f'runtime/{profile.key}/manifest.json'] = manifest_path
        runtimes[profile.key] = manifest
    bundled['rom_compatibility.json'] = ROOT/'tools/rom_compatibility.json'
    return bundled, runtimes, runtime_lock
