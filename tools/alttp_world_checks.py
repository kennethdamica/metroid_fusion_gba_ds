"""Independent ROM oracle for the bottom world's terrain and quest sprites."""
import struct


def unpack_sheet(rom, offset):
    size=int.from_bytes(rom[offset+1:offset+4],'little')
    if rom[offset]!=0x10 or size!=2048:raise ValueError('Unexpected marker sheet')
    output=bytearray();position=offset+4
    while len(output)<size:
        flags=rom[position];position+=1
        for bit in range(7,-1,-1):
            if len(output)>=size:break
            if flags>>bit&1:
                token=int.from_bytes(rom[position:position+2],'big');position+=2
                distance=(token&4095)+1
                for _ in range((token>>12)+3):output.append(output[-distance])
            else:output.append(rom[position]);position+=1
    return output


def world_colors(rom, ram, shared, world=0):
    half=lambda address:struct.unpack_from('<H',rom,address)[0]
    colors=[]
    for y in range(128):
        for x in range(128):
            sx,sy=128+x*2,128+y*2
            tile=rom[0x3BFEF8+world*4096+sy//8*64+sx//8]
            index=rom[0x28A7E0+tile*64+sy%8*8+sx%8]
            colors.append(half(0x3BFA58+world*256+index*2) if index else 3|(5<<5)|(4<<10))
    markers=[]
    px=ram[0x1094F]|ram[0x1095F]<<8;py=ram[0x1096F]|ram[0x1097F]<<8
    if world==0 and (px or py):markers.append((px,py,0xCA,2,16))
    stage=shared[0x3890]
    if stage<=8 and (stage>=6)==bool(world) and not ram[0x22DB]&32:
        for i in range(7):
            if stage==3 and i<3 and ram[0x2354]&rom[0x16EEB6+i]:continue
            if stage==7 and ram[0x235A]&rom[0x16EEB9+i]:continue
            x=half(0x16ED34+36*i+2*stage);y=half(0x16ED46+36*i+2*stage)
            style=half(0x16EE30+18*i+2*stage)
            if x&0x8000:continue
            markers.append((x,y,style>>8 if style else 0xC8,(style>>1)&7 if style else 1,16 if style else 8))
    sheet=unpack_sheet(rom,0x236420)
    for x,y,tile,bank,size in markers:
        if x>=4096 or y>=4096:continue
        for row in range(8):
            for col in range(8):
                dx,dy=x//32-4+col,y//32-4+row
                if not(0<=dx<128 and 0<=dy<128):continue
                sx,sy=col*size//8,row*size//8
                tile_index=32+(tile-0xC0)//32*16+(tile&31)+(sy//8)*16+sx//8
                value=(sheet[tile_index*32+sy%8*4+sx%8//2]>>(sx%2*4))&15
                if value:colors[dy*128+dx]=half(0x3B566C+bank*32+value*2)
    return colors


def verify_perspective(root, rom, debug_address):
    """Validate captured map rows against Zelda's live affine table, not a screenshot baseline.

    Run with tests/alttp/world-map-input.json and a copy of a save that resumes
    in Link's house. The normal save and its original SD folder are never edited.
    """
    from pathlib import Path
    from PIL import Image
    root=Path(root);checks=[];matches={}
    def check(name,value):checks.append(dict(name=name,passed=bool(value)))
    for frame in (4100,4101,4102,4103,4200,4500,4501,4502,4503,4800,5100):
        ram=(root/f'ram-{frame:06d}.bin').read_bytes()
        shared=(root/f'shared-wram-{frame:06d}.bin').read_bytes()
        screen=Image.open(root/f'top-{frame:06d}.png').convert('RGB')
        check(f'original_map_open_{frame}',shared[0x2BDC]==14 and shared[0x2BB2]==3)
        cx=struct.unpack_from('<h',shared,0x2B80)[0];cy=struct.unpack_from('<h',shared,0x2B86)[0]
        world=(shared[0x2BF6]>>6)&1
        matched=total=0
        # Window clips rows 0/1 and 158/159. HBlank h prepares visible row h+1.
        for y in range(3,157):
            h=y-1;scale=struct.unpack_from('<H',ram,0x1400+h*2)[0]
            for x in range(240):
                sx=((cx*256+scale*(x-120))>>8)%512
                sy=((cy*256+(scale+scale//2)*h)>>8)%512
                tile=rom[0x3BFEF8+world*4096+sy//8*64+sx//8]
                index=rom[0x28A7E0+tile*64+sy%8*8+sx%8]
                color=struct.unpack_from('<H',ram,0xC00+index*2)[0]
                expected=tuple((color>>shift&31)*255//31 for shift in (0,5,10))
                actual=screen.getpixel((x+8,y+16))
                matched+=all(abs(a-b)<=8 for a,b in zip(expected,actual));total+=1
        matches[str(frame)]=matched/total
        # Sprite markers cover a small part of the background and are allowed.
        check(f'perspective_matches_ROM_scanlines_{frame}',matched/total>0.98)
    def shared(frame):return (root/f'shared-wram-{frame:06d}.bin').read_bytes()
    check('zoom_out',shared(4200)[0x2DE3]==1 and shared(4500)[0x2DE3]==0)
    check('zoom_in',shared(5100)[0x2DE3]==1)
    check('return_to_gameplay',shared(5400)[0x2BDC]==9)
    def counts(frame):
        return struct.unpack_from('<2I',(root/f'ram-{frame:06d}.bin').read_bytes(),debug_address-0x02000000)
    start,end=counts(4200),counts(5100)
    check('native_scanline_handler_active',end[0]-start[0]>100000)
    check('no_crossed_scanlines_during_stable_map',end[1]==start[1])
    return dict(status='passed' if all(c['passed'] for c in checks) else 'failed',
                checks=checks,background_match=matches,hblank_start=start,hblank_end=end)


def verify_bottom_markers(root,rom):
    """Check seeded pendant/crystal progression against an independent ROM oracle."""
    from pathlib import Path
    from PIL import Image
    root=Path(root);checks=[]
    for frame in (5700,5950,6200,6450):
        ram=(root/f'ram-{frame:06d}.bin').read_bytes()
        shared=(root/f'shared-wram-{frame:06d}.bin').read_bytes()
        world=(shared[0x2BF6]>>6)&1
        colors=world_colors(rom,ram,shared,world)
        screen=Image.open(root/f'bottom-{frame:06d}.png').convert('RGB')
        px=struct.unpack_from('<H',shared,0x38F4)[0]//32
        py=struct.unpack_from('<H',shared,0x38F0)[0]//32
        mismatches=0
        for y in range(128):
            for x in range(128):
                if abs(x-px)+abs(y-py)<=2:continue # Link's separate foreground diamond
                color=colors[y*128+x]
                expected=tuple((color>>shift&31)*255//31 for shift in (0,5,10))
                actual=screen.getpixel((8+x,40+y))
                mismatches+=any(abs(a-b)>8 for a,b in zip(expected,actual))
        checks.append(dict(frame=frame,world=world,stage=shared[0x3890],
                           mismatches=mismatches,passed=mismatches==0))
    return dict(status='passed' if all(c['passed'] for c in checks) else 'failed',checks=checks,
                fixture='Quest/collection/world state seeded in isolated emulator RAM; Link marker excluded.')


if __name__=='__main__':
    import argparse,json
    from pathlib import Path
    parser=argparse.ArgumentParser(description='Validate the original Zelda world-map perspective after an emulator run.')
    parser.add_argument('--captures',type=Path,required=True)
    parser.add_argument('--rom',type=Path,required=True)
    parser.add_argument('--debug-address',type=lambda s:int(s,0))
    parser.add_argument('--markers',action='store_true',help='Validate seeded bottom-map progression instead of top-map timing')
    args=parser.parse_args()
    if not args.markers and args.debug_address is None:parser.error('--debug-address is required for perspective checks')
    result=verify_bottom_markers(args.captures,args.rom.read_bytes()) if args.markers else verify_perspective(args.captures,args.rom.read_bytes(),args.debug_address)
    filename='marker-validation.json' if args.markers else 'world-map-validation.json'
    (args.captures/filename).write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'])
    raise SystemExit(result['status']!='passed')
