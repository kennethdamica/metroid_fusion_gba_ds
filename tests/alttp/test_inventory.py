"""Original inventory assets, variants and renderer memory boundaries."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
ROM = ROOT / 'Legend of Zelda, The - A Link to the Past & Four Swords (USA).gba'

class InventoryRendererTests(unittest.TestCase):
    def test_original_assets_variants_and_memory_bounds(self):
        compiler = shutil.which('clang++') or shutil.which('g++')
        if not compiler or not ROM.exists():
            self.skipTest('Requires a C++ compiler and the local verified Zelda ROM')
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / 'inventory'
            subprocess.run([compiler, '-std=c++17', '-fsanitize=address,undefined',
                            str(ROOT / 'tests/alttp/inventory_renderer.cpp'), '-o', str(executable)],
                           check=True, capture_output=True)
            run = subprocess.run([str(executable), str(ROM)], check=True, capture_output=True, text=True)
            self.assertGreater(json.loads(run.stdout)['item_variants'], 50)
