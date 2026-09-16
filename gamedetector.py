
#!/usr/bin/env python3

import os
import re
import json
import sqlite3
import argparse
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional


# ============================================================
# GAME DISCOVERY SCANNER
# ============================================================
#
# Scanner non destructif.
#
# Il NE :
#   - lance aucun executable
#   - ne modifie aucun jeu
#   - ne modifie aucun prefix Wine
#   - ne nécessite pas root
#
# Il recherche en priorité les métadonnées des launchers.
#
# Catégories :
#
#   TRUSTED
#       Launcher + manifest/config + installation + executable
#
#   HIGH
#       Source connue + installation + executable plausible
#
#   MEDIUM
#       Installation locale plausible mais origine non confirmée
#
#   LOW
#       Preuve faible
#
#   UNVERIFIED
#       Installation locale dont l'origine n'est pas connue
#
# Les "indicateurs" ne prouvent PAS qu'une installation est
# illégale ou piratée. Ils servent uniquement à signaler
# qu'une vérification manuelle peut être nécessaire.
#
# ============================================================


VERSION = "2.0"


# ============================================================
# Configuration
# ============================================================

HOME = Path.home()

DEFAULT_OUTPUT = Path("games_detected.json")

USER_LIBRARY_DIRS = [
    HOME / "Games",
    HOME / "games",
]

MAX_MANUAL_SCAN_DEPTH = 3
MAX_LAUNCHER_SCAN_DEPTH = 4


# ============================================================
# Répertoires à ignorer
# ============================================================

IGNORED_DIR_NAMES = {
    "windows",
    "system32",
    "syswow64",
    "windowsapps",

    "temp",
    "tmp",

    ".cache",
    "cache",

    "redist",
    "redistributable",

    "directx",
    "vcredist",
    "physx",

    "__pycache__",
}


# ============================================================
# Executables à rejeter
# ============================================================

REJECTED_EXECUTABLE_NAMES = {
    "wine",
    "wine64",
    "wineserver",
    "proton",
    "protontricks",
    "winetricks",
}


REJECTED_EXECUTABLE_PATTERNS = [
    r"^uninstall",
    r"^unins",

    r"^setup",
    r"^installer",
    r"^install",

    r"^update",
    r"^updater",
    r"^patcher",
    r"^repair",

    r"^crash",
    r"^crashhandler",

    r"^redist",
    r"^vc_redist",
    r"^vcredist",
    r"^dxsetup",

    r"^dotnet",

    r"^helper",
    r"^service",

    r"^config",
    r"^configurator",

    r"^benchmark",

    r"^dedicatedserver",
    r"^server",
]


# ============================================================
# Indices nécessitant une vérification
# ============================================================
#
# ATTENTION :
# Ces indices ne prouvent PAS qu'un jeu est piraté.
#
# Ils peuvent également apparaître dans :
#   - mods
#   - outils de compatibilité
#   - backups
#   - installations légitimes
#   - versions anciennes
#   - logiciels de test
#
# ============================================================

UNVERIFIED_INDICATOR_NAMES = {
    "crack",
    "cracks",
    "cracked",
    "crackfix",
    "crackfixes",

    "nodvd",
    "no-cd",
    "nocd",

    "loader",
    "loaders",
}


UNVERIFIED_INDICATOR_FILES = {
    "steam_api.dll",
    "steam_api64.dll",
    "steamclient.dll",
    "cream_api.ini",
}


# ============================================================
# Modèle
# ============================================================

@dataclass
class GameCandidate:

    name: str

    source: str

    confidence: str

    verification: str = "UNVERIFIED"

    install_path: Optional[str] = None

    executable_path: Optional[str] = None

    launcher_id: Optional[str] = None

    appid: Optional[str] = None

    reason: Optional[str] = None

    indicators: list = field(default_factory=list)


# ============================================================
# Utilitaires filesystem
# ============================================================

def safe_resolve(path: Path) -> Optional[Path]:

    try:
        return path.resolve()

    except (
        OSError,
        RuntimeError
    ):
        return None


def path_exists(path: Path) -> bool:

    try:
        return path.exists()

    except OSError:
        return False


def is_directory(path: Path) -> bool:

    try:
        return path.is_dir()

    except OSError:
        return False


