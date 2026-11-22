#!/usr/bin/env python3
"""Build original DS and GBA diagnostics with the same pinned toolchain."""
from pathlib import Path
import subprocess
from build_baseline import IMAGE, ROOT

for name in ('nds_probe', 'gba_probe', 'nds_mpu_probe'):
    source = ROOT / 'tests' / name
    command = ['docker', 'run', '--rm', '--platform', 'linux/amd64', '--network', 'none',
               '--mount', f'type=bind,source={source},target=/probe', '--workdir', '/probe', IMAGE]
    subprocess.run(command + ['make', 'clean'], check=True)
    subprocess.run(command + ['make'], check=True)
    print(f'Built {source}')
