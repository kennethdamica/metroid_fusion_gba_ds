"""Read-only checks for the pinned US Fusion ROM and scripted new-game run.

Definitions: metroidret/mf revision 8614cc3eec194092cd756d6382c879b4c2ab4967,
linker.ld, include/globals.h, and include/structs/samus.h.
"""
import hashlib
from pathlib import Path

from fusion_profile import FUSION_SHA1
CAPTURES = '1200,24000,26000,26150,26300,26700,26850,27000,27500,27520,27600,30000'


def decode(data):
    if len(data) != 0x8000:
        raise ValueError('Expected all 32 KiB of physical shared WRAM')
    u16 = lambda offset: int.from_bytes(data[offset:offset+2], 'little')
    return dict(game_frame=u16(2), main_mode=u16(0xBDE), sub_mode=u16(0xBE0),
                area=data[0x2C], room=data[0x2D], demo=data[0x1242], demo_seen=data[0x1F],
                buttons=u16(0x11E8), x=u16(0x125A), y=u16(0x125C))


def verify(root, sd, check, save_path=None):
    samples = {}
    for frame in map(int, CAPTURES.split(',')):
        path = root / f'shared-wram-{frame:06d}.bin'
        if path.exists():
            samples[frame] = decode(path.read_bytes())
    check('Fusion_required_checkpoints', len(samples) == len(CAPTURES.split(',')))
    if len(samples) != len(CAPTURES.split(',')):
        return
    check('Fusion_file_select', samples[1200]['main_mode'] == 7)
    playing = [s for f, s in samples.items() if f >= 24000]
    check('Fusion_playable_not_demo', all(s['main_mode'] == 1 and s['sub_mode'] == 2 and s['demo'] == 0 for s in playing))
    check('Fusion_guest_frames_advance', all(0 < (b['game_frame']-a['game_frame']) % 65536 < 32768 for a, b in zip(playing, playing[1:])))
    check('Fusion_right_input', samples[26150]['buttons'] == 16)
    check('Fusion_moves_right', samples[26150]['room'] == samples[26000]['room'] and samples[26150]['x'] > samples[26000]['x'])
    check('Fusion_left_input', samples[26850]['buttons'] == 32)
    check('Fusion_moves_left', samples[26850]['room'] == samples[26700]['room'] and samples[26850]['x'] < samples[26700]['x'])
    check('Fusion_room_transition', samples[27000]['room'] != samples[26700]['room'])
    check('Fusion_jump_input', samples[27520]['buttons'] == 1)
    check('Fusion_jumps_and_lands', samples[27520]['y'] < samples[27500]['y'] and samples[27600]['y'] == samples[27500]['y'])
    rom = sd / 'rom.gba'
    check('Fusion_ROM_unchanged', rom.is_file() and hashlib.sha1(rom.read_bytes()).hexdigest() == FUSION_SHA1)
    save = save_path if save_path is not None else sd / 'rom.sav'
    check('Fusion_separate_32KiB_save', save.is_file() and save.stat().st_size == 32768)