def is_file(path: Path) -> bool:

    try:
        return path.is_file()

    except OSError:
        return False


# ============================================================
# Répertoires ignorés
# ============================================================

def is_ignored_directory(path: Path) -> bool:

    return (
        path.name.lower()
        in IGNORED_DIR_NAMES
    )


# ============================================================
# Validation executable
# ============================================================

def is_valid_executable(path: Path) -> bool:

    if not is_file(path):
        return False

    name = path.name.lower()

    if name in REJECTED_EXECUTABLE_NAMES:
        return False

    for pattern in REJECTED_EXECUTABLE_PATTERNS:

        if re.match(
            pattern,
            name,
            re.IGNORECASE
        ):
            return False

    if path.suffix.lower() != ".exe":
        return False

    try:

        size = path.stat().st_size

    except OSError:

        return False

    # Évite beaucoup de petits launchers,
    # installateurs et wrappers.
    if size < 32 * 1024:
        return False

    return True


# ============================================================
# Recherche executable contrôlée
# ============================================================

def find_executables(
    directory: Path,
    max_depth: int = 3
):

    if not is_directory(directory):
        return []

    results = []

    try:

        base_depth = len(directory.parts)

        for root, dirs, files in os.walk(
            directory,
            topdown=True
        ):

            current = Path(root)

            depth = (
                len(current.parts)
                - base_depth
            )

            if depth >= max_depth:
                dirs[:] = []

            dirs[:] = [
                d
                for d in dirs
                if not is_ignored_directory(
                    current / d
                )
            ]

            for filename in files:

                if not filename.lower().endswith(".exe"):
                    continue

                path = current / filename

                if is_valid_executable(path):

                    results.append(path)

    except (
        PermissionError,
        OSError
    ):
        pass

    return results


# ============================================================
# Choix executable
# ============================================================

def choose_executable(executables):

    if not executables:
        return None

    def score(path):

        name = path.name.lower()

        score = 0

        # Plus proche de la racine = mieux
        score -= len(path.parts)

        # Noms génériques peu intéressants
        bad_words = [
            "launcher",
            "updater",
            "setup",
            "installer",
            "helper",
            "crash",
            "server",
            "config",
        ]

        for word in bad_words:

            if word in name:
                score -= 20

        return score

    return max(
        executables,
        key=score
    )


# ============================================================
# Indicateurs d'installation non vérifiée
# ============================================================

def detect_unverified_indicators(
    install_path: Path
):

    indicators = []

    if not is_directory(install_path):
        return indicators

    try:

        entries = list(
            install_path.iterdir()
        )

    except (
        PermissionError,
        OSError
    ):

        return indicators

    for entry in entries:

        name = entry.name.lower()

        if (
            entry.is_dir()
            and name in UNVERIFIED_INDICATOR_NAMES
        ):

            indicators.append(
                f"dossier indicateur: {entry.name}"
            )

        if (
            entry.is_file()
            and name in UNVERIFIED_INDICATOR_FILES
        ):

            indicators.append(
                f"fichier indicateur: {entry.name}"
            )

    return indicators


# ============================================================
# Déduplication
# ============================================================

CONFIDENCE_RANK = {

    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "TRUSTED": 4,
}


def add_candidate(
    results,
    candidate: GameCandidate
):

    candidate_path = None

    if candidate.install_path:

        candidate_path = safe_resolve(
            Path(candidate.install_path)
        )

    for existing in results:

        existing_path = None

        if existing.install_path:

            existing_path = safe_resolve(
                Path(existing.install_path)
            )

        # Même installation
        if (
            candidate_path
            and existing_path
            and candidate_path == existing_path
        ):

            old_rank = CONFIDENCE_RANK.get(
                existing.confidence,
                0
            )

            new_rank = CONFIDENCE_RANK.get(
                candidate.confidence,
                0
            )

            if new_rank > old_rank:

                existing.confidence = (
                    candidate.confidence
                )

                existing.verification = (
                    candidate.verification
                )

                existing.reason = (
                    candidate.reason
                )

                existing.executable_path = (
                    candidate.executable_path
                )

                existing.indicators = (
                    candidate.indicators
                )

            return

        # Même AppID
        if (
            candidate.appid
            and existing.appid
            and candidate.appid == existing.appid
            and candidate.source == existing.source
        ):

            return

    results.append(candidate)


