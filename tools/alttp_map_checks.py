"""Display checks using explicitly synthetic locations in isolated emulator RAM.

These exercise the shipping overlay, touch mailbox and video renderer. They do
not claim that the player naturally entered each dungeon or acquired its map.
"""
import json
import struct
from pathlib import Path
from PIL import Image

CASES=json.loads((Path(__file__).resolve().parents[1]/'tests/alttp/map-cases.json').read_text())
# Allow the bounded composer to finish dense floors before pixel assertions.
FLOOR_FRAMES=(21770,21812,21852,21892,21932)
MAP_CAPTURES=','.join(str(f) for f in [*[c['frame'] for c in CASES],*FLOOR_FRAMES])


def verify_maps(root,check,render_debug_address=None):
    root=Path(root)
    def screen(frame):return Image.open(root/f'bottom-{frame:06d}.png').convert('RGB')
    for case in CASES:
        frame=case['frame'];image=screen(frame).crop((8,40,136,168))
        gold=sum(r>230 and 160<g<215 and b<80 for r,g,b in image.getdata())
        check(f'dungeon_{case["dungeon"]}_current_room_highlight',gold>20)
        ram=(root/f'shared-wram-{frame:06d}.bin').read_bytes()
        check(f'dungeon_{case["dungeon"]}_map_keeps_equipped_item',ram[0x2C7E]==2 and ram[0x39BC]==2)
    images=[screen(f) for f in FLOOR_FRAMES]
    labels=[im.crop((192,96,208,104)).tobytes() for im in images]
    check('floor_up_changes_label',labels[0]!=labels[1])
    check('floor_down_returns_to_1F',labels[0]==labels[2])
    check('floor_down_enters_basement',labels[0]!=labels[3])
    check('follow_returns_to_current_floor',labels[0]==labels[4])
    maps=[im.crop((8,40,136,168)).tobytes() for im in images]
    check('floor_controls_change_room_layout',maps[0]!=maps[1] and maps[0]!=maps[3])
    check('follow_restores_current_room_layout',maps[0]==maps[4])
    if render_debug_address:
        for frame in [CASES[0]['frame'],*FLOOR_FRAMES]:
            ram=(root/f'ram-{frame:06d}.bin').read_bytes()
            phase=struct.unpack_from('<I',ram,render_debug_address-0x02000000+24)[0]
            check(f'map_composition_complete_{frame}',phase==0)
