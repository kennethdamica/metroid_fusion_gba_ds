"""Conservative adapter preflight, not a guarantee of hack compatibility.

Only digests/addresses are shipped. No reference ROM or game assets are needed.
"""
import hashlib
import json
from pathlib import Path
from fusion_profile import ROM_BYTES

# Keep this beside the module in source and include it explicitly in frozen builds.
RULES = json.loads(Path(__file__).with_name('rom_compatibility.json').read_text())


def check_lz(rom, offset, size):
    """Validate the bounded GBA LZ stream consumed by the bottom-screen adapter."""
    limit = min(offset + 2048, len(rom))
    if (offset < 0 or offset + 4 > limit or rom[offset] != 0x10 or
            int.from_bytes(rom[offset + 1:offset + 4], 'little') != size):
        raise ValueError(f'Incompatible graphics stream at ROM offset 0x{offset:X}')
    position, produced = offset + 4, 0
    while produced < size:
        if position >= limit:
            raise ValueError('Compressed graphics exceed the runtime input buffer')
        flags = rom[position]
        position += 1
        for bit in range(7, -1, -1):
            if produced == size:
                break
            if flags >> bit & 1:
                if position + 2 > limit:
                    raise ValueError('Truncated graphics backreference')
                token = int.from_bytes(rom[position:position + 2], 'big')
                position += 2
                length, distance = (token >> 12) + 3, (token & 4095) + 1
                if distance > produced or produced + length > size:
                    raise ValueError('Invalid graphics backreference')
                produced += length
            else:
                if position >= limit:
                    raise ValueError('Truncated graphics literal')
                position += 1
                produced += 1


def validate_rom(rom, profile, allow_unsupported=False):
    actual = hashlib.sha1(rom).hexdigest()
    known = actual == profile.rom_sha1
    if not known and not allow_unsupported:
        raise ValueError(
            f'Only the verified US {profile.title} ROM is supported by default. '
            f'For an experimental variant use --game {profile.key} --allow-unsupported-rom.')
    if len(rom) != ROM_BYTES:
        raise ValueError('ROM must be exactly 8 MiB; expanded or truncated ROMs are not supported')
    code = {'fusion': b'AMTE', 'alttp': b'AZLE'}[profile.key]
    if rom[0xAC:0xB0] != code or rom[0xBC] != 0:
        raise ValueError(f'Incompatible game/region/revision: expected {code.decode()} revision 0')
    if rom[0xB2] != 0x96 or (sum(rom[0xA0:0xBE]) + 0x19) & 255:
        raise ValueError('Invalid GBA header/checksum')
    checks = ['8 MiB ROM', 'game/region/revision', 'GBA header checksum']
    for rule in RULES[profile.key]:
        if hashlib.sha256(rom[rule['start']:rule['end']]).hexdigest() != rule['sha256']:
            raise ValueError('Incompatible ROM: ' + rule['name'] +
                             ' differs from the supported adapter layout. '
                             '--allow-unsupported-rom cannot bypass this check.')
        checks.append(rule['name'])
    if profile.key == 'alttp':
        streams = [(0x3BFC58, 2048), (0x27C5CC, 4096)]
        streams += [(offset, 2048) for offset in
                    (0x255460, 0x2521CC, 0x255658, 0x2523F8, 0x246EA0, 0x236420)]
        for offset, size in streams:
            check_lz(rom, offset, size)
        if max(rom[0x28A7E0:0x28A7E0 + 16384]) >= 128:
            raise ValueError('World-map graphics reference colors outside the adapter palette')
        checks += ['bounded inventory/map graphics', 'world-map palette indices']
    return dict(rom_sha1=actual, experimental=not known, compatibility_checks=checks,
                compatibility='experimental' if not known else 'verified')
