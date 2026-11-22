#!/bin/zsh
set -e
cd -- "${0:A:h}"
exec .venv/bin/python tools/play_fusion.py
