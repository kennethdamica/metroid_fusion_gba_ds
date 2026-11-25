"""Exact input identities for game-specific extractors; no copyrighted assets."""
from dataclasses import dataclass
from pathlib import Path
from fusion_profile import FUSION_SHA1


@dataclass(frozen=True)
class GameProfile:
    key: str
    title: str
    rom_sha1: str
    magic: bytes
    nds_title: bytes
    template: str
    filename: str
    directory: str

    @property
    def data_root(self):
        return Path(self.directory) / self.rom_sha1

    @property
    def data_dir(self):
        return self.data_root / 'v1'


FUSION = GameProfile('fusion', 'Fusion', FUSION_SHA1, b'FUSPKG01', b'FUSION DS   ',
                     'FusionTemplate.nds', 'Fusion.nds', '_fusion')
ALTTP = GameProfile('alttp', 'Zelda ALttP', 'a272055abbbf6c26b0cd54c87395d01699589161',
                    b'ZELPKG01', b'ZELDA DS    ', 'ZeldaTemplate.nds', 'Zelda.nds', '_alttp')
