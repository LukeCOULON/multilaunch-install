#!/usr/bin/env python3
"""Graphical interface for the local MultiLaunch catalogue."""

from __future__ import annotations

import json
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

import launcher


APP_NAME = "MultiLaunch"
APP_SUBTITLE = "Launcher de jeux Linux · Wine · Proton"
APP_AUTHOR = "Créé par Luke Coulon"
BG_COLOR = "#0b1220"
PANEL_COLOR = "#141e2d"
FIELD_COLOR = "#1d2a3b"
TEXT_COLOR = "#edf4fb"
MUTED_COLOR = "#8ea2b8"
ACCENT_COLOR = "#38bdf8"
SUCCESS_COLOR = "#4ade80"
WARNING_COLOR = "#fbbf24"


class LauncherWindow(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME} — {APP_SUBTITLE}")
        self.geometry("1080x680")
        self.minsize(900, 560)
        self.selected_id: str | None = None
        self.games: list[launcher.Game] = []
        self.detected_candidates: list[launcher.DetectedCandidate] = []
        self.scan_window: tk.Toplevel | None = None
        self.scan_cancelled = False
        self._resize_pending = False
        self._configure_style()
        self._build_ui()
        self.bind("<Configure>", self._on_resize)
        self.refresh_games()
        self.after(350, self.show_release_notes)

    def _configure_style(self) -> None:
        self.configure(bg=BG_COLOR)
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("App.TFrame", background=BG_COLOR)
        style.configure("Panel.TFrame", background=PANEL_COLOR)
        style.configure("Brand.TLabel", background=BG_COLOR, foreground=TEXT_COLOR, font=("DejaVu Sans", 24, "bold"))
        style.configure("Subtitle.TLabel", background=BG_COLOR, foreground=ACCENT_COLOR, font=("DejaVu Sans", 10))
        style.configure("Title.TLabel", background=BG_COLOR, foreground=TEXT_COLOR, font=("DejaVu Sans", 22, "bold"))
        style.configure("SelectedTitle.TLabel", background=PANEL_COLOR, foreground=ACCENT_COLOR, font=("DejaVu Sans", 22, "bold"))
        style.configure("Muted.TLabel", background=BG_COLOR, foreground=MUTED_COLOR, font=("DejaVu Sans", 10))
        style.configure("Panel.TLabel", background=PANEL_COLOR, foreground=TEXT_COLOR, font=("DejaVu Sans", 10))
        style.configure("Field.TLabel", background=PANEL_COLOR, foreground=MUTED_COLOR, font=("DejaVu Sans", 9))
        style.configure("Accent.TButton", background=ACCENT_COLOR, foreground="#07111f", padding=(14, 8), borderwidth=0, font=("DejaVu Sans", 9, "bold"))
        style.map("Accent.TButton", background=[("active", "#7dd3fc")])
        style.configure("Danger.TButton", background="#3a2029", foreground="#fda4af", padding=(10, 7), borderwidth=0)
        style.map("Danger.TButton", background=[("active", "#542532")])
        style.configure("TButton", padding=(10, 7), background="#243247", foreground=TEXT_COLOR, borderwidth=0)
        style.map("TButton", background=[("active", "#33445d")])
        style.configure("TEntry", fieldbackground=FIELD_COLOR, foreground=TEXT_COLOR, insertcolor="white", borderwidth=0, padding=8)
        style.configure("TCombobox", fieldbackground=FIELD_COLOR, foreground=TEXT_COLOR, padding=7)
        style.configure("Treeview", background=PANEL_COLOR, fieldbackground=PANEL_COLOR, foreground=TEXT_COLOR, rowheight=42, borderwidth=0, font=("DejaVu Sans", 10))
        style.configure("Treeview.Heading", background=FIELD_COLOR, foreground=MUTED_COLOR, relief="flat", padding=10, font=("DejaVu Sans", 9, "bold"))
        style.map("Treeview", background=[("selected", "#164e63")], foreground=[("selected", "white")])

    def _build_ui(self) -> None:
        root = ttk.Frame(self, style="App.TFrame", padding=24)
        root.pack(fill="both", expand=True)
        header = ttk.Frame(root, style="App.TFrame")
        header.pack(fill="x", pady=(0, 18))
        brand = ttk.Frame(header, style="App.TFrame")
        brand.pack(side="left")
        ttk.Label(brand, text=APP_NAME, style="Brand.TLabel").pack(anchor="w")
        ttk.Label(brand, text=APP_SUBTITLE, style="Subtitle.TLabel").pack(anchor="w", pady=(1, 0))
        ttk.Label(header, text=f"Catalogue local · {launcher.GAMES_FILE}", style="Muted.TLabel").pack(side="left", padx=20, pady=(22, 0))
        self.stats_var = tk.StringVar(value="0 jeu")
        ttk.Label(header, textvariable=self.stats_var, style="Muted.TLabel").pack(side="right", padx=14, pady=(9, 0))
        toolbar = ttk.Frame(root, style="App.TFrame")
        toolbar.pack(fill="x", pady=(0, 14))
        ttk.Button(toolbar, text="+ Ajouter un jeu", style="Accent.TButton", command=self.add_game).pack(side="left")
        ttk.Button(toolbar, text="Détecter", command=self.detect_games).pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="Chercher dans un dossier", command=self.search_folder).pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="Mises à jour", command=self.check_updates).pack(side="right")
        ttk.Button(toolbar, text="Vider la liste", command=self.clear_games).pack(side="right", padx=(0, 8))
        ttk.Separator(root, orient="horizontal").pack(fill="x", pady=(0, 18))

        content = ttk.Panedwindow(root, orient="horizontal")
        content.pack(fill="both", expand=True)
        library = ttk.Frame(content, style="Panel.TFrame", padding=12)
        details = ttk.Frame(content, style="Panel.TFrame", padding=20)
        content.add(library, weight=4)
        content.add(details, weight=5)

        search_row = ttk.Frame(library, style="Panel.TFrame")
        search_row.pack(fill="x", pady=(0, 10))
        ttk.Label(search_row, text="BIBLIOTHÈQUE", style="Field.TLabel").pack(side="left", padx=(2, 12))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh_games())
        ttk.Entry(search_row, textvariable=self.search_var).pack(side="left", fill="x", expand=True)
        ttk.Button(search_row, text="Actualiser", command=self.refresh_games).pack(side="right", padx=(8, 0))
        tree_frame = ttk.Frame(library, style="Panel.TFrame")
        tree_frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(tree_frame, columns=("name", "platform", "backend", "state"), show="headings", selectmode="browse")
        self.tree.heading("name", text="Jeu")
        self.tree.heading("platform", text="Plateforme")
        self.tree.heading("backend", text="Backend")
        self.tree.heading("state", text="État")
        self.tree.column("name", width=270, anchor="w")
        self.tree.column("platform", width=90, anchor="center")
        self.tree.column("backend", width=90, anchor="center")
        self.tree.column("state", width=130, anchor="center")
        self.tree.tag_configure("game", font=("DejaVu Sans", 11, "bold"))
        self.tree.tag_configure("verified", foreground=SUCCESS_COLOR)
        self.tree.tag_configure("warning", foreground=WARNING_COLOR)
        self.tree.tag_configure("disabled", foreground="#718096")
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        self.tree.bind("<Button-3>", self.show_context_menu)
        self.tree.bind("<Delete>", lambda _: self.delete_current())
        self.tree.bind("<F2>", lambda _: self.rename_current())
        self.tree.bind("<Double-1>", lambda _: self.rename_current())

        ttk.Label(details, text="Configuration du jeu", style="Panel.TLabel", font=("DejaVu Sans", 10)).pack(anchor="w")
        self.selected_title_var = tk.StringVar(value="Aucun jeu sélectionné")
        ttk.Label(details, textvariable=self.selected_title_var, style="SelectedTitle.TLabel").pack(anchor="w", pady=(2, 16))
        self.name_var = tk.StringVar()
        self.backend_var = tk.StringVar(value="auto")
        self.prefix_var = tk.StringVar()
        self.workdir_var = tk.StringVar()
        self.executable_var = tk.StringVar()
        self._field(details, "Nom", self.name_var)
        self._field(details, "Exécutable", self.executable_var, readonly=True)
        backend_row = ttk.Frame(details, style="Panel.TFrame")
        backend_row.pack(fill="x", pady=6)
        ttk.Label(backend_row, text="Backend", style="Field.TLabel", width=16).pack(side="left")
        ttk.Combobox(backend_row, textvariable=self.backend_var, values=("auto", "native", "wine", "proton"), state="readonly", width=18).pack(side="left", fill="x", expand=True)
        self._field(details, "Prefix Wine", self.prefix_var, browse="directory")
        self._field(details, "Répertoire de travail", self.workdir_var, browse="directory")
        ttk.Label(details, text="Arguments (un par ligne)", style="Field.TLabel").pack(anchor="w", pady=(14, 4))
        self.arguments_text = tk.Text(details, height=4, bg=FIELD_COLOR, fg=TEXT_COLOR, insertbackground="white", relief="flat", padx=8, pady=7)
        self.arguments_text.pack(fill="x")
        ttk.Label(details, text="Variables d’environnement (KEY=VALUE, une par ligne)", style="Field.TLabel").pack(anchor="w", pady=(12, 4))
        self.environment_text = tk.Text(details, height=4, bg=FIELD_COLOR, fg=TEXT_COLOR, insertbackground="white", relief="flat", padx=8, pady=7)
        self.environment_text.pack(fill="x")

        actions = ttk.Frame(details, style="Panel.TFrame")
        actions.pack(fill="x", pady=(18, 0))
        self.action_buttons = [
            ttk.Button(actions, text="Enregistrer", style="Accent.TButton", command=self.save_current),
            ttk.Button(actions, text="Lancer", command=self.launch_current),
            ttk.Button(actions, text="Diagnostiquer", command=self.diagnose_current),
            ttk.Button(actions, text="Ouvrir le dossier", command=self.open_game_folder),
            ttk.Button(actions, text="Ouvrir les logs", command=self.open_logs),
            ttk.Button(actions, text="Supprimer", style="Danger.TButton", command=self.delete_current),
        ]
        for index, button in enumerate(self.action_buttons):
            button.grid(row=0, column=index, padx=(0, 8) if index < len(self.action_buttons) - 1 else 0, pady=(0, 6), sticky="ew")
            actions.columnconfigure(index, weight=1)

        self.status_var = tk.StringVar(value="Prêt")
        status = ttk.Label(root, textvariable=self.status_var, style="Muted.TLabel", anchor="w")
        status.pack(fill="x", pady=(14, 0))
        footer = ttk.Frame(root, style="App.TFrame")
        footer.pack(fill="x", pady=(6, 0))
        ttk.Label(footer, text=APP_AUTHOR, style="Muted.TLabel").pack(side="left")
        ttk.Label(footer, text="MultiLaunch · gestion locale des jeux", style="Muted.TLabel").pack(side="right")

    def _on_resize(self, _: tk.Event[tk.Misc]) -> None:
        if self._resize_pending:
            return
        self._resize_pending = True
        self.after_idle(self._apply_responsive_layout)

    def _apply_responsive_layout(self) -> None:
        self._resize_pending = False
        width = self.winfo_width()
        tree_width = max(360, self.tree.winfo_width() - 18) if hasattr(self, "tree") else 700
        name_width = max(150, int(tree_width * 0.48))
        state_width = max(90, int(tree_width * 0.18))
        platform_width = max(70, int(tree_width * 0.16))
        backend_width = max(70, tree_width - name_width - state_width - platform_width)
        if hasattr(self, "tree"):
            self.tree.column("name", width=name_width)
            self.tree.column("platform", width=platform_width)
            self.tree.column("backend", width=backend_width)
            self.tree.column("state", width=state_width)
        if hasattr(self, "action_buttons"):
            for button in self.action_buttons:
                button.grid_forget()
            columns = 3 if width < 1050 else len(self.action_buttons)
            for index, button in enumerate(self.action_buttons):
                row, column = divmod(index, columns)
                button.grid(row=row, column=column, padx=(0, 8), pady=(0, 6), sticky="ew")

    def _field(self, parent: ttk.Frame, label: str, variable: tk.StringVar, readonly: bool = False,
               browse: str | None = None) -> None:
        row = ttk.Frame(parent, style="Panel.TFrame")
        row.pack(fill="x", pady=6)
        ttk.Label(row, text=label, style="Field.TLabel", width=20).pack(side="left")
        entry = ttk.Entry(row, textvariable=variable)
        entry.pack(side="left", fill="x", expand=True)
        if readonly:
            entry.configure(state="readonly")
        if browse:
            ttk.Button(row, text="Choisir", command=lambda: self.choose_directory(variable)).pack(side="right", padx=(8, 0))

    def refresh_games(self) -> None:
        try:
            self.games = launcher.load_games()
        except RuntimeError as error:
            self.status_var.set(str(error))
            return
        query = self.search_var.get().casefold()
        for item in self.tree.get_children():
            self.tree.delete(item)
        for game in self.games:
            if query and query not in f"{game.name} {game.id} {game.executable}".casefold():
                continue
            state = "Désactivé" if not game.enabled else resolve_status(game)
            state_tag = "disabled" if not game.enabled else "warning" if state == "À vérifier" else "verified"
            self.tree.insert("", "end", iid=game.id, values=(game.name, game.platform, launcher.resolve_backend(game), state), tags=("game", state_tag))
        enabled = sum(game.enabled for game in self.games)
        wine_games = sum(launcher.resolve_backend(game) in {"wine", "proton"} for game in self.games)
        self.stats_var.set(f"{len(self.games)} jeu(x) · {enabled} actif(s) · {wine_games} Windows")

    def show_release_notes(self) -> None:
        try:
            if not launcher.should_show_updates():
                return
            updates = launcher.read_update_file()
            items = "\n".join(f"• {item}" for item in updates["items"])
            messagebox.showinfo(updates.get("title", "Nouveautés"), f"Version {updates['version']}\n\n{items}")
            launcher.mark_updates_seen()
        except RuntimeError as error:
            self.status_var.set(str(error))

    def check_updates(self) -> None:
        self.status_var.set("Vérification de la version GitHub...")
        threading.Thread(target=self._check_updates_worker, daemon=True).start()

    def _check_updates_worker(self) -> None:
        try:
            result = launcher.check_for_update()
            self.after(0, lambda: self._show_update_result(result))
        except RuntimeError as error:
            self.after(0, lambda: messagebox.showwarning("Mise à jour", str(error)))
            self.after(0, lambda: self.status_var.set("Vérification GitHub indisponible"))

    def _show_update_result(self, result: dict[str, object]) -> None:
        current = result["current"]["version"]
        remote = result["remote"]["version"]
        if not result["update_available"]:
            self.status_var.set(f"MultiLaunch est à jour ({current})")
            messagebox.showinfo("Mise à jour", f"MultiLaunch est à jour.\nVersion actuelle : {current}")
            return
        remote_data = result["remote"]
        notes = remote_data.get("release_notes", "") if isinstance(remote_data, dict) else ""
        message = f"Une nouvelle version est disponible : {current} -> {remote}"
        if notes:
            message += f"\n\n{notes}"
        if messagebox.askyesno("Mise à jour disponible", message + "\n\nInstaller maintenant ?"):
            self.status_var.set(f"Installation de la version {remote}...")
            threading.Thread(target=self._install_update_worker, args=(remote_data,), daemon=True).start()

    def _install_update_worker(self, remote: dict[str, object]) -> None:
        try:
            backup = launcher.install_update(remote)
            self.after(0, lambda: self.status_var.set(f"Mise à jour installée · sauvegarde : {backup.name}"))
            self.after(0, lambda: messagebox.showinfo("Mise à jour", "Mise à jour installée. Redémarre MultiLaunch pour l'utiliser."))
        except RuntimeError as error:
            self.after(0, lambda: messagebox.showerror("Mise à jour impossible", str(error)))

    def on_select(self, _: tk.Event[tk.Misc]) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        self.selected_id = selection[0]
        game = next((item for item in self.games if item.id == self.selected_id), None)
        if game:
            self.selected_title_var.set(game.name)
            self.name_var.set(game.name)
            self.executable_var.set(game.executable)
            self.backend_var.set(game.backend)
            self.prefix_var.set(game.prefix or "")
            self.workdir_var.set(game.working_directory or "")
            self._replace_text(self.arguments_text, "\n".join(game.arguments))
            self._replace_text(self.environment_text, "\n".join(f"{key}={value}" for key, value in game.environment.items()))

    def show_context_menu(self, event: tk.Event[tk.Misc]) -> None:
        row = self.tree.identify_row(event.y)
        if not row:
            return
        self.tree.selection_set(row)
        self.tree.focus(row)
        menu = tk.Menu(self, tearoff=False, bg="#202a36", fg="#f2f5f8", activebackground="#245493", activeforeground="white")
        menu.add_command(label="Renommer", command=self.rename_current)
        menu.add_separator()
        menu.add_command(label="Supprimer du catalogue", command=self.delete_current)
        menu.tk_popup(event.x_root, event.y_root)

    @staticmethod
    def _replace_text(widget: tk.Text, value: str) -> None:
        widget.delete("1.0", "end")
        widget.insert("1.0", value)

    def choose_directory(self, variable: tk.StringVar) -> None:
        directory = filedialog.askdirectory(title="Choisir un dossier")
        if directory:
            variable.set(directory)

    def detect_games(self) -> None:
        self.start_scan_popup("Analyse automatique des jeux")
        threading.Thread(target=self._run_detection, daemon=True).start()

    def _run_detection(self) -> None:
        candidates = launcher.discover_candidates(progress_callback=self._scan_progress)
        self.after(0, lambda: self.finish_scan(candidates))

    def search_folder(self) -> None:
        folder = filedialog.askdirectory(title="Choisir le dossier à analyser")
        if not folder:
            return
        selected_folder = Path(folder).expanduser().resolve()
        self.start_scan_popup("Recherche approfondie", selected_folder)
        threading.Thread(target=self._run_folder_search, args=(selected_folder,), daemon=True).start()

    def _run_folder_search(self, folder: Path) -> None:
        candidates = launcher.discover_candidates([folder], max_files=20000, recursive=True,
                                                  progress_callback=self._scan_progress)
        self.after(0, lambda: self.finish_scan(candidates))

    def start_scan_popup(self, title: str, folder: Path | None = None) -> None:
        self.scan_cancelled = False
        self.scan_window = tk.Toplevel(self)
        self.scan_window.title(title)
        self.scan_window.geometry("520x190")
        self.scan_window.resizable(False, False)
        self.scan_window.configure(bg="#10151c")
        ttk.Label(self.scan_window, text=title, style="Title.TLabel").pack(anchor="w", padx=22, pady=(20, 4))
        self.scan_path_var = tk.StringVar(value=str(folder) if folder else "Préparation des emplacements connus...")
        self.scan_file_var = tk.StringVar(value="Initialisation du scan...")
        self.scan_count_var = tk.StringVar(value="0 fichier inspecté")
        ttk.Label(self.scan_window, textvariable=self.scan_path_var, style="Muted.TLabel").pack(anchor="w", padx=22)
        ttk.Label(self.scan_window, textvariable=self.scan_file_var, style="Muted.TLabel").pack(anchor="w", padx=22, pady=(6, 0))
        self.scan_progress = ttk.Progressbar(self.scan_window, mode="indeterminate")
        self.scan_progress.pack(fill="x", padx=22, pady=(12, 4))
        self.scan_progress.start(12)
        ttk.Label(self.scan_window, textvariable=self.scan_count_var, style="Muted.TLabel").pack(anchor="w", padx=22)
        ttk.Button(self.scan_window, text="Annuler", command=self.cancel_scan).pack(anchor="e", padx=22, pady=(8, 14))
        self.scan_window.protocol("WM_DELETE_WINDOW", self.cancel_scan)

    def _scan_progress(self, root: str, current: int, maximum: int) -> bool:
        if self.scan_cancelled:
            return False
        self.after(0, lambda: self.update_scan_popup(root, current, maximum))
        return True

    def update_scan_popup(self, root: str, current: int, maximum: int) -> None:
        if not self.scan_window or not self.scan_window.winfo_exists():
            return
        self.scan_path_var.set(f"Dossier : {root}")
        self.scan_file_var.set("Recherche des exécutables et fichiers associés...")
        self.scan_count_var.set(f"{current} fichier(s) inspecté(s)")
        self.scan_progress.configure(maximum=max(maximum, 1), value=current)

    def cancel_scan(self) -> None:
        self.scan_cancelled = True
        self.status_var.set("Annulation du scan en cours...")

    def finish_scan(self, candidates: list[launcher.DetectedCandidate]) -> None:
        if self.scan_window and self.scan_window.winfo_exists():
            self.scan_progress.stop()
            self.scan_window.destroy()
        self.scan_window = None
        self.status_var.set(f"Scan terminé : {len(candidates)} candidat(s)")
        self.show_detected_candidates(candidates)

    def show_detected_candidates(self, candidates: list[launcher.DetectedCandidate]) -> None:
        if not candidates:
            self.status_var.set("Aucun nouveau candidat détecté")
            messagebox.showinfo("Détection automatique", "Aucun jeu fiable n’a été trouvé dans les métadonnées ou la bibliothèque autorisée.")
            return
        self.detected_candidates = candidates
        window = tk.Toplevel(self)
        window.title("Jeux détectés")
        window.geometry("860x500")
        window.configure(bg="#10151c")
        trusted_count = sum(candidate.confidence in {"TRUSTED", "HIGH"} for candidate in candidates)
        uncertain_count = len(candidates) - trusted_count
        ttk.Label(window, text="Jeux détectés", style="Title.TLabel").pack(anchor="w", padx=20, pady=(18, 4))
        ttk.Label(window, text=f"{trusted_count} fiable(s) · {uncertain_count} à vérifier", style="Muted.TLabel").pack(anchor="w", padx=20, pady=(0, 8))
        include_uncertain = tk.BooleanVar(value=False)
        uncertain_toggle = ttk.Checkbutton(
            window,
            text="Afficher aussi MEDIUM / LOW / non vérifiées (crack, loader, etc.)",
            variable=include_uncertain,
        )
        uncertain_toggle.pack(anchor="w", padx=20, pady=(0, 10))
        frame = ttk.Frame(window, style="Panel.TFrame", padding=10)
        frame.pack(fill="both", expand=True, padx=20)
        listbox = tk.Listbox(frame, selectmode="extended", bg="#202a36", fg="#f2f5f8", selectbackground="#245493",
                             relief="flat", highlightthickness=0)
        listbox.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=listbox.yview)
        scroll.pack(side="right", fill="y")
        listbox.configure(yscrollcommand=scroll.set)

        displayed_candidates: list[launcher.DetectedCandidate] = []
        show_all = tk.BooleanVar(value=False)
        all_toggle = ttk.Checkbutton(
            window,
            text="Afficher toutes les découvertes du scanner (LOW / REJECTED inclus)",
            variable=show_all,
        )
        all_toggle.pack(anchor="w", padx=20, pady=(0, 10))

        def refresh_results() -> None:
            displayed_candidates.clear()
            displayed_candidates.extend(
                candidate for candidate in candidates
                if show_all.get()
                or include_uncertain.get() and (
                    candidate.confidence in {"TRUSTED", "HIGH", "MEDIUM", "LOW"}
                    or candidate.verification.startswith("UNVERIFIED")
                )
                or candidate.confidence in {"TRUSTED", "HIGH"}
            )
            listbox.delete(0, "end")
            for candidate in displayed_candidates:
                evidence = ", ".join(candidate.evidence + candidate.indicators)
                identity = f" · AppID {candidate.appid}" if candidate.appid else ""
                listbox.insert(
                    "end",
                    f"[{candidate.confidence} · {candidate.verification}] {candidate.name} · "
                    f"{candidate.source}{identity} · {candidate.reason or evidence} · {candidate.executable}",
                )
            if displayed_candidates:
                listbox.selection_set(0, "end")

        uncertain_toggle.configure(command=refresh_results)
        all_toggle.configure(command=refresh_results)
        refresh_results()
        buttons = ttk.Frame(window, style="App.TFrame")
        buttons.pack(fill="x", padx=20, pady=16)
        ttk.Button(buttons, text="Annuler", command=window.destroy).pack(side="right")
        ttk.Button(buttons, text="Importer la sélection", style="Accent.TButton",
                   command=lambda: self.import_detected(window, listbox, displayed_candidates)).pack(side="right", padx=8)

    def import_detected(self, window: tk.Toplevel, listbox: tk.Listbox, candidates: list[launcher.DetectedCandidate]) -> None:
        imported = 0
        for index in listbox.curselection():
            try:
                launcher.import_candidate(candidates[index])
                imported += 1
            except ValueError:
                pass
        window.destroy()
        self.status_var.set(f"{imported} jeu(x) importé(s)")

    def add_game(self) -> None:
        path = filedialog.askopenfilename(title="Choisir l'exécutable du jeu")
        if not path:
            return
        try:
            platform = launcher.detect_platform(Path(path))
            game = launcher.Game(id=f"game-{launcher.uuid.uuid4().hex[:12]}", name=Path(path).stem,
                                 executable=str(Path(path).resolve()), platform=platform,
                                 created_at=launcher.dt.datetime.now().astimezone().isoformat())
            games = launcher.load_games()
            games.append(game)
            launcher.save_games(games)
            self.status_var.set(f"Jeu ajouté : {game.name}")
            self.refresh_games()
            self.tree.selection_set(game.id)
            self.tree.focus(game.id)
            self.on_select(None)  # type: ignore[arg-type]
        except (OSError, ValueError, RuntimeError) as error:
            messagebox.showerror("Ajout impossible", str(error))

    def save_current(self) -> None:
        if not self.selected_id:
            messagebox.showinfo("Aucun jeu", "Sélectionnez un jeu dans la bibliothèque.")
            return
        try:
            game = launcher.find_game(self.selected_id)
            game.name = self.name_var.get().strip() or game.name
            game.backend = self.backend_var.get()
            game.prefix = self.prefix_var.get().strip() or None
            game.working_directory = self.workdir_var.get().strip() or None
            game.arguments = self.arguments_text.get("1.0", "end").splitlines()
            game.environment = launcher.parse_environment(self.environment_text.get("1.0", "end").splitlines())
            launcher.save_game(game)
            self.selected_title_var.set(game.name)
            self.status_var.set(f"Configuration enregistrée : {game.name}")
            self.refresh_games()
        except (KeyError, ValueError, OSError, RuntimeError) as error:
            messagebox.showerror("Enregistrement impossible", str(error))

    def rename_current(self) -> None:
        if not self.selected_id:
            return
        try:
            game = launcher.find_game(self.selected_id)
            new_name = simpledialog.askstring("Renommer le jeu", "Nouveau nom :", initialvalue=game.name, parent=self)
            if new_name is None:
                return
            new_name = new_name.strip()
            if not new_name:
                messagebox.showwarning("Nom invalide", "Le nom ne peut pas être vide.")
                return
            game.name = new_name
            launcher.save_game(game)
            self.selected_title_var.set(new_name)
            self.status_var.set(f"Jeu renommé : {new_name}")
            self.refresh_games()
            self.tree.selection_set(game.id)
        except (KeyError, OSError, RuntimeError) as error:
            messagebox.showerror("Renommage impossible", str(error))

    def launch_current(self) -> None:
        if not self.selected_id:
            return
        try:
            game = launcher.find_game(self.selected_id)
            if game.confidence in {"MEDIUM", "LOW"} or game.verification.startswith("UNVERIFIED"):
                messagebox.showwarning(
                    "Jeu non vérifié",
                    "Cette découverte doit être vérifiée et sa configuration confirmée avant le lancement.",
                )
                return
            prepared = launcher.prepare_launch(game)
        except (KeyError, ValueError, OSError, RuntimeError) as error:
            messagebox.showerror("Lancement impossible", str(error))
            return
        self.status_var.set(f"Lancement de {game.name}...")
        threading.Thread(target=self._run_process, args=(game, prepared), daemon=True).start()

    def _run_process(self, game: launcher.Game, prepared: launcher.PreparedLaunch) -> None:
        try:
            result = subprocess.run(prepared.argv, cwd=prepared.working_directory, env=prepared.environment,
                                   capture_output=True, text=True, check=False)
            game.last_launched_at = launcher.dt.datetime.now().astimezone().isoformat()
            game.launch_count += 1
            launcher.save_game(game)
            log_path = launcher.write_log(game, prepared, result)
            self.after(0, lambda: self.status_var.set(f"{game.name} terminé avec le code {result.returncode} · {log_path.name}"))
            self.after(0, self.refresh_games)
        except (OSError, RuntimeError) as error:
            self.after(0, lambda: messagebox.showerror("Erreur de lancement", str(error)))

    def diagnose_current(self) -> None:
        if not self.selected_id:
            return
        try:
            game = launcher.find_game(self.selected_id)
            executable = Path(game.executable).expanduser()
            backend = launcher.resolve_backend(game)
            checks = {
                "Exécutable": executable.is_file(),
                "Répertoire": Path(game.working_directory or executable.parent).is_dir(),
                "Backend": backend,
                "Runtime": "native" if backend == "native" else launcher.find_runtime(game.runtime, backend),
                "Prefix": not game.prefix or Path(game.prefix).expanduser().exists(),
            }
            messagebox.showinfo("Diagnostic", json.dumps(checks, indent=2, ensure_ascii=False))
        except (KeyError, OSError, RuntimeError) as error:
            messagebox.showerror("Diagnostic impossible", str(error))

    def open_game_folder(self) -> None:
        if not self.selected_id:
            return
        try:
            game = launcher.find_game(self.selected_id)
            folder = Path(game.working_directory or game.executable).expanduser().resolve()
            if folder.is_file():
                folder = folder.parent
            subprocess.Popen(["xdg-open", str(folder)])
            self.status_var.set(f"Dossier ouvert : {folder}")
        except (KeyError, OSError) as error:
            messagebox.showerror("Ouverture impossible", str(error))

    def open_logs(self) -> None:
        if not self.selected_id:
            return
        log_folder = launcher.LOG_DIR / self.selected_id
        log_folder.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.Popen(["xdg-open", str(log_folder)])
            self.status_var.set(f"Logs ouverts : {log_folder}")
        except OSError as error:
            messagebox.showerror("Ouverture impossible", str(error))

    def delete_current(self) -> None:
        if not self.selected_id:
            return
        game = launcher.find_game(self.selected_id)
        if not messagebox.askyesno("Supprimer le jeu", f"Supprimer « {game.name} » du catalogue ?"):
            return
        launcher.save_games([item for item in launcher.load_games() if item.id != game.id])
        self.selected_id = None
        self.status_var.set(f"Jeu supprimé : {game.name}")
        self.refresh_games()

    def clear_games(self) -> None:
        if not self.games:
            self.status_var.set("La bibliothèque est déjà vide")
            return
        if not messagebox.askyesno(
            "Vider la bibliothèque",
            f"Supprimer les {len(self.games)} jeux du catalogue ?\n\nLes fichiers installés seront conservés.",
        ):
            return
        launcher.save_games([])
        self.selected_id = None
        self.selected_title_var.set("Aucun jeu sélectionné")
        self.status_var.set("Bibliothèque vidée")
        self.refresh_games()


def resolve_status(game: launcher.Game) -> str:
    if game.confidence == "MEDIUM" or game.verification.startswith("UNVERIFIED"):
        return "À vérifier"
    return f"{game.launch_count} lancement(s)" if game.launch_count else "Jamais lancé"


if __name__ == "__main__":
    LauncherWindow().mainloop()