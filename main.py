#!/usr/bin/env python3
import os
import sys
import shutil
import pathlib
import re, glob
import subprocess
import time
import tempfile
import tqdm
import zipfile
import shlex
import argparse



from pathlib import Path
from subprocess import Popen, PIPE, STDOUT




from tools.run import run




SCRIPT_DIR = Path(__file__).parent.resolve()
MSDOS_SOURCE = SCRIPT_DIR / "sources" / "msdos" / "v4.0"
BUILD_DIR = SCRIPT_DIR / "build"
BUILD_SRC = BUILD_DIR / Path("src")

DEST_DIR = Path("/mnt/ndos")


CONFIGS_DIR = SCRIPT_DIR / "configs"
DOSBOX_CONFIG = CONFIGS_DIR / "dosbox-0.74-3.conf"


FDISO = "/home/hexzhen3x7/Development/Projekte/NexuzDOS-Development/Releases/FreeDOS/FDT2603/FDT2603-LiveCD/T2603LIVE.iso"






def prepare_build_dir():
    print(f"Erstelle Build-Verzeichnis: {BUILD_DIR}")
    BUILD_DIR.mkdir(exist_ok=True)
    # BUILD_SRC.mkdir(exist_ok=True)
    
    print(f"Kopiere MS-DOS Quellen von {MSDOS_SOURCE} nach {BUILD_DIR}")
    for item in MSDOS_SOURCE.iterdir():
        dest = BUILD_DIR / item.name
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
    print("Console > Running PATCH... .. .")
    
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
    
    print("Console > Your DOS-Buildenviroment hat successfully patched your contents !!! ... .. . ")
    
                        
                    
                    
def create_scripts():
    print(f"Console > Generating: AUTOEXEC.BAT ")
    dosbox_commands = f"""
        D:
        CD src
        CALL RUNME.BAT
        CALL SETENV.BAT
        NMAKE
        """
        
    autoexec_file = BUILD_SRC / "AUTOEXEC.BAT"
    with open(autoexec_file, "w") as f:
        f.write(dosbox_commands)
    
    return autoexec_file
        
        

def copy_code(src, dest):
    print(f"Console > Copying: {src} \n TO: \n {dest}")
    for item in src.rglob("*"):
        target = dest / item.relative_to(src)

        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            print(f"copy {item} -> {target}")
            shutil.copy2(item, target)
             
    print(f"Console > FINISHED: Successfully Copied: {src} to {dest}")





def start_dosbox_sudo_live(conf_path):
    """
    Startet DOSBox via sudo mit angegebener Config-Datei
    und gibt die Ausgabe live in der Konsole aus.
    """
    
    create_scripts()
    
    # Kommando
    cmd = ["sudo", "dosbox", "-conf", str(conf_path), "-noconsole"]

    print(f"Starte DOSBox: {' '.join(shlex.quote(x) for x in cmd)}")

    # Popen für live Ausgabe
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) as proc:
        for line in proc.stdout:
            print(line, end="")  # Live-Ausgabe
        proc.wait()

    if proc.returncode != 0:
        raise RuntimeError(f"DOSBox exit code: {proc.returncode}")
    
    

    
def create_qemu_image(name="ndos", fmt="qcow2", size="2G"):
    print(f"Console > Creating Image: {name} , as: {fmt} with: {size} !!! ... \n")
    img = f"{name}.{fmt}"

    cmd = [
        "qemu-img",
        "create",
        "-f",
        fmt,
        img,
        size
    ]

    run(cmd)

    return img



def create_qemu_image2(name="ndos", fmt="qcow2", size="2G", directory=BUILD_DIR):
    """
    Erstellt ein QCOW2-Image im angegebenen Verzeichnis und gibt den Path zurück.
    """
    
    directory.mkdir(parents=True, exist_ok=True)
    img_path = directory / f"{name}.{fmt}"
    print(f"Console > Creating Image: {img_path} , as: {fmt} with: {size} !!! ... \n")
    cmd = [
        "qemu-img",
        "create",
        "-f", fmt,
        str(img_path),
        size
    ]
    run(cmd)
    return img_path  # Path-Objekt zurückgeben1


def start_qemu(build_dir, hdd_image):
    print(f"Console > Starting: Qemu -> HDD: {hdd_image} , in {build_dir}")
    cmd = [
        "qemu-system-i386",
        "-m", "4096",

        "-hda", hdd_image,

        "-drive",
        f"file=fat:rw:{build_dir},format=raw",

        "-boot", "c"
    ]

    run(cmd)
    
    
    
    
def start_freedos_install(
    freedos_iso,
    ndos_img,
    target_img,
    build_dir
):


    print("Starte FreeDOS Installer... .. .  ")
    print(f" qemu -> {freedos_iso} , hda: {target_img} , data_disk: {ndos_img}  at: {build_dir}")
    cmd = [

        "qemu-system-i386",

        "-m", "4096",

        "-cdrom", freedos_iso,

        "-hda", target_img,        # Ziel HDD
        "-hdb", ndos_img,          # Daten HDD

        "-drive",
        f"file=fat:rw:{build_dir},format=raw",

        "-boot", "d"
    ]

    run(cmd)


