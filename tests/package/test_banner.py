"""Check menu metadata and DS tile encoding without proprietary game inputs."""
from pathlib import Path
import struct
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools'))
from nds_banner import TITLES, PALETTE, crc16, icon_pixels, make_banner, set_menu_banner


class BannerTests(unittest.TestCase):
    def test_titles_crc_palette_and_tile_roundtrip(self):
        for game,title in TITLES.items():
            with self.subTest(game=game):
                b=make_banner(game)
                self.assertEqual(len(b),0x840)
                self.assertEqual(struct.unpack_from('<HH',b), (1,crc16(b[0x20:])))
                for language in range(6):
                    text=b[0x240+language*256:0x340+language*256].decode('utf-16le')
                    self.assertEqual(text.split('\0')[0],title)
                    self.assertTrue(text.endswith('\0'))
                decoded=[0]*1024
                for tile in range(16):
                    for byte in range(32):
                        packed=b[0x20+tile*32+byte]
                        start=(tile//4*8+byte//4)*32+tile%4*8+byte%4*2
                        decoded[start:start+2]=[packed&15,packed>>4]
                self.assertEqual(decoded,icon_pixels(game))
                self.assertGreater(len(set(decoded)),7)
                self.assertEqual(decoded[0],0)
                for i,(r,g,blue) in enumerate(PALETTE):
                    self.assertEqual(struct.unpack_from('<H',b,0x220+2*i)[0],r//8+g//8*32+blue//8*1024)
        self.assertNotEqual(make_banner('fusion')[0x20:0x220],make_banner('alttp')[0x20:0x220])

    def test_replacement_only_changes_banner(self):
        data=bytearray(0x2000)
        struct.pack_into('<I',data,0x68,0x800)
        struct.pack_into('<H',data,0x800,1)
        original=bytes(data)
        set_menu_banner(data,'fusion')
        self.assertEqual(data[:0x800],original[:0x800])
        self.assertEqual(data[0x1040:],original[0x1040:])
        self.assertEqual(data[0x800:0x1040],make_banner('fusion'))

    def test_reject_overlapping_or_missing_banner(self):
        data=bytearray(0x2000)
        with self.assertRaises(ValueError):set_menu_banner(data,'fusion')
        struct.pack_into('<I',data,0x68,0x800)
        struct.pack_into('<H',data,0x800,1)
        struct.pack_into('<4I',data,0x20,0x800,0,0,256)
        original=bytes(data)
        with self.assertRaisesRegex(ValueError,'overlaps'):set_menu_banner(data,'fusion')
        self.assertEqual(data,original)
