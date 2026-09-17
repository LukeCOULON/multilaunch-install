#!/usr/bin/env python3
"""Install MultiLaunch in the user's home directory."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import stat
import sys
from pathlib import Path


APP_NAME = "MultiLaunch"
SOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
DEFAULT_INSTALL_DIR = Path.home() / APP_NAME
DATA_DIR = Path.home() / "Documents" / APP_NAME
DATA_FILE = DATA_DIR / "data.json"
BACKUP_DIR = DATA_DIR / "backups"
BIN_DIR = Path.home() / ".local" / "bin"
APPLICATIONS_DIR = Path.home() / ".local" / "share" / "applications"
LAUNCHER_PATH = BIN_DIR / "multilaunch"
DESKTOP_FILE = APPLICATIONS_DIR / "multilaunch.desktop"
FILES_TO_INSTALL = ("app_entry.py", "launcher.py", "gui.py", "gamedetector.py", "version.json", "update.json", "old_version.json")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def make_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def backup_raw_data() -> Path | None:
    """Keep an untouched copy of data.json before installation changes anything."""
    if not DATA_FILE.is_file():
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    backup_path = BACKUP_DIR / f"data-{timestamp}.json"
    shutil.copy2(DATA_FILE, backup_path)
    return backup_path


def install(install_dir: Path, dry_run: bool = False) -> None:
    missing = [name for name in FILES_TO_INSTALL if not (SOURCE_DIR / name).is_file()]
    if missing:
        raise RuntimeError(f"Fichiers du programme manquants: {', '.join(missing)}")

    if os.name == "nt":
        raise RuntimeError("MultiLaunch est disponible uniquement sous Linux")
    print(f"Installation Linux de {APP_NAME} dans {install_dir}")
    if dry_run:
        print(f"- Copier: {', '.join(FILES_TO_INSTALL)}")
        print(f"- Donnees: {DATA_FILE}")
        print(f"- Sauvegardes JSON: {BACKUP_DIR}")
        print(f"- Lanceur: {LAUNCHER_PATH}")
        print(f"- Menu: {DESKTOP_FILE}")
        return

    install_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_raw_data()
    if backup_path:
        print(f"Sauvegarde JSON: {backup_path}")
    for filename in FILES_TO_INSTALL:
        shutil.copy2(SOURCE_DIR / filename, install_dir / filename)
    make_executable(install_dir / "launcher.py")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text("[]\n", encoding="utf-8")

    BIN_DIR.mkdir(parents=True, exist_ok=True)
    wrapper = f'''#!/bin/sh
exec "{sys.executable}" "{install_dir / 'launcher.py'}" "$@"
'''
    write_text(LAUNCHER_PATH, wrapper)
    make_executable(LAUNCHER_PATH)

    desktop = f'''[Desktop Entry]
Type=Application
Name=MultiLaunch
Comment=Launcher de jeux Linux Wine Proton
Exec={LAUNCHER_PATH} gui
Path={install_dir}
Terminal=false
Categories=Game;
StartupNotify=true
'''
    write_text(DESKTOP_FILE, desktop)
    make_executable(DESKTOP_FILE)

    update_desktop_database = shutil.which("update-desktop-database")
    if update_desktop_database:
        os.system(f'"{update_desktop_database}" "{APPLICATIONS_DIR}" >/dev/null 2>&1')

    print("Installation terminee.")
    print(f"Programme: {install_dir}")
    print(f"Donnees: {DATA_FILE}")
    print(f"Menu: {DESKTOP_FILE}")
    print(f"Commande: {LAUNCHER_PATH} gui")


def uninstall(install_dir: Path, dry_run: bool = False) -> None:
    print(f"Desinstallation du programme dans {install_dir}")
    if dry_run:
        print(f"- Supprimer: {install_dir}")
        print(f"- Supprimer: {LAUNCHER_PATH}")
        print(f"- Supprimer: {DESKTOP_FILE}")
        print(f"- Conserver: {DATA_FILE}")
        return
    if install_dir.exists():
        shutil.rmtree(install_dir)
    for path in (LAUNCHER_PATH, DESKTOP_FILE):
        if path.exists():
            path.unlink()
    print(f"Programme desinstalle. Les donnees sont conservees dans {DATA_FILE}.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Installe MultiLaunch dans le home utilisateur")
    parser.add_argument("--target", type=Path, default=DEFAULT_INSTALL_DIR, help="Dossier d'installation")
    parser.add_argument("--uninstall", action="store_true", help="Desinstalle le programme sans supprimer les donnees")
    parser.add_argument("--dry-run", action="store_true", help="Affiche les actions sans modifier le systeme")
    args = parser.parse_args()
    try:
        if args.uninstall:
            uninstall(args.target.expanduser().resolve(), args.dry_run)
        else:
            install(args.target.expanduser().resolve(), args.dry_run)
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Erreur: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