def unmount_qcow2(mountpoint, nbd="/dev/nbd0"):
    print(f"Unmounte: {mountpoint}, {nbd}")
    run(["sudo", "umount", mountpoint])
    run(["sudo", "qemu-nbd", "--disconnect", nbd])
    
    




def mount_qcow2(image, mountpoint, nbd="/dev/nbd0"):
    mountpoint = Path(mountpoint)
    mountpoint.mkdir(parents=True, exist_ok=True)

    image = str(image)  # PosixPath -> str, wichtig für run()

    print("Checke NBD-Modul...")
    run(["sudo", "modprobe", "nbd", "max_part=16"])

    # Vorherige Verbindung trennen, falls noch aktiv
    subprocess.run(["sudo", "qemu-nbd", "--disconnect", nbd],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Image mit NBD verbinden
    print(f"Verbinde {image} mit {nbd} ...")
    run(["sudo", "qemu-nbd", "--connect", nbd, image])

    # Kernel Partitionstabelle neu laden
    run(["sudo", "partprobe", nbd])

    partition = f"{nbd}p1"

    # Prüfen, ob Partition existiert
    if not Path(partition).exists():
        print("Partition nicht gefunden, erstelle primäre Partition & FAT16...")

        # fdisk Script als String für Shell
        fdisk_script = "n\np\n1\n\n\nt\n6\na\n1\nw\n"
        subprocess.run(f"echo -e '{fdisk_script}' | sudo fdisk {nbd}",
                       shell=True, check=True)

        # FAT16 formatieren
        subprocess.run(["sudo", "mkfs.vfat", "-F16", f"{nbd}p1"], check=True)

        # Partitionstabelle erneut laden
        run(["sudo", "partprobe", nbd])

    # Mounten
    run(["sudo", "mount", partition, str(mountpoint)])
    print(f"Image {image} erfolgreich auf {mountpoint} gemountet.")

    return partition

def old():
    prepare_build_dir()
    patch_msdos_source()
        
    copy_code(BUILD_DIR, DEST_DIR)

    # start_dosbox_sudo_live(DOSBOX_CONFIG)
    

    ndos_img = create_qemu_image("ndos", "qcow2", "2G")

    target_img = create_qemu_image("ndos_custom", "qcow2", "4G")
    
    
    
    mount_ndos = "/mnt/ndos_hdd"
    mount_target = "/mnt/ndos_custom_image"
    
    mount_qcow2(ndos_img, mount_ndos, "/dev/nbd0")
    # mount_qcow2(target_img, mount_target, "/dev/nbd1")

    copy_code(BUILD_DIR, mount_ndos)
    
    # flush
    os.sync()


    # unmount
    unmount_qcow2(mount_ndos, "/dev/nbd0")
    # unmount_qcow2(mount_target, "/dev/nbd1")
    
    start_freedos_install(
        FDISO,
        ndos_img,
        target_img,
        BUILD_DIR
    )
    
    
    print("\nFertig! Build wurde in DOSBox ausgeführt.")
    
    
if __name__ == "__main__":
    prepare_build_dir()
    patch_msdos_source()
        
    copy_code(BUILD_DIR, DEST_DIR)

    # --- QCOW2 Images im Build-Verzeichnis erstellen ---
    # ndos_img = BUILD_DIR / "ndos.qcow2"
    # target_img = BUILD_DIR / "ndos_custom.qcow2"

    # create_qemu_image(name=ndos_img.stem, fmt="qcow2", size="2G")
    # create_qemu_image(name=target_img.stem, fmt="qcow2", size="4G")

    ndos_img = create_qemu_image("ndos", "qcow2", "2G", BUILD_DIR)
    target_img = create_qemu_image("ndos_custom", "qcow2", "4G", BUILD_DIR)



    # --- Mountpoints im Build-Verzeichnis ---
    mount_ndos = BUILD_DIR / "mnt_ndos"
    mount_target = BUILD_DIR / "mnt_ndos_custom"

    # --- Mount QCOW2 ---
    mount_qcow2(ndos_img, mount_ndos, "/dev/nbd0")
    # mount_qcow2(target_img, mount_target, "/dev/nbd1")  # falls benötigt

    # --- Build-Code in das gemountete Image kopieren ---
    copy_code(BUILD_DIR, mount_ndos)

    # --- flush ---
    os.sync()

    # --- Unmount ---
    unmount_qcow2(mount_ndos, "/dev/nbd0")
    # unmount_qcow2(mount_target, "/dev/nbd1")

    # --- FreeDOS Installer starten ---
    start_freedos_install(
        FDISO,
        ndos_img,
        target_img,
        BUILD_DIR
    )

    print("\nFertig! Build wurde in DOSBox ausgeführt.")
    
    