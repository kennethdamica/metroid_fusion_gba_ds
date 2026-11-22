"""Local package-format tests; proprietary inputs stay in ignored fixtures."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
import package_fusion
from package_fusion import build, inspect_package, crc16, DATA_DIR

class BuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runtime=ROOT/'artifacts/hardware-runtime'
        cls.rom=ROOT/'Metroid Fusion (USA).gba'
        cls.bios=ROOT/'gba_bios.zip'
        if not all(p.exists() for p in (cls.runtime/'manifest.json',cls.rom,cls.bios)):
            raise unittest.SkipTest('Build package runtime and supply local ROM/BIOS first')
        cls.work=tempfile.TemporaryDirectory()
        cls.directory=Path(cls.work.name)
        cls.package=cls.directory/'Fusion.nds'
        cls.report=build(cls.runtime,cls.rom,cls.bios,cls.package)
    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()
    def altered(self,name,transform):
        b=bytearray(self.package.read_bytes());transform(b)
        p=self.directory/name;p.write_bytes(b);return p
    def test_payloads_and_executable_segments(self):
        result=inspect_package(self.package)
        self.assertEqual(result['payloads']['rom.gba']['sha256'],hashlib.sha256(self.rom.read_bytes()).hexdigest())
        a=(self.runtime/'sdcard/FusionTemplate.nds').read_bytes();b=self.package.read_bytes()
        for header in (0x20,0x30):
            offset,entry,address,size=struct.unpack_from('<4I',a,header)
            self.assertEqual(a[header:header+16],b[header:header+16])
            self.assertEqual(a[offset:offset+size],b[offset:offset+size])
            self.assertLess(size,4*1024*1024)
    def test_reproducible_output(self):
        p=self.directory/'again.nds';build(self.runtime,self.rom,self.bios,p)
        self.assertEqual(p.read_bytes(),self.package.read_bytes())
    def test_existing_output_refused(self):
        before=self.package.read_bytes()
        with self.assertRaisesRegex(ValueError,'Output must be new'):
            build(self.runtime,self.rom,self.bios,self.package)
        self.assertEqual(before,self.package.read_bytes())
    def test_single_file_output(self):
        p=self.directory/'single.nds'
        build(self.runtime,self.rom,self.bios,p,write_manifest=False)
        self.assertEqual(p.read_bytes(),self.package.read_bytes())
        self.assertFalse(p.with_suffix('.manifest.json').exists())
    def test_failed_sync_leaves_no_partial_output(self):
        folder=self.directory/'failed-sync';folder.mkdir()
        p=folder/'Fusion.nds'
        with patch('package_fusion.os.fsync',side_effect=OSError('Disk full')):
            with self.assertRaisesRegex(OSError,'Disk full'):
                build(self.runtime,self.rom,self.bios,p)
        self.assertEqual(list(folder.iterdir()),[])
    def test_destination_created_during_build_is_not_overwritten(self):
        folder=self.directory/'race';folder.mkdir()
        p=folder/'Fusion.nds'
        original=package_fusion.publish_new
        def race(source,destination):
            if destination==p:
                p.write_bytes(b'created by another process')
            original(source,destination)
        with patch('package_fusion.publish_new',side_effect=race):
            with self.assertRaises(FileExistsError):
                build(self.runtime,self.rom,self.bios,p)
        self.assertEqual(p.read_bytes(),b'created by another process')
        self.assertEqual(list(folder.iterdir()),[p])
    def test_dangling_output_symlink_is_preserved(self):
        p=self.directory/'symlink.nds'
        try:p.symlink_to('missing-target')
        except (OSError,NotImplementedError):self.skipTest('Symlinks unavailable')
        # Wine 10's CreateSymbolicLinkW can report success without creating a
        # directory entry. Do not pretend that exercises a dangling symlink.
        if not os.path.lexists(p):
            self.skipTest('Symlink API returned without creating a link')
        with self.assertRaisesRegex(ValueError,'Output must be new'):
            build(self.runtime,self.rom,self.bios,p)
        self.assertTrue(p.is_symlink())
        self.assertFalse(p.exists())
    def test_runtime_hash_mismatch_is_rejected(self):
        runtime=self.directory/'bad-runtime';shutil.copytree(self.runtime,runtime)
        template=runtime/'sdcard/FusionTemplate.nds'
        template.write_bytes(template.read_bytes()+b'changed')
        p=self.directory/'bad-runtime.nds'
        with self.assertRaisesRegex(ValueError,'Runtime template'):
            build(runtime,self.rom,self.bios,p)
        self.assertFalse(p.exists())
    def test_wrong_game_refused_before_output(self):
        rom=self.directory/'wrong.gba';rom.write_bytes(b'not Fusion')
        p=self.directory/'wrong.nds'
        with self.assertRaisesRegex(ValueError,'verified US Fusion'):
            build(self.runtime,rom,self.bios,p)
        self.assertFalse(p.exists())
    def test_corrupt_payload_rejected(self):
        def change(b):
            fat=struct.unpack_from('<I',b,0x48)[0]
            offset=struct.unpack_from('<I',b,fat+8)[0]
            b[offset+100]^=1
        with self.assertRaisesRegex(ValueError,'Payload hash mismatch'):
            inspect_package(self.altered('corrupt.nds',change))
    def test_invalid_offsets_rejected(self):
        def change(b):
            fat=struct.unpack_from('<I',b,0x48)[0]
            struct.pack_into('<II',b,fat+8,0,len(b)+100)
        with self.assertRaisesRegex(ValueError,'payload bounds'):
            inspect_package(self.altered('bounds.nds',change))
    def test_header_and_truncation_rejected(self):
        def change(b):b[0]^=1
        with self.assertRaisesRegex(ValueError,'header checksum'):
            inspect_package(self.altered('header.nds',change))
        def truncate(b):del b[-1024:]
        with self.assertRaises(ValueError):inspect_package(self.altered('short.nds',truncate))

if __name__=='__main__':unittest.main()
