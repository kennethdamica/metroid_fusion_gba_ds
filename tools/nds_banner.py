"""Original pixel icons and game-specific DS menu banners; standard library only.

Layout: https://mgba-emu.github.io/gbatek/#ds-cartridge-icontitle
The icon is 16 tiled 8x8 blocks, 4bpp, with palette entry zero transparent.
"""
import struct

TITLES = {
    'fusion': 'Metroid Fusion\nDS',
    'alttp': 'The Legend of Zelda\nA Link to the Past\nDS',
}
# Original, code-drawn artwork; no extracted game graphics.
PALETTE = (
    (0,0,0), (8,16,32), (21,43,66), (38,76,100),
    (38,139,191), (104,214,239), (249,190,44), (255,229,123),
    (194,101,22), (236,76,39), (119,30,35), (39,110,57),
    (91,211,82), (198,255,137), (156,186,191), (237,250,246),
)


def crc16(data):
    crc=0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):crc=(crc>>1)^(0xA001 if crc&1 else 0)
    return crc


def icon_pixels(game):
    if game not in TITLES:raise ValueError('Unsupported banner game')
    pixels=[0]*1024
    def polygon(points,color):
        for y in range(32):
            for x in range(32):
                px,py=x+0.5,y+0.5;inside=False
                for i,(ax,ay) in enumerate(points):
                    bx,by=points[i-1]
                    if (ay>py)!=(by>py) and px<(bx-ax)*(py-ay)/(by-ay)+ax:inside=not inside
                if inside:pixels[y*32+x]=color
    def rect(x,y,w,h,c):polygon(((x,y),(x+w,y),(x+w,y+h),(x,y+h)),c)
    polygon(((7,0),(25,0),(32,7),(32,25),(25,32),(7,32),(0,25),(0,7)),1)
    polygon(((8,2),(24,2),(30,8),(30,24),(24,30),(8,30),(2,24),(2,8)),3 if game=='fusion' else 11)
    polygon(((8,3),(24,3),(29,8),(29,15),(3,15),(3,8)),2 if game=='fusion' else 1)
    if game=='fusion':
        # Fusion-blue shoulders frame an orange helmet and green visor.
        polygon(((8,21),(24,21),(30,27),(30,30),(2,30),(2,27)),1)
        polygon(((7,23),(25,23),(29,27),(29,29),(3,29),(3,27)),4)
        rect(4,26,5,2,5);rect(23,26,5,2,5)
        polygon(((10,4),(22,4),(27,10),(27,21),(22,27),(10,27),(5,21),(5,10)),1)
        polygon(((11,5),(21,5),(25,10),(25,21),(21,25),(11,25),(7,21),(7,10)),8)
        polygon(((11,6),(21,6),(24,10),(24,19),(20,23),(12,23),(8,19),(8,10)),9)
        polygon(((12,6),(20,6),(23,10),(9,10)),6)
        rect(12,6,7,2,7)
        polygon(((8,11),(24,11),(22,16),(18,18),(14,18),(10,16)),1)
        polygon(((10,12),(22,12),(20,15),(17,16),(15,16),(12,15)),12)
        rect(11,12,9,1,13)
        rect(14,18,4,5,10);rect(15,18,2,4,8)
        rect(8,18,3,3,6);rect(21,18,3,3,6)
    else:
        # Diagonal silver blade behind the three golden triangles.
        polygon(((25,3),(29,3),(29,7),(11,25),(7,21)),1)
        polygon(((25,4),(28,4),(28,7),(11,24),(8,21)),14)
        polygon(((26,4),(28,4),(28,6),(10,24),(9,22)),15)
        polygon(((4,19),(6,17),(15,26),(13,28)),8)
        polygon(((4,18),(6,17),(15,26),(14,27)),7)
        polygon(((5,24),(8,21),(11,24),(8,27)),1)
        polygon(((3,27),(7,23),(9,25),(5,29)),8)
        for x,y in ((16,5),(9,17),(23,17)):
            polygon(((x,y),(x+8,y+13),(x-8,y+13)),1)
            polygon(((x,y+2),(x+6,y+12),(x-6,y+12)),6)
            polygon(((x,y+2),(x,y+10),(x-6,y+12)),7)
            polygon(((x,y+10),(x+6,y+12),(x-6,y+12)),8)
    return pixels


def make_banner(game):
    banner=bytearray(0x840)
    struct.pack_into('<H',banner,0,1)
    pixels=icon_pixels(game)
    for y in range(32):
        for x in range(0,32,2):
            offset=0x20+((y//8)*4+x//8)*32+(y%8)*4+(x%8)//2
            banner[offset]=pixels[y*32+x]|pixels[y*32+x+1]<<4
    for i,(r,g,b) in enumerate(PALETTE):
        struct.pack_into('<H',banner,0x220+i*2,(r>>3)|((g>>3)<<5)|((b>>3)<<10))
    title=TITLES[game].encode('utf-16le')
    if len(title)>254:raise ValueError('DS banner title is too long')
    for language in range(6):banner[0x240+language*0x100:0x240+language*0x100+len(title)]=title
    struct.pack_into('<H',banner,2,crc16(banner[0x20:]))
    return banner


def set_menu_banner(data,game):
    """Replace only a standard template's banner, never code or filesystem data."""
    if len(data)<0x200:raise ValueError('Invalid NDS template')
    offset=struct.unpack_from('<I',data,0x68)[0]
    if offset<0x200 or offset+0x840>len(data) or data[offset:offset+2]!=b'\x01\x00':
        raise ValueError('Expected a standard DS template banner')
    for start,size in (
        (struct.unpack_from('<I',data,0x20)[0],struct.unpack_from('<I',data,0x2C)[0]),
        (struct.unpack_from('<I',data,0x30)[0],struct.unpack_from('<I',data,0x3C)[0]),
        struct.unpack_from('<II',data,0x40),struct.unpack_from('<II',data,0x48),
    ):
        if size and start<offset+0x840 and start+size>offset:
            raise ValueError('Template banner overlaps executable/filesystem data')
    data[offset:offset+0x840]=make_banner(game)