# ============================================================
# STEAM
# ============================================================

def find_steam_roots():

    candidates = [

        HOME
        / ".steam"
        / "steam",

        HOME
        / ".steam"
        / "root",

        HOME
        / ".local"
        / "share"
        / "Steam",

        HOME
        / ".var"
        / "app"
        / "com.valvesoftware.Steam"
        / ".local"
        / "share"
        / "Steam",

        HOME
        / "snap"
        / "steam"
        / "common"
        / ".steam"
        / "steam",
    ]

    roots = []

    for path in candidates:

        resolved = safe_resolve(path)

        if (
            resolved
            and resolved.exists()
            and resolved.is_dir()
            and resolved not in roots
        ):

            roots.append(resolved)

    return roots


def parse_steam_libraryfolders(
    vdf: Path
):

    libraries = []

    if not is_file(vdf):
        return libraries

    try:

        content = vdf.read_text(
            encoding="utf-8",
            errors="ignore"
        )

    except OSError:

        return libraries

    matches = re.findall(
        r'"path"\s*"([^"]+)"',
        content,
        re.IGNORECASE
    )

    for value in matches:

        path = Path(value)

        if (
            path.exists()
            and path.is_dir()
        ):

            resolved = safe_resolve(path)

            if (
                resolved
                and resolved not in libraries
            ):

                libraries.append(resolved)

    return libraries


def parse_steam_manifest(
    manifest: Path
):

    try:

        content = manifest.read_text(
            encoding="utf-8",
            errors="ignore"
        )

    except OSError:

        return None

    def get_value(key):

        match = re.search(
            rf'"{re.escape(key)}"\s*"([^"]*)"',
            content,
            re.IGNORECASE
        )

        if match:
            return match.group(1)

        return None

    appid = get_value("appid")
    name = get_value("name")
    installdir = get_value("installdir")

    if (
        not appid
        or not name
        or not installdir
    ):

        return None

    return {
        "appid": appid,
        "name": name,
        "installdir": installdir,
    }

# ============================================================
# STEAM : RECHERCHE DES DOSSIERS ORPHELINS
# ============================================================

