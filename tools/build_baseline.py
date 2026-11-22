#!/usr/bin/env python3
"""Build untouched GBARunner3 using the pinned upstream Linux toolchain on macOS."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
REVISION = "ecaa817815d9761745606592f04affe5ee9c3731"
LIBTWL = "e069645bed14a93e149e873e9273f04851e3a04e"
IMAGE = "devkitpro/devkitarm@sha256:a998edf6b06416b5c053edbcd879abfa22b1b88e9cd3f267f5c4ee9fec71a93a"


def output(*args):
    return subprocess.check_output(args, text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()
    source = ROOT / "vendor/GBARunner3"
    if not source.exists():
        source.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "https://github.com/Gericom/GBARunner3.git", str(source)], check=True)
        subprocess.run(["git", "-C", str(source), "checkout", "--detach", REVISION], check=True)
        subprocess.run(["git", "-C", str(source), "submodule", "update", "--init", "--recursive"], check=True)
    for path, revision in ((source, REVISION), (source / "code/libs/libtwl", LIBTWL)):
        if output("git", "-C", str(path), "rev-parse", "HEAD") != revision:
            raise RuntimeError(f"Unexpected revision in {path}; refusing to modify checkout")
        if output("git", "-C", str(path), "diff", "HEAD", "--"):
            raise RuntimeError(f"Tracked source changes in {path}; baseline must be unmodified")
    dest = ROOT / "artifacts/baseline"
    dest.mkdir(parents=True, exist_ok=True)
    command = ["docker", "run", "--rm", "--platform", "linux/amd64", "--network", "none",
               "--mount", f"type=bind,source={source},target=/src", "--workdir", "/src", IMAGE]
    with (dest / "build.log").open("w") as log:
        if args.clean:
            subprocess.run(command + ["make", "-C", "code", "clean"], stdout=log, stderr=subprocess.STDOUT, check=True)
        # Follow upstream's serial invocation: its recursive Makefiles share outputs.
        result = subprocess.run(command + ["make", "-C", "code"], stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        print((dest / "build.log").read_text()[-6000:], file=sys.stderr)
        return result.returncode
    package = dest / "sdcard"
    (package / "_gba").mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / "code/bootstrap/GBARunner3.nds", package / "GBARunner3.nds")
    shutil.copytree(source / "configs", package / "_gba/configs", dirs_exist_ok=True)
    debug = dest / "debug"
    debug.mkdir(exist_ok=True)
    for path in source.glob("code/**/*.elf"):
        shutil.copy2(path, debug / (str(path.relative_to(source)).replace("/", "_")))
    for path in source.glob("code/**/*.map"):
        shutil.copy2(path, debug / (str(path.relative_to(source)).replace("/", "_")))
    manifest = {"gbarunner3_commit": REVISION, "libtwl_commit": LIBTWL,
                "image": IMAGE, "platform": "linux/amd64", "source_modified": False,
                "rom_sha256": hashlib.sha256((package / "GBARunner3.nds").read_bytes()).hexdigest(),
                "rom_bytes": (package / "GBARunner3.nds").stat().st_size}
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))
    print(f"Built {package / 'GBARunner3.nds'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
