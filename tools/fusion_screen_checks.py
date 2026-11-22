"""Check rendered pixels against independent live guest memory snapshots."""
from PIL import Image
from fusion_checks import CAPTURES, decode

DIGITS = {
    '0': [14,17,19,21,25,17,14], '1': [4,12,4,4,4,4,14],
    '2': [14,17,1,2,4,8,31], '3': [30,1,1,14,1,1,30],
    '4': [2,6,10,18,31,2,2], '5': [31,16,16,30,1,1,30],
    '6': [14,16,16,30,17,17,14], '7': [31,1,2,4,8,8,8],
    '8': [14,17,17,14,17,17,14], '9': [14,17,17,15,1,1,14],
    'A': [14,17,17,31,17,17,17], 'B': [30,17,17,30,17,17,30],
    'C': [14,17,16,16,16,17,14], 'D': [30,17,17,17,17,17,30],
    'E': [31,16,16,30,16,16,31], 'F': [31,16,16,30,16,16,16],
    '-': [0,0,0,31,0,0,0],
}


def read_digit(image, x, y):
    rows = []
    for dy in range(7):
        bits = 0
        for dx in range(5):
            r, g, b = image.getpixel((x + 1 + dx, y + dy))
            bits = (bits << 1) | int(g > 180 and b > 200)
        rows.append(bits)
    return next((digit for digit, pattern in DIGITS.items() if rows == pattern), '?')


# Independently verified from Fusion's room headers and minimap layout. These
# fixtures intentionally do not implement the runtime's artwork flood fill.
ROOM_CELLS = {(0, 0): {(19, 13), (20, 13)}, (0, 3): {(17, 13), (18, 13)}}


def centered_frame(image):
    """Every pixel outside the exact native-size GBA viewport must be black."""
    return all(image.crop(box).getbbox() is None for box in
               ((0, 0, 256, 16), (0, 176, 256, 192),
                (0, 16, 8, 176), (248, 16, 256, 176)))


def map_image(rom, ram, state, shared):
    import struct
    palette = list(struct.unpack_from('<48H', rom, 0x5657A8))
    palette += palette[16:32] * 2
    palette[50] = palette[51] = 31 | (22 << 5) | (6 << 10)
    palette[66] = palette[67] = 0x7FFF
    palette[0] = 1 | (2 << 5) | (4 << 10)
    rgb = lambda c: tuple((((c >> shift) & 31) << 3) | (((c >> shift) & 31) >> 3) for shift in (0, 5, 10))
    expected = Image.new('RGB', (256, 160), rgb(palette[0]))
    px, py = shared[0x31:0x33]
    top = max(0, min(12, py - 10))
    cells = ROOM_CELLS[state['area'], state['room']]
    for y in range(20):
        for x in range(32):
            entry = struct.unpack_from('<H', ram, 0x34000 + 2*((y + top)*32 + x))[0]
            tile, bank = entry & 1023, entry >> 12
            if tile >= 448 or tile == 160 or bank > 2:
                continue
            if (x, y + top) in cells:
                bank = 4 if (x, y + top) == (px, py) else 3
            for ty in range(8):
                sy = 7-ty if entry & 0x800 else ty
                for tx in range(8):
                    sx = 7-tx if entry & 0x400 else tx
                    byte = rom[0x561FA8 + tile*32 + sy*4 + sx//2]
                    ink = (byte >> (4*(sx % 2))) & 15
                    color = palette[bank*16+ink] if ink else palette[0]
                    expected.putpixel((x*8+tx, y*8+ty), rgb(color))
    return expected


def verify(root, check):
    import hashlib
    from fusion_checks import FUSION_SHA1
    from package_fusion import DATA_DIR
    sd = root / 'state/save/melonDS DS/dldi_sd_card'
    rom_path = sd / 'rom.gba'
    if not rom_path.exists():
        rom_path = sd / DATA_DIR / 'rom.gba'
    rom = rom_path.read_bytes()
    if hashlib.sha1(rom).hexdigest() != FUSION_SHA1:
        raise ValueError('Map graphics reference requires the verified US ROM')
    before = decode((root / 'shared-wram-024000.bin').read_bytes())
    after = decode((root / 'shared-wram-026000.bin').read_bytes())
    check('Fusion_map_idle_frame_budget', (after['game_frame'] - before['game_frame']) % 65536 >= 1998)
    for frame in map(int, CAPTURES.split(',')):
        paths = [root / f'{prefix}-{frame:06d}.{extension}' for prefix, extension in
                 [('bottom', 'png'), ('top', 'png'), ('shared-wram', 'bin'), ('ram', 'bin')]]
        if not all(p.is_file() for p in paths):
            check(f'Fusion_screen_checkpoint_{frame}', False)
            continue
        bottom, top = Image.open(paths[0]).convert('RGB'), Image.open(paths[1]).convert('RGB')
        check(f'Fusion_centered_240x160_frame_{frame}', centered_frame(top))
        shared = paths[2].read_bytes()
        state = decode(shared)
        live = state['main_mode'] == 1 and state['sub_mode'] == 2 and state['demo'] == 0
        for name, x in [('area', 48), ('room', 112)]:
            actual = ''.join(read_digit(bottom, x+i*8, 8) for i in range(2))
            expected = f'{state[name]:02X}' if live else '--'
            check(f'Fusion_screen_{name}_{frame}_{expected}', actual == expected)
        actual = bottom.crop((0, 24, 256, 184))
        if live:
            expected = map_image(rom, paths[3].read_bytes(), state, shared)
            expected.save(root / f'expected-map-{frame:06d}.png')
            check(f'Fusion_real_map_pixels_{frame}', actual.tobytes() == expected.tobytes())
            colors = actual.getcolors(256*160)
            gold = sum(n for n,c in colors if c[0] > 240 and 160 < c[1] < 200 and c[2] < 70)
            check(f'Fusion_current_room_highlight_{frame}', gold > 20)
        else:
            check(f'Fusion_map_wait_{frame}', len(actual.getcolors(256*160)) == 1)
            check(f'Fusion_no_false_highlight_{frame}', actual.getpixel((0, 0)) == (8, 16, 32))
        check(f'Fusion_top_gameplay_visible_{frame}', len(top.getcolors(256*192) or []) >= 32 and top.tobytes() != bottom.tobytes())