def scan_steam_common_directories(results):
    """
    Recherche les jeux potentiels directement dans les dossiers :

        <SteamLibrary>/steamapps/common/

    Contrairement au scan Steam classique, cette fonction
    ne dépend PAS des appmanifest_*.acf.

    Un dossier présent dans common/ mais sans manifest Steam
    est donc considéré comme une installation non vérifiée.

    IMPORTANT :
    cela ne signifie PAS que le jeu est piraté.
    Il peut s'agir :
        - d'un ancien jeu Steam
        - d'un jeu copié manuellement
        - d'un backup
        - d'un jeu non installé par Steam
        - d'une installation provenant d'une autre source
        - d'une installation dont le manifest a disparu
    """

    print("[Steam Common] Recherche des installations non référencées...")

    for steam_root in find_steam_roots():

        steamapps = steam_root / "steamapps"

        if not is_directory(steamapps):
            continue

        # ----------------------------------------------------
        # Récupération des bibliothèques Steam
        # ----------------------------------------------------

        libraries = [
            steam_root
        ]

        library_file = (
            steamapps
            / "libraryfolders.vdf"
        )

        for library in parse_steam_libraryfolders(
            library_file
        ):

            if library not in libraries:
                libraries.append(library)

        # ----------------------------------------------------
        # Parcours des bibliothèques
        # ----------------------------------------------------

        for library in libraries:

            common = (
                library
                / "steamapps"
                / "common"
            )

            if not is_directory(common):
                continue

            # ------------------------------------------------
            # Construire la liste des dossiers déjà connus
            # ------------------------------------------------

            known_install_dirs = set()

            for manifest in (
                common.parent.glob(
                    "appmanifest_*.acf"
                )
            ):

                data = parse_steam_manifest(
                    manifest
                )

                if not data:
                    continue

                known_path = (
                    common
                    / data["installdir"]
                )

                resolved = safe_resolve(
                    known_path
                )

                if resolved:

                    known_install_dirs.add(
                        str(resolved)
                    )

            # ------------------------------------------------
            # Scanner les dossiers de common/
            # ------------------------------------------------

            try:

                directories = list(
                    common.iterdir()
                )

            except (
                PermissionError,
                OSError
            ):

                continue

            for game_dir in directories:

                if not game_dir.is_dir():
                    continue

                if is_ignored_directory(
                    game_dir
                ):
                    continue

                resolved_game_dir = safe_resolve(
                    game_dir
                )

                if not resolved_game_dir:
                    continue

                # --------------------------------------------
                # Déjà connu de Steam
                # --------------------------------------------

                if str(resolved_game_dir) in known_install_dirs:
                    continue

                # --------------------------------------------
                # Chercher des exécutables
                # --------------------------------------------

                executables = find_executables(
                    game_dir,
                    max_depth=3
                )

                executable = choose_executable(
                    executables
                )

                if not executable:
                    continue

                # --------------------------------------------
                # Chercher les indicateurs
                # --------------------------------------------

                indicators = (
                    detect_unverified_indicators(
                        game_dir
                    )
                )

                # --------------------------------------------
                # Ajouter comme installation non vérifiée
                # --------------------------------------------

                add_candidate(
                    results,

                    GameCandidate(
                        name=game_dir.name,

                        source="Steam Common",

                        confidence="MEDIUM",

                        verification=(
                            "UNVERIFIED_WITH_INDICATORS"
                            if indicators
                            else "UNVERIFIED"
                        ),

                        install_path=str(
                            game_dir
                        ),

                        executable_path=str(
                            executable
                        ),

                        launcher_id=None,

                        appid=None,

                        reason=(
                            "Dossier présent dans "
                            "Steam/steamapps/common "
                            "sans appmanifest Steam "
                            "correspondant"
                        ),

                        indicators=indicators,
                    )
                )

def scan_steam(results):

    print("[Steam] Recherche...")

    for steam_root in find_steam_roots():

        steamapps = (
            steam_root
            / "steamapps"
        )

        if not is_directory(steamapps):
            continue

        libraries = [
            steam_root
        ]

        library_file = (
            steamapps
            / "libraryfolders.vdf"
        )

        for library in parse_steam_libraryfolders(
            library_file
        ):

            if library not in libraries:

                libraries.append(library)

        for library in libraries:

            apps = (
                library
                / "steamapps"
            )

            if not is_directory(apps):
                continue

            for manifest in apps.glob(
                "appmanifest_*.acf"
            ):

                data = parse_steam_manifest(
                    manifest
                )

                if not data:
                    continue

                install_path = (
                    apps
                    / "common"
                    / data["installdir"]
                )

                if not is_directory(
                    install_path
                ):
                    continue

                executables = find_executables(
                    install_path,
                    max_depth=3
                )

                executable = choose_executable(
                    executables
                )

                if not executable:
                    continue

                add_candidate(
                    results,

                    GameCandidate(
                        name=data["name"],

                        source="Steam",

                        confidence="TRUSTED",

                        verification="VERIFIED",

                        install_path=str(
                            install_path
                        ),

                        executable_path=str(
                            executable
                        ),

                        launcher_id=(
                            f"steam:{data['appid']}"
                        ),

                        appid=data["appid"],

                        reason=(
                            "Steam manifest + "
                            "installation + "
                            "executable confirmé"
                        ),

                        indicators=(
                            detect_unverified_indicators(
                                install_path
                            )
                        ),
                    )
                )


# ============================================================
# LUTRIS
# ============================================================

def find_lutris_databases():

    paths = [

        HOME
        / ".local"
        / "share"
        / "lutris"
        / "pga.db",

        HOME
        / ".var"
        / "app"
        / "net.lutris.Lutris"
        / ".local"
        / "share"
        / "lutris"
        / "pga.db",

        HOME
        / ".var"
        / "app"
        / "net.lutris.Lutris"
        / "data"
        / "lutris"
        / "pga.db",
    ]

    return [
        path
        for path in paths
        if is_file(path)
    ]


