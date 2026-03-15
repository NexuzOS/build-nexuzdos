#!/usr/bin/env python3
import os
import shutil
import pathlib
import re
import subprocess

SCRIPT_DIR = pathlib.Path(__file__).parent.resolve()
MSDOS_SOURCE = SCRIPT_DIR / "sources" / "msdos" / "v4.0"
BUILD_DIR = SCRIPT_DIR / "build"
BUILD_SRC = BUILD_DIR / "src"

def prepare_build_dir():
    print(f"Erstelle Build-Verzeichnis: {BUILD_DIR}")
    BUILD_DIR.mkdir(exist_ok=True)
    BUILD_SRC.mkdir(exist_ok=True)
    
    print(f"Kopiere MS-DOS Quellen von {MSDOS_SOURCE} nach {BUILD_SRC}")
    for item in MSDOS_SOURCE.iterdir():
        dest = BUILD_SRC / item.name
        if item.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(item, dest)
        else:
            shutil.copy2(item, dest)
    
    setenv_src = SCRIPT_DIR / "SETENV.BAT"
    setenv_dst = BUILD_SRC / "SETENV.BAT"
    setenv_backup = BUILD_SRC / "SETENV.BAK"

    if setenv_dst.exists():
        shutil.copy2(setenv_dst, setenv_backup)
        print("SETENV.BAT gesichert als SETENV.BAK")
    
    if setenv_src.exists():
        shutil.copy2(setenv_src, setenv_dst)
        print("SETENV.BAT ins Build-Verzeichnis kopiert")

def patch_msdos_source():
    os.chdir(BUILD_SRC)
    if os.path.exists("SETENV.BAT"):
        print("Patche SETENV.BAT Pfade...")
        with open("SETENV.BAT", "r", encoding="ascii", errors="ignore") as f:
            content = f.read()
        content = content.replace("tools\\lib", "tools\\bld\\lib")
        content = content.replace("tools\\inc", "tools\\bld\\inc")
        with open("SETENV.BAT", "w", encoding="ascii") as f:
            f.write(content)

    special_targets = ["MAPPER/GETMSG.ASM", "SELECT/SELECT2.ASM", "SELECT/USA.INF"]
    hex_pattern = re.compile(rb'\xEF\xBF\xBD|\xC4\xBF|\xC4\xB4')
    for target in special_targets:
        target_path = pathlib.Path(target.replace("/", os.sep))
        if target_path.exists():
            print(f"Fixe Sonderzeichen in: {target_path}")
            with open(target_path, "rb") as f:
                data = f.read()
            new_data = hex_pattern.sub(b'#', data)
            with open(target_path, "wb") as f:
                f.write(new_data)

    extensions = ('.BAT', '.ASM', '.SKL')
    exact_files = ('ZERO.DAT', 'LOCSCR')
    print("Starte rekursive CRLF-Konvertierung...")
    for root, _, files in os.walk("."):
        for file in files:
            upper_file = file.upper()
            if upper_file.endswith(extensions) or upper_file in exact_files:
                full_path = pathlib.Path(root) / file
                with open(full_path, "rb") as f:
                    raw_data = f.read()
                normalized_data = raw_data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
                if normalized_data != raw_data:
                    with open(full_path, "wb") as f:
                        f.write(normalized_data)
                    print(f"  [CRLF Fix] {full_path}")