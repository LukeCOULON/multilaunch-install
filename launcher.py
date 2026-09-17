#!/usr/bin/env python3
"""MultiLaunch, launcher local de jeux Linux, Wine et Proton."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import shlex
import re
import sqlite3
import subprocess
import sys
import tempfile
import uuid
import urllib.error
import urllib.request
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

import gamedetector


DEFAULT_APP_DIR = Path.home() / "Documents" / "MultiLaunch"
APP_DIR = Path(os.environ.get("MULTILAUNCH_HOME", DEFAULT_APP_DIR))
GAMES_FILE = APP_DIR / "data.json"
DATA_BACKUP_DIR = Path.home() / "Documents" / "MultiLaunch" / "backups"
UPDATE_STATE_FILE = APP_DIR / "update-state.json"
SETTINGS_FILE = APP_DIR / "settings.json"
LOG_DIR = APP_DIR / "logs"
APP_NAME = "MultiLaunch"
APP_AUTHOR = "Luke Coulon"
PROJECT_ROOT = Path(__file__).resolve().parent
VERSION_FILE = PROJECT_ROOT / "version.json"
UPDATE_FILE = PROJECT_ROOT / "update.json"
OLD_VERSION_FILE = PROJECT_ROOT / "old_version.json"
GITHUB_REPOSITORY = "LukeCOULON/multilaunch"
IGNORED_EXECUTABLE_NAMES = {
    "setup", "install", "installer", "unins000", "uninstall", "uninstaller",
    "update", "updater", "patcher", "crashhandler", "crashreporter", "launcher",
    "steamwebhelper", "unitycrashhandler", "vcredist", "dotnet", "dxsetup",
    "wine", "wine64", "wineserver",
}
IGNORED_DIRECTORIES = {
    "windows", "system32", "syswow64", "common files", "redist", "redistributables",
}
IGNORED_PATH_PARTS = {
    "compatibilitytools.d", "runners", "runtime", "runtimes", "tools", "toolkit",
    "wine", "wineserver", "system32", "syswow64", "programdata",
}
DEFAULT_DETECTION_PATHS = (
    "~/.steam/", "~/.steam/steam/", "~/.steam/root/", "~/.steam/steam/steamapps/",
    "~/.steam/steam/steamapps/common/", "~/.steam/steam/steamapps/compatdata/",
    "~/.steam/steam/compatibilitytools.d/", "~/.steam/root/compatibilitytools.d/",
    "~/.local/share/Steam/", "~/.local/share/Steam/steamapps/",
    "~/.local/share/Steam/steamapps/common/", "~/.local/share/Steam/steamapps/compatdata/",
    "~/.local/share/Steam/compatibilitytools.d/", "~/.var/app/com.valvesoftware.Steam/",
    "~/.var/app/com.valvesoftware.Steam/.steam/", "~/.var/app/com.valvesoftware.Steam/.local/share/Steam/",
    "~/.var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/",
    "~/.var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/common/",
    "~/.var/app/com.valvesoftware.Steam/.local/share/Steam/steamapps/compatdata/",
    "~/snap/steam/common/.steam/steam/", "~/.config/heroic/", "~/.config/heroic/store_cache/",
    "~/.config/legendary/", "~/.config/legendary/installed.json", "~/.var/app/com.heroicgameslauncher.hgl/",
    "~/.var/app/com.heroicgameslauncher.hgl/config/", "~/.var/app/com.heroicgameslauncher.hgl/config/heroic/",
    "~/.var/app/com.heroicgameslauncher.hgl/config/heroic/store_cache/",
    "~/.var/app/com.heroicgameslauncher.hgl/config/legendary/", "~/.local/share/lutris/",
    "~/.local/share/lutris/pga.db", "~/.local/share/lutris/runners/", "~/.local/share/lutris/runners/wine/",
    "~/.config/lutris/", "~/.var/app/net.lutris.Lutris/", "~/.var/app/net.lutris.Lutris/config/",
    "~/.var/app/net.lutris.Lutris/data/", "~/.var/app/net.lutris.Lutris/data/lutris/",
    "~/.var/app/net.lutris.Lutris/data/lutris/pga.db", "~/.var/app/com.usebottles.bottles/",
    "~/.var/app/com.usebottles.bottles/config/", "~/.var/app/com.usebottles.bottles/data/",
    "~/.var/app/com.usebottles.bottles/data/bottles/", "~/.var/app/com.usebottles.bottles/data/bottles/bottles/",
    "~/.wine/", "~/.wine/drive_c/", "~/.local/share/wine/", "~/.local/share/wineprefixes/", "~/.config/wine/",
    "~/.config/minigalaxy/", "~/.local/share/minigalaxy/", "~/.config/com.github.tkashkin.gamehub/",
    "~/.local/share/com.github.tkashkin.gamehub/", "~/.config/retroarch/", "~/.local/share/retroarch/",
    "~/.emulationstation/", "~/.config/emulationstation/", "~/Games/", "~/games/", "~/Desktop/", "~/Downloads/",
    "/mnt/", "/media/", "/run/media/$USER/", "~/.var/app/", "~/snap/",
    "/usr/bin/wine", "/usr/bin/wine64", "/usr/bin/wineserver", "/usr/local/bin/wine", "/usr/local/bin/wine64",
)


@dataclass
class Game:
    id: str
    name: str
    executable: str
    platform: str
    backend: str = "auto"
    runtime: str | None = None
    prefix: str | None = None
    working_directory: str | None = None
    arguments: list[str] = field(default_factory=list)
    environment: dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    created_at: str | None = None
    last_launched_at: str | None = None
    launch_count: int = 0
    source: str | None = None
    discovery_method: str | None = None
    confidence: str | None = None
    install_path: str | None = None
    launcher_id: str | None = None
    detected_at: str | None = None
    status: str = "ready"
    verification: str = "VERIFIED"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Game":
        return cls(**data)


@dataclass
class PreparedLaunch:
    executable: str
    arguments: list[str]
    environment: dict[str, str]
    working_directory: str

    @property
    def argv(self) -> list[str]:
        return [self.executable, *self.arguments]


def read_version_file(path: Path = VERSION_FILE) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Impossible de lire la version: {error}") from error
    if not isinstance(data, dict) or not isinstance(data.get("version"), str):
        raise RuntimeError("version.json ne contient pas une version valide")
    return data


def version_tuple(version: str) -> tuple[int, ...]:
    match = re.match(r"^v?(\d+(?:\.\d+)*)(?:[-+].*)?$", version.strip())
    if not match:
        raise ValueError(f"Version invalide: {version}")
    return tuple(int(part) for part in match.group(1).split("."))


def compare_versions(local: str, remote: str) -> int:
    left = version_tuple(local)
    right = version_tuple(remote)
    size = max(len(left), len(right))
    padded_left = left + (0,) * (size - len(left))
    padded_right = right + (0,) * (size - len(right))
    return (padded_left > padded_right) - (padded_left < padded_right)


def read_update_file(path: Path = UPDATE_FILE) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Impossible de lire les nouveautés: {error}") from error
    if not isinstance(data, dict) or not isinstance(data.get("version"), str) or not isinstance(data.get("items"), list):
        raise RuntimeError("update.json ne contient pas un format valide")
    return data


def should_show_updates() -> bool:
    updates = read_update_file()
    if not UPDATE_STATE_FILE.exists():
        return True
    try:
        state = json.loads(UPDATE_STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True
    return state.get("last_seen_version") != updates["version"]


def mark_updates_seen() -> None:
    updates = read_update_file()
    ensure_storage()
    UPDATE_STATE_FILE.write_text(
        json.dumps({"last_seen_version": updates["version"]}, indent=2) + "\n",
        encoding="utf-8",
    )


def fetch_remote_version(timeout: float = 8.0) -> dict[str, Any]:
    urls = [
        f"https://raw.githubusercontent.com/{GITHUB_REPOSITORY}/main/version.json",
        f"https://raw.githubusercontent.com/{GITHUB_REPOSITORY}/master/version.json",
    ]
    last_error: Exception | None = None
    for url in urls:
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "MultiLaunch-Updater"})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
            if not isinstance(data, dict) or not isinstance(data.get("version"), str):
                raise RuntimeError("Le version.json distant est invalide")
            return data
        except (OSError, json.JSONDecodeError, RuntimeError) as error:
            last_error = error
    raise RuntimeError(f"Version GitHub indisponible: {last_error}")


def check_for_update() -> dict[str, Any]:
    local = read_version_file()
    remote = fetch_remote_version()
    comparison = compare_versions(local["version"], remote["version"])
    return {
        "current": local,
        "remote": remote,
        "update_available": comparison < 0,
    }


def install_update(remote: dict[str, Any], timeout: float = 30.0) -> Path:
    if compare_versions(read_version_file()["version"], remote["version"]) >= 0:
        raise RuntimeError("Aucune mise à jour plus récente à installer")
    branch = str(remote.get("branch", "main"))
    archive_url = f"https://github.com/{GITHUB_REPOSITORY}/archive/refs/heads/{branch}.zip"
    backup_dir = APP_DIR / "updates" / dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir.mkdir(parents=True, exist_ok=True)
    if GAMES_FILE.is_file():
        DATA_BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        data_backup = DATA_BACKUP_DIR / f"data-{dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
        shutil.copy2(GAMES_FILE, data_backup)
    update_files = {"app_entry.py", "launcher.py", "gui.py", "gamedetector.py", "version.json", "update.json", "old_version.json", "test_launcher.py"}
    with tempfile.TemporaryDirectory(prefix="multilaunch-update-") as temporary:
        archive_path = Path(temporary) / "update.zip"
        request = urllib.request.Request(archive_url, headers={"User-Agent": "MultiLaunch-Updater"})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response, archive_path.open("wb") as output:
                shutil.copyfileobj(response, output)
            with zipfile.ZipFile(archive_path) as archive:
                members = [member for member in archive.infolist() if not member.is_dir()]
                for member in members:
                    relative = Path(member.filename)
                    if len(relative.parts) < 2 or relative.name not in update_files:
                        continue
                    destination = PROJECT_ROOT / relative.name
                    backup_target = backup_dir / relative.name
                    if destination.exists():
                        shutil.copy2(destination, backup_target)
                    with archive.open(member) as source, destination.open("wb") as target:
                        shutil.copyfileobj(source, target)
        except (OSError, zipfile.BadZipFile, urllib.error.URLError) as error:
            raise RuntimeError(f"Mise à jour impossible: {error}") from error
    return backup_dir


@dataclass
class DetectedCandidate:
    executable: str
    platform: str
    source: str
    confidence: str
    name: str
    score: int = 0
    evidence: list[str] = field(default_factory=list)
    install_path: str | None = None
    launcher_id: str | None = None
    discovery_method: str = "unknown"
    detected_at: str = field(default_factory=lambda: dt.datetime.now().astimezone().isoformat())
    verification: str = "VERIFIED"
    appid: str | None = None
    reason: str | None = None
    indicators: list[str] = field(default_factory=list)
    backend: str = "auto"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def load_games() -> list[Game]:
    ensure_storage()
    if not GAMES_FILE.exists():
        return []
    try:
        data = json.loads(GAMES_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Impossible de lire {GAMES_FILE}: {error}") from error
    return [Game.from_dict(item) for item in data]


def ensure_storage() -> None:
    """Create the user data directory and its JSON file on first use."""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    if not GAMES_FILE.exists():
        GAMES_FILE.write_text("[]\n", encoding="utf-8")


def save_games(games: list[Game]) -> None:
    ensure_storage()
    temporary_file = GAMES_FILE.with_suffix(".tmp")
    temporary_file.write_text(
        json.dumps([asdict(game) for game in games], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary_file.replace(GAMES_FILE)


def backup_data() -> Path:
    if not GAMES_FILE.is_file():
        ensure_storage()
    backup_dir = DATA_BACKUP_DIR
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"data-{dt.datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
    shutil.copy2(GAMES_FILE, backup_path)
    return backup_path


def load_settings() -> dict[str, Any]:
    if not SETTINGS_FILE.exists():
        return {"theme": "dark"}
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"theme": "dark"}
    return data if isinstance(data, dict) else {"theme": "dark"}


def save_settings(settings: dict[str, Any]) -> None:
    ensure_storage()
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def detect_platform(path: Path) -> str:
    with path.open("rb") as executable_file:
        header = executable_file.read(4)
    if header == b"\x7fELF":
        return "linux"
    if header[:2] == b"MZ":
        return "windows"
    raise ValueError(f"Format d'exécutable inconnu: {path}")


def find_install_executables(install_path: str | Path, max_depth: int = 4) -> list[Path]:
    """List PE executables in one known installation, without scanning outside it."""
    root = Path(install_path).expanduser().resolve()
    if not root.is_dir() or root.is_symlink():
        return []
    results: list[Path] = []
    base_depth = len(root.parts)
    for current, directories, files in os.walk(root, followlinks=False):
        current_path = Path(current)
        if len(current_path.parts) - base_depth >= max_depth:
            directories.clear()
        directories[:] = [
            directory for directory in directories
            if directory.casefold() not in IGNORED_DIRECTORIES
            and not (current_path / directory).is_symlink()
        ]
        for filename in files:
            path = current_path / filename
            if path.suffix.casefold() != ".exe" or path.is_symlink():
                continue
            try:
                if detect_platform(path) == "windows":
                    results.append(path.resolve())
            except (OSError, ValueError):
                continue
    return sorted(set(results), key=lambda path: (len(path.parts), path.name.casefold(), str(path)))


def default_scan_roots() -> list[Path]:
    roots: list[Path] = []
    seen: set[Path] = set()
    for raw_path in DEFAULT_DETECTION_PATHS:
        expanded = Path(os.path.expandvars(raw_path)).expanduser()
        if expanded.exists() and expanded not in seen:
            roots.append(expanded)
            seen.add(expanded)
    return roots


def _candidate_name(path: Path) -> str:
    name = path.stem.replace("_", " ").replace("-", " ").strip()
    return name or path.parent.name


def _is_rejected_executable(path: Path) -> str | None:
    name = path.stem.casefold()
    path_parts = {part.casefold() for part in path.parts}
    if path.suffix.casefold() in {".dll", ".sys", ".ocx", ".msi"}:
        return "fichier système ou installateur"
    if name in IGNORED_EXECUTABLE_NAMES or any(name.startswith(prefix) for prefix in (
        "uninstall", "unins", "setup", "installer", "install", "update", "updater",
        "repair", "crash", "redist", "vc_redist", "dxsetup", "vcredist", "dotnet",
        "launcher", "helper", "service", "patcher", "config", "configurator", "benchmark",
        "dedicatedserver", "server",
    )):
        return "nom d'outil, d'installation ou de maintenance"
    if path_parts & IGNORED_PATH_PARTS:
        return "chemin de runtime ou d'outil technique"
    if any(name.startswith(prefix) for prefix in ("kernel", "ntdll", "api-ms-", "concrt", "msvcp", "msvcr", "ucrt", "d3d", "d3dx", "dxgi", "xinput", "xaudio")):
        return "fichier système"
    if any(marker in " ".join(path_parts) for marker in ("directx", "vcredist", "dotnet", "physx", "openal", "vulkan", "anticheat", "middleware")):
        return "runtime ou middleware"
    return None


def _inspect_context(path: Path) -> tuple[int, list[str]]:
    if reason := _is_rejected_executable(path):
        return -100, [reason]
    score = 1
    evidence = ["exécutable ELF" if path.read_bytes()[:4] == b"\x7fELF" else "exécutable PE"]
    try:
        nearby: list[Path] = []
        for context_directory in [path.parent, *list(path.parent.parents)[:2]]:
            nearby.extend(list(context_directory.iterdir())[:160])
        nearby = nearby[:320]
        markers = {"data", "assets", "content", "plugins", "managed", "resources"}
        marker_hits = [marker for marker in markers if any(marker in item.name.casefold() for item in nearby)]
        companions = sum(item.suffix.casefold() in {".dll", ".pak", ".dat", ".so"} for item in nearby)
        if marker_hits:
            score += min(3, len(marker_hits))
            evidence.append("données: " + ", ".join(marker_hits[:3]))
        if companions:
            score += min(2, companions)
            evidence.append(f"{companions} fichier(s) compagnon(s)")
    except OSError:
        pass
    return score, evidence


def _add_candidate(
    found: dict[str, DetectedCandidate],
    path: Path,
    source: str,
    install_path: Path | None = None,
    launcher_id: str | None = None,
    method: str = "filesystem",
    metadata_confirmed: bool = False,
    evidence: list[str] | None = None,
) -> None:
    try:
        path = path.expanduser().resolve()
        if not path.is_file():
            return
        platform = detect_platform(path)
    except (OSError, ValueError):
        return
    if not metadata_confirmed and path.stat().st_size < 4096:
        return
    key = str(path)
    score, context_evidence = _inspect_context(path)
    if score < 0:
        return
    all_evidence = list(evidence or []) + context_evidence
    if metadata_confirmed:
        score += 5
    elif not evidence or score < 2:
        return
    confidence = "TRUSTED" if metadata_confirmed and install_path and launcher_id else "HIGH" if metadata_confirmed or (install_path and score >= 2) else "LOW"
    candidate = DetectedCandidate(
        key, platform, source, confidence, _candidate_name(path), score, all_evidence,
        str(install_path) if install_path else str(path.parent), launcher_id, method,
    )
    previous = found.get(key)
    if previous is None or candidate.score > previous.score:
        found[key] = candidate


def _quoted_value(text: str, key: str) -> str | None:
    match = re.search(rf'"{re.escape(key)}"\s+"([^"]+)"', text)
    return match.group(1) if match else None


def _select_game_executable(install_path: Path, metadata_confirmed: bool) -> Path | None:
    candidates: list[tuple[int, Path]] = []
    for current, directories, files in os.walk(install_path, followlinks=False):
        depth = len(Path(current).relative_to(install_path).parts)
        if depth > 3:
            directories.clear()
            continue
        directories[:] = [item for item in directories if item.casefold() not in IGNORED_DIRECTORIES and not Path(current, item).is_symlink()]
        for filename in files:
            path = Path(current) / filename
            if _is_rejected_executable(path):
                continue
            try:
                detect_platform(path)
            except (OSError, ValueError):
                continue
            rank = 5 if path.parent == install_path else 3 if path.parent.name.casefold() in {"bin", "game", "binaries"} else 1
            if path.stem.casefold() in {install_path.name.casefold(), install_path.name.replace(" ", "").casefold()}:
                rank += 2
            candidates.append((rank, path))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    if len(candidates) > 1 and candidates[0][0] == candidates[1][0] and not metadata_confirmed:
        return None
    return candidates[0][1]


def _steam_candidates(found: dict[str, DetectedCandidate]) -> None:
    steam_roots = [Path(os.path.expandvars(path)).expanduser() for path in (
        "~/.steam/steam", "~/.steam/root", "~/.local/share/Steam",
        "~/.var/app/com.valvesoftware.Steam/.local/share/Steam", "~/snap/steam/common/.steam/steam",
    )]
    for steam_root in steam_roots:
        steamapps = steam_root / "steamapps"
        if not steamapps.is_dir():
            continue
        libraries = [steam_root]
        folders = steamapps / "libraryfolders.vdf"
        if folders.is_file():
            for value in re.findall(r'"path"\s+"([^"]+)"', folders.read_text(encoding="utf-8", errors="ignore")):
                libraries.append(Path(value))
        for library in {item.resolve() for item in libraries if item.exists()}:
            for manifest in (library / "steamapps").glob("appmanifest_*.acf"):
                text = manifest.read_text(encoding="utf-8", errors="ignore")
                app_id = manifest.stem.removeprefix("appmanifest_")
                name = _quoted_value(text, "name") or app_id
                install_dir_name = _quoted_value(text, "installdir")
                if not install_dir_name:
                    continue
                install_path = library / "steamapps" / "common" / install_dir_name
                executable = _select_game_executable(install_path, True)
                if executable:
                    _add_candidate(found, executable, "Steam", install_path, app_id, "Steam manifest", True, [f"Steam manifest appid {app_id}", f"nom: {name}"])


def _metadata_candidates(found: dict[str, DetectedCandidate], source: str, roots: list[Path]) -> None:
    for root in roots:
        if not root.exists():
            continue
        for metadata in root.rglob("*.json"):
            if metadata.is_symlink() or metadata.stat().st_size > 10_000_000:
                continue
            try:
                text = metadata.read_text(encoding="utf-8", errors="ignore")
                data = json.loads(text)
            except (OSError, json.JSONDecodeError):
                continue
            values: list[tuple[str, str]] = []
            def collect(value: Any) -> None:
                if isinstance(value, dict):
                    for key, item in value.items():
                        if key.casefold() in {"executable", "exepath", "launchexecutable", "installpath", "install_dir"} and isinstance(item, str):
                            values.append((key.casefold(), item))
                        collect(item)
                elif isinstance(value, list):
                    for item in value:
                        collect(item)
            collect(data)
            for key, raw in values:
                executable = Path(os.path.expandvars(raw)).expanduser()
                if not executable.is_absolute():
                    executable = metadata.parent / executable
                if key in {"installpath", "install_dir"} and executable.is_dir():
                    executable = _select_game_executable(executable, True) or executable
                if executable.is_file():
                    _add_candidate(found, executable, source, executable.parent, metadata.stem, f"{source} metadata", True, [f"Trouvé via {source} metadata"])


def _lutris_database_candidates(found: dict[str, DetectedCandidate]) -> None:
    databases = [
        Path("~/.local/share/lutris/pga.db").expanduser(),
        Path("~/.var/app/net.lutris.Lutris/data/lutris/pga.db").expanduser(),
    ]
    for database in databases:
        if not database.is_file():
            continue
        try:
            connection = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "games" not in tables:
                connection.close()
                continue
            columns = {row[1] for row in connection.execute("PRAGMA table_info(games)")}
            wanted = [column for column in ("id", "name", "slug", "directory", "configpath", "exe", "working_dir") if column in columns]
            if not wanted:
                connection.close()
                continue
            for row in connection.execute(f"SELECT {', '.join(wanted)} FROM games"):
                record = dict(zip(wanted, row))
                raw_executable = record.get("exe") or ""
                if not raw_executable and record.get("configpath"):
                    config = Path(str(record["configpath"])).expanduser()
                    if config.is_file():
                        text = config.read_text(encoding="utf-8", errors="ignore")
                        match = re.search(r"(?:executable|exe):\s*['\"]?([^'\"\n]+)", text)
                        raw_executable = match.group(1).strip() if match else ""
                if not raw_executable:
                    continue
                executable = Path(os.path.expandvars(str(raw_executable))).expanduser()
                if not executable.is_absolute() and record.get("directory"):
                    executable = Path(str(record["directory"])) / executable
                if executable.is_file():
                    identifier = str(record.get("id") or record.get("slug") or executable)
                    name = str(record.get("name") or record.get("slug") or executable.stem)
                    _add_candidate(found, executable, "Lutris", executable.parent, identifier, "Lutris pga.db", True, [f"Exécutable déclaré par Lutris", f"nom: {name}"])
            connection.close()
        except (OSError, sqlite3.Error):
            continue


def discover_candidates(
    roots: list[Path] | None = None,
    max_files: int = 5000,
    recursive: bool = True,
    progress_callback: Callable[[str, int, int], bool] | None = None,
) -> list[DetectedCandidate]:
    """Adapt the dedicated non-destructive scanner to the launcher model."""
    results: list[gamedetector.GameCandidate] = []
    if roots is None:
        gamedetector.scan_steam(results)
        gamedetector.scan_steam_common_directories(results)
        gamedetector.scan_lutris(results)
        gamedetector.scan_heroic(results)
        gamedetector.scan_bottles(results)
        gamedetector.scan_wine_prefixes(results)
        gamedetector.scan_user_libraries(results)
    else:
        for root in roots:
            authorized_root = root.expanduser().resolve()
            if not authorized_root.is_dir() or authorized_root.is_symlink():
                continue
            gamedetector.scan_custom_directory(results, authorized_root)
    return [_adapt_detector_candidate(candidate) for candidate in gamedetector.sort_results(results)]


def _adapt_detector_candidate(candidate: gamedetector.GameCandidate) -> DetectedCandidate:
    executable = candidate.executable_path or ""
    platform = "windows" if executable.casefold().endswith(".exe") else "linux"
    score = gamedetector.CONFIDENCE_RANK.get(candidate.confidence, 0)
    evidence = [candidate.reason] if candidate.reason else []
    evidence.extend(candidate.indicators)
    launcher_id = candidate.launcher_id or candidate.appid
    return DetectedCandidate(
        executable=executable,
        platform=platform,
        source=candidate.source,
        confidence=candidate.confidence,
        name=candidate.name,
        score=score,
        evidence=evidence,
        install_path=candidate.install_path,
        launcher_id=launcher_id,
        discovery_method=candidate.reason or "gamedetector",
        verification=candidate.verification,
        appid=candidate.appid,
        reason=candidate.reason,
        indicators=list(candidate.indicators),
        backend="auto",
    )


def _scan_explicit_library(found: dict[str, DetectedCandidate], root: Path, max_files: int, recursive: bool, progress_callback: Callable[[str, int, int], bool] | None) -> None:
    """Scan only a user-selected library, never an implicit system path."""
    root = root.expanduser().resolve()
    forbidden = {Path("/"), Path("/usr"), Path("/bin"), Path("/sbin"), Path("/etc"), Path("/var"), Path.home() / ".local/share/Trash"}
    if not root.is_dir() or root.is_symlink() or root in forbidden:
        return
    visited = 0
    if progress_callback and not progress_callback(str(root), 0, max_files):
        return
    for current, directories, files in os.walk(root, onerror=lambda _: None, followlinks=False):
        directories[:] = [directory for directory in directories
                          if not directory.startswith(".") and directory.casefold() not in IGNORED_DIRECTORIES
                          and not Path(current, directory).is_symlink()]
        if not recursive:
            directories.clear()
        for filename in files:
            visited += 1
            if visited > max_files:
                return
            path = Path(current) / filename
            if progress_callback and visited % 25 == 0 and not progress_callback(str(root), visited, max_files):
                return
            suffix = path.suffix.casefold()
            if suffix in {".exe", ".msi"}:
                _add_candidate(found, path, "installation utilisateur", root, None, "bibliothèque explicitement ajoutée", False, ["Trouvé dans une bibliothèque utilisateur"])
            elif suffix == ".desktop":
                try:
                    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
                    exec_line = next((line[5:] for line in lines if line.startswith("Exec=")), "")
                    tokens = shlex.split(exec_line)
                    if tokens:
                        executable = Path(os.path.expandvars(tokens[0].replace("%f", "").replace("%u", ""))).expanduser()
                        _add_candidate(found, executable, "installation utilisateur", executable.parent, path.stem, "raccourci .desktop", True, ["Exécutable déclaré par un raccourci .desktop"])
                except (OSError, ValueError):
                    pass
            elif os.access(path, os.X_OK):
                try:
                    if path.read_bytes()[:4] == b"\x7fELF":
                        _add_candidate(found, path, "installation utilisateur", root, None, "bibliothèque explicitement ajoutée", False, ["Trouvé dans une bibliothèque utilisateur"])
                except OSError:
                    pass


def import_candidate(candidate: DetectedCandidate) -> Game:
    existing = {game.executable for game in load_games()}
    if candidate.executable in existing:
        raise ValueError(f"Jeu déjà présent: {candidate.executable}")
    game = Game(
        id=f"game-{uuid.uuid4().hex[:12]}", name=candidate.name,
        executable=candidate.executable, platform=candidate.platform,
        created_at=dt.datetime.now().astimezone().isoformat(),
        source=candidate.source,
        discovery_method=candidate.discovery_method,
        confidence=candidate.confidence,
        install_path=candidate.install_path,
        launcher_id=candidate.launcher_id,
        detected_at=candidate.detected_at,
        verification=candidate.verification,
        backend=candidate.backend,
    )
    games = load_games()
    games.append(game)
    save_games(games)
    return game


def find_runtime(runtime: str | None, backend: str) -> str | None:
    if backend == "proton" and runtime in {"proton", "auto"}:
        runtime = None
    candidates = [runtime] if runtime else (["wine"] if backend == "wine" else ["proton"])
    if backend == "native":
        return None
    for candidate in candidates:
        if candidate:
            candidate_path = Path(candidate).expanduser()
            if candidate_path.is_file() and os.access(candidate_path, os.X_OK):
                return str(candidate_path.resolve())
            resolved = shutil.which(candidate)
            if resolved:
                return resolved
    if backend == "proton":
        configured_runtime = os.environ.get("MULTILAUNCH_PROTON")
        if configured_runtime:
            configured_path = Path(configured_runtime).expanduser()
            if configured_path.is_file() and os.access(configured_path, os.X_OK):
                return str(configured_path.resolve())
        proton_roots = [
            Path.home() / ".local/share/Steam/steamapps/common",
            Path.home() / ".steam/steam/steamapps/common",
            Path.home() / ".steam/root/steamapps/common",
            Path.home() / ".local/share/Steam/compatibilitytools.d",
            Path.home() / ".steam/root/compatibilitytools.d",
        ]
        for root in proton_roots:
            if not root.is_dir():
                continue
            if runtime:
                matches = [root / runtime / "proton", root / runtime / "proton".lower()]
            else:
                matches = list(root.glob("*/proton"))
            for match in matches:
                if match.is_file() and os.access(match, os.X_OK):
                    return str(match.resolve())
    return None


def resolve_backend(game: Game) -> str:
    if game.backend != "auto":
        return game.backend
    if game.platform == "windows" and (game.source == "Steam" or (game.launcher_id or "").startswith("steam:")):
        return "proton"
    return "native" if game.platform == "linux" else "wine"


def find_game(game_id: str) -> Game:
    game = next((item for item in load_games() if item.id == game_id), None)
    if not game:
        raise KeyError(f"Jeu introuvable: {game_id}")
    return game


def parse_environment(values: list[str]) -> dict[str, str]:
    environment: dict[str, str] = {}
    for value in values:
        key, separator, content = value.partition("=")
        valid_name = key and (key[0].isalpha() or key[0] == "_") and all(
            character.isalnum() or character == "_" for character in key
        )
        if not separator or not valid_name:
            raise ValueError(f"Variable invalide: {value!r}; format attendu KEY=VALUE")
        environment[key] = content
    return environment


def save_game(game: Game) -> None:
    games = load_games()
    for index, current in enumerate(games):
        if current.id == game.id:
            games[index] = game
            save_games(games)
            return
    raise KeyError(f"Jeu introuvable: {game.id}")


def prepare_launch(game: Game) -> PreparedLaunch:
    executable = Path(game.executable).expanduser().resolve()
    if not executable.is_file():
        raise FileNotFoundError(f"Exécutable introuvable: {executable}")
    backend = resolve_backend(game)
    working_directory = Path(game.working_directory or executable.parent).expanduser().resolve()
    if not working_directory.is_dir():
        raise NotADirectoryError(f"Répertoire de travail introuvable: {working_directory}")
    environment = dict(os.environ)
    environment.update(game.environment)
    arguments = list(game.arguments)
    if backend == "native":
        if not os.access(executable, os.X_OK):
            raise PermissionError(f"Exécutable non autorisé à l'exécution: {executable}")
        command = str(executable)
    elif backend in {"wine", "proton"}:
        runtime = find_runtime(game.runtime, backend)
        if not runtime:
            raise RuntimeError(f"Runtime indisponible pour le backend {backend}")
        command = runtime
        if game.prefix:
            prefix = Path(game.prefix).expanduser().resolve()
        elif backend == "proton":
            prefix = APP_DIR / "prefixes" / game.id / "compatdata" / "pfx"
        else:
            prefix = None
        if prefix:
            prefix.mkdir(parents=True, exist_ok=True)
            environment["WINEPREFIX"] = str(prefix)
            if backend == "proton":
                environment["STEAM_COMPAT_DATA_PATH"] = str(prefix.parent)
        if backend == "proton":
            app_id = (game.launcher_id or "").removeprefix("steam:")
            if app_id.isdigit():
                steam_compatdata = Path.home() / ".local/share/Steam/steamapps/compatdata" / app_id
                if game.prefix is None:
                    prefix = steam_compatdata / "pfx"
                    prefix.mkdir(parents=True, exist_ok=True)
                    environment["WINEPREFIX"] = str(prefix)
                if prefix is None:
                    raise RuntimeError("Prefix Proton indisponible")
                environment["STEAM_COMPAT_DATA_PATH"] = str(prefix.parent)
                environment["STEAM_COMPAT_APP_ID"] = app_id
                environment["SteamAppId"] = app_id
                environment["SteamGameId"] = app_id
            steam_root = next((candidate for candidate in (
                Path.home() / ".local/share/Steam",
                Path.home() / ".steam/steam",
                Path.home() / ".steam/root",
            ) if candidate.is_dir()), None)
            if steam_root:
                environment.setdefault("STEAM_COMPAT_CLIENT_INSTALL_PATH", str(steam_root))
            environment.setdefault("STEAM_COMPAT_INSTALL_PATH", str(Path(runtime).parent))
        arguments = (["run"] if backend == "proton" else []) + [str(executable), *arguments]
    else:
        raise ValueError(f"Backend inconnu: {backend}")
    return PreparedLaunch(command, arguments, environment, str(working_directory))


def write_log(game: Game, prepared: PreparedLaunch, result: subprocess.CompletedProcess[str]) -> Path:
    timestamp = dt.datetime.now().astimezone()
    log_path = LOG_DIR / game.id / f"{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        "\n".join([
            f"timestamp={timestamp.isoformat()}", f"game={game.name}",
            f"backend={resolve_backend(game)}", f"prefix={game.prefix or ''}",
            f"command={json.dumps(prepared.argv, ensure_ascii=False)}",
            f"exit_code={result.returncode}", "", "[stdout]", result.stdout,
            "[stderr]", result.stderr,
        ]),
        encoding="utf-8",
    )
    return log_path


def add_game(args: argparse.Namespace) -> int:
    executable = Path(args.executable).expanduser().resolve()
    if not executable.is_file():
        raise FileNotFoundError(f"Exécutable introuvable: {executable}")
    game = Game(
        id=f"game-{uuid.uuid4().hex[:12]}", name=args.name or executable.stem,
        executable=str(executable), platform=detect_platform(executable),
        backend=args.backend,
        prefix=str(Path(args.prefix).expanduser().resolve()) if args.prefix else None,
        working_directory=str(Path(args.working_directory).expanduser().resolve()) if args.working_directory else None,
        arguments=args.arguments,
        environment=parse_environment(args.environment),
        created_at=dt.datetime.now().astimezone().isoformat(),
    )
    games = load_games()
    games.append(game)
    save_games(games)
    print(json.dumps(asdict(game), indent=2, ensure_ascii=False))
    return 0


def list_games(args: argparse.Namespace) -> int:
    games = load_games()
    if args.search:
        query = args.search.casefold()
        games = [game for game in games if query in " ".join([
            game.id, game.name, game.platform, game.executable,
        ]).casefold()]
    if args.json:
        print(json.dumps([asdict(game) for game in games], indent=2, ensure_ascii=False))
        return 0
    for game in games:
        print(f"{game.id}\t{game.name}\t{game.platform}\t{resolve_backend(game)}\t{game.executable}")
    return 0


def show_game(args: argparse.Namespace) -> int:
    print(json.dumps(asdict(find_game(args.game_id)), indent=2, ensure_ascii=False))
    return 0


def remove_game(args: argparse.Namespace) -> int:
    game = find_game(args.game_id)
    games = [item for item in load_games() if item.id != game.id]
    save_games(games)
    print(f"Jeu supprimé: {game.name}")
    return 0


def rename_game(args: argparse.Namespace) -> int:
    game = find_game(args.game_id)
    new_name = args.name.strip()
    if not new_name:
        raise ValueError("Le nouveau nom ne peut pas être vide")
    old_name = game.name
    game.name = new_name
    save_game(game)
    print(f"Jeu renommé : {old_name} -> {new_name}")
    return 0


def clear_games(args: argparse.Namespace) -> int:
    games = load_games()
    if games and not args.yes:
        raise ValueError("Cette action supprime toute la liste; ajoutez --yes pour confirmer")
    save_games([])
    print(f"{len(games)} jeu(x) retiré(s) du catalogue. Les fichiers installés sont conservés.")
    return 0


def update_game(args: argparse.Namespace) -> int:
    game = find_game(args.game_id)
    if args.name is not None:
        game.name = args.name
    if args.backend is not None:
        game.backend = args.backend
    if args.prefix is not None:
        game.prefix = str(Path(args.prefix).expanduser().resolve())
    if args.working_directory is not None:
        game.working_directory = str(Path(args.working_directory).expanduser().resolve())
    if args.argument:
        game.arguments = args.argument
    if args.environment:
        game.environment.update(parse_environment(args.environment))
    if args.disable:
        game.enabled = False
    if args.enable:
        game.enabled = True
    save_game(game)
    print(json.dumps(asdict(game), indent=2, ensure_ascii=False))
    return 0


def launch_game(args: argparse.Namespace) -> int:
    game = find_game(args.game_id)
    if not game.enabled:
        raise RuntimeError(f"Jeu désactivé: {game.name}")
    uncertain = game.confidence in {"MEDIUM", "LOW"} or game.verification.startswith("UNVERIFIED")
    if uncertain and not args.allow_unverified:
        raise RuntimeError(f"Jeu non vérifié: {game.name}; confirmez sa configuration avant de le lancer")
    if uncertain and args.allow_unverified:
        game.verification = "USER_CONFIRMED"
        game.status = "ready"
        save_game(game)
    prepared = prepare_launch(game)
    print(f"Lancement: {json.dumps(prepared.argv, ensure_ascii=False)}")
    if args.dry_run:
        return 0
    try:
        result = subprocess.run(prepared.argv, cwd=prepared.working_directory,
                                env=prepared.environment, capture_output=True, text=True,
                                check=False, timeout=args.timeout)
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"Lancement interrompu après {args.timeout} seconde(s)") from error
    except OSError as error:
        raise RuntimeError(f"Impossible de démarrer le processus: {error}") from error
    game.last_launched_at = dt.datetime.now().astimezone().isoformat()
    game.launch_count += 1
    save_game(game)
    log_path = write_log(game, prepared, result)
    print(f"Code retour: {result.returncode}; log: {log_path}")
    return result.returncode


def diagnose(args: argparse.Namespace) -> int:
    game = find_game(args.game_id)
    executable = Path(game.executable).expanduser()
    backend = resolve_backend(game)
    runtime = "native" if backend == "native" else find_runtime(game.runtime, backend)
    checks = {
        "executable": executable.is_file(),
        "working_directory": Path(game.working_directory or executable.parent).expanduser().is_dir(),
        "backend": backend,
        "runtime": runtime,
        "prefix": not game.prefix or Path(game.prefix).expanduser().exists(),
    }
    print(json.dumps(checks, indent=2, ensure_ascii=False))
    return 0 if all(value is not False and value is not None for value in checks.values()) else 1


def scan_games(args: argparse.Namespace) -> int:
    roots = [Path(root).expanduser() for root in args.root] if args.root else None
    candidates = discover_candidates(roots=roots, max_files=args.max_files, recursive=not args.no_recursive)
    visible = [candidate for candidate in candidates if candidate.confidence in {"TRUSTED", "HIGH"} or (args.include_medium and candidate.confidence == "MEDIUM")]
    if args.import_games:
        imported = 0
        for candidate in visible:
            try:
                import_candidate(candidate)
                imported += 1
            except ValueError:
                pass
        print(f"{imported} jeu(x) importé(s) sur {len(candidates)} candidat(s).")
        return 0
    visible = [candidate for candidate in candidates if candidate.confidence in {"TRUSTED", "HIGH"} or (args.include_medium and candidate.confidence == "MEDIUM")]
    payload = [candidate.as_dict() for candidate in visible]
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for candidate in visible:
            evidence = ", ".join(candidate.evidence)
            print(f"[{candidate.confidence}/{candidate.score}] {candidate.name}\t{candidate.platform}\t{candidate.source}\t{evidence}\t{candidate.executable}")
        print(f"{len(visible)} candidat(s) fiable(s) détecté(s). Utilisez --import pour les ajouter.")
    return 0


def launch_gui(_: argparse.Namespace) -> int:
    from gui import LauncherWindow

    LauncherWindow().mainloop()
    return 0


def update_check(_: argparse.Namespace) -> int:
    result = check_for_update()
    current = result["current"]["version"]
    remote = result["remote"]["version"]
    if result["update_available"]:
        print(f"Mise à jour disponible: {current} -> {remote}")
        return 2
    print(f"MultiLaunch est à jour: {current}")
    return 0


def update_install(_: argparse.Namespace) -> int:
    result = check_for_update()
    if not result["update_available"]:
        print(f"MultiLaunch est déjà à jour: {result['current']['version']}")
        return 0
    backup = install_update(result["remote"])
    print(f"Mise à jour installée vers {result['remote']['version']}; sauvegarde: {backup}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"{APP_NAME} — launcher local de jeux Linux/Wine/Proton, créé par {APP_AUTHOR}")
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("add", help="Ajoute un exécutable")
    add.add_argument("executable")
    add.add_argument("--name")
    add.add_argument("--backend", choices=["auto", "native", "wine", "proton"], default="auto")
    add.add_argument("--prefix")
    add.add_argument("--arg", dest="arguments", action="append", default=[], help="Argument du jeu, répétable")
    add.set_defaults(function=add_game)
    add.add_argument("--workdir", dest="working_directory")
    add.add_argument("--env", dest="environment", action="append", default=[], help="Variable KEY=VALUE")
    show = commands.add_parser("list", help="Liste les jeux")
    show.add_argument("--search", help="Filtre par ID, nom, plateforme ou chemin")
    show.add_argument("--json", action="store_true", help="Produit une sortie JSON")
    show.set_defaults(function=list_games)
    details = commands.add_parser("show", help="Affiche la configuration complète")
    details.add_argument("game_id")
    details.set_defaults(function=show_game)
    remove = commands.add_parser("remove", help="Supprime un jeu du catalogue")
    remove.add_argument("game_id")
    remove.set_defaults(function=remove_game)
    rename = commands.add_parser("rename", help="Renomme un jeu du catalogue")
    rename.add_argument("game_id")
    rename.add_argument("name")
    rename.set_defaults(function=rename_game)
    clear = commands.add_parser("clear", help="Vide toute la liste du catalogue")
    clear.add_argument("--yes", action="store_true", help="Confirme la suppression de toutes les entrées")
    clear.set_defaults(function=clear_games)
    update = commands.add_parser("update", help="Modifie la configuration d'un jeu")
    update.add_argument("game_id")
    update.add_argument("--name")
    update.add_argument("--backend", choices=["auto", "native", "wine", "proton"])
    update.add_argument("--prefix")
    update.add_argument("--workdir", dest="working_directory")
    update.add_argument("--arg", dest="argument", action="append", default=[])
    update.add_argument("--env", dest="environment", action="append", default=[])
    update.add_argument("--enable", action="store_true")
    update.add_argument("--disable", action="store_true")
    update.set_defaults(function=update_game)
    launch = commands.add_parser("launch", help="Lance un jeu")
    launch.add_argument("game_id")
    launch.add_argument("--dry-run", action="store_true", help="Affiche la commande sans la lancer")
    launch.add_argument("--timeout", type=float, help="Arrête le processus après N secondes")
    launch.add_argument("--allow-unverified", action="store_true", help="Autorise le lancement après vérification manuelle")
    launch.set_defaults(function=launch_game)
    check = commands.add_parser("diagnose", help="Diagnostique un jeu")
    check.add_argument("game_id")
    check.set_defaults(function=diagnose)
    scan = commands.add_parser("scan", help="Détecte les jeux présents sur le PC")
    scan.add_argument("--root", action="append", default=[], help="Dossier supplémentaire à analyser")
    scan.add_argument("--max-files", type=int, default=5000)
    scan.add_argument("--no-recursive", action="store_true", help="Ne cherche pas dans les sous-dossiers")
    scan.add_argument("--json", action="store_true")
    scan.add_argument("--import", dest="import_games", action="store_true", help="Importe les candidats fiables détectés")
    scan.add_argument("--include-medium", action="store_true", help="Affiche aussi les découvertes MEDIUM à vérifier")
    scan.set_defaults(function=scan_games)
    graphical = commands.add_parser("gui", help="Ouvre l'interface graphique")
    graphical.set_defaults(function=launch_gui)
    version = commands.add_parser("update-check", help="Vérifie la version GitHub")
    version.set_defaults(function=update_check)
    update = commands.add_parser("update-install", help="Installe la dernière version GitHub")
    update.set_defaults(function=update_install)
    return parser


def main() -> int:
    try:
        args = build_parser().parse_args()
        return args.function(args)
    except (FileNotFoundError, NotADirectoryError, RuntimeError, ValueError, KeyError) as error:
        print(f"Erreur: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())