def scan_lutris(results):

    print("[Lutris] Recherche...")

    for database in find_lutris_databases():

        connection = None

        try:

            connection = sqlite3.connect(
                f"file:{database}?mode=ro",
                uri=True
            )

            cursor = connection.cursor()

            cursor.execute(
                """
                SELECT
                    name,
                    slug,
                    directory,
                    executable
                FROM games
                """
            )

            rows = cursor.fetchall()

        except (
            sqlite3.Error,
            OSError
        ):

            continue

        finally:

            if connection:

                try:
                    connection.close()
                except Exception:
                    pass

        for (
            name,
            slug,
            directory,
            executable
        ) in rows:

            if not name:
                continue

            install_path = None

            if directory:

                install_path = Path(
                    str(directory)
                )

            executable_path = None

            if executable:

                executable_path = Path(
                    str(executable)
                )

            exe = None

            if (
                executable_path
                and is_file(executable_path)
                and is_valid_executable(
                    executable_path
                )
            ):

                exe = executable_path

            elif install_path:

                candidates = find_executables(
                    install_path,
                    max_depth=3
                )

                exe = choose_executable(
                    candidates
                )

            if not exe:
                continue

            confidence = (
                "TRUSTED"
                if executable
                else "HIGH"
            )

            reason = (
                "Lutris configuration + "
                "executable déclaré"
                if executable
                else
                "Lutris installation + "
                "executable trouvé"
            )

            add_candidate(
                results,

                GameCandidate(
                    name=name,

                    source="Lutris",

                    confidence=confidence,

                    verification="VERIFIED",

                    install_path=(
                        str(install_path)
                        if install_path
                        else None
                    ),

                    executable_path=str(
                        exe
                    ),

                    launcher_id=(
                        f"lutris:{slug or name}"
                    ),

                    reason=reason,

                    indicators=(
                        detect_unverified_indicators(
                            install_path
                        )
                        if install_path
                        else []
                    ),
                )
            )


# ============================================================
# HEROIC
# ============================================================

def find_heroic_configs():

    return [

        HOME
        / ".config"
        / "heroic",

        HOME
        / ".var"
        / "app"
        / "com.heroicgameslauncher.hgl"
        / "config"
        / "heroic",
    ]


def scan_heroic(results):

    print("[Heroic] Recherche...")

    for config in find_heroic_configs():

        if not is_directory(config):
            continue

        try:

            json_files = list(
                config.rglob("*.json")
            )

        except OSError:

            continue

        for json_file in json_files:

            try:

                data = json.loads(
                    json_file.read_text(
                        encoding="utf-8",
                        errors="ignore"
                    )
                )

            except (
                OSError,
                json.JSONDecodeError
            ):

                continue

            inspect_heroic_json(
                data,
                results,
                json_file
            )


def inspect_heroic_json(
    data,
    results,
    source_file
):

    if isinstance(data, dict):

        name = (
            data.get("title")
            or data.get("name")
            or data.get("appName")
        )

        install = (
            data.get("installPath")
            or data.get("install_path")
            or data.get("installDir")
        )

        executable = (
            data.get("executable")
            or data.get("executablePath")
        )

        appid = (
            data.get("appName")
            or data.get("app_id")
            or data.get("appId")
        )

        if (
            name
            and install
        ):

            install_path = Path(
                str(install)
            )

            if is_directory(
                install_path
            ):

                exe = None

                if executable:

                    candidate = Path(
                        str(executable)
                    )

                    if (
                        is_file(candidate)
                        and is_valid_executable(
                            candidate
                        )
                    ):

                        exe = candidate

                if not exe:

                    exe = choose_executable(
                        find_executables(
                            install_path,
                            max_depth=3
                        )
                    )

                if exe:

                    add_candidate(
                        results,

                        GameCandidate(
                            name=str(name),

                            source="Heroic",

                            confidence="HIGH",

                            verification="VERIFIED",

                            install_path=str(
                                install_path
                            ),

                            executable_path=str(
                                exe
                            ),

                            launcher_id=(
                                f"heroic:"
                                f"{appid or name}"
                            ),

                            reason=(
                                "Configuration Heroic + "
                                "installation confirmée"
                            ),

                            indicators=(
                                detect_unverified_indicators(
                                    install_path
                                )
                            ),
                        )
                    )

        for value in data.values():

            inspect_heroic_json(
                value,
                results,
                source_file
            )

    elif isinstance(data, list):

        for value in data:

            inspect_heroic_json(
                value,
                results,
                source_file
            )


