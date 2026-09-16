#!/usr/bin/env python3
"""Install MultiLaunch in the user's home directory."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import sys
import subprocess
from pathlib import Path


APP_NAME = "MultiLaunch"
SOURCE_DIR = Path(__file__).resolve().parent
DEFAULT_INSTALL_DIR = Path.home() / APP_NAME
DATA_DIR = Path.home() / "Documents" / APP_NAME
DATA_FILE = DATA_DIR / "data.json"
BIN_DIR = Path.home() / ".local" / "bin"
APPLICATIONS_DIR = Path.home() / ".local" / "share" / "applications"
LAUNCHER_PATH = BIN_DIR / "multilaunch"
DESKTOP_FILE = APPLICATIONS_DIR / "multilaunch.desktop"
WINDOWS_START_MENU = Path(os.environ.get("APPDATA", Path.home())) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
WINDOWS_LAUNCHER = DEFAULT_INSTALL_DIR / "multilaunch.bat"
WINDOWS_SHORTCUT = WINDOWS_START_MENU / "MultiLaunch.lnk"
FILES_TO_INSTALL = ("launcher.py", "gui.py", "gamedetector.py", "version.json", "update.json")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def make_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def choose_platform(requested: str | None = None) -> str:
    if requested:
        return requested
    detected = "windows" if os.name == "nt" else "linux"
    print(f"Plateforme détectée : {detected}")
    answer = input("Choisir la plateforme [L]inux/[W]indows (Entrée = plateforme détectée) : ").strip().lower()
    if not answer:
        return detected
    if answer in {"l", "linux"}:
        return "linux"
    if answer in {"w", "windows", "win"}:
        return "windows"
    raise ValueError("Plateforme invalide: choisissez Linux ou Windows")


def powershell_escape(value: Path) -> str:
    return str(value).replace("'", "''")


def create_windows_shortcut(install_dir: Path) -> None:
    WINDOWS_START_MENU.mkdir(parents=True, exist_ok=True)
    target = powershell_escape(install_dir / "multilaunch.bat")
    shortcut = powershell_escape(WINDOWS_SHORTCUT)
    working_dir = powershell_escape(install_dir)
    command = (
        "$shell = New-Object -ComObject WScript.Shell; "
        f"$link = $shell.CreateShortcut('{shortcut}'); "
        f"$link.TargetPath = '{target}'; $link.WorkingDirectory = '{working_dir}'; "
        "$link.Description = 'Launcher de jeux Linux Wine Proton'; $link.Save()"
    )
    try:
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command], check=True)
    except (OSError, subprocess.CalledProcessError) as error:
        raise RuntimeError(f"Impossible de créer le raccourci Windows: {error}") from error


def install(install_dir: Path, platform: str, dry_run: bool = False) -> None:
    missing = [name for name in FILES_TO_INSTALL if not (SOURCE_DIR / name).is_file()]
    if missing:
        raise RuntimeError(f"Fichiers du programme manquants: {', '.join(missing)}")

    print(f"Installation de {APP_NAME} pour {platform} dans {install_dir}")
    if dry_run:
        print(f"- Copier: {', '.join(FILES_TO_INSTALL)}")
        print(f"- Donnees: {DATA_FILE}")
        if platform == "windows":
            print(f"- Lanceur: {install_dir / 'multilaunch.bat'}")
            print(f"- Menu Démarrer: {WINDOWS_SHORTCUT}")
        else:
            print(f"- Lanceur: {LAUNCHER_PATH}")
            print(f"- Menu: {DESKTOP_FILE}")
        return

    install_dir.mkdir(parents=True, exist_ok=True)
    for filename in FILES_TO_INSTALL:
        shutil.copy2(SOURCE_DIR / filename, install_dir / filename)
    make_executable(install_dir / "launcher.py")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text("[]\n", encoding="utf-8")

    if platform == "windows":
        windows_launcher = install_dir / "multilaunch.bat"
        wrapper = f'''@echo off
"{sys.executable}" "{install_dir / 'launcher.py'}" gui %*
'''
        write_text(windows_launcher, wrapper)
        create_windows_shortcut(install_dir)
        print("Installation terminee.")
        print(f"Programme: {install_dir}")
        print(f"Donnees: {DATA_FILE}")
        print(f"Menu Démarrer: {WINDOWS_SHORTCUT}")
        print(f"Commande: {windows_launcher}")
        return

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


def uninstall(install_dir: Path, platform: str, dry_run: bool = False) -> None:
    print(f"Desinstallation du programme dans {install_dir}")
    if dry_run:
        print(f"- Supprimer: {install_dir}")
        if platform == "windows":
            print(f"- Supprimer: {install_dir / 'multilaunch.bat'}")
            print(f"- Supprimer: {WINDOWS_SHORTCUT}")
        else:
            print(f"- Supprimer: {LAUNCHER_PATH}")
            print(f"- Supprimer: {DESKTOP_FILE}")
        print(f"- Conserver: {DATA_FILE}")
        return
    if install_dir.exists():
        shutil.rmtree(install_dir)
    paths = (WINDOWS_SHORTCUT,) if platform == "windows" else (LAUNCHER_PATH, DESKTOP_FILE)
    for path in paths:
        if path.exists():
            path.unlink()
    print(f"Programme desinstalle. Les donnees sont conservees dans {DATA_FILE}.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Installe MultiLaunch dans le home utilisateur")
    parser.add_argument("--target", type=Path, default=DEFAULT_INSTALL_DIR, help="Dossier d'installation")
    parser.add_argument("--uninstall", action="store_true", help="Desinstalle le programme sans supprimer les donnees")
    parser.add_argument("--dry-run", action="store_true", help="Affiche les actions sans modifier le systeme")
    parser.add_argument("--platform", choices=("linux", "windows"), help="Plateforme cible; sinon une question est posée")
    args = parser.parse_args()
    try:
        platform = choose_platform(args.platform)
        if args.uninstall:
            uninstall(args.target.expanduser().resolve(), platform, args.dry_run)
        else:
            install(args.target.expanduser().resolve(), platform, args.dry_run)
        return 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Erreur: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
