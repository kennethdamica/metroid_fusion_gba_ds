"""Checks for the local AZLE r0 touch fixture (two test-seeded owned items)."""
import struct
from pathlib import Path
from PIL import Image

CAPTURES = '1000,19000,20010,20034,20040,20080,20104,20140,20240,20304,20320,20380,20540,20604,20620,20800,21060,21140,21400'


def verify(root, rom, check):
    root=Path(root)
    samples={}
    for frame in (20010,20034,20040,20080,20104,20140,20240,20304,20320,20380,20540,20604,20620,20800,21060,21140):
        main=(root/f'ram-{frame:06d}.bin').read_bytes()
        ram=(root/f'shared-wram-{frame:06d}.bin').read_bytes()
        half=lambda at:int.from_bytes(ram[at:at+2],'little')
        samples[frame]=dict(slot=ram[0x2C7E], item=ram[0x39BC], in_use=ram[0x39BD],
            mode=ram[0x2BDC], submode=ram[0x2BDD], x=half(0x38F4), y=half(0x38F0),
            magic=main[0x234E], inventory=main[0x2320:0x2338],
            projectiles=list(ram[0x3045:0x304F]),
            hud=b''.join(main[i:i+2] for i in (0xB1F8,0xB1FA,0xB238,0xB23A)))
    check('live_gameplay_through_item_switches',all(s['mode'] in (7,9) and s['submode']==0 for f,s in samples.items() if f<21000))
    for frame,slot,item in ((20034,2,2),(20104,13,9),(20540,2,2)):
        s=samples[frame]
        check(f'touch_equips_slot_{slot}_at_{frame}',s['slot']==slot and s['item']==item and s['in_use']==item)
        pointer=struct.unpack_from('<I',rom,0x16B5A8+(slot-1)*4)[0]-0x08000000
        check(f'game_HUD_matches_selected_item_at_{frame}',s['hud']==rom[pointer+8:pointer+16])
    check('movement_continues_during_touch',samples[20010]['x']<samples[20034]['x']<samples[20080]['x'])
    check('unowned_bow_tap_ignored',samples[20240]['slot']==13 and samples[20240]['item']==9)
    check('lamp_action_consumes_magic',samples[20140]['magic']==samples[20240]['magic'] and samples[20304]['magic']<samples[20240]['magic'])
    check('boomerang_does_not_consume_magic',samples[20540]['magic']==samples[20620]['magic'])
    check('boomerang_action_spawns_then_retires_projectile',5 not in samples[20540]['projectiles'] and 5 in samples[20604]['projectiles'] and 5 not in samples[20800]['projectiles'])
    check('touch_rejected_in_original_menu',samples[21060]['mode']==14 and samples[21140]['mode']==14 and samples[21140]['slot']==samples[21060]['slot']==2)
    check('equipping_and_using_does_not_grant_items',all(s['inventory']==samples[20010]['inventory'] for s in samples.values()))
    for frame,slot in ((20040,2),(20140,13),(20540,2)):
        check(f'bottom_highlight_slot_{slot}_at_{frame}',native_highlight(root,frame,slot))
    check('inventory_bottom_edge_is_black',all(
        pixel==(0,0,0) for frame in (20040,20140,20540)
        for pixel in Image.open(root/f'bottom-{frame:06d}.png').convert('RGB').crop((0,184,256,192)).getdata()))
    check('bottom_blank_before_gameplay',all(pixel==(0,0,0) for pixel in
        Image.open(root/'bottom-001000.png').convert('RGB').getdata()))
    # The same selected item appears in the game's own pause menu later. Compare
    # its original art with our menu, translated down by the 8px taller tab strip.
    original=Image.open(root/'top-021140.png').convert('RGB').crop((8,16,248,176))
    native=Image.open(root/'bottom-020540.png').convert('RGB').crop((8,24,248,184))
    matching=sum(all(abs(x-y)<=8 for x,y in zip(a,b)) for a,b in zip(original.getdata(),native.getdata()))
    check('inventory_matches_original_menu_art',matching>=240*160*0.99)
    image=Image.open(root/'bottom-020800.png').convert('RGB')
    from alttp_world_checks import world_colors
    colors=world_colors(rom,(root/'ram-020800.bin').read_bytes(),(root/'shared-wram-020800.bin').read_bytes())
    mismatches=0
    for y in range(128):
        for x in range(128):
            color=colors[y*128+x]
            expected=tuple(((color>>shift)&31)*255//31 for shift in (0,5,10))
            if any(abs(a-b)>8 for a,b in zip(image.getpixel((8+x,40+y)),expected)):mismatches+=1
    check('map_tab_renders_original_world_and_objectives',mismatches==0)
    check('map_tab_preserves_equipped_item',samples[20800]['slot']==samples[20540]['slot']==2)
    return {str(f):{k:v for k,v in s.items() if k not in ('inventory','hud')} for f,s in samples.items()}


def native_highlight(root,frame,slot):
    image=Image.open(Path(root)/f'bottom-{frame:06d}.png').convert('RGB')
    x=16+(slot-1)%6*24;y=32+(slot-1)//6*24
    return sum(g>230 and r<80 and b<80 for r,g,b in image.crop((x,y,x+8,y+16)).getdata())>=6
