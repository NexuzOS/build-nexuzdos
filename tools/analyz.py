#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, os, argparse, subprocess
from pathlib import Path
from rich.table import Table
from rich.console import Console
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Tree, Static
from textual.widgets import scroll_view
from textual.containers import Horizontal

console = Console()

# ---------- Kernel Analysis Functions ----------
def file_size(path: Path) -> int:
    return path.stat().st_size

def detect_bitness(path: Path) -> str:
    try:
        out = subprocess.check_output(f"ndisasm -b16 {path}", shell=True, stderr=subprocess.DEVNULL)
        if b"mov" in out or b"jmp" in out:
            return "16-bit real mode"
        return "unknown"
    except:
        return "unknown"

def detect_fat(path: Path) -> str:
    try:
        strings = subprocess.check_output(f"strings {path}", shell=True).decode(errors="ignore")
        fats = [f for f in ["FAT12","FAT16","FAT32"] if f in strings]
        return ", ".join(fats) if fats else "unknown"
    except:
        return "unknown"

def detect_entry(path: Path) -> str:
    try:
        out = subprocess.check_output(f"xxd -l 3 {path}", shell=True).decode(errors="ignore")
        parts = out.strip().split()
        return "".join(parts[1:4]) if len(parts) >= 4 else "unknown"
    except:
        return "unknown"

def detect_boot_sig(path: Path) -> str:
    try:
        sig = subprocess.check_output(f"xxd -p -s 510 -l 2 {path}", shell=True).decode().strip()
        return "boot-sector" if sig.lower() == "55aa" else "none"
    except:
        return "none"

def extract_kernel_strings(path: Path):
    try:
        out = subprocess.check_output(f"strings {path}", shell=True).decode(errors="ignore")
        return [line for line in out.splitlines() if any(w in line.lower() for w in ["cluster","disk","memory","error","sector"])][:10]
    except:
        return []

def detect_oem(path: Path):
    try:
        out = subprocess.check_output(f"strings {path}", shell=True).decode(errors="ignore")
        oem = [line.strip() for line in out.splitlines() if any(x in line for x in ["MSDOS","MICROSOFT","IBM"])]
        return ", ".join(oem[:2]) if oem else "unknown"
    except:
        return "unknown"

def analyze_file(path: Path):
    return {
        "name": path.name,
        "size": file_size(path),
        "bitness": detect_bitness(path),
        "entry": detect_entry(path),
        "boot": detect_boot_sig(path),
        "fat": detect_fat(path),
        "oem": detect_oem(path),
        "kernel_strings": extract_kernel_strings(path)
    }

# ---------- Textual App ----------
class MSKAnalyzerApp(App):

    CSS_PATH = None

    def __init__(self, root_path: Path, log_file: Path):
        super().__init__()
        self.root_path = root_path
        self.log_file = log_file
        self.analysis_results = {}

    def compose(self):
        yield Header(show_clock=True)
        with Horizontal():
            self.tree_panel = Tree("Source Tree", id="tree")
            yield self.tree_panel
            self.info_panel = scroll_view.ScrollView(Static("Analysis Info", id="info"), id="info_scroll")
            yield self.info_panel
        yield Footer()

    def on_mount(self):
        self.build_tree()
        self.run_analysis()

    # Neuer Tree-Builder für aktuelle Textual Version
    def build_tree(self):
        root = self.tree_panel.root
        def add_nodes(node, path: Path):
            for p in sorted(path.iterdir()):
                if p.is_dir():
                    child = node.add(p.name, expand=True)
                    add_nodes(child, p)
                else:
                    # Neon highlight für IO.SYS und MSDOS.SYS
                    label = p.name
                    if p.name.upper() in ["IO.SYS","MSDOS.SYS"]:
                        label = f"[bold magenta]{p.name}[/bold magenta]"
                    node.add(label)
        add_nodes(root, self.root_path)
        root.expand()

    def run_analysis(self):
        for fname in ["IO.SYS","MSDOS.SYS"]:
            fpath = self.root_path / fname
            if fpath.exists():
                res = analyze_file(fpath)
                self.analysis_results[fname] = res
        self.render_analysis()

    def render_analysis(self):
        table = Table(title="MS-DOS Kernel Analysis", style="bold cyan")
        table.add_column("File", style="bold magenta")
        table.add_column("Size")
        table.add_column("Bitness")
        table.add_column("Entry")
        table.add_column("Boot")
        table.add_column("FAT")
        table.add_column("OEM")
        table.add_column("Kernel Strings", style="yellow")

        for fname, res in self.analysis_results.items():
            ks = "\n".join(res["kernel_strings"])
            table.add_row(res["name"], str(res["size"]), res["bitness"], res["entry"],
                          res["boot"], res["fat"], res["oem"], ks)

        self.info_panel.update(table)

        # Log export
        with open(self.log_file,"w") as f:
            from rich.console import Console
            temp_console = Console(file=f, record=True)
            temp_console.print(table)

# ---------- Main ----------
def main():
    parser = argparse.ArgumentParser(description="MS-DOS Kernel Analyzer (Textual TUI)")
    parser.add_argument("-i","--input", type=str, required=True, help="Path to MS-DOS Source directory")
    parser.add_argument("-log","--logfile", type=str, default="output.log", help="Log file path")
    args = parser.parse_args()

    root_path = Path(args.input).resolve()
    log_file = Path(args.logfile).resolve()

    app = MSKAnalyzerApp(root_path, log_file)
    app.run()

if __name__ == "__main__":
    main()