# ============================================================
# BOTTLES
# ============================================================

def find_bottles_roots():

    return [

        HOME
        / ".var"
        / "app"
        / "com.usebottles.bottles"
        / "data"
        / "bottles"
        / "bottles",

        HOME
        / ".local"
        / "share"
        / "bottles"
        / "bottles",
    ]


def scan_bottles(results):

    print("[Bottles] Recherche...")

    for root in find_bottles_roots():

        if not is_directory(root):
            continue

        try:

            bottles = list(
                root.iterdir()
            )

        except OSError:

            continue

        for bottle in bottles:

            if not bottle.is_dir():
                continue

            executables = find_executables(
                bottle,
                max_depth=5
            )

            executable = choose_executable(
                executables
            )

            if not executable:
                continue

            indicators = (
                detect_unverified_indicators(
                    bottle
                )
            )

            add_candidate(
                results,

                GameCandidate(
                    name=bottle.name,

                    source="Bottles",

                    confidence="MEDIUM",

                    verification=(
                        "UNVERIFIED_WITH_INDICATORS"
                        if indicators
                        else "UNVERIFIED"
                    ),

                    install_path=str(
                        bottle
                    ),

                    executable_path=str(
                        executable
                    ),

                    launcher_id=(
                        f"bottles:{bottle.name}"
                    ),

                    reason=(
                        "Bottle détectée + "
                        "executable plausible"
                    ),

                    indicators=indicators,
                )
            )


# ============================================================
# WINE
# ============================================================

def scan_wine_prefixes(results):

    print("[Wine] Recherche de prefixes...")

    prefixes = [

        HOME / ".wine",

        HOME / ".local" / "share" / "wineprefixes",
    ]

    for prefix_root in prefixes:

        if not is_directory(prefix_root):
            continue

        prefixes_to_scan = []

        if prefix_root.name == ".wine":

            prefixes_to_scan.append(
                prefix_root
            )

        else:

            try:

                prefixes_to_scan.extend(
                    p
                    for p in prefix_root.iterdir()
                    if p.is_dir()
                )

            except OSError:

                continue

        for prefix in prefixes_to_scan:

            program_roots = [

                prefix
                / "drive_c"
                / "Program Files",

                prefix
                / "drive_c"
                / "Program Files (x86)",
            ]

            for root in program_roots:

                if not is_directory(root):
                    continue

                try:

                    children = list(
                        root.iterdir()
                    )

                except OSError:

                    continue

                for directory in children:

                    if not directory.is_dir():
                        continue

                    if is_ignored_directory(
                        directory
                    ):
                        continue

                    executables = find_executables(
                        directory,
                        max_depth=2
                    )

                    executable = choose_executable(
                        executables
                    )

                    if not executable:
                        continue

                    add_unverified_candidate(
                        results,

                        name=directory.name,

                        install_path=directory,

                        executable=executable,

                        source="Wine",
                    )


# ============================================================
# INSTALLATIONS UTILISATEUR
# ============================================================

def add_unverified_candidate(
    results,
    name,
    install_path,
    executable,
    source
):

    indicators = (
        detect_unverified_indicators(
            install_path
        )
    )

    verification = (
        "UNVERIFIED_WITH_INDICATORS"
        if indicators
        else "UNVERIFIED"
    )

    add_candidate(
        results,

        GameCandidate(
            name=name,

            source=source,

            confidence="MEDIUM",

            verification=verification,

            install_path=str(
                install_path
            ),

            executable_path=str(
                executable
            ),

            launcher_id=None,

            appid=None,

            reason=(
                "Installation locale "
                "non associée à un "
                "launcher connu"
            ),

            indicators=indicators,
        )
    )


