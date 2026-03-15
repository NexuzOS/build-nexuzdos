import os
import sys
import subprocess
import shutil
import re, glob
import shlex
import logging
import pathlib 


from pathlib import Path
from subprocess import Popen, STDOUT, PIPE 
from shutil import * 
from tools.run import run






ROOT = Path(__file__).resolve().parent
SRC = ROOT / "sources" / "msdos" / "v4.0"


BUILD = ROOT / "build"
KERNEL_SRC = BUILD / "src"

FAT_TYPE = "FAT12"   # FAT12 oder FAT16


if BUILD.exists():
    shutil.rmtree(BUILD)
    
BUILD.mkdir()
shutil.copytree(SRC, BUILD, dirs_exist_ok=True)

MSDOS_SRC = BUILD / "src"


dos_dir = MSDOS_SRC / "DOS"


def build():
    # Prüfe, ob das Verzeichnis existiert
    if not dos_dir.exists():
        raise RuntimeError(f"DOS source directory not found: {dos_dir}")
    # Alle ASM-Dateien sammeln
    asm_files = list(dos_dir.glob("*.ASM"))
    if not asm_files:
        raise RuntimeError(f"No ASM files found in {dos_dir}")
    # JWasm Optionen
    defines = []
    if FAT_TYPE.upper() == "FAT12":
        defines.append("-DFAT12")
    elif FAT_TYPE.upper() == "FAT16":
        defines.append("-DFAT16")
    else:
        raise RuntimeError(f"Unsupported FAT_TYPE: {FAT_TYPE}")
    # Alle ASM-Dateien kompilieren
    for asm_file in asm_files:
        run([
            "jwasm",
            "-Zm",
            *defines,
            asm_file.name
        ], cwd=dos_dir)
    # Linker-Skript ausführen
    lnk_file = dos_dir / "MSDOS.LNK"
    if not lnk_file.exists():
        raise RuntimeError(f"Linker script not found: {lnk_file}")
    run([
        "jwlink",
        lnk_file.name
    ], cwd=dos_dir)

def create_image():
    image = BUILD / "dos.img"

    # Leeres 1.44MB Disk-Image erzeugen
    run([
        "dd",
        "if=/dev/zero",
        f"of={image}",
        "bs=512",
        "count=2880"
    ])

    # FAT-Dateisystem erstellen
    if FAT_TYPE.upper() == "FAT12":
        run(["mkfs.fat", "-F12", str(image)])
    else:
        run(["mkfs.fat", "-F16", str(image)])

    # Gebaute Kernel-Dateien kopieren
    dos_dir = KERNEL_SRC / "DOS"
    for sys_file in ["IO.SYS", "MSDOS.SYS"]:
        src_file = dos_dir / sys_file
        if src_file.exists():
            run(["mcopy", "-i", str(image), str(src_file) + "::"])
        else:
            print(f"Warning: {sys_file} not found, skipping copy.")

def main():
    build()

    print("Creating disk image")
    create_image()

    print("Build finished")

if __name__ == "__main__":
    main()