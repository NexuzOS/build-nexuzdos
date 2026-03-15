import shutil
from pathlib import Path
from tools import config
from tools.run import run
import glob


app_dir = Path(__file__).resolve().parent

build_dirx = app_dir / "build"
src_dirx = build_dirx / "src"

def prepare():
    if config.BUILD.exists():
        shutil.rmtree(config.BUILD)

    config.BUILD.mkdir()
    # Kopiere den gesamten MS-DOS Quellcode
    shutil.copytree(config.SRC, build_dirx, dirs_exist_ok=True)

def build_kernel():
    dos_dir = src_dirx / "DOS"

    # Prüfe, ob das Verzeichnis existiert
    if not dos_dir.exists():
        raise RuntimeError(f"DOS source directory not found: {dos_dir}")

    # Alle ASM-Dateien sammeln
    asm_files = list(dos_dir.glob("*.ASM"))
    if not asm_files:
        raise RuntimeError(f"No ASM files found in {dos_dir}")

    # JWasm Optionen
    defines = []
    if config.FAT_TYPE.upper() == "FAT12":
        defines.append("-DFAT12")
    elif config.FAT_TYPE.upper() == "FAT16":
        defines.append("-DFAT16")
    else:
        raise RuntimeError(f"Unsupported FAT_TYPE: {config.FAT_TYPE}")

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
    image = config.BUILD / "dos.img"

    # Leeres 1.44MB Disk-Image erzeugen
    run([
        "dd",
        "if=/dev/zero",
        f"of={image}",
        "bs=512",
        "count=2880"
    ])

    # FAT-Dateisystem erstellen
    if config.FAT_TYPE.upper() == "FAT12":
        run(["mkfs.fat", "-F12", str(image)])
    else:
        run(["mkfs.fat", "-F16", str(image)])

    # Gebaute Kernel-Dateien kopieren
    dos_dir = config.KERNEL_SRC / "DOS"
    for sys_file in ["IO.SYS", "MSDOS.SYS"]:
        src_file = dos_dir / sys_file
        if src_file.exists():
            run(["mcopy", "-i", str(image), str(src_file) + "::"])
        else:
            print(f"Warning: {sys_file} not found, skipping copy.")

def main():
    print("Preparing build environment")
    prepare()

    print("Building DOS kernel")
    build_kernel()

    print("Creating disk image")
    create_image()

    print("Build finished")

if __name__ == "__main__":
    main()