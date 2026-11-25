"""Decode original ROM maps through the shipping C++ renderer in bounded memory."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
ROM=ROOT/'Legend of Zelda, The - A Link to the Past & Four Swords (USA).gba'
sys.path.insert(0,str(ROOT/'tools'))
from alttp_world_checks import world_colors


class MapRendererTests(unittest.TestCase):
    def test_world_pixels_all_dungeon_floors_and_memory_bounds(self):
        compiler=shutil.which('clang++') or shutil.which('g++')
        if not compiler or not ROM.exists():
            self.skipTest('Requires a C++ compiler and the local verified Zelda ROM')
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)
            subprocess.run([compiler,'-std=c++17','-fsanitize=address,undefined',str(ROOT/'tests/alttp/map_renderer.cpp'),'-o',str(out/'renderer')],check=True,capture_output=True)
            run=subprocess.run([str(out/'renderer'),str(ROM),str(out)],check=True,capture_output=True,text=True)
            report=json.loads(run.stdout)
            self.assertEqual(report['floors'],59)
            self.assertEqual(report['room_cells'],186)
            self.assertLess(report['cache_bytes'],32768)
            rom=ROM.read_bytes()
            for world in range(2):
                actual=(out/f'world{world}.raw').read_bytes()
                for y in range(128):
                    for x in range(128):
                        sx,sy=128+x*2,128+y*2
                        tile=rom[0x3BFEF8+world*4096+sy//8*64+sx//8]
                        expected=rom[0x28A7E0+tile*64+sy%8*8+sx%8]
                        self.assertEqual(actual[(y//8*16+x//8)*64+y%8*8+x%8],expected)
                for stage in range(9):
                    actual=(out/f'markers{world}s{stage}.raw').read_bytes()
                    shared=bytearray(32768);shared[0x3890]=stage
                    colors=world_colors(rom,bytes(0x40000),shared,world)
                    for y in range(128):
                        for x in range(128):
                            index=actual[(y//8*16+x//8)*64+y%8*8+x%8]
                            if index<128:
                                at=0x3BFA58+world*256+index*2
                            else:
                                bank=(1,2,4)[(index-128)//16]
                                at=0x3B566C+bank*32+(index%16)*2
                            color=int.from_bytes(rom[at:at+2],'little') if index else 3|(5<<5)|(4<<10)
                            self.assertEqual(color,colors[y*128+x],(world,stage,x,y))