def scan_user_libraries(results):

    print("[User Libraries] Recherche...")

    for library in USER_LIBRARY_DIRS:

        if not is_directory(library):
            continue

        try:

            children = list(
                library.iterdir()
            )

        except OSError:

            continue

        for directory in children:

            if not directory.is_dir():
                continue

            if is_ignored_directory(
                directory
            ):
                continue

            executables = find_executables(
                directory,
                max_depth=MAX_MANUAL_SCAN_DEPTH
            )

            executable = choose_executable(
                executables
            )

            if not executable:
                continue

            add_unverified_candidate(
                results,

                name=directory.name,

                install_path=directory,

                executable=executable,

                source="User Library",
            )


# ============================================================
# INSTALLATIONS LOCALES OPTIONNELLES
# ============================================================

def scan_custom_directory(
    results,
    directory
):

    directory = safe_resolve(
        Path(directory)
    )

    if not directory:
        return

    if not is_directory(directory):
        return

    print(
        f"[Custom] Recherche : {directory}"
    )

    try:

        children = list(
            directory.iterdir()
        )

    except OSError:

        return

    for child in children:

        if not child.is_dir():
            continue

        if is_ignored_directory(child):
            continue

        executables = find_executables(
            child,
            max_depth=MAX_MANUAL_SCAN_DEPTH
        )

        executable = choose_executable(
            executables
        )

        if not executable:
            continue

        add_unverified_candidate(
            results,

            name=child.name,

            install_path=child,

            executable=executable,

            source="Custom Library",
        )


# ============================================================
# Résultats
# ============================================================

def sort_results(results):

    results.sort(
        key=lambda candidate: (
            -CONFIDENCE_RANK.get(
                candidate.confidence,
                0
            ),
            candidate.source.lower(),
            candidate.name.lower(),
        )
    )

    return results


def build_output(results):

    confirmed = [
        candidate
        for candidate in results
        if candidate.confidence
        in ("TRUSTED", "HIGH")
    ]

    uncertain = [
        candidate
        for candidate in results
        if candidate.confidence
        == "MEDIUM"
    ]

    low = [
        candidate
        for candidate in results
        if candidate.confidence
        == "LOW"
    ]

    unverified = [
        candidate
        for candidate in results
        if candidate.verification.startswith(
            "UNVERIFIED"
        )
    ]

    with_indicators = [
        candidate
        for candidate in results
        if candidate.indicators
    ]

    return {

        "scanner_version": VERSION,

        "summary": {

            "confirmed": len(
                confirmed
            ),

            "uncertain": len(
                uncertain
            ),

            "low_confidence": len(
                low
            ),

            "unverified": len(
                unverified
            ),

            "with_verification_indicators": len(
                with_indicators
            ),
        },

        "games": [
            asdict(candidate)
            for candidate in confirmed
        ],

        "uncertain_candidates": [
            asdict(candidate)
            for candidate in uncertain
        ],

        "low_confidence": [
            asdict(candidate)
            for candidate in low
        ],

        "unverified_installations": [
            asdict(candidate)
            for candidate in unverified
        ],

        "verification_indicators": [
            asdict(candidate)
            for candidate in with_indicators
        ],
    }


# ============================================================
# Affichage
# ============================================================

def print_results(results):

    confirmed = [
        x for x in results
        if x.confidence
        in ("TRUSTED", "HIGH")
    ]

    uncertain = [
        x for x in results
        if x.confidence == "MEDIUM"
    ]

    unverified = [
        x for x in results
        if x.verification.startswith(
            "UNVERIFIED"
        )
    ]

    print()
    print("=" * 60)
    print("JEUX CONFIRMÉS")
    print("=" * 60)

    if not confirmed:

        print("Aucun jeu confirmé.")

    else:

        for game in confirmed:

            print()
            print(
                f"[{game.confidence}] "
                f"{game.name}"
            )

            print(
                f"  Source      : {game.source}"
            )

            print(
                f"  Installation: "
                f"{game.install_path}"
            )

            print(
                f"  Executable  : "
                f"{game.executable_path}"
            )

    print()
    print("=" * 60)
    print("CANDIDATS INCERTAINS")
    print("=" * 60)

    if not uncertain:

        print("Aucun candidat incertain.")

    else:

        for game in uncertain:

            print()
            print(
                f"[MEDIUM] {game.name}"
            )

            print(
                f"  Source : {game.source}"
            )

            print(
                f"  Installation : "
                f"{game.install_path}"
            )

            print(
                f"  Executable : "
                f"{game.executable_path}"
            )

            print(
                f"  Vérification : "
                f"{game.verification}"
            )

            if game.indicators:

                print("  Indices :")

                for indicator in game.indicators:

                    print(
                        f"    - {indicator}"
                    )

    print()
    print("=" * 60)
    print("INSTALLATIONS NON VÉRIFIÉES")
    print("=" * 60)

    if not unverified:

        print(
            "Aucune installation "
            "non vérifiée."
        )

    else:

        for game in unverified:

            print()
            print(
                f"[UNVERIFIED] "
                f"{game.name}"
            )

            print(
                f"  Source : "
                f"{game.source}"
            )

            print(
                f"  Installation : "
                f"{game.install_path}"
            )

            if game.indicators:

                print(
                    "  Indices nécessitant "
                    "une vérification :"
                )

                for indicator in game.indicators:

                    print(
                        f"    - {indicator}"
                    )


