#!/usr/bin/env python3
"""Build a separate, clearly labelled melonDS GUI using the tested CPU patch."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import xml.etree.ElementTree as ET
from build_patched_emulator import ROOT, apply_exact_patch, output, run


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--jobs',type=int,default=8)
    args=p.parse_args()
    lock=json.loads((ROOT/'tools/melonds-lock.json').read_text())
    source=ROOT/'.tools/melonds-gui-source'
    build=ROOT/'.tools/melonds-gui-build'
    qt=ROOT/'.tools/qt-sdk/6.8.3/macos'
    deps=ROOT/'.tools/gui-deps'
    dest=ROOT/'artifacts/melonds-desktop'
    dest.mkdir(parents=True,exist_ok=True)
    if not source.exists():
        run('git','clone','--no-hardlinks',str(ROOT/'.tools/melonds-debug-build/_deps/melonds-src'),str(source))
    if output('git','-C',str(source),'rev-parse','HEAD')!=lock['dependencies']['melonds']:
        raise RuntimeError('Unexpected GUI engine revision')
    patch=ROOT/'patches/melonds-arm9-data-abort.patch'
    apply_exact_patch(source,patch)
    if not (qt/'bin/macdeployqt').exists() or not (deps/'lib/pkgconfig/faad2.pc').exists():
        raise RuntimeError('Install the project-local Qt SDK and FAAD dependency; see README desktop build notes')
    env=os.environ.copy()
    env['PKG_CONFIG_PATH']=':'.join([str(deps/'lib/pkgconfig'),*[f'/opt/homebrew/opt/{n}/lib/pkgconfig' for n in ('libarchive','enet','sdl2','zstd')]])
    command=['cmake','-S',str(source),'-B',str(build),
             f'-DCMAKE_PREFIX_PATH={qt};/opt/homebrew/opt/libarchive;{deps}',
             '-DCMAKE_BUILD_TYPE=Release','-DENABLE_JIT=OFF','-DENABLE_GDBSTUB=OFF',
             '-DENABLE_OGLRENDERER=ON','-DENABLE_LTO_RELEASE=OFF',
             '-DMELONDS_VERSION_SUFFIX= - Fusion patched','-DCMAKE_OSX_ARCHITECTURES=arm64']
    with (dest/'configure.log').open('w') as log:
        run(*command,env=env,stdout=log,stderr=subprocess.STDOUT)
    with (dest/'build.log').open('w') as log:
        run('cmake','--build',str(build),'-j',str(args.jobs),stdout=log,stderr=subprocess.STDOUT)
    app=dest/'melonDS Fusion.app'
    if app.exists():
        shutil.rmtree(app)  # generated app only; portable profile is a sibling
    shutil.copytree(build/'melonDS.app',app,symlinks=True)
    plist=app/'Contents/Info.plist'
    # This pinned upstream template uses <key> for archive extensions in an
    # array. Repair those value tags before parsing the otherwise valid plist.
    tree=ET.fromstring(plist.read_bytes())
    for element in tree.findall('.//array/key'):
        element.tag='string'
    info=plistlib.loads(ET.tostring(tree))
    info['CFBundleIdentifier']='local.gba-ds.melonds-fusion'
    info['CFBundleName']='melonDS Fusion'
    info['CFBundleDisplayName']='melonDS Fusion'
    plist.write_bytes(plistlib.dumps(info))
    with (dest/'deploy.log').open('w') as log:
        run(str(qt/'bin/macdeployqt'),str(app),'-always-overwrite','-no-strip',stdout=log,stderr=subprocess.STDOUT)
    run('codesign','--force','--deep','--sign','-',str(app))
    manifest=dict(engine_commit=lock['dependencies']['melonds'],jit=False,
                  cpu_patch_sha256=hashlib.sha256(patch.read_bytes()).hexdigest(),
                  executable_sha256=hashlib.sha256((app/'Contents/MacOS/melonDS').read_bytes()).hexdigest(),
                  qt='6.8.3',faad='2.11.4',app=str(app),build_command=command)
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(app)


if __name__=='__main__':
    main()
