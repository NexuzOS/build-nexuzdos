#!/usr/bin/env python3

import os
import shutil
import subprocess
import re
from pathlib import Path

from tools.run import run


# ------------------------------------------------------------
# PATHS
# ------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent

MSDOS_SOURCE = SCRIPT_DIR / "sources" / "msdos" / "v4.0"

BUILD_DIR = SCRIPT_DIR / "build"
BUILD_SRC = BUILD_DIR / "src"

CONFIGS_DIR = SCRIPT_DIR / "configs"
DOSBOX_CONFIG = CONFIGS_DIR / "dosbox.conf"

DEST_DIR = Path("/mnt/ndos")

FDISO = Path(
"/home/hexzhen3x7/Development/Projekte/NexuzDOS-Development/Releases/FreeDOS/FDT2603/FDT2603-LiveCD/T2603LIVE.iso"
)

# ------------------------------------------------------------
# UTIL
# ------------------------------------------------------------

def check_sources():
    if not MSDOS_SOURCE.exists():
        raise RuntimeError(f"MSDOS source missing: {MSDOS_SOURCE}")

    if not FDISO.exists():
        raise RuntimeError(f"FreeDOS ISO missing: {FDISO}")


# ------------------------------------------------------------
# BUILD PREP
# ------------------------------------------------------------

def prepare_build_dir():

    print(f"[BUILD] preparing build dir: {BUILD_DIR}")

    BUILD_SRC.mkdir(parents=True, exist_ok=True)

    print(f"[BUILD] copying sources")

    shutil.copytree(
        MSDOS_SOURCE,
        BUILD_SRC,
        dirs_exist_ok=True
    )

    # backup original SETENV
    setenv = BUILD_SRC / "SETENV.BAT"
    if setenv.exists():
        shutil.copy2(setenv, BUILD_SRC / "SETENV.BAK")

    # copy custom SETENV
    custom_setenv = SCRIPT_DIR / "SETENV.BAT"
    if custom_setenv.exists():
        shutil.copy2(custom_setenv, setenv)

    print("[BUILD] sources ready")


# ------------------------------------------------------------
# PATCH SOURCES
# ------------------------------------------------------------

def patch_msdos_source():

    print("[PATCH] running patches")

    os.chdir(BUILD_SRC)

    # -------------------------
    # PATCH SETENV PATHS
    # -------------------------

    setenv = BUILD_SRC / "SETENV.BAT"

    if setenv.exists():

        text = setenv.read_text(
            encoding="ascii",
            errors="ignore"
        )

        text = text.replace("tools\\lib", "tools\\bld\\lib")
        text = text.replace("tools\\inc", "tools\\bld\\inc")

        setenv.write_text(text, encoding="ascii")

        print("[PATCH] SETENV fixed")

    # -------------------------
    # FIX UTF8 BROKEN BYTES
    # -------------------------

    special_targets = [
        "MAPPER/GETMSG.ASM",
        "SELECT/SELECT2.ASM",
        "SELECT/USA.INF"
    ]

    pattern = re.compile(rb'\xEF\xBF\xBD|\xC4\xBF|\xC4\xB4')

    for target in special_targets:

        path = BUILD_SRC / target

        if path.exists():

            data = path.read_bytes()

            fixed = pattern.sub(b"#", data)

            path.write_bytes(fixed)

            print(f"[PATCH] fixed encoding: {target}")

    # -------------------------
    # CRLF NORMALIZATION
    # -------------------------

    extensions = (".BAT", ".ASM", ".SKL")
    exact = ("ZERO.DAT", "LOCSCR")

    for file in BUILD_SRC.rglob("*"):

        name = file.name.upper()

        if name.endswith(extensions) or name in exact:

            data = file.read_bytes()

            normalized = (
                data
                .replace(b"\r\n", b"\n")
                .replace(b"\n", b"\r\n")
            )

            if data != normalized:
                file.write_bytes(normalized)

    print("[PATCH] CRLF normalization done")


# ------------------------------------------------------------
# AUTOEXEC
# ------------------------------------------------------------

def create_autoexec():

    print("[BUILD] generating AUTOEXEC.BAT")

    autoexec = BUILD_SRC / "AUTOEXEC.BAT"

    autoexec.write_text(
"""@echo off
CALL RUNME.BAT
CALL SETENV.BAT
NMAKE
""",
        encoding="ascii"
    )


# ------------------------------------------------------------
# QEMU
# ------------------------------------------------------------

def create_qemu_image(name="ndos", size="2G"):

    img = SCRIPT_DIR / f"{name}.qcow2"

    print(f"[QEMU] creating image: {img}")

    run([
        "qemu-img",
        "create",
        "-f",
        "qcow2",
        str(img),
        size
    ])

    return img


def start_freedos_install(ndos_img, target_img):

    print("[QEMU] starting FreeDOS installer")

    run([

        "qemu-system-i386",

        "-m", "4096",

        "-cpu", "pentium",

        "-cdrom", str(FDISO),

        "-hda", str(target_img),

        "-hdb", str(ndos_img),

        "-drive",
        f"file=fat:rw:{BUILD_DIR},format=raw",

        "-boot", "d",

        "-vga", "std"

    ])


# ------------------------------------------------------------
# DOSBOX
# ------------------------------------------------------------

def start_dosbox():

    print("[DOSBOX] starting build")

    run([
        "dosbox",
        "-conf",
        str(DOSBOX_CONFIG)
    ])


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def main():

    check_sources()

    prepare_build_dir()

    patch_msdos_source()

    create_autoexec()

    ndos_img = create_qemu_image("ndos", "2G")
    target_img = create_qemu_image("ndos_custom", "4G")

    start_freedos_install(
        ndos_img,
        target_img
    )


if __name__ == "__main__":
    main()