# ============================================================
# CLI
# ============================================================

def parse_arguments():

    parser = argparse.ArgumentParser(
        description=(
            "Scanner Linux de découverte "
            "de jeux"
        )
    )

    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help=(
            "Fichier JSON de sortie"
        ),
    )

    parser.add_argument(
        "--custom",
        action="append",
        default=[],
        help=(
            "Ajoute une bibliothèque "
            "personnalisée à scanner. "
            "Peut être utilisé plusieurs fois."
        ),
    )

    parser.add_argument(
        "--no-wine",
        action="store_true",
        help=(
            "Désactive le scan Wine"
        ),
    )

    parser.add_argument(
        "--no-user-libraries",
        action="store_true",
        help=(
            "Désactive ~/Games et ~/games"
        ),
    )

    return parser.parse_args()


# ============================================================
# MAIN
# ============================================================

def main():

    args = parse_arguments()

    print()
    print("=" * 60)
    print("       GAME DISCOVERY SCANNER")
    print("=" * 60)
    print()
    print(
        f"Version : {VERSION}"
    )
    print(
        "Mode : non destructif"
    )
    print(
        "Aucun executable ne sera lancé."
    )
    print()

    results = []

    # --------------------------------------------------------
    # Launchers
    # --------------------------------------------------------

    scan_steam(results)

    scan_steam_common_directories(results)

    scan_lutris(results)

    scan_heroic(results)

    scan_bottles(results)

    # --------------------------------------------------------
    # Wine
    # --------------------------------------------------------

    if not args.no_wine:

        scan_wine_prefixes(
            results
        )

    # --------------------------------------------------------
    # Bibliothèques utilisateur
    # --------------------------------------------------------

    if not args.no_user_libraries:

        scan_user_libraries(
            results
        )

    # --------------------------------------------------------
    # Bibliothèques personnalisées
    # --------------------------------------------------------

    for custom in args.custom:

        scan_custom_directory(
            results,
            custom
        )

    # --------------------------------------------------------
    # Tri
    # --------------------------------------------------------

    results = sort_results(
        results
    )

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    output = build_output(
        results
    )

    output_path = Path(
        args.output
    ).expanduser()

    try:

        output_path.write_text(
            json.dumps(
                output,
                indent=4,
                ensure_ascii=False
            ),
            encoding="utf-8"
        )

    except OSError as error:

        print(
            f"Erreur écriture JSON : "
            f"{error}"
        )

    # --------------------------------------------------------
    # Affichage
    # --------------------------------------------------------

    print_results(
        results
    )

    print()
    print("=" * 60)
    print("RÉSUMÉ")
    print("=" * 60)

    print(
        f"Total candidats : "
        f"{len(results)}"
    )

    print(
        f"Jeux confirmés : "
        f"{len(output['games'])}"
    )

    print(
        f"Candidats incertains : "
        f"{len(output['uncertain_candidates'])}"
    )

    print(
        f"Installations non vérifiées : "
        f"{len(output['unverified_installations'])}"
    )

    print(
        f"Indices à vérifier : "
        f"{len(output['verification_indicators'])}"
    )

    print()
    print(
        f"Rapport JSON : "
        f"{output_path}"
    )

    print()


if __name__ == "__main__":

    main()
