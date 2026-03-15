from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SRC = ROOT / "sources/msdos/v4.0"
BUILD = ROOT / "build"

KERNEL_SRC = BUILD / "src"

FAT_TYPE = "FAT12"   # FAT12 oder FAT16