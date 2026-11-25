#!/usr/bin/env python3
"""Unified standalone entry point; fusion_pack remains an import compatibility shim."""
from fusion_pack import main

if __name__ == '__main__':
    raise SystemExit(main())
