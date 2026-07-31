#!/usr/bin/env python3
"""TerminalHacker desktop GUI — computer-style interface for the simulator."""

from __future__ import annotations

import os
from datetime import datetime
import tkinter as tk
from tkinter import font as tkfont
from tkinter import scrolledtext

import sounds
from main import (
    NOTES_PATH,
    SHOP_CATALOG,
    Console,
    Game,
    MailMessage,
    Shop,
    TUTORIAL_CURRICULUM,
    defense_firewall_help,
)
from chaos_system import ChaosCareerManager, NotorietyManager, MeltdownManager, ChaosNewsManager
from progression import ACHIEVEMENTS, RANKS, ReputationSystem, SaveManager
from retention import SEASON_TIERS, RetentionManager

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------

# Ubuntu Yaru dark + GNOME Terminal palette
COLORS = {
    "desktop": "#241f31",
    "taskbar": "#1e1e1e",
    "window": "#303030",
    "window_header": "#303030",
    "border": "#4d4d4d",
    "text": "#ffffff",
    "accent": "#E95420",
    "accent_dim": "#c34113",
    "aubergine": "#77216F",
    "muted": "#babdb4",
    "terminal_bg": "#300A24",
    "terminal_fg": "#ffffff",
    "prompt_user": "#8AE234",
    "prompt_path": "#729FCF",
    "prompt_sym": "#ffffff",
    "info": "#729FCF",
    "success": "#8AE234",
    "warn": "#FCAF3E",
    "error": "#EF2929",
    "teach": "#AD7FA8",
    "selection": "#E95420",
}

# Text scale — set TERMINALHACKER_UI_SCALE=2.0 in env for even larger UI
UI_SCALE = float(os.environ.get("TERMINALHACKER_UI_SCALE", "1.55"))
DOCK_WIDTH = 58

# Dock apps locked during tutorial — visible previews of career endgame.
DOCK_CAREER_LOCKED: frozenset[str] = frozenset({"jobs", "board", "botnet"})

WINDOW_SIZES: dict[str, tuple[int, int]] = {
    "training": (680, 520),
    "terminal": (820, 560),
    "notes": (440, 520),
    "files": (520, 480),
    "mail": (640, 500),
    "jobs": (660, 500),
    "board": (620, 480),
    "shop": (560, 480),
    "botnet": (520, 460),
    "achieve": (560, 440),
    "status": (480, 360),
}

WINDOW_STAGGER: dict[str, tuple[int, int]] = {
    "terminal": (48, 36),
    "notes": (36, 48),
    "files": (72, 52),
    "training": (56, 40),
    "mail": (64, 44),
}

# Quick-launch buttons appear only after the player types each command once.
TERMINAL_QUICK_COMMANDS: tuple[tuple[str, str], ...] = (
    ("hint", "hint"),
    ("probe", "probe"),
    ("crack", "crack"),
    ("ls", "ls"),
    ("download", "download"),
    ("disconnect", "disconnect"),
    ("help", "help"),
)


def _fs(size: int) -> int:
    return max(10, int(round(size * UI_SCALE)))


def F(size: int, *, bold: bool = False) -> tuple[str, int] | tuple[str, int, str]:
    # DejaVu ships on Ubuntu; Tk accepts one family per font tuple.
    base: tuple[str, int] | tuple[str, int, str] = ("DejaVu Sans", _fs(size))
    return (*base, "bold") if bold else base


def MONO(size: int, *, bold: bool = False) -> tuple[str, int] | tuple[str, int, str]:
    base: tuple[str, int] | tuple[str, int, str] = ("DejaVu Sans Mono", _fs(size))
    return (*base, "bold") if bold else base


class DesktopApp:
    """Simulated hacker workstation desktop."""

    ANIM_MS = 14
    ANIM_STEPS = 12

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("TerminalHacker — Ubuntu 24.04 LTS")
        self.root.minsize(1024, 720)
        self.root.tk.call("tk", "scaling", UI_SCALE)
        self.root.configure(bg=COLORS["desktop"])
        try:
            self.root.state("zoomed")
        except tk.TclError:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            self.root.geometry(f"{sw}x{sh}+0+0")

        self.game = Game()
        self.game.gui_mode = True
        self.game.player._game_ref = self.game
        Console.fast_mode = True
        self.game.mail.on_new_mail = self._on_new_mail

        self._install_global_console_handler()

        self.open_windows: dict[str, object] = {}
        self.terminal_booted = False
        self.mail_badge: tk.Label | None = None
        self._mail_listbox: tk.Listbox | None = None
        self._mail_viewer: scrolledtext.ScrolledText | None = None
        self._mail_meta: tk.Label | None = None
        self._mail_folder: str = "inbox"
        self._mail_header: tk.Label | None = None
        self._mail_btn_row: tk.Frame | None = None
        self._mail_inbox_btn: tk.Button | None = None
        self._mail_trash_btn: tk.Button | None = None
        self.taskbar_label: tk.Label | None = None
        self.clock_label: tk.Label | None = None
        self.desktop_canvas: tk.Canvas | None = None
        self.dock_frame: tk.Frame | None = None
        self._dock_icons: dict[str, tk.Label] = {}
        self._dock_dots: dict[str, tk.Label] = {}
        self._dock_indicators: dict[str, tk.Frame] = {}
        self._active_app: str | None = None
        self.desktop_view: tk.Canvas | None = None
        self._built_panels: set[str] = set()
        self.hint_label: tk.Label | None = None
        self.onboarding_banner: tk.Frame | None = None
        self._banner_place_id: int | None = None
        self._terminal_entry: tk.Entry | None = None
        self._terminal_input: tk.Text | None = None
        self._terminal_input_frame: tk.Frame | None = None
        self._terminal_focus_job: str | None = None
        self._terminal_key_catcher: str | None = None
        self._terminal_key_catcher_active = False
        self._terminal_run_cmd: object | None = None
        self._terminal_submit_cmd: object | None = None
        self._terminal_prompt_frame: tk.Frame | None = None
        self._terminal_title_lbl: tk.Label | None = None
        self._files_list_frame: tk.Frame | None = None
        self._files_preview_frame: tk.Frame | None = None
        self._notes_editor: scrolledtext.ScrolledText | None = None
        self._notes_save_job: str | None = None
        self._botnet_text: scrolledtext.ScrolledText | None = None
        self._botnet_map_canvas: tk.Canvas | None = None
        self._terminal_history: list[str] = []
        self._terminal_history_pos: int = 0
        self._terminal_log: list[tuple[str, str]] = []
        self._terminal_output_widget: scrolledtext.ScrolledText | None = None
        self._terminal_toolbar: tk.Frame | None = None
        self._terminal_toolbar_label: tk.Label | None = None
        self._terminal_quick_buttons: dict[str, tk.Button] = {}
        self._terminal_used_commands: set[str] = set()
        self._taskbar_refresh_job: str | None = None
        self._save_loaded = False
        self._save_restore_notice: str = ""

        self._try_resume_save()
        self._build_top_panel()
        self._build_desktop()
        self._tick_clock()
        self._run_onboarding()
        self.root.protocol("WM_DELETE_WINDOW", self._on_quit)
        self.root.bind_all("<Escape>", self._unmaximize_active, add="+")
        self._schedule_autosave()
        self.refresh_taskbar()
        if self.game.defer_career_session:
            self.root.after(200, self._run_deferred_career_session)
        self._raise_main_window()

    def _raise_main_window(self) -> None:
        """Bring desktop to front after agent restarts (VNC often hides new windows)."""
        try:
            self.root.lift()
            self.root.attributes("-topmost", True)
            self.root.after(400, lambda: self.root.attributes("-topmost", False))
            self.root.focus_force()
        except tk.TclError:
            pass

    def _schedule_taskbar_refresh(self) -> None:
        if self._taskbar_refresh_job:
            return
        self._taskbar_refresh_job = self.root.after(80, self._flush_taskbar_refresh)

    def _flush_taskbar_refresh(self) -> None:
        self._taskbar_refresh_job = None
        self.refresh_taskbar()

    def _run_deferred_career_session(self) -> None:
        if not self.game.defer_career_session:
            return
        self.game.defer_career_session = False
        from retention import RetentionManager
        RetentionManager.on_career_session(self.game)
        self.refresh_taskbar()

    def _install_global_console_handler(self) -> None:
        """Keep terminal output across Desktop ↔ app switches."""

        def handler(text: str, tag: str = "normal") -> None:
            if not text:
                return
            lines = text.split("\n")
            for i, line in enumerate(lines):
                if i < len(lines) - 1:
                    self._terminal_log.append((line, tag))
                elif line:
                    self._terminal_log.append((line, tag))
            if len(self._terminal_log) > 4000:
                self._terminal_log = self._terminal_log[-3000:]

            def paint() -> None:
                out = self._terminal_output_widget
                if out and out.winfo_exists():
                    out.configure(state=tk.NORMAL)
                    out.insert(tk.END, text + ("\n" if not text.endswith("\n") else ""), tag)
                    out.see(tk.END)
                    out.configure(state=tk.DISABLED)

            try:
                if self.root.winfo_exists():
                    self.root.after_idle(paint)
                else:
                    paint()
            except tk.TclError:
                pass

            self._schedule_taskbar_refresh()
            if tag == "error":
                sounds.play("error")
            elif tag == "warn" and "INTRUSION" in text:
                sounds.play("alert")

        Console.handler = handler

    def _replay_terminal_log(self, output: scrolledtext.ScrolledText) -> None:
        output.configure(state=tk.NORMAL)
        output.delete("1.0", tk.END)
        for line, tag in self._terminal_log:
            output.insert(tk.END, line + "\n", tag)
        output.see(tk.END)
        output.configure(state=tk.DISABLED)

    def _try_resume_save(self) -> None:
        from progression import BACKUP_PATH, SAVE_PATH, SaveManager

        primary_was_reset = False
        if SAVE_PATH.exists() and BACKUP_PATH.exists():
            primary = SaveManager._read_save_file(SAVE_PATH)
            backup = SaveManager._read_save_file(BACKUP_PATH)
            if primary and backup and SaveManager._progress_key(backup) > SaveManager._progress_key(primary):
                primary_was_reset = True

        self._save_loaded = SaveManager.load(self.game, quiet=True)
        if self._save_loaded:
            self.game.tutorial.reconcile_stuck_lessons()
        if self._save_loaded and primary_was_reset:
            self._save_restore_notice = (
                "Your career progress was restored from save backup. "
                "A bad save overwrite was detected and fixed."
            )
        elif not self._save_loaded:
            self._save_restore_notice = (
                "Could not load save — starting fresh. Progress will save after each command."
            )

    def _on_quit(self) -> None:
        self.game.autosave(force=True)
        self.root.destroy()

    def _schedule_autosave(self) -> None:
        # Do not autosave immediately on startup — that can overwrite a good save
        # if load failed and left a fresh Game() in memory.
        self.root.after(120_000, self._periodic_autosave)

    def _periodic_autosave(self) -> None:
        self.game.autosave(force=True)
        self.refresh_taskbar()
        self.root.after(120_000, self._periodic_autosave)

    # ----- mail notifications -----

    def _on_new_mail(self, msg: MailMessage) -> None:
        sounds.play("mail")
        if self.taskbar_label is None:
            return
        self.refresh_taskbar()
        self._refresh_mail_badge()
        if self._mail_listbox and "mail" in self.open_windows:
            self._populate_mail_list(self._mail_listbox)

    def _refresh_mail_badge(self) -> None:
        if not self.mail_badge:
            return
        count = self.game.mail.unread_count()
        if count:
            self.mail_badge.configure(text=str(count))
            self.mail_badge.place(relx=0.72, rely=0.02, width=22, height=18)
        else:
            self.mail_badge.configure(text="")
            self.mail_badge.place_forget()

    def _prompt_home(self) -> str:
        return "/home/hacker"

    def _prompt_path_display(self, path: str) -> str:
        home = self._prompt_home()
        if path == home:
            return "~"
        if path.startswith(home + "/"):
            return "~" + path[len(home):]
        return path

    def _prompt_parts(self) -> list[tuple[str, str]]:
        p = self.game.player
        if p.is_local():
            user, host = p.username, "localhost"
        elif p.remote_is_root:
            user, host = "root", p.prompt_host
        else:
            srv = self.game.remote_server()
            user = srv.ssh_user if srv else p.username
            host = p.prompt_host
        if p.has_remote_shell or p.is_local():
            path = self._prompt_path_display(p.cwd)
        else:
            path = "~"
        sym = "#" if (p.is_local() or p.has_remote_shell) and p.remote_is_root else "$"
        if not p.is_local() and not p.has_remote_shell:
            sym = ">"
        vpn = " [VPN]" if p.vpn_active else ""
        return [
            (f"{user}@{host}", COLORS["prompt_user"]),
            (":", COLORS["prompt_sym"]),
            (path, COLORS["prompt_path"]),
            (sym, COLORS["prompt_sym"]),
            (vpn, COLORS["muted"]),
            (" ", COLORS["prompt_sym"]),
        ]

    def _terminal_window_title(self) -> str:
        p = self.game.player
        if p.is_local():
            user, host = p.username, "localhost"
        elif p.remote_is_root:
            user, host = "root", p.prompt_host
        else:
            srv = self.game.remote_server()
            user = srv.ssh_user if srv else p.username
            host = p.prompt_host
        path = self._prompt_path_display(p.cwd) if (p.has_remote_shell or p.is_local()) else "~"
        return f"{user}@{host}: {path}"

    def _rebuild_terminal_prompt(self) -> None:
        frame = self._terminal_prompt_frame
        if not frame or not frame.winfo_exists():
            return
        for child in frame.winfo_children():
            child.destroy()
        for text, color in self._prompt_parts():
            if not text:
                continue
            tk.Label(
                frame, text=text, fg=color, bg=COLORS["terminal_bg"], font=MONO(13),
            ).pack(side=tk.LEFT)

    # ----- layout -----

    def _draw_wallpaper(self) -> None:
        canvas = self.desktop_canvas
        if not canvas or not canvas.winfo_exists():
            return
        w = max(canvas.winfo_width(), 1)
        h = max(canvas.winfo_height(), 1)
        canvas.delete("wallpaper")
        steps = 48
        top = (0x77, 0x21, 0x6F)
        bottom = (0x2C, 0x00, 0x1E)
        for i in range(steps):
            t = i / max(steps - 1, 1)
            r = int(top[0] + (bottom[0] - top[0]) * t)
            g = int(top[1] + (bottom[1] - top[1]) * t)
            b = int(top[2] + (bottom[2] - top[2]) * t)
            color = f"#{r:02x}{g:02x}{b:02x}"
            y0 = int(h * i / steps)
            y1 = int(h * (i + 1) / steps) + 1
            canvas.create_rectangle(0, y0, w, y1, fill=color, outline=color, tags="wallpaper")
        canvas.tag_lower("wallpaper")

    def _on_desktop_resize(self, _event: object = None) -> None:
        self._draw_wallpaper()
        canvas = self.desktop_canvas
        if canvas and self._banner_place_id and self.onboarding_banner:
            try:
                bw = min(int(760 * UI_SCALE), max(canvas.winfo_width() - 80, 420))
                canvas.itemconfigure(self._banner_place_id, width=bw)
                canvas.coords(self._banner_place_id, canvas.winfo_width() // 2, 48)
            except tk.TclError:
                pass
        for key, panel in self.open_windows.items():
            shell = panel._shell  # type: ignore[attr-defined]
            if not shell.winfo_ismapped():
                continue
            if getattr(panel, "_maximized", False):
                self._place_maximized(shell)
            else:
                geom = getattr(panel, "_geom", self._default_window_geom(key))
                self._apply_window_geom(key, shell, geom)

    def _build_desktop(self) -> None:
        self.content = tk.Frame(self.root, bg=COLORS["desktop"])
        self.content.pack(fill=tk.BOTH, expand=True)

        self._build_dock()

        self.desktop_canvas = tk.Canvas(
            self.content, bg=COLORS["desktop"], highlightthickness=0, bd=0,
        )
        self.desktop_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.desktop_view = self.desktop_canvas
        self.desktop_canvas.bind("<Configure>", self._on_desktop_resize)
        self.root.after_idle(self._draw_wallpaper)

    def _build_dock(self) -> None:
        dock = tk.Frame(self.content, bg=COLORS["taskbar"], width=DOCK_WIDTH)
        dock.pack(side=tk.LEFT, fill=tk.Y)
        dock.pack_propagate(False)
        self.dock_frame = dock

        tk.Frame(dock, bg=COLORS["taskbar"], height=8).pack(fill=tk.X)

        apps = [
            ("training", "?", "Training", self.open_training),
            ("terminal", ">_", "Terminal", self.open_terminal),
            ("notes", "≡", "Notes", self.open_notes),
            ("files", "{}", "Files", self.open_files),
            ("mail", "@", "Mail", self.open_mail),
            ("jobs", "[]", "Jobs", self.open_job_board),
            ("board", "//", "Board", self.open_social_board),
            ("shop", "$", "Shop", self.open_shop),
            ("botnet", "⊛", "Botnet", self.open_botnet),
            ("chaos", "☠", "Chaos", self.open_chaos),
            ("achieve", "*", "Awards", self.open_achievements),
            ("status", "#", "Settings", self.open_status),
        ]
        for key, glyph, name, command in apps:
            self._dock_icon(dock, key, glyph, name, command)

        tk.Frame(dock, bg=COLORS["taskbar"]).pack(fill=tk.BOTH, expand=True)

        show_btn = tk.Label(
            dock, text="▦", fg=COLORS["muted"], bg=COLORS["taskbar"],
            font=F(14), cursor="hand2", pady=10,
        )
        show_btn.pack(side=tk.BOTTOM, pady=(0, 10))
        show_btn.bind("<Button-1>", lambda _e: self._show_desktop())

    def _dock_locked(self, key: str) -> bool:
        return self.game.player.phase == "tutorial" and key in DOCK_CAREER_LOCKED

    def _dock_icon(
        self, parent: tk.Frame, key: str, glyph: str, name: str, command,
    ) -> None:
        wrap = tk.Frame(parent, bg=COLORS["taskbar"], cursor="hand2")
        wrap.pack(fill=tk.X, pady=3)

        indicator = tk.Frame(wrap, bg=COLORS["taskbar"], width=3)
        indicator.pack(side=tk.LEFT, fill=tk.Y)

        if key == "terminal":
            box_bg, box_fg = COLORS["terminal_bg"], COLORS["prompt_user"]
        elif key == "training" and self.game.player.phase == "tutorial":
            box_bg, box_fg = COLORS["accent"], "white"
        elif self._dock_locked(key):
            box_bg, box_fg = COLORS["border"], COLORS["muted"]
        else:
            box_bg, box_fg = COLORS["aubergine"], COLORS["text"]

        glyph_text = glyph
        if self._dock_locked(key):
            glyph_text = f"{glyph}"

        icon = tk.Label(
            wrap, text=glyph_text, fg=box_fg, bg=box_bg,
            font=MONO(18, bold=True), width=3, height=1,
            relief=tk.FLAT, bd=0, cursor="hand2",
        )
        icon.pack(side=tk.LEFT, padx=(4, 6), pady=2)

        dot = tk.Label(
            wrap, text="●", fg=COLORS["accent"], bg=COLORS["taskbar"],
            font=F(7),
        )
        self._dock_icons[key] = icon
        self._dock_dots[key] = dot
        self._dock_indicators[key] = indicator

        if key == "mail":
            self.mail_badge = tk.Label(
                icon, text="", fg="white", bg=COLORS["error"],
                font=F(7, bold=True),
            )
            self._refresh_mail_badge()

        if self._dock_locked(key):
            tk.Label(
                wrap, text="🔒", fg=COLORS["muted"], bg=COLORS["taskbar"], font=F(8),
            ).pack(side=tk.RIGHT, padx=(0, 4))

        def launch(_e=None) -> None:
            if self._dock_locked(key):
                sounds.play("error")
                from tkinter import messagebox
                messagebox.showinfo(
                    "Career locked",
                    f"{_name} unlocks after you graduate training.\n\n"
                    "Finish the tutorial to access contracts, the darknet board, and botnet payloads.",
                )
                return
            self._toggle_dock_app(key, command)

        for widget in (wrap, indicator, icon):
            widget.bind("<Button-1>", launch)
            widget.configure(cursor="hand2")

        def on_enter(_e: object, b: tk.Label = icon, bg: str = box_bg) -> None:
            b.configure(bg=COLORS["accent_dim"])

        def on_leave(_e: object, b: tk.Label = icon, bg: str = box_bg) -> None:
            b.configure(bg=bg)

        icon.bind("<Enter>", on_enter)
        icon.bind("<Leave>", on_leave)

    def _update_dock_highlight(self) -> None:
        for key, indicator in self._dock_indicators.items():
            if not indicator.winfo_exists():
                continue
            if key == self._active_app:
                indicator.configure(bg=COLORS["accent"])
            else:
                indicator.configure(bg=COLORS["taskbar"])
        for key, dot in self._dock_dots.items():
            if not dot.winfo_exists():
                continue
            if key in self.open_windows:
                dot.pack(side=tk.RIGHT, padx=(0, 4))
            else:
                dot.pack_forget()

    def _desktop_size(self) -> tuple[int, int]:
        canvas = self.desktop_canvas
        if not canvas:
            return 1280, 720
        canvas.update_idletasks()
        return max(canvas.winfo_width(), 400), max(canvas.winfo_height(), 300)

    def _default_window_geom(self, key: str) -> tuple[int, int, int, int]:
        w, h = WINDOW_SIZES.get(key, (720, 520))
        cw, ch = self._desktop_size()
        stagger = WINDOW_STAGGER.get(key, (40 + len(self.open_windows) * 28, 40 + len(self.open_windows) * 24))
        x = min(stagger[0], max(12, cw - w - 12))
        y = min(stagger[1], max(12, ch - h - 12))
        if key == "terminal" and cw > w + 480:
            x = cw - w - 24
        if key == "notes":
            x = 24
            y = 48
        return x, y, w, h

    def _apply_window_geom(self, key: str, shell: tk.Frame, geom: tuple[int, int, int, int]) -> None:
        x, y, w, h = geom
        cw, ch = self._desktop_size()
        w = min(w, cw - 8)
        h = min(h, ch - 8)
        x = max(0, min(x, cw - w))
        y = max(0, min(y, ch - h))
        # Clear any prior relwidth/relheight from maximize — Tk keeps stale absolute
        # width/height when switching place modes, which clips the right edge.
        shell.place_forget()
        shell.place(x=x, y=y, width=w, height=h, relwidth=0, relheight=0)
        shell.lift()

    def _place_maximized(self, shell: tk.Frame) -> None:
        cw, ch = self._desktop_size()
        # Use explicit pixel size — relwidth=1 on top of a prior width=… overflows the canvas.
        shell.place_forget()
        shell.place(x=0, y=0, width=cw, height=ch, relwidth=0, relheight=0)
        shell.lift()

    def _sync_window_layout(self, key: str) -> None:
        panel = self.open_windows.get(key)
        if not panel:
            return
        shell = panel._shell  # type: ignore[attr-defined]
        body: tk.Frame = panel._body  # type: ignore[attr-defined]
        shell.update_idletasks()
        body.update_idletasks()

    def _place_window(self, key: str, shell: tk.Frame, width: int = 0, height: int = 0) -> None:
        panel = self.open_windows.get(key)
        if panel and getattr(panel, "_maximized", False):
            self._place_maximized(shell)
            return
        if panel and getattr(panel, "_geom", None):
            self._apply_window_geom(key, shell, panel._geom)  # type: ignore[attr-defined]
            return
        geom = self._default_window_geom(key)
        if panel:
            panel._geom = geom  # type: ignore[attr-defined]
        self._apply_window_geom(key, shell, geom)

    def _toggle_dock_app(self, key: str, opener) -> None:
        """Dock click: minimize focused app, focus unfocused app, or open it."""
        if key in self.open_windows:
            shell = self.open_windows[key]._shell  # type: ignore[attr-defined]
            try:
                if shell.winfo_ismapped():
                    if self._active_app == key:
                        self._minimize_window(key)
                    else:
                        self._focus_window(key)
                    return
            except tk.TclError:
                pass
        opener()

    def _tick_clock(self) -> None:
        if self.clock_label and self.clock_label.winfo_exists():
            now = datetime.now()
            self.clock_label.configure(text=now.strftime(f"%a %b {now.day}  %H:%M"))
        self.root.after(30_000, self._tick_clock)

    def _titlebar_button(
        self, parent: tk.Frame, text: str, bg: str, command, *, side: str = tk.RIGHT,
    ) -> tk.Label:
        btn = tk.Label(
            parent, text=text, fg=COLORS["text"], bg=bg,
            font=F(10, bold=True), width=3, cursor="hand2",
        )
        btn.pack(side=side, padx=1, pady=4)

        def on_click(_event=None) -> str:
            command()
            return "break"

        btn.bind("<Button-1>", on_click)
        return btn

    def _bind_window_drag(self, key: str, titlebar: tk.Frame, title_lbl: tk.Label, shell: tk.Frame) -> None:
        drag = {"x": 0, "y": 0}

        def _can_drag() -> bool:
            panel = self.open_windows.get(key)
            return bool(panel and not getattr(panel, "_maximized", False))

        def start(event) -> None:
            if not _can_drag():
                return
            drag["x"] = event.x_root
            drag["y"] = event.y_root
            self._focus_window(key)

        def move(event) -> None:
            if not _can_drag():
                return
            panel = self.open_windows[key]
            dx = event.x_root - drag["x"]
            dy = event.y_root - drag["y"]
            drag["x"] = event.x_root
            drag["y"] = event.y_root
            nx = shell.winfo_x() + dx
            ny = shell.winfo_y() + dy
            geom = getattr(panel, "_geom", self._default_window_geom(key))
            panel._geom = (nx, ny, geom[2], geom[3])  # type: ignore[attr-defined]
            self._apply_window_geom(key, shell, panel._geom)  # type: ignore[attr-defined]

        def dbl_toggle(_event=None) -> str:
            self._toggle_maximize(key)
            return "break"

        title_lbl.bind("<ButtonPress-1>", start, add="+")
        title_lbl.bind("<B1-Motion>", move, add="+")
        title_lbl.bind("<Double-Button-1>", dbl_toggle, add="+")

    def _run_onboarding(self) -> None:
        """Guide new tutorial players — auto-open Training on first launch."""
        p = self.game.player
        if p.phase == "tutorial":
            self.game.tutorial.send_opening_hook()
        if p.phase != "tutorial":
            if p.phase == "career":
                self.root.after(500, self.open_files)
                self._maybe_show_returning_chaos_cta()
            return

        from progression import PlayerProfile
        lesson = self.game.tutorial.current()
        if self.onboarding_banner:
            self.onboarding_banner.destroy()
            self.onboarding_banner = None

        canvas = self.desktop_canvas
        if not canvas:
            return

        banner = tk.Frame(canvas, bg=COLORS["window"], padx=16, pady=12,
                          highlightthickness=1, highlightbackground=COLORS["border"])
        self.onboarding_banner = banner

        if PlayerProfile.is_veteran():
            headline = "WELCOME BACK — NEW SAVE (LESSON 1)"
            steps = (
                "This save starts at tutorial lesson 1 unless you skip.\n\n"
                "☠ CHAOS CAREER — skip all lessons, loud career mode (uses real wallet)\n"
                "skip tutorial — standard career skip from Terminal\n"
                "Or open Training and work through lesson 1 normally."
            )
            auto_open = False
        elif p.tutorial_step == 0:
            headline = "TRAINING MODE — START HERE"
            steps = (
                "Goal today: crack training-node and capture the flag (~30 min).\n\n"
                "1. Open Mail — urgent orders from Training Officer\n"
                "2. Open Terminal → type: lesson\n"
                "3. Run: ifconfig  then  route  then  scan\n"
                "4. Open Notes to jot IPs while you work"
            )
            auto_open = "mail"
        else:
            headline = f"RESUME TRAINING — Lesson {p.tutorial_step + 1}/{len(TUTORIAL_CURRICULUM)}"
            steps = "Pick up where you left off.\nOpen Terminal and type: lesson"
            auto_open = False

        tk.Label(
            banner, text=headline,
            fg=COLORS["accent"], bg=COLORS["window"],
            font=F(14, bold=True),
        ).pack(anchor=tk.W)
        save_note = ""
        if self._save_restore_notice:
            save_note = f"\n\n{self._save_restore_notice}"
        elif self._save_loaded:
            save_note = (
                f"\n\nTutorial lesson {p.tutorial_step + 1}/{len(TUTORIAL_CURRICULUM)} "
                "— progress auto-saves after each command."
            )
        else:
            save_note = "\n\nNew game — progress saves after each command. Type save anytime in Terminal."

        tk.Label(
            banner,
            text=(
                f"{lesson.title if lesson else 'Network Boot'}\n"
                f"{lesson.objective if lesson else 'Run: ifconfig then route'}\n\n"
                f"{steps}{save_note}"
            ),
            fg=COLORS["text"], bg=COLORS["window"],
            font=F(12), justify=tk.LEFT, wraplength=int(720 * UI_SCALE),
        ).pack(anchor=tk.W, pady=(6, 8))

        btn_row = tk.Frame(banner, bg=COLORS["window"])
        btn_row.pack(anchor=tk.W)
        tk.Button(
            btn_row, text="Open Training", command=self.open_training,
            bg=COLORS["accent_dim"], fg="white", relief=tk.FLAT, padx=14, pady=4,
        ).pack(side=tk.LEFT)
        tk.Button(
            btn_row, text="Open Terminal", command=self.open_terminal,
            bg=COLORS["border"], fg=COLORS["text"], relief=tk.FLAT, padx=14, pady=4,
        ).pack(side=tk.LEFT, padx=8)
        tk.Button(
            btn_row, text="Open Notes", command=self.open_notes,
            bg=COLORS["border"], fg=COLORS["text"], relief=tk.FLAT, padx=14, pady=4,
        ).pack(side=tk.LEFT, padx=8)
        tk.Button(
            btn_row, text="Read Mail", command=self.open_mail,
            bg=COLORS["border"], fg=COLORS["text"], relief=tk.FLAT, padx=14, pady=4,
        ).pack(side=tk.LEFT)
        if ChaosCareerManager.can_start(self.game):
            tk.Button(
                btn_row, text="☠ CHAOS CAREER", command=self._start_chaos_career,
                bg=COLORS["error"], fg="white", relief=tk.FLAT, padx=14, pady=4,
            ).pack(side=tk.LEFT, padx=(12, 0))

        canvas.update_idletasks()
        bw = min(int(760 * UI_SCALE), max(canvas.winfo_width() - 80, 420))
        self._banner_place_id = canvas.create_window(
            canvas.winfo_width() // 2, 48, window=banner, anchor=tk.N, width=bw,
        )
        if auto_open == "mail":
            self.root.after(400, self.open_mail)
            self.root.after(900, self.open_terminal)
        elif auto_open:
            self.root.after(400, self.open_training)
        else:
            self.root.after(400, self.open_terminal)

    def _maybe_show_returning_chaos_cta(self) -> None:
        """Nudge returning players toward chaos dock / endless run."""
        from progression import PlayerProfile
        from tkinter import messagebox

        p = self.game.player
        if p.phase != "career" or not PlayerProfile.suggest_chaos_on_career_load():
            return
        if self.game.meta.chaos_mode:
            return
        data = PlayerProfile._read()
        data["chaos_cta_shown"] = True
        from progression import PROFILE_PATH
        import json
        try:
            PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
            PROFILE_PATH.write_text(json.dumps(data, indent=2))
        except OSError:
            pass
        self.root.after(1200, lambda: messagebox.showinfo(
            "RETURNING OPERATOR",
            "Welcome back. Training's behind you.\n\n"
            "• Open ☠ Chaos dock — provoke rivals, ghost raids, faction wars\n"
            "• Type chaos run for roguelike endless floors\n"
            "• Botnet dock now shows a live infection map",
        ))
        self.root.after(1600, self.open_chaos)

    def _build_top_panel(self) -> None:
        bar = tk.Frame(self.root, bg=COLORS["taskbar"], height=30)
        bar.pack(fill=tk.X, side=tk.TOP)

        left = tk.Frame(bar, bg=COLORS["taskbar"])
        left.pack(side=tk.LEFT, padx=(6, 0))
        activities = tk.Label(
            left, text="  Activities", fg=COLORS["text"], bg=COLORS["taskbar"],
            font=F(11, bold=True), cursor="hand2", padx=6, pady=6,
        )
        activities.pack(side=tk.LEFT)
        activities.bind("<Button-1>", lambda _e: self._show_desktop())
        tk.Label(
            left, text="TerminalHacker", fg=COLORS["muted"], bg=COLORS["taskbar"],
            font=F(10),
        ).pack(side=tk.LEFT, padx=(4, 0))

        self.taskbar_label = tk.Label(
            bar, text="", fg=COLORS["muted"], bg=COLORS["taskbar"],
            font=F(10), anchor=tk.W,
        )
        self.taskbar_label.pack(fill=tk.X, side=tk.LEFT, expand=True, padx=8)

        self.chaos_ticker = tk.Label(
            bar, text="", fg=COLORS["warn"], bg=COLORS["taskbar"],
            font=F(9), anchor=tk.E, width=42,
        )
        self.chaos_ticker.pack(side=tk.RIGHT, padx=(0, 8))

        right = tk.Frame(bar, bg=COLORS["taskbar"])
        right.pack(side=tk.RIGHT, padx=8)
        self.clock_label = tk.Label(
            right, text="", fg=COLORS["text"], bg=COLORS["taskbar"],
            font=F(10), padx=8,
        )
        self.clock_label.pack(side=tk.RIGHT)
        tk.Label(
            right, text="  ⏻  🔊  ", fg=COLORS["muted"], bg=COLORS["taskbar"],
            font=F(10),
        ).pack(side=tk.RIGHT)

    def refresh_taskbar(self) -> None:
        if self.taskbar_label is None:
            return
        p = self.game.player
        phase = "TRAINING" if p.phase == "tutorial" else ("ENDLESS" if p.phase == "endless" else "CAREER")
        if p.phase == "tutorial":
            wallet = f"Tutorial ${p.tutorial_credits} | Career ${p.money} locked"
        else:
            wallet = f"Balance ${p.money}"
        lesson = ""
        if p.phase == "tutorial":
            lesson = f" | Lesson {p.tutorial_step + 1}/{len(TUTORIAL_CURRICULUM)}"
        vpn = "VPN ON" if p.vpn_active else "VPN off"
        unread = self.game.mail.unread_count()
        mail_txt = f" | Mail: {unread} unread" if unread else ""
        rank_txt = ""
        if p.phase == "career":
            rank_txt = f" | {ReputationSystem.rank_name(p)} ({p.reputation} rep)"
            rank_txt += f" | Streak {self.game.retention.streak}d"
            rank_txt += f" | S{self.game.retention.season_tier}/{len(SEASON_TIERS)}"
            if self.game.meta.chaos_mode or self.game.meta.notoriety > 0:
                rank_txt += f" | Notoriety {self.game.meta.notoriety}"
        save_txt = ""
        if self.game.last_autosave:
            save_txt = f" | Saved {self.game.last_autosave}"
        self.taskbar_label.configure(
            text=(
                f"  {phase}{lesson}{rank_txt}{save_txt}  |  {wallet}  |  CPU L{p.cpu_level}  |  "
                f"FW L{p.firewall_level}  |  {vpn}{mail_txt}"
            )
        )
        if self.chaos_ticker and self.chaos_ticker.winfo_exists():
            headline = ChaosNewsManager.latest(self.game)
            if headline and p.phase in ("career", "endless"):
                self.chaos_ticker.configure(text=headline[:60])
            else:
                self.chaos_ticker.configure(text="")

    def _show_desktop(self) -> None:
        for key in list(self.open_windows.keys()):
            shell = self.open_windows[key]._shell  # type: ignore[attr-defined]
            shell.place_forget()
        self._active_app = None
        self._update_dock_highlight()
        sounds.play("click")

    def _minimize_window(self, key: str) -> None:
        if key not in self.open_windows:
            return
        panel = self.open_windows[key]
        if getattr(panel, "_maximized", False):
            panel._maximized = False  # type: ignore[attr-defined]
            max_btn = getattr(panel, "_max_btn", None)
            if max_btn and max_btn.winfo_exists():
                max_btn.configure(text="□")
        panel._shell.place_forget()  # type: ignore[attr-defined]
        if key == "terminal":
            self._uninstall_terminal_key_catcher()
            self._cancel_terminal_focus()
        self._active_app = None
        for other in reversed(list(self.open_windows.keys())):
            shell = self.open_windows[other]._shell  # type: ignore[attr-defined]
            try:
                if other != key and shell.winfo_ismapped():
                    self._active_app = other
                    break
            except tk.TclError:
                continue
        self._update_dock_highlight()
        sounds.play("close")

    def _window(self, key: str, title: str, width: int, height: int) -> object:
        if key in self.open_windows:
            panel = self.open_windows[key]
            self._focus_window(key)
            sounds.play("click")
            return panel

        canvas = self.desktop_canvas
        assert canvas is not None

        shell = tk.Frame(
            canvas, bg=COLORS["border"],
            highlightthickness=1, highlightbackground=COLORS["border"],
        )
        inner = tk.Frame(shell, bg=COLORS["window"])
        inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        titlebar = tk.Frame(inner, bg=COLORS["window_header"], height=32, cursor="fleur")
        titlebar.pack(fill=tk.X)
        title_lbl = tk.Label(
            titlebar, text=f"  {title}", fg=COLORS["text"], bg=COLORS["window_header"],
            font=F(10), cursor="fleur",
        )
        title_lbl.pack(side=tk.LEFT, pady=5, fill=tk.X, expand=True)
        controls = tk.Frame(titlebar, bg=COLORS["window_header"])
        controls.pack(side=tk.RIGHT, padx=4)
        self._titlebar_button(controls, "×", "#E95420", lambda k=key: self._close_window(k))
        max_btn = self._titlebar_button(
            controls, "□", COLORS["border"], lambda k=key: self._toggle_maximize(k),
        )
        self._titlebar_button(controls, "−", COLORS["border"], lambda k=key: self._minimize_window(k))

        body = tk.Frame(inner, bg=COLORS["window"])
        body.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        geom = self._default_window_geom(key)
        if width and height:
            geom = (geom[0], geom[1], width, height)

        panel = type("Panel", (), {})()
        panel._body = body
        panel._shell = shell
        panel._inner = inner  # type: ignore[attr-defined]
        panel._key = key
        panel._title_lbl = title_lbl  # type: ignore[attr-defined]
        panel._titlebar = titlebar  # type: ignore[attr-defined]
        panel._geom = geom  # type: ignore[attr-defined]
        panel._maximized = True  # type: ignore[attr-defined]
        panel._max_btn = max_btn  # type: ignore[attr-defined]
        max_btn.configure(text="=")
        self.open_windows[key] = panel

        self._bind_window_drag(key, titlebar, title_lbl, shell)
        inner.bind("<Button-1>", lambda _e, k=key: self._focus_window(k), add="+")
        shell.bind("<Button-1>", lambda _e, k=key: self._focus_window(k), add="+")

        self._place_maximized(shell)
        self._focus_window(key)
        sounds.play("open")
        return panel

    def _focus_window(self, key: str) -> None:
        if key not in self.open_windows:
            return
        panel = self.open_windows[key]
        shell = panel._shell  # type: ignore[attr-defined]
        if not shell.winfo_ismapped():
            self._place_window(key, shell)
        shell.lift()
        self._active_app = key
        self._update_dock_highlight()
        if key == "terminal" and (self._terminal_entry or self._terminal_input):
            self._arm_terminal_focus()
            self._ensure_terminal_key_catcher()
        elif key == "notes" and self._notes_editor and self._notes_editor.winfo_exists():
            self._uninstall_terminal_key_catcher()
            self._cancel_terminal_focus()
            self._notes_editor.focus_set()
        else:
            self._uninstall_terminal_key_catcher()
            self._cancel_terminal_focus()
        if key == "files" and "files" in self._built_panels:
            self._refresh_files()

    def _show_app(self, key: str) -> None:
        self._focus_window(key)

    def _toggle_maximize(self, key: str) -> None:
        if key not in self.open_windows:
            return
        panel = self.open_windows[key]
        shell = panel._shell  # type: ignore[attr-defined]
        max_btn = getattr(panel, "_max_btn", None)
        if getattr(panel, "_maximized", False):
            panel._maximized = False  # type: ignore[attr-defined]
            geom = getattr(panel, "_geom", self._default_window_geom(key))
            self._apply_window_geom(key, shell, geom)
            if max_btn and max_btn.winfo_exists():
                max_btn.configure(text="□")
        else:
            if shell.winfo_ismapped():
                panel._geom = (  # type: ignore[attr-defined]
                    shell.winfo_x(), shell.winfo_y(),
                    max(shell.winfo_width(), 200), max(shell.winfo_height(), 160),
                )
            panel._maximized = True  # type: ignore[attr-defined]
            self._place_maximized(shell)
            if max_btn and max_btn.winfo_exists():
                max_btn.configure(text="=")
        self._sync_window_layout(key)
        self._focus_window(key)
        sounds.play("click")

    def _unmaximize_active(self, _event=None) -> str | None:
        if self._active_app and self._active_app in self.open_windows:
            panel = self.open_windows[self._active_app]
            if getattr(panel, "_maximized", False):
                self._toggle_maximize(self._active_app)
                return "break"
        return None

    def _uninstall_terminal_key_catcher(self) -> None:
        self._terminal_key_catcher_active = False

    def _ensure_terminal_key_catcher(self) -> None:
        entry = self._terminal_entry
        submit = self._terminal_submit_cmd or self._terminal_run_cmd
        if entry and entry.winfo_exists() and submit:
            self._install_terminal_key_catcher(entry, submit)

    def _install_terminal_key_catcher(self, entry: tk.Entry, run_command) -> None:
        """Route keyboard to command line when Terminal is open (Cursor Desktop fix)."""
        self._terminal_key_catcher_active = True

        if self._terminal_key_catcher is not None:
            return

        def _focus_is_other_editor() -> bool:
            focus = self.root.focus_get()
            if focus is None or focus == entry:
                return False
            cls = focus.winfo_class()
            if cls not in ("Text", "Entry", "TEntry"):
                return False
            w: tk.Misc | None = focus
            while w is not None:
                if w == entry:
                    return False
                w = w.master if hasattr(w, "master") else None
            return True

        def catcher(event) -> str | None:
            if not self._terminal_key_catcher_active:
                return None
            if self._active_app != "terminal":
                return None
            if "terminal" not in self.open_windows or not entry.winfo_exists():
                return None
            # Entry already has focus — let it handle keys (prevents double-typing).
            if self.root.focus_get() == entry:
                return None
            if _focus_is_other_editor():
                return None
            keysym = event.keysym
            if keysym in ("Return", "KP_Enter"):
                run_command()
                return "break"
            if keysym == "BackSpace":
                entry.focus_set()
                if entry.selection_present():
                    entry.delete(tk.SEL_FIRST, tk.SEL_LAST)
                else:
                    pos = entry.index(tk.INSERT)
                    if pos > 0:
                        entry.delete(pos - 1)
                return "break"
            if keysym == "Up":
                entry.event_generate("<Up>")
                return "break"
            if keysym == "Down":
                entry.event_generate("<Down>")
                return "break"
            if keysym in ("Left", "Right", "Home", "End"):
                entry.focus_set()
                entry.event_generate(f"<{keysym}>")
                return "break"
            if event.char and len(event.char) == 1 and event.char.isprintable():
                entry.focus_set()
                entry.insert(tk.INSERT, event.char)
                return "break"
            return None

        self._terminal_key_catcher = self.root.bind_all("<KeyPress>", catcher, add="+")

    def _cancel_terminal_focus(self) -> None:
        if self._terminal_focus_job:
            try:
                self.root.after_cancel(self._terminal_focus_job)
            except tk.TclError:
                pass
            self._terminal_focus_job = None

    def _arm_terminal_focus(self) -> None:
        """Repeatedly reclaim keyboard focus — needed in some remote desktop hosts."""
        self._cancel_terminal_focus()

        def pump(remaining: int = 12) -> None:
            if "terminal" not in self.open_windows or not (self._terminal_entry or self._terminal_input):
                return
            self._activate_terminal_input()
            if remaining > 0:
                self._terminal_focus_job = self.root.after(250, lambda: pump(remaining - 1))

        pump()

    def _activate_terminal_input(self) -> None:
        entry = self._terminal_entry or self._terminal_input
        if not entry or not entry.winfo_exists():
            return
        try:
            entry.configure(state="normal")
            entry.focus_force()
            if isinstance(entry, tk.Text):
                entry.mark_set(tk.INSERT, tk.END)
                entry.see(tk.END)
            else:
                entry.icursor(tk.END)
            if self._terminal_input_frame:
                self._terminal_input_frame.configure(
                    highlightbackground=COLORS["accent"],
                    highlightthickness=2,
                )
        except tk.TclError:
            pass

    def _focus_terminal_input(self) -> None:
        self._activate_terminal_input()

    def _get_terminal_command(self) -> str:
        if self._terminal_input and self._terminal_input.winfo_exists():
            return self._terminal_input.get("1.0", "end-1c").strip()
        if self._terminal_entry and self._terminal_entry.winfo_exists():
            return self._terminal_entry.get().strip()
        return ""

    def _clear_terminal_command(self) -> None:
        if self._terminal_input and self._terminal_input.winfo_exists():
            self._terminal_input.delete("1.0", tk.END)
        elif self._terminal_entry and self._terminal_entry.winfo_exists():
            self._terminal_entry.delete(0, tk.END)

    def _any_app_visible(self) -> bool:
        for panel in self.open_windows.values():
            shell = panel._shell  # type: ignore[attr-defined]
            try:
                if shell.winfo_ismapped():
                    return True
            except tk.TclError:
                continue
        return False

    def _hide_app(self, key: str, *, show_desktop: bool = True) -> None:
        if key not in self.open_windows:
            return
        sounds.play("close")
        self.open_windows[key]._shell.place_forget()  # type: ignore[attr-defined]
        if key == "terminal":
            self.game.close_terminal = False
            self._uninstall_terminal_key_catcher()
            self._cancel_terminal_focus()
        if self._active_app == key:
            self._active_app = None
        self._update_dock_highlight()
        if show_desktop and not self._any_app_visible():
            pass  # desktop wallpaper stays visible

    def _close_window(self, key: str) -> None:
        if key == "terminal":
            self._hide_app(key)
            return
        if key == "notes":
            self._save_notes_from_editor()
        if key in self.open_windows:
            sounds.play("close")
            self.open_windows[key]._shell.destroy()
            del self.open_windows[key]
            self._built_panels.discard(key)
        if key == "mail":
            self._mail_listbox = None
            self._mail_viewer = None
            self._mail_meta = None
            self._mail_header = None
            self._mail_btn_row = None
            self._mail_inbox_btn = None
            self._mail_trash_btn = None
            self._mail_folder = "inbox"
        if key == "files":
            self._files_list_frame = None
            self._files_preview_frame = None
        if key == "notes":
            self._notes_editor = None
            if self._notes_save_job:
                try:
                    self.root.after_cancel(self._notes_save_job)
                except tk.TclError:
                    pass
                self._notes_save_job = None
        if key == "botnet":
            self._botnet_text = None
            self._botnet_map_canvas = None
        if self._active_app == key:
            self._active_app = None
        self._update_dock_highlight()

    def _terminal_command_verb(self, cmd: str) -> str:
        line = cmd.strip().split("#", 1)[0].strip()
        if not line:
            return ""
        verb = line.split()[0].lower()
        return "help" if verb == "?" else verb

    def _reveal_terminal_quick(self, cmd: str) -> None:
        """Show a toolbar shortcut only after the player has typed that command."""
        verb = self._terminal_command_verb(cmd)
        if not verb or verb not in self._terminal_quick_buttons:
            return
        if verb in self._terminal_used_commands:
            return
        was_empty = not self._terminal_used_commands
        self._terminal_used_commands.add(verb)
        btn = self._terminal_quick_buttons[verb]
        if btn.winfo_exists():
            btn.pack(side=tk.LEFT, padx=2, pady=4)
        toolbar = self._terminal_toolbar
        if toolbar and toolbar.winfo_exists():
            toolbar.grid(row=0, column=0, sticky="ew")
        if was_empty and self._terminal_toolbar_label and self._terminal_toolbar_label.winfo_exists():
            self._terminal_toolbar_label.pack(side=tk.LEFT, padx=(8, 6), pady=4)

    # ----- terminal command bridge -----

    def _gui_run_command(self, cmd: str) -> None:
        """Run a game command from a GUI button (opens Terminal if needed)."""
        self.open_terminal()
        if self._terminal_run_cmd:
            self._terminal_run_cmd(cmd)

    # ----- apps -----

    def open_mail(self) -> None:
        if "mail" in self._built_panels:
            self._show_app("mail")
            self._refresh_mail_ui()
            return
        win = self._window("mail", "Mail — Secure Inbox", 720, 520)
        body: tk.Frame = win._body  # type: ignore[attr-defined]
        body.columnconfigure(0, weight=1)
        body.rowconfigure(2, weight=1)

        self._mail_header = tk.Label(body, text="INBOX", fg=COLORS["accent"], bg=COLORS["window"],
                                     font=F(14, bold=True))
        self._mail_header.grid(row=0, column=0, sticky="ew")

        self._mail_btn_row = tk.Frame(body, bg=COLORS["window"])
        self._mail_btn_row.grid(row=1, column=0, sticky="ew", pady=(8, 6))

        panes = tk.Frame(body, bg=COLORS["window"])
        panes.grid(row=2, column=0, sticky="nsew")

        left = tk.Frame(panes, bg=COLORS["window"], width=240)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)

        folder_row = tk.Frame(left, bg=COLORS["window"])
        folder_row.pack(fill=tk.X, pady=(0, 6))
        self._mail_inbox_btn = tk.Button(
            folder_row, text="Inbox", command=lambda: self._switch_mail_folder("inbox"),
            bg=COLORS["accent_dim"], fg="white", relief=tk.FLAT, padx=8, pady=2,
        )
        self._mail_inbox_btn.pack(side=tk.LEFT)
        self._mail_trash_btn = tk.Button(
            folder_row, text="Trash", command=lambda: self._switch_mail_folder("trash"),
            bg=COLORS["border"], fg=COLORS["text"], relief=tk.FLAT, padx=8, pady=2,
        )
        self._mail_trash_btn.pack(side=tk.LEFT, padx=6)

        listbox = tk.Listbox(
            left, bg=COLORS["terminal_bg"], fg=COLORS["text"],
            font=F(10), relief=tk.FLAT, selectbackground=COLORS["accent_dim"],
            activestyle="none",
        )
        listbox.pack(fill=tk.BOTH, expand=True)
        self._mail_listbox = listbox

        right = tk.Frame(panes, bg=COLORS["window"])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))

        meta = tk.Label(right, text="Select a message", fg=COLORS["muted"],
                        bg=COLORS["window"], font=F(10), anchor=tk.W)
        meta.pack(fill=tk.X)

        viewer = scrolledtext.ScrolledText(
            right, bg=COLORS["terminal_bg"], fg=COLORS["text"],
            font=F(11), relief=tk.FLAT, wrap=tk.WORD,
        )
        viewer.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        viewer.configure(state=tk.DISABLED)
        self._mail_viewer = viewer
        self._mail_meta = meta

        def show_message(_event=None) -> None:
            sel = listbox.curselection()
            if not sel:
                return
            msgs = self._mail_current_messages()
            if sel[0] >= len(msgs):
                return
            msg = msgs[sel[0]]
            self.game.mail.mark_read(msg.mail_id)
            meta.configure(
                text=f"From: {msg.sender}  |  {msg.timestamp}  |  {msg.subject}",
                fg=COLORS["text"],
            )
            viewer.configure(state=tk.NORMAL)
            viewer.delete("1.0", tk.END)
            viewer.insert(tk.END, msg.body)
            viewer.configure(state=tk.DISABLED)
            self._refresh_mail_badge()
            self.refresh_taskbar()

        listbox.bind("<<ListboxSelect>>", show_message)
        listbox.bind("<Delete>", self._mail_delete_key)
        listbox.bind("<BackSpace>", self._mail_delete_key)

        self._rebuild_mail_buttons()

        self._refresh_mail_ui()
        self._built_panels.add("mail")

    def _mail_current_messages(self) -> list[MailMessage]:
        if self._mail_folder == "trash":
            return self.game.mail.trash
        return self.game.mail.messages

    def _switch_mail_folder(self, folder: str) -> None:
        self._mail_folder = folder
        self._refresh_mail_ui()

    def _refresh_mail_ui(self) -> None:
        if not self._mail_listbox:
            return
        trash_n = len(self.game.mail.trash)
        if self._mail_trash_btn and self._mail_trash_btn.winfo_exists():
            self._mail_trash_btn.configure(text=f"Trash ({trash_n})" if trash_n else "Trash")
        if self._mail_inbox_btn and self._mail_inbox_btn.winfo_exists():
            if self._mail_folder == "inbox":
                self._mail_inbox_btn.configure(bg=COLORS["accent_dim"], fg="white")
                if self._mail_trash_btn:
                    self._mail_trash_btn.configure(bg=COLORS["border"], fg=COLORS["text"])
            else:
                self._mail_inbox_btn.configure(bg=COLORS["border"], fg=COLORS["text"])
                if self._mail_trash_btn:
                    self._mail_trash_btn.configure(bg=COLORS["warn"], fg="white")
        if self._mail_header:
            self._mail_header.configure(
                text="TRASH" if self._mail_folder == "trash" else "INBOX",
                fg=COLORS["warn"] if self._mail_folder == "trash" else COLORS["accent"],
            )
        self._rebuild_mail_buttons()
        self._populate_mail_list(self._mail_listbox)
        if self._mail_meta:
            folder_hint = "Trash — select to read. Delete Forever removes permanently."
            inbox_hint = "Select a message"
            self._mail_meta.configure(
                text=folder_hint if self._mail_folder == "trash" else inbox_hint,
                fg=COLORS["muted"],
            )
        if self._mail_viewer:
            self._mail_viewer.configure(state=tk.NORMAL)
            self._mail_viewer.delete("1.0", tk.END)
            self._mail_viewer.configure(state=tk.DISABLED)
        msgs = self._mail_current_messages()
        if msgs:
            self._mail_listbox.selection_set(0)
            self._mail_listbox.event_generate("<<ListboxSelect>>")

    def _rebuild_mail_buttons(self) -> None:
        if not self._mail_btn_row:
            return
        for w in self._mail_btn_row.winfo_children():
            w.destroy()
        row = self._mail_btn_row
        if self._mail_folder == "trash":
            tk.Button(row, text="Delete Forever", command=self._permanent_delete_mail,
                      bg=COLORS["error"], fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT)
            tk.Button(row, text="Restore to Inbox", command=self._restore_selected_mail,
                      bg=COLORS["accent_dim"], fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=8)
            tk.Button(row, text="Empty Trash", command=self._empty_mail_trash,
                      bg=COLORS["border"], fg=COLORS["warn"], relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=8)
        else:
            tk.Button(row, text="Move to Trash", command=self._delete_selected_mail,
                      bg=COLORS["error"], fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT)
            tk.Button(row, text="Trash All Read", command=self._delete_read_mail,
                      bg=COLORS["border"], fg=COLORS["warn"], relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=8)
            tk.Button(row, text="Mark All Read", command=self._mark_all_mail_read,
                      bg=COLORS["border"], fg=COLORS["text"], relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=8)
        tk.Label(
            row, text="Del/⌫ = trash or delete forever",
            fg=COLORS["muted"], bg=COLORS["window"], font=F(9),
        ).pack(side=tk.RIGHT, padx=(8, 0))
        tk.Button(row, text="Open Job Board", command=self.open_job_board,
                  bg=COLORS["accent_dim"], fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=8)

    def _populate_mail_list(self, listbox: tk.Listbox) -> None:
        listbox.delete(0, tk.END)
        for msg in self._mail_current_messages():
            prefix = "● " if not msg.read and self._mail_folder == "inbox" else "   "
            tag = "🗑 " if self._mail_folder == "trash" else prefix
            listbox.insert(tk.END, f"{tag}{msg.subject[:40]}")

    def _clear_mail_viewer(self, status: str) -> None:
        if self._mail_meta:
            self._mail_meta.configure(text=status, fg=COLORS["muted"])
        if self._mail_viewer:
            self._mail_viewer.configure(state=tk.NORMAL)
            self._mail_viewer.delete("1.0", tk.END)
            self._mail_viewer.configure(state=tk.DISABLED)

    def _selected_mail_message(self) -> MailMessage | None:
        if not self._mail_listbox:
            return None
        sel = self._mail_listbox.curselection()
        if not sel:
            return None
        msgs = self._mail_current_messages()
        if sel[0] >= len(msgs):
            return None
        return msgs[sel[0]]

    def _mail_delete_key(self, _event=None) -> str:
        if self._mail_folder == "trash":
            self._permanent_delete_mail()
        else:
            self._delete_selected_mail()
        return "break"

    def _mark_all_mail_read(self) -> None:
        self.game.mail.mark_all_read()
        self._refresh_mail_badge()
        self.refresh_taskbar()
        if self._mail_listbox:
            self._populate_mail_list(self._mail_listbox)

    def _delete_selected_mail(self) -> None:
        if self._mail_folder != "inbox":
            return
        msg = self._selected_mail_message()
        if not msg:
            return
        self.game.mail.trash_message(msg.mail_id)
        self.game.autosave(force=True)
        self._refresh_mail_ui()
        self._clear_mail_viewer("Moved to Trash.")
        self._refresh_mail_badge()
        self.refresh_taskbar()

    def _delete_read_mail(self) -> None:
        if self._mail_folder != "inbox":
            return
        removed = self.game.mail.trash_all_read()
        if removed:
            self.game.autosave(force=True)
        self._refresh_mail_ui()
        self._clear_mail_viewer(
            f"Moved {removed} read message(s) to Trash." if removed else "No read messages to trash."
        )
        self._refresh_mail_badge()
        self.refresh_taskbar()

    def _permanent_delete_mail(self) -> None:
        if self._mail_folder != "trash":
            return
        msg = self._selected_mail_message()
        if not msg:
            return
        self.game.mail.permanent_delete(msg.mail_id)
        self.game.autosave(force=True)
        self._refresh_mail_ui()
        self._clear_mail_viewer("Permanently deleted.")
        self.refresh_taskbar()

    def _restore_selected_mail(self) -> None:
        if self._mail_folder != "trash":
            return
        msg = self._selected_mail_message()
        if not msg:
            return
        self.game.mail.restore_message(msg.mail_id)
        self.game.autosave(force=True)
        self._mail_folder = "inbox"
        self._refresh_mail_ui()
        self._clear_mail_viewer("Restored to Inbox.")
        self._refresh_mail_badge()
        self.refresh_taskbar()

    def _empty_mail_trash(self) -> None:
        if self._mail_folder != "trash":
            return
        removed = self.game.mail.empty_trash()
        if removed:
            self.game.autosave(force=True)
        self._refresh_mail_ui()
        self._clear_mail_viewer(
            f"Emptied trash ({removed} message(s) gone forever)." if removed else "Trash is already empty."
        )
        self.refresh_taskbar()

    def open_terminal(self) -> None:
        if "terminal" in self._built_panels:
            self._show_app("terminal")
            self._arm_terminal_focus()
            self._ensure_terminal_key_catcher()
            return
        title = self._terminal_window_title()
        win = self._window("terminal", title, 820, 580)
        body: tk.Frame = win._body  # type: ignore[attr-defined]
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=0)
        body.rowconfigure(1, weight=1)
        body.rowconfigure(2, weight=0)

        toolbar = tk.Frame(body, bg=COLORS["window"])
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.grid_remove()
        self._terminal_toolbar = toolbar
        quick_lbl = tk.Label(
            toolbar, text="Quick:", fg=COLORS["muted"], bg=COLORS["window"], font=F(9),
        )
        self._terminal_toolbar_label = quick_lbl
        self._terminal_quick_buttons = {}
        for label, cmd in TERMINAL_QUICK_COMMANDS:
            btn = tk.Button(
                toolbar, text=label,
                command=lambda c=cmd: self._gui_run_command(c),
                bg=COLORS["border"], fg=COLORS["text"], relief=tk.FLAT,
                font=F(9), padx=8, pady=2,
            )
            self._terminal_quick_buttons[cmd] = btn
        for verb in self._terminal_used_commands:
            if verb in self._terminal_quick_buttons:
                self._terminal_quick_buttons[verb].pack(side=tk.LEFT, padx=2, pady=4)
        if self._terminal_used_commands:
            quick_lbl.pack(side=tk.LEFT, padx=(8, 6), pady=4)
            toolbar.grid()

        output = scrolledtext.ScrolledText(
            body, bg=COLORS["terminal_bg"], fg=COLORS["terminal_fg"],
            insertbackground=COLORS["prompt_user"], font=MONO(12),
            relief=tk.FLAT, wrap=tk.WORD, takefocus=0, padx=8, pady=8,
        )
        output.grid(row=1, column=0, sticky="nsew")
        output.configure(state=tk.DISABLED)
        self._terminal_output_widget = output

        for tag, color in (
            ("normal", COLORS["terminal_fg"]),
            ("info", COLORS["info"]),
            ("success", COLORS["success"]),
            ("warn", COLORS["warn"]),
            ("error", COLORS["error"]),
            ("teach", COLORS["teach"]),
            ("muted", COLORS["muted"]),
            ("prompt", COLORS["prompt_user"]),
        ):
            output.tag_configure(tag, foreground=color)

        if self._terminal_log:
            self._replay_terminal_log(output)

        cmd_outer = tk.Frame(
            body, bg=COLORS["terminal_bg"],
            highlightthickness=1, highlightbackground=COLORS["border"],
        )
        cmd_outer.grid(row=2, column=0, sticky="ew")
        cmd_outer.columnconfigure(1, weight=1)
        self._terminal_input_frame = cmd_outer

        prompt_frame = tk.Frame(cmd_outer, bg=COLORS["terminal_bg"])
        prompt_frame.grid(row=0, column=0, sticky="w", padx=(8, 0), pady=6)
        self._terminal_prompt_frame = prompt_frame

        entry = tk.Entry(
            cmd_outer,
            bg=COLORS["terminal_bg"], fg=COLORS["terminal_fg"],
            insertbackground=COLORS["prompt_user"],
            font=MONO(12),
            relief=tk.FLAT, bd=0,
            highlightthickness=0,
            selectbackground=COLORS["selection"],
            selectforeground="#ffffff",
        )
        entry.grid(row=0, column=1, sticky="ew", padx=4, pady=6, ipady=4)
        self._terminal_entry = entry
        self._terminal_input = None
        self._terminal_title_lbl = getattr(win, "_title_lbl", None)

        def remember_command(cmd: str) -> None:
            if not cmd:
                return
            if not self._terminal_history or self._terminal_history[-1] != cmd:
                self._terminal_history.append(cmd)
            self._terminal_history_pos = len(self._terminal_history)

        def history_up(_event=None) -> str:
            if not self._terminal_history:
                return "break"
            if self._terminal_history_pos > 0:
                self._terminal_history_pos -= 1
            entry.delete(0, tk.END)
            entry.insert(0, self._terminal_history[self._terminal_history_pos])
            return "break"

        def history_down(_event=None) -> str:
            if not self._terminal_history:
                return "break"
            if self._terminal_history_pos < len(self._terminal_history) - 1:
                self._terminal_history_pos += 1
                entry.delete(0, tk.END)
                entry.insert(0, self._terminal_history[self._terminal_history_pos])
            else:
                self._terminal_history_pos = len(self._terminal_history)
                entry.delete(0, tk.END)
            return "break"

        def execute_command(cmd: str) -> None:
            if not cmd:
                return
            remember_command(cmd)
            sounds.play("click")
            phase_before = self.game.player.phase
            Console.out(self.game.prompt() + cmd, "prompt")
            self.root.update_idletasks()
            self.game.close_terminal = False
            self.game.dispatch(cmd)
            self._reveal_terminal_quick(cmd)
            self._flush_taskbar_refresh()
            if phase_before == "tutorial" and self.game.player.phase == "career":
                self.root.after(150, self._show_graduation_popup)
            elif self.game.defer_career_session:
                self.root.after(50, self._run_deferred_career_session)
            if self._files_list_frame:
                self._refresh_files()
            if "shop" in self._built_panels:
                self.root.after(100, self._maybe_refresh_shop_after_command)
            if self.game.quit_game:
                self._on_quit()
                return
            if self.game.close_terminal:
                self._close_window("terminal")
                return
            self._rebuild_terminal_prompt()
            if self._terminal_title_lbl and self._terminal_title_lbl.winfo_exists():
                self._terminal_title_lbl.configure(text=f"  {self._terminal_window_title()}")
            self._activate_terminal_input()

        def run_command(_event=None) -> str:
            cmd = entry.get().strip()
            entry.delete(0, tk.END)
            execute_command(cmd)
            return "break"

        self._terminal_run_cmd = execute_command
        self._terminal_submit_cmd = run_command

        def paste_clip(_event=None) -> str:
            try:
                text = self.root.clipboard_get()
                if text:
                    entry.insert(tk.INSERT, text.replace("\n", " ").strip())
            except tk.TclError:
                pass
            return "break"

        def focus_cmd(_event=None) -> str:
            self._activate_terminal_input()
            return "break"

        entry.bind("<Return>", run_command)
        entry.bind("<KP_Enter>", run_command)
        entry.bind("<Up>", history_up)
        entry.bind("<Down>", history_down)
        entry.bind("<Control-v>", paste_clip)
        entry.bind("<Control-V>", paste_clip)
        entry.bind("<Button-1>", lambda _e: self._activate_terminal_input())
        cmd_outer.bind("<Button-1>", focus_cmd)
        output.bind("<Button-1>", focus_cmd)
        prompt_frame.bind("<Button-1>", focus_cmd)

        self._install_terminal_key_catcher(entry, run_command)

        self._rebuild_terminal_prompt()
        self._arm_terminal_focus()
        if not self.terminal_booted:
            self.terminal_booted = True
            self.game.banner()
        elif not self._terminal_log:
            self.game.banner()
        self.root.after(150, self._activate_terminal_input)

        self._built_panels.add("terminal")

    def _list_vfs_entries(self, files: dict, directory: str) -> tuple[list[str], list[str]]:
        d = directory.rstrip("/") + "/"
        subdirs: set[str] = set()
        names: list[str] = []
        for path in files:
            if not path.startswith(d) or path == d:
                continue
            rel = path[len(d):]
            if "/" in rel:
                subdirs.add(rel.split("/")[0])
            else:
                names.append(rel)
        return sorted(subdirs), sorted(names)

    def _files_locations(self) -> list[tuple[str, str, dict]]:
        """Return (label, path, files_dict) for each browsable location."""
        p = self.game.player
        locs: list[tuple[str, str, dict]] = [
            ("Home", "/home/hacker", p.files),
            ("Downloads", "/home/hacker/downloads", p.files),
        ]
        if not p.is_local():
            s = self.game.remote_server()
            if s and p.has_remote_shell:
                cwd = p.cwd if p.cwd.startswith("/") else f"/home/{s.hostname}"
                locs.append((f"Remote ({p.connection})", cwd, s.files))
        return locs

    def _save_notes_from_editor(self) -> None:
        editor = self._notes_editor
        if not editor or not editor.winfo_exists():
            return
        notes = self.game._local_notes_file()
        notes.content = editor.get("1.0", "end-1c")
        if notes.content and not notes.content.endswith("\n"):
            notes.content += "\n"
        self.game.autosave(force=True)

    def _schedule_notes_save(self) -> None:
        if self._notes_save_job:
            try:
                self.root.after_cancel(self._notes_save_job)
            except tk.TclError:
                pass
        self._notes_save_job = self.root.after(800, self._flush_notes_save)

    def _flush_notes_save(self) -> None:
        self._notes_save_job = None
        self._save_notes_from_editor()

    def open_notes(self) -> None:
        if "notes" in self._built_panels:
            self._show_app("notes")
            if self._notes_editor and self._notes_editor.winfo_exists():
                self._notes_editor.focus_set()
            return
        win = self._window("notes", "Notes — scratchpad", 440, 520)
        body: tk.Frame = win._body  # type: ignore[attr-defined]

        tk.Label(
            body, text="SCRATCHPAD", fg=COLORS["accent"], bg=COLORS["window"],
            font=F(14, bold=True),
        ).pack(anchor=tk.W)
        tk.Label(
            body,
            text=(
                f"{NOTES_PATH} — jot IPs, targets, and passwords while you hack. "
                "Drag this window next to Terminal or Files. Auto-saves."
            ),
            fg=COLORS["muted"], bg=COLORS["window"], font=F(10),
            wraplength=400, justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(4, 8))

        notes = self.game._local_notes_file()
        editor = scrolledtext.ScrolledText(
            body, bg=COLORS["terminal_bg"], fg=COLORS["text"],
            font=MONO(11), relief=tk.FLAT, wrap=tk.WORD,
            insertbackground=COLORS["accent"], undo=True,
        )
        editor.pack(fill=tk.BOTH, expand=True)
        editor.insert("1.0", notes.read())
        self._notes_editor = editor

        def on_edit(_event=None) -> None:
            try:
                if editor.edit_modified():
                    editor.edit_modified(False)
                    self._schedule_notes_save()
            except tk.TclError:
                pass

        editor.bind("<<Modified>>", on_edit)
        editor.bind("<FocusOut>", lambda _e: self._save_notes_from_editor())

        btn_row = tk.Frame(body, bg=COLORS["window"])
        btn_row.pack(fill=tk.X, pady=(8, 0))
        tk.Button(
            btn_row, text="Save Now", command=lambda: (self._save_notes_from_editor(), sounds.play("success")),
            bg=COLORS["accent_dim"], fg="white", relief=tk.FLAT, padx=12, pady=4,
        ).pack(side=tk.LEFT)
        tk.Button(
            btn_row, text="Open Terminal", command=self.open_terminal,
            bg=COLORS["border"], fg=COLORS["text"], relief=tk.FLAT, padx=12, pady=4,
        ).pack(side=tk.LEFT, padx=8)
        tk.Button(
            btn_row, text="Open Files", command=self.open_files,
            bg=COLORS["border"], fg=COLORS["text"], relief=tk.FLAT, padx=12, pady=4,
        ).pack(side=tk.LEFT)

        self._built_panels.add("notes")

    def open_files(self) -> None:
        if "files" in self._built_panels:
            self._show_app("files")
            self._refresh_files()
            return
        win = self._window("files", "Files — Local & Remote", 760, 520)
        body: tk.Frame = win._body  # type: ignore[attr-defined]

        tk.Label(body, text="FILE MANAGER", fg=COLORS["accent"], bg=COLORS["window"],
                 font=F(14, bold=True)).pack(anchor=tk.W)
        tk.Label(
            body,
            text="View downloaded loot and remote files. Hack in Terminal, then download — files appear under Downloads.",
            fg=COLORS["muted"], bg=COLORS["window"], font=F(10), wraplength=700, justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(4, 8))

        panes = tk.Frame(body, bg=COLORS["window"])
        panes.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(panes, bg=COLORS["window"], width=280)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)
        self._files_list_frame = left

        right = tk.Frame(panes, bg=COLORS["terminal_bg"])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))
        self._files_preview_frame = right

        btn_row = tk.Frame(body, bg=COLORS["window"])
        btn_row.pack(fill=tk.X, pady=(8, 0))
        tk.Button(btn_row, text="↻ Refresh", command=self._refresh_files,
                  bg=COLORS["border"], fg=COLORS["text"], relief=tk.FLAT, padx=10).pack(side=tk.LEFT)
        tk.Button(btn_row, text="Open Terminal", command=self.open_terminal,
                  bg=COLORS["accent_dim"], fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=8)
        tk.Button(btn_row, text="Open Notes", command=self.open_notes,
                  bg=COLORS["border"], fg=COLORS["text"], relief=tk.FLAT, padx=10).pack(side=tk.LEFT)

        self._refresh_files()
        self._built_panels.add("files")

    def _refresh_files(self) -> None:
        if not self._files_list_frame or not self._files_preview_frame:
            return
        for w in self._files_list_frame.winfo_children():
            w.destroy()
        for w in self._files_preview_frame.winfo_children():
            w.destroy()

        locs = self._files_locations()
        for label, path, files in locs:
            tk.Label(
                self._files_list_frame,
                text=f"📂 {label}  ({path})",
                fg=COLORS["accent"], bg=COLORS["window"],
                font=F(10, bold=True), anchor=tk.W,
            ).pack(fill=tk.X, padx=4, pady=(10, 4))

            subdirs, names = self._list_vfs_entries(files, path)
            if not subdirs and not names:
                tk.Label(
                    self._files_list_frame,
                    text="  (empty)",
                    fg=COLORS["muted"], bg=COLORS["window"], font=F(9), anchor=tk.W,
                ).pack(fill=tk.X, padx=8)
                continue

            for sub in subdirs:
                full = f"{path.rstrip('/')}/{sub}"
                tk.Button(
                    self._files_list_frame,
                    text=f"  📁 {sub}/",
                    anchor=tk.W,
                    command=lambda f=full, fl=files: self._files_show_dir(f, fl),
                    bg=COLORS["border"], fg=COLORS["text"], relief=tk.FLAT,
                    font=F(9), padx=6, pady=2,
                ).pack(fill=tk.X, padx=8, pady=1)

            for name in names:
                full = f"{path.rstrip('/')}/{name}"
                tk.Button(
                    self._files_list_frame,
                    text=f"  📄 {name}",
                    anchor=tk.W,
                    command=lambda f=full, fl=files: self._files_show_file(f, fl),
                    bg=COLORS["window"], fg=COLORS["text"], relief=tk.FLAT,
                    font=F(9), padx=6, pady=2,
                ).pack(fill=tk.X, padx=8, pady=1)

        tk.Label(
            self._files_preview_frame,
            text="Select a file to preview its contents.",
            fg=COLORS["muted"], bg=COLORS["terminal_bg"], font=F(10),
        ).pack(anchor=tk.NW, padx=12, pady=12)

    def _files_show_dir(self, path: str, files: dict) -> None:
        if not self._files_preview_frame:
            return
        for w in self._files_preview_frame.winfo_children():
            w.destroy()
        subdirs, names = self._list_vfs_entries(files, path)
        tk.Label(
            self._files_preview_frame,
            text=f"📁 {path}/",
            fg=COLORS["accent"], bg=COLORS["terminal_bg"], font=F(11, bold=True),
        ).pack(anchor=tk.NW, padx=12, pady=(12, 6))
        listing = "\n".join(f"  {d}/" for d in subdirs) + "\n" + "\n".join(f"  {n}" for n in names)
        tk.Label(
            self._files_preview_frame,
            text=listing.strip() or "(empty directory)",
            fg=COLORS["text"], bg=COLORS["terminal_bg"], font=MONO(10),
            justify=tk.LEFT, anchor=tk.NW,
        ).pack(anchor=tk.NW, padx=12)

    def _files_show_file(self, path: str, files: dict) -> None:
        if not self._files_preview_frame:
            return
        for w in self._files_preview_frame.winfo_children():
            w.destroy()
        vf = files.get(path)
        if not vf:
            tk.Label(self._files_preview_frame, text="File not found.", fg=COLORS["error"],
                     bg=COLORS["terminal_bg"]).pack(padx=12, pady=12)
            return

        editable = path == NOTES_PATH and files is self.game.player.files and self.game.player.is_local()
        tk.Label(
            self._files_preview_frame,
            text=f"📄 {path}" + (" — editable scratchpad" if editable else ""),
            fg=COLORS["accent"], bg=COLORS["terminal_bg"], font=F(10, bold=True),
        ).pack(anchor=tk.NW, padx=12, pady=(12, 4))

        if editable:
            tk.Label(
                self._files_preview_frame,
                text="Save IPs, targets, passwords — persists across saves.",
                fg=COLORS["muted"], bg=COLORS["terminal_bg"], font=F(9),
            ).pack(anchor=tk.NW, padx=12, pady=(0, 4))
            editor = scrolledtext.ScrolledText(
                self._files_preview_frame, bg=COLORS["terminal_bg"], fg=COLORS["text"],
                font=MONO(11), relief=tk.FLAT, wrap=tk.WORD, height=18,
                insertbackground=COLORS["accent"],
            )
            editor.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
            editor.insert("1.0", vf.read())
            editor.focus_set()

            def save_notes() -> None:
                vf.content = editor.get("1.0", "end-1c")
                if vf.content and not vf.content.endswith("\n"):
                    vf.content += "\n"
                self.game.autosave(force=True)
                sounds.play("success")

            btn_row = tk.Frame(self._files_preview_frame, bg=COLORS["terminal_bg"])
            btn_row.pack(fill=tk.X, padx=12, pady=(0, 12))
            tk.Button(
                btn_row, text="Save Notes", command=save_notes,
                bg=COLORS["accent_dim"], fg="white", relief=tk.FLAT, padx=12, pady=4,
            ).pack(side=tk.LEFT)
            tk.Button(
                btn_row, text="Open Notes App", command=self.open_notes,
                bg=COLORS["accent_dim"], fg="white", relief=tk.FLAT, padx=12, pady=4,
            ).pack(side=tk.LEFT)
            tk.Button(
                btn_row, text="Show in Terminal (note)", command=lambda: self._gui_run_command("note"),
                bg=COLORS["border"], fg=COLORS["text"], relief=tk.FLAT, padx=12, pady=4,
            ).pack(side=tk.LEFT, padx=8)
            return

        content = vf.read()
        preview = content[:12000] + ("\n\n… (truncated — open in Terminal with cat)" if len(content) > 12000 else "")
        viewer = scrolledtext.ScrolledText(
            self._files_preview_frame, bg=COLORS["terminal_bg"], fg=COLORS["text"],
            font=MONO(10), relief=tk.FLAT, wrap=tk.WORD,
        )
        viewer.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        viewer.insert("1.0", preview)
        viewer.configure(state=tk.DISABLED)

    def open_job_board(self) -> None:
        if "jobs" in self._built_panels:
            self._show_app("jobs")
            return
        win = self._window("jobs", "Job Board — Secure Contracts", 620, 480)
        body: tk.Frame = win._body  # type: ignore[attr-defined]
        p = self.game.player

        tk.Label(body, text="CONTRACT CHANNEL", fg=COLORS["accent"], bg=COLORS["window"],
                 font=F(14, bold=True)).pack(anchor=tk.W)
        tk.Label(body, text=p.wallet_label(), fg=COLORS["muted"], bg=COLORS["window"],
                 font=F(10)).pack(anchor=tk.W, pady=(4, 12))

        if p.phase == "tutorial":
            tk.Label(
                body,
                text="Complete training to unlock live contracts.\n"
                     "Check Mail for messages from your training officer.",
                fg=COLORS["warn"], bg=COLORS["window"], font=F(11),
                justify=tk.LEFT,
            ).pack(anchor=tk.W, pady=8)
            lesson = self.game.tutorial.current()
            tk.Label(body, text=f"Current: {lesson.title}", fg=COLORS["text"],
                     bg=COLORS["window"], font=F(10, bold=True)).pack(anchor=tk.W, pady=(16, 4))
            tk.Label(body, text=lesson.objective, fg=COLORS["muted"], bg=COLORS["window"],
                     font=F(10), wraplength=560, justify=tk.LEFT).pack(anchor=tk.W)
            tk.Button(body, text="Open Training", command=self.open_training,
                      bg=COLORS["accent_dim"], fg="white", relief=tk.FLAT, padx=12, pady=4).pack(anchor=tk.W, pady=12)
            return

        if p.phase == "career":
            from retention import RetentionManager
            from session_content import HourlyManager, LateralManager

            HourlyManager.refresh(self.game)
            s = self.game.session
            hourly_m = next((m for m in self.game.missions.missions if m.hourly_event and not m.completed), None)
            if hourly_m:
                rem = HourlyManager.time_remaining()
                tk.Label(body, text=f"⚡ HOURLY FLASH ({rem} left): {hourly_m.briefing}",
                         fg=COLORS["warn"], bg=COLORS["window"], font=F(9, bold=True),
                         wraplength=560, justify=tk.LEFT).pack(anchor=tk.W, pady=(4, 0))
            if s.active_chain_id:
                chain = LateralManager.chain_by_id(s.active_chain_id)
                step = LateralManager.active_step(self.game)
                if chain and step:
                    tk.Label(body, text=f"LATERAL: {chain['name']} — step {s.chain_step + 1}/{len(chain['steps'])}: {step['label']}",
                             fg=COLORS["accent"], bg=COLORS["window"], font=F(9, bold=True),
                             wraplength=560, justify=tk.LEFT).pack(anchor=tk.W, pady=(4, 0))
            if RetentionManager.bridge_active(self.game):
                tk.Label(body, text="PREP TONIGHT (type 'bridge' in terminal):",
                         fg=COLORS["warn"], bg=COLORS["window"], font=F(9, bold=True)).pack(anchor=tk.W, pady=(4, 0))
                prep = tk.Label(body, text=RetentionManager.bridge_summary(self.game).replace("  ", ""),
                                fg=COLORS["muted"], bg=COLORS["window"], font=F(9),
                                justify=tk.LEFT, wraplength=560)
                prep.pack(anchor=tk.W, pady=(2, 4))

        scroll = scrolledtext.ScrolledText(body, height=16, bg=COLORS["terminal_bg"],
                                           fg=COLORS["text"], font=F(11), relief=tk.FLAT)
        scroll.pack(fill=tk.BOTH, expand=True)
        for m in self.game.missions.missions:
            scroll.insert(tk.END, f"{m.status_line()}{__import__('rival_ai', fromlist=['RivalAIManager']).RivalAIManager.race_progress_line(self.game, m)}\n\n")
        scroll.configure(state=tk.DISABLED)

        d = self.game.daily
        daily_txt = f"Today's challenge: COMPLETE (+${d.reward})" if d.completed else (
            f"Today's challenge: {d.description} — ${d.reward}"
        )
        r = self.game.retention
        tk.Label(body, text=daily_txt, fg=COLORS["teach"], bg=COLORS["window"],
                 font=F(10), wraplength=560, justify=tk.LEFT).pack(anchor=tk.W, pady=(8, 4))
        tk.Label(body, text=f"Streak: {r.streak} days | Season {r.season_tier}/{len(SEASON_TIERS)} | Ops {len(r.completed_operations)} done",
                 fg=COLORS["muted"], bg=COLORS["window"], font=F(9)).pack(anchor=tk.W, pady=(0, 4))
        btn_row_intel = tk.Frame(body, bg=COLORS["window"])
        btn_row_intel.pack(fill=tk.X, pady=(0, 4))
        tk.Button(btn_row_intel, text="Intel (intel)", command=self.open_terminal,
                  bg=COLORS["border"], fg=COLORS["text"], relief=tk.FLAT, padx=8, pady=2).pack(side=tk.LEFT)
        tk.Button(btn_row_intel, text="Rival Dossier (rivals)", command=self.open_terminal,
                  bg=COLORS["border"], fg=COLORS["warn"], relief=tk.FLAT, padx=8, pady=2).pack(side=tk.LEFT, padx=6)

        tk.Label(body, text="Contract details also arrive via Mail from brokers.",
                 fg=COLORS["muted"], bg=COLORS["window"], font=F(9)).pack(anchor=tk.W, pady=(4, 0))

        btn_row = tk.Frame(body, bg=COLORS["window"])
        btn_row.pack(fill=tk.X, pady=(10, 0))
        tk.Button(btn_row, text="Request New Contract", command=self._request_contract,
                  bg=COLORS["accent_dim"], fg="white", relief=tk.FLAT, padx=12, pady=4).pack(side=tk.LEFT)
        self._built_panels.add("jobs")

    def open_social_board(self) -> None:
        from social_board import BOARD_NAMES, SocialBoardManager

        if "board" in self._built_panels:
            self._show_app("board")
            return
        win = self._window("board", "Darknet Board — Social Channels", 680, 520)
        body: tk.Frame = win._body  # type: ignore[attr-defined]
        p = self.game.player

        tk.Label(body, text="DARKNET BOARDS", fg=COLORS["accent"], bg=COLORS["window"],
                 font=F(14, bold=True)).pack(anchor=tk.W)
        if p.phase not in ("career", "endless"):
            tk.Label(body, text="Complete training to access the board.",
                     fg=COLORS["warn"], bg=COLORS["window"]).pack(anchor=tk.W, pady=12)
            return

        SocialBoardManager.seed_if_needed(self.game)
        tk.Label(body, text=f"Karma: {self.game.board.karma}  |  Boards: {', '.join(BOARD_NAMES)}",
                 fg=COLORS["muted"], bg=COLORS["window"], font=F(10)).pack(anchor=tk.W, pady=(4, 8))

        scroll = scrolledtext.ScrolledText(body, height=18, bg=COLORS["terminal_bg"],
                                           fg=COLORS["text"], font=F(10), relief=tk.FLAT)
        scroll.pack(fill=tk.BOTH, expand=True)
        for post in SocialBoardManager.list_posts(self.game, limit=20):
            tag = " [YOU]" if post.player_post else ""
            scroll.insert(tk.END, f"/{post.board}/{tag} {post.author}: {post.title}\n")
            scroll.insert(tk.END, f"  {post.body[:200]}{'...' if len(post.body) > 200 else ''}\n")
            scroll.insert(tk.END, f"  id={post.post_id}  +{post.likes} likes\n\n")
        scroll.configure(state=tk.DISABLED)

        tk.Label(body, text="Terminal: board post flex Title | body  |  board upvote post-0001",
                 fg=COLORS["muted"], bg=COLORS["window"], font=F(9)).pack(anchor=tk.W, pady=(8, 0))
        self._built_panels.add("board")

    def open_shop(self) -> None:
        if "shop" in self._built_panels:
            self._show_app("shop")
            p = self.game.player
            if (
                p.phase == "tutorial"
                and p.tutorial_step >= len(TUTORIAL_CURRICULUM) - 1
                and p.firewall_level >= 2
            ):
                self.game.tutorial.reconcile_stuck_lessons()
                if self.game.player.phase == "career":
                    self.root.after(200, self._show_graduation_popup)
            return
        win = self._window("shop", "Black Market — Upgrades", 680, 580)
        body: tk.Frame = win._body  # type: ignore[attr-defined]
        p = self.game.player

        tk.Label(body, text="BLACK MARKET SHOP", fg=COLORS["accent"], bg=COLORS["window"],
                 font=F(14, bold=True)).pack(anchor=tk.W)
        wallet = tk.Label(body, text=p.wallet_label(), fg=COLORS["muted"], bg=COLORS["window"],
                          font=F(10))
        wallet.pack(anchor=tk.W, pady=(4, 4))

        tk.Label(
            body,
            text=(
                "Upgrades (cpu, firewall) level your gear. Tools (hydra, hashcat, vpn_pro) are permanent. "
                "Consumables are bought into inventory — activate with use <item> in Terminal "
                "(botnet payloads use infect miner / infect ddos instead)."
            ),
            fg=COLORS["muted"], bg=COLORS["window"], font=F(9), wraplength=620, justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(0, 6))

        if p.phase == "career":
            help_frame = tk.Frame(body, bg=COLORS["terminal_bg"], padx=8, pady=6)
            help_frame.pack(fill=tk.X, pady=(0, 8))
            for line in defense_firewall_help(self.game):
                fg = COLORS["accent"] if line.startswith("FIREWALL") else COLORS["text"]
                tk.Label(
                    help_frame, text=line, fg=fg, bg=COLORS["terminal_bg"],
                    font=F(9, bold=True) if line.startswith("FIREWALL") else F(9),
                    anchor=tk.W, justify=tk.LEFT, wraplength=600,
                ).pack(anchor=tk.W)

        if not p.is_local():
            warn_row = tk.Frame(body, bg=COLORS["window"])
            warn_row.pack(fill=tk.X, pady=(0, 8))
            tk.Label(
                warn_row,
                text=f"Connected to {p.connection} — disconnect to shop safely.",
                fg=COLORS["warn"], bg=COLORS["window"], font=F(10),
            ).pack(side=tk.LEFT)
            tk.Button(
                warn_row, text="Disconnect (go home)",
                command=lambda: (self._gui_run_command("disconnect"), self.root.after(300, self._refresh_shop_panel)),
                bg=COLORS["accent_dim"], fg="white", relief=tk.FLAT, padx=10,
            ).pack(side=tk.LEFT, padx=12)

        from faction_consumables import ConsumableManager
        inv_lines = ConsumableManager.inventory_lines(self.game)
        if inv_lines:
            tk.Label(body, text="Consumables:", fg=COLORS["muted"], bg=COLORS["window"],
                     font=F(10, bold=True)).pack(anchor=tk.W)
            for line in inv_lines:
                tk.Label(body, text=f"  {line}", fg=COLORS["text"], bg=COLORS["window"],
                         font=F(9)).pack(anchor=tk.W, padx=8)

        if not p.is_local():
            tk.Label(
                body,
                text="Return home to purchase upgrades (or click Disconnect above).",
                fg=COLORS["muted"], bg=COLORS["window"], font=F(9),
            ).pack(anchor=tk.W, pady=(8, 0))
            self._built_panels.add("shop")
            return

        if (
            p.phase == "tutorial"
            and p.tutorial_step >= len(TUTORIAL_CURRICULUM) - 1
            and p.firewall_level >= 2
        ):
            grad_row = tk.Frame(body, bg=COLORS["window"])
            grad_row.pack(fill=tk.X, pady=(0, 8))
            tk.Label(
                grad_row,
                text="Final lesson: firewall L2+ ready — click to finish training.",
                fg=COLORS["success"], bg=COLORS["window"], font=F(10, bold=True),
            ).pack(side=tk.LEFT)
            tk.Button(
                grad_row, text="Finish Training",
                command=self._finish_training_from_shop,
                bg=COLORS["accent_dim"], fg="white", relief=tk.FLAT, padx=12, pady=4,
            ).pack(side=tk.LEFT, padx=12)

        list_frame = tk.Frame(body, bg=COLORS["window"])
        list_frame.pack(fill=tk.BOTH, expand=True)

        scroll = tk.Canvas(list_frame, bg=COLORS["window"], highlightthickness=0, bd=0)
        scroll_sb = tk.Scrollbar(list_frame, orient=tk.VERTICAL, command=scroll.yview)
        scroll_inner = tk.Frame(scroll, bg=COLORS["window"])
        scroll_inner.bind("<Configure>", lambda _e: scroll.configure(scrollregion=scroll.bbox("all")))
        scroll.create_window((0, 0), window=scroll_inner, anchor=tk.NW)
        scroll.configure(yscrollcommand=scroll_sb.set)
        scroll.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll_sb.pack(side=tk.RIGHT, fill=tk.Y)
        list_frame = scroll_inner

        def refresh_wallet() -> None:
            wallet.configure(text=p.wallet_label())
            self.refresh_taskbar()

        def refresh_shop() -> None:
            self._refresh_shop_panel()

        def buy_item(key: str) -> None:
            sounds.play("click")
            if Shop.buy(p, key):
                sounds.play("success")
                graduated = self.game.on_shop_purchase(key)
                refresh_wallet()
                refresh_shop()
                self.refresh_taskbar()
                if graduated:
                    self._show_graduation_popup()
            elif (
                key == "firewall"
                and p.phase == "tutorial"
                and p.tutorial_step >= len(TUTORIAL_CURRICULUM) - 1
                and p.firewall_level >= 2
            ):
                # Already have firewall L2+ but buy failed (maxed / low credits) — still graduate
                self._finish_training_from_shop()

        for item in SHOP_CATALOG:
            row = tk.Frame(list_frame, bg=COLORS["border"], pady=6, padx=8)
            row.pack(fill=tk.X, pady=4)

            if item.key in ("cpu", "firewall"):
                lvl = p.cpu_level if item.key == "cpu" else p.firewall_level
                if lvl >= item.max_level:
                    price_text = "MAXED"
                    state = tk.DISABLED
                else:
                    price_text = f"${item.base_cost * (lvl + 1)}"
                    state = tk.NORMAL
            elif item.consumable:
                from faction_consumables import ConsumableManager, FactionRepManager
                owned = ConsumableManager.inventory_count(self.game, item.key)
                cost = int(item.base_cost * FactionRepManager.consumable_discount(self.game))
                price_text = f"${cost} (x{owned})"
                state = tk.NORMAL
            else:
                owned = item.key in p.owned_tools
                price_text = "OWNED" if owned else f"${item.base_cost}"
                state = tk.DISABLED if owned else tk.NORMAL

            tk.Label(row, text=item.name, fg=COLORS["text"], bg=COLORS["border"],
                     font=F(11, bold=True), width=16, anchor=tk.W).pack(side=tk.LEFT)
            text_col = tk.Frame(row, bg=COLORS["border"])
            text_col.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
            tk.Label(text_col, text=item.description, fg=COLORS["text"], bg=COLORS["border"],
                     font=F(9), wraplength=340, justify=tk.LEFT, anchor=tk.W).pack(anchor=tk.W)
            if item.detail:
                tk.Label(text_col, text=item.detail, fg=COLORS["muted"], bg=COLORS["border"],
                         font=F(8), wraplength=340, justify=tk.LEFT, anchor=tk.W).pack(anchor=tk.W, pady=(2, 0))
            tk.Label(row, text=price_text, fg=COLORS["accent"], bg=COLORS["border"],
                     font=F(10, bold=True), width=8).pack(side=tk.RIGHT, padx=(4, 8))
            tk.Button(
                row, text="BUY", command=lambda k=item.key: buy_item(k),
                bg=COLORS["accent_dim"], fg="white", relief=tk.FLAT, padx=10,
                state=state,
            ).pack(side=tk.RIGHT)
        self._built_panels.add("shop")

    def _refresh_shop_panel(self) -> None:
        if "shop" not in self._built_panels:
            return
        self._close_window("shop")
        self.open_shop()

    def _maybe_refresh_shop_after_command(self) -> None:
        if self.game.player.is_local() and "shop" in self._built_panels:
            self._refresh_shop_panel()

    def _request_contract(self) -> None:
        self.game.cmd_contracts([])
        self.refresh_taskbar()
        self._close_window("jobs")
        self.open_job_board()

    def open_achievements(self) -> None:
        if "achieve" in self._built_panels:
            self._show_app("achieve")
            return
        win = self._window("achieve", "Achievements & Daily", 560, 440)
        body: tk.Frame = win._body  # type: ignore[attr-defined]

        tk.Label(body, text="ACHIEVEMENTS", fg=COLORS["accent"], bg=COLORS["window"],
                 font=F(14, bold=True)).pack(anchor=tk.W)
        scroll = scrolledtext.ScrolledText(body, height=12, bg=COLORS["terminal_bg"],
                                           fg=COLORS["text"], font=F(10), relief=tk.FLAT)
        scroll.pack(fill=tk.BOTH, expand=True, pady=8)
        for key, desc in ACHIEVEMENTS.items():
            mark = "[x]" if key in self.game.achievements.unlocked else "[ ]"
            scroll.insert(tk.END, f"{mark} {desc}\n")
        scroll.configure(state=tk.DISABLED)

        d = self.game.daily
        daily = "COMPLETE" if d.completed else f"{d.description} — ${d.reward}"
        r = self.game.retention
        tk.Label(body, text=f"TODAY'S CHALLENGE: {daily}", fg=COLORS["teach"],
                 bg=COLORS["window"], font=F(10), wraplength=520).pack(anchor=tk.W)
        tk.Label(body, text=f"Streak: {r.streak} days (best {r.longest_streak}) | Season tier {r.season_tier}/{len(SEASON_TIERS)}",
                 fg=COLORS["muted"], bg=COLORS["window"], font=F(10)).pack(anchor=tk.W, pady=(4, 0))
        self._built_panels.add("achieve")

    def open_training(self) -> None:
        if "training" in self._built_panels:
            self._show_app("training")
            return
        win = self._window("training", "Training Center", 640, 500)
        body: tk.Frame = win._body  # type: ignore[attr-defined]

        tk.Label(body, text="CYBERSECURITY CURRICULUM", fg=COLORS["accent"], bg=COLORS["window"],
                 font=F(14, bold=True)).pack(anchor=tk.W, pady=(0, 4))

        if self.game.player.phase == "tutorial":
            lesson = self.game.tutorial.current()
            if lesson is not None:
                cta = tk.Frame(body, bg=COLORS["window"], padx=10, pady=8,
                               highlightthickness=1, highlightbackground=COLORS["accent"])
                cta.pack(fill=tk.X, pady=(0, 8))
                tk.Label(
                    cta, text="DO THIS NOW", fg=COLORS["accent"], bg=COLORS["window"],
                    font=F(11, bold=True),
                ).pack(anchor=tk.W)
                tk.Label(
                    cta, text=lesson.objective, fg=COLORS["text"], bg=COLORS["window"],
                    font=F(12, bold=True), wraplength=560, justify=tk.LEFT,
                ).pack(anchor=tk.W, pady=(4, 2))
                tk.Label(
                    cta, text=f"Hint: {lesson.hint}", fg=COLORS["muted"], bg=COLORS["window"],
                    font=F(10), wraplength=560, justify=tk.LEFT,
                ).pack(anchor=tk.W)
                tk.Label(
                    cta,
                    text=f"Tutorial wallet: ${self.game.player.tutorial_credits} (career ${self.game.player.money} locked)",
                    fg=COLORS["teach"], bg=COLORS["window"], font=F(9),
                ).pack(anchor=tk.W, pady=(4, 0))
        else:
            done = tk.Frame(body, bg=COLORS["window"], padx=10, pady=8,
                            highlightthickness=1, highlightbackground=COLORS["success"])
            done.pack(fill=tk.X, pady=(0, 8))
            skipped = self.game.tutorial.skipped_training()
            tk.Label(
                done, text="TRAINING COMPLETE" if not skipped else "CHAOS CAREER — SKIPPED BOOT CAMP",
                fg=COLORS["success"], bg=COLORS["window"], font=F(11, bold=True),
            ).pack(anchor=tk.W)
            tk.Label(
                done,
                text=(
                    f"Wallet: {self.game.player.wallet_label()}\n"
                    f"Gear: CPU L{self.game.player.cpu_level} | Firewall L{self.game.player.firewall_level}\n"
                    + (
                        "Shop purchases use your career balance — not tutorial credits."
                        if self.game.player.phase == "career"
                        else "Endless run wallet active."
                    )
                ),
                fg=COLORS["text"], bg=COLORS["window"], font=F(10), wraplength=560, justify=tk.LEFT,
            ).pack(anchor=tk.W, pady=(4, 0))

        tk.Label(body, text="", bg=COLORS["window"]).pack()  # spacer

        scroll = scrolledtext.ScrolledText(body, bg=COLORS["terminal_bg"], fg=COLORS["text"],
                                           font=F(10), relief=tk.FLAT)
        scroll.pack(fill=tk.BOTH, expand=True)

        step = self.game.player.tutorial_step
        for i, lesson in enumerate(TUTORIAL_CURRICULUM):
            if self.game.player.phase == "career":
                mark = "[x]"
            elif i < step:
                mark = "[x]"
            elif i == step:
                mark = "[>]"
            else:
                mark = "[ ]"
            scroll.insert(tk.END, f"{mark} {i + 1}. {lesson.title}\n")
            scroll.insert(tk.END, f"    {lesson.concept}\n")
            scroll.insert(tk.END, f"    Objective: {lesson.objective}\n\n")

        scroll.configure(state=tk.DISABLED)

        btn_row = tk.Frame(body, bg=COLORS["window"])
        btn_row.pack(fill=tk.X, pady=(8, 0))
        tk.Button(btn_row, text="Show Current Lesson in Terminal", command=self._lesson_to_terminal,
                  bg=COLORS["accent_dim"], fg="white", relief=tk.FLAT, padx=12, pady=4).pack(side=tk.LEFT)
        tk.Button(btn_row, text="Open Terminal", command=self.open_terminal,
                  bg=COLORS["border"], fg=COLORS["text"], relief=tk.FLAT, padx=12, pady=4).pack(side=tk.LEFT, padx=8)
        self._built_panels.add("training")

    def _lesson_to_terminal(self) -> None:
        self.open_terminal()
        self.game.cmd_lesson([])

    def _refresh_botnet_panel(self) -> None:
        viewer = self._botnet_text
        if not viewer or not viewer.winfo_exists():
            return
        from botnet_system import BotnetManager, BotnetMapRenderer
        from io import StringIO
        import contextlib
        from main import Console

        buf = StringIO()
        old = Console.handler

        def capture(text: str, tag: str = "normal") -> None:
            buf.write(text)

        Console.handler = capture
        try:
            BotnetManager.cmd_botnet(self.game, [])
        finally:
            Console.handler = old
        viewer.configure(state=tk.NORMAL)
        viewer.delete("1.0", tk.END)
        viewer.insert("1.0", buf.getvalue() or "(no output)")
        viewer.configure(state=tk.DISABLED)
        map_canvas = self._botnet_map_canvas
        if map_canvas and map_canvas.winfo_exists():
            w = max(map_canvas.winfo_width(), 480)
            h = max(map_canvas.winfo_height(), 100)
            BotnetMapRenderer.draw_tk(map_canvas, self.game, w, h)

    def open_botnet(self) -> None:
        if "botnet" in self._built_panels:
            self._show_app("botnet")
            self._refresh_botnet_panel()
            return
        win = self._window("botnet", "Botnet — payloads & income", 560, 520)
        body: tk.Frame = win._body  # type: ignore[attr-defined]

        tk.Label(
            body, text="BOTNET CONTROL", fg=COLORS["accent"], bg=COLORS["window"],
            font=F(14, bold=True),
        ).pack(anchor=tk.W)
        tk.Label(
            body,
            text="Subnet map shows infected nodes. Deploy miners, ransom, virus, deface, or frame kits.",
            fg=COLORS["muted"], bg=COLORS["window"], font=F(10), wraplength=520, justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(4, 4))

        map_canvas = tk.Canvas(body, bg="#1a1a2e", height=110, highlightthickness=1,
                               highlightbackground=COLORS["border"])
        map_canvas.pack(fill=tk.X, pady=(0, 6))
        self._botnet_map_canvas = map_canvas
        map_canvas.bind("<Configure>", lambda _e: self._refresh_botnet_panel())

        viewer = scrolledtext.ScrolledText(
            body, bg=COLORS["terminal_bg"], fg=COLORS["text"],
            font=MONO(10), relief=tk.FLAT, wrap=tk.WORD, height=14,
        )
        viewer.pack(fill=tk.BOTH, expand=True)
        self._botnet_text = viewer

        btn_row = tk.Frame(body, bg=COLORS["window"])
        btn_row.pack(fill=tk.X, pady=(8, 0))
        tk.Button(
            btn_row, text="↻ Refresh", command=self._refresh_botnet_panel,
            bg=COLORS["border"], fg=COLORS["text"], relief=tk.FLAT, padx=10,
        ).pack(side=tk.LEFT)
        tk.Button(
            btn_row, text="Collect $",
            command=lambda: (self._gui_run_command("botnet collect"), self.root.after(150, self._refresh_botnet_panel)),
            bg=COLORS["accent_dim"], fg="white", relief=tk.FLAT, padx=10,
        ).pack(side=tk.LEFT, padx=8)
        tk.Button(
            btn_row, text="Open Terminal", command=self.open_terminal,
            bg=COLORS["border"], fg=COLORS["text"], relief=tk.FLAT, padx=10,
        ).pack(side=tk.LEFT)
        tk.Button(
            btn_row, text="Shop Payloads", command=self.open_shop,
            bg=COLORS["border"], fg=COLORS["text"], relief=tk.FLAT, padx=10,
        ).pack(side=tk.LEFT, padx=8)

        self._built_panels.add("botnet")
        self._refresh_botnet_panel()

    def _start_chaos_career(self) -> None:
        from tkinter import messagebox

        if not ChaosCareerManager.can_start(self.game):
            return
        if not messagebox.askyesno(
            "Chaos Career",
            "Skip training and jump into loud career mode?\n\n"
            "• No tutorial sandbox — real money, rivals, heat\n"
            "• Loud runs (traces left) pay +35%\n"
            "• Botnet worms can spread on hot subnets\n\n"
            "Training will be skipped.",
        ):
            return
        ChaosCareerManager.start(self.game)
        if self.onboarding_banner:
            self.onboarding_banner.destroy()
            self.onboarding_banner = None
            if self._banner_place_id and self.desktop_canvas:
                try:
                    self.desktop_canvas.delete(self._banner_place_id)
                except tk.TclError:
                    pass
                self._banner_place_id = None
        self.refresh_taskbar()
        self._run_deferred_career_session()
        sounds.play("success")
        messagebox.showinfo(
            "CHAOS CAREER LIVE",
            "No training wheels. Scan loud, infect nodes, provoke rivals.\n\n"
            "Open Chaos dock (☠) or type: chaos status",
        )
        self.root.after(400, self.open_mail)
        self.root.after(900, self.open_chaos)

    def open_chaos(self) -> None:
        if "chaos" in self._built_panels:
            self._refresh_chaos_panel()
            self._show_app("chaos")
            return
        win = self._window("chaos", "Chaos — Mischief Console", 560, 480)
        body: tk.Frame = win._body  # type: ignore[attr-defined]
        p = self.game.player

        tk.Label(
            body, text="CHAOS / MISCHIEF", fg=COLORS["error"], bg=COLORS["window"],
            font=F(14, bold=True),
        ).pack(anchor=tk.W)
        tk.Label(
            body,
            text="Loud runs pay more. Heat triggers lockdowns and rival raids. Infections can spread.",
            fg=COLORS["muted"], bg=COLORS["window"], font=F(9), wraplength=500, justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(4, 8))

        self._chaos_viewer = scrolledtext.ScrolledText(
            body, bg=COLORS["terminal_bg"], fg=COLORS["text"],
            font=MONO(11), relief=tk.FLAT, wrap=tk.WORD, height=14,
        )
        self._chaos_viewer.pack(fill=tk.BOTH, expand=True)

        btn_row = tk.Frame(body, bg=COLORS["window"])
        btn_row.pack(fill=tk.X, pady=(8, 0))
        if ChaosCareerManager.can_start(self.game):
            tk.Button(
                btn_row, text="Start Chaos Career", command=self._start_chaos_career,
                bg=COLORS["error"], fg="white", relief=tk.FLAT, padx=10,
            ).pack(side=tk.LEFT)
        if p.phase in ("career", "endless"):
            tk.Button(
                btn_row, text="Provoke Rival", command=lambda: self._gui_run_command("chaos provoke"),
                bg=COLORS["accent_dim"], fg="white", relief=tk.FLAT, padx=10,
            ).pack(side=tk.LEFT, padx=6)
            tk.Button(
                btn_row, text="Chaos Run", command=lambda: self._gui_run_command("chaos run"),
                bg=COLORS["border"], fg=COLORS["warn"], relief=tk.FLAT, padx=10,
            ).pack(side=tk.LEFT, padx=6)
            tk.Button(
                btn_row, text="Ghost Raid", command=lambda: self._gui_run_command("chaos raid"),
                bg=COLORS["border"], fg=COLORS["accent"], relief=tk.FLAT, padx=10,
            ).pack(side=tk.LEFT, padx=6)
        btn_row2 = tk.Frame(body, bg=COLORS["window"])
        btn_row2.pack(fill=tk.X, pady=(4, 0))
        if p.phase in ("career", "endless"):
            tk.Button(
                btn_row2, text="Leak Intel", command=lambda: self._gui_run_command("chaos leak"),
                bg=COLORS["border"], fg=COLORS["text"], relief=tk.FLAT, padx=10,
            ).pack(side=tk.LEFT)
            tk.Button(
                btn_row2, text="War: Rivals", command=lambda: self._gui_run_command("chaos war rivals"),
                bg=COLORS["border"], fg=COLORS["error"], relief=tk.FLAT, padx=10,
            ).pack(side=tk.LEFT, padx=6)
            tk.Button(
                btn_row2, text="Strike Rival", command=lambda: self._gui_run_command("chaos strike"),
                bg=COLORS["border"], fg=COLORS["warn"], relief=tk.FLAT, padx=10,
            ).pack(side=tk.LEFT, padx=6)
            tk.Button(
                btn_row2, text="Deface", command=lambda: self._gui_run_command("chaos deface"),
                bg=COLORS["border"], fg=COLORS["error"], relief=tk.FLAT, padx=10,
            ).pack(side=tk.LEFT, padx=6)
            tk.Button(
                btn_row2, text="Frame Rival", command=lambda: self._gui_run_command("chaos frame"),
                bg=COLORS["border"], fg="#aa66ff", relief=tk.FLAT, padx=10,
            ).pack(side=tk.LEFT, padx=6)
            tk.Button(
                btn_row2, text="Field Manual", command=self.open_training,
                bg=COLORS["border"], fg=COLORS["muted"], relief=tk.FLAT, padx=10,
            ).pack(side=tk.LEFT, padx=6)
            tk.Button(
                btn_row, text="Unlock Chaos Subnet", command=lambda: self._gui_run_command("chaos unlock"),
                bg=COLORS["border"], fg=COLORS["text"], relief=tk.FLAT, padx=10,
            ).pack(side=tk.LEFT, padx=6)
        tk.Button(
            btn_row, text="↻ Refresh", command=self._refresh_chaos_panel,
            bg=COLORS["border"], fg=COLORS["text"], relief=tk.FLAT, padx=10,
        ).pack(side=tk.RIGHT)

        self._built_panels.add("chaos")
        self._refresh_chaos_panel()

    def _refresh_chaos_panel(self) -> None:
        viewer = getattr(self, "_chaos_viewer", None)
        if not viewer or not viewer.winfo_exists():
            return
        lines: list[str] = []
        for block in (
            NotorietyManager.status_lines(self.game),
            MeltdownManager.status_lines(self.game),
            __import__("depth_systems", fromlist=["RivalHeatManager"]).RivalHeatManager.status_lines(self.game),
            __import__("botnet_system", fromlist=["BotnetManager"]).BotnetManager.status_lines(self.game),
            ChaosNewsManager.status_lines(self.game),
        ):
            lines.extend(block)
            lines.append("")
        viewer.configure(state=tk.NORMAL)
        viewer.delete("1.0", tk.END)
        viewer.insert("1.0", "\n".join(lines))
        viewer.configure(state=tk.DISABLED)
        self.refresh_taskbar()

    def _status_lines(self) -> list[str]:
        p = self.game.player
        lines: list[str] = []
        if p.phase == "endless":
            lines.append("Phase:       endless (roguelike run)")
        elif p.phase == "career":
            lines.append("Phase:       career (training complete)")
        else:
            lines.append(f"Phase:       tutorial (lesson {p.tutorial_step + 1}/{len(TUTORIAL_CURRICULUM)})")
        lines.append(p.wallet_label())
        lines.append(f"CPU level:   {p.cpu_level}")
        lines.append(f"Firewall:    {p.firewall_level}  (always on — blocks rivals passively)")
        lines.append(f"Cracker:     tier {p.cracker_tier}")
        lines.append(f"LAN IP:      {p.lan_ip}")
        lines.append(f"Public IP:   {p.public_ip}")
        lines.append(f"Egress IP:   {p.effective_egress_ip}")
        lines.append(f"VPN:         {'active' if p.vpn_active else 'inactive'}")
        lines.append(f"Connected:   {p.prompt_host}")
        lines.append(f"Routes:      {len(p.routes)}")
        lines.append(f"Tools:       {', '.join(sorted(p.owned_tools)) or 'none'}")
        lines.append(f"Unread mail: {self.game.mail.unread_count()}")
        lines.append(f"UI scale:    {UI_SCALE}x (set TERMINALHACKER_UI_SCALE=2.0 for larger text)")
        if self.game.last_autosave:
            lines.append(f"Auto-save:   {self.game.last_autosave} (~/.terminalhacker/save.json)")
        if p.phase == "endless":
            from endless_mode import EndlessManager
            lines.extend(EndlessManager.status_lines(self.game)[1:])
        if p.phase == "career":
            lines.append("")
            lines.extend(defense_firewall_help(self.game))
            lines.append(f"IDS level:   {self.game.blue.ids_level}")
            lines.append(f"Blocks:      {self.game.blue.attacks_blocked} rival attacks stopped")
            lines.append("Tip: defend on in Terminal for active mode (+rep on blocks)")
            lines.append("")
            lines.append(f"Rank:        {ReputationSystem.rank_name(p)} ({p.reputation} rep)")
            lines.append(f"Streak:      {self.game.retention.streak} days (best {self.game.retention.longest_streak})")
            lines.append(f"Season:      tier {self.game.retention.season_tier}/{len(SEASON_TIERS)} ({self.game.retention.season_xp} XP)")
            lines.append(f"Story flags: {', '.join(sorted(self.game.story.flags)) or 'none'}")
            lines.append(f"Board karma: {self.game.board.karma}")
            lines.append(f"Rival threat: {self.game.retention.rival_aggression}/10 ({self.game.retention.last_rival or 'none'})")
            nxt = RANKS[min(p.rank_index + 1, len(RANKS) - 1)]
            if p.rank_index < len(RANKS) - 1:
                lines.append(f"Next rank:   {nxt.name} at {nxt.rep_required} rep")
        elif p.phase == "endless":
            lines.append(f"Best floor:  {self.game.endless.best_floor} (meta)")
        return lines

    def _refresh_status_panel(self) -> None:
        viewer = getattr(self, "_status_viewer", None)
        if viewer and viewer.winfo_exists():
            viewer.configure(state=tk.NORMAL)
            viewer.delete("1.0", tk.END)
            viewer.insert("1.0", "\n".join(self._status_lines()))
            viewer.configure(state=tk.DISABLED)

    def open_status(self) -> None:
        if "status" in self._built_panels:
            self._refresh_status_panel()
            self._show_app("status")
            return
        win = self._window("status", "System Status", 520, 420)
        body: tk.Frame = win._body  # type: ignore[attr-defined]

        viewer = scrolledtext.ScrolledText(
            body, bg=COLORS["window"], fg=COLORS["text"],
            font=MONO(12), relief=tk.FLAT, wrap=tk.WORD,
        )
        viewer.pack(fill=tk.BOTH, expand=True)
        self._status_viewer = viewer
        self._refresh_status_panel()

        p = self.game.player
        btn_row = tk.Frame(body, bg=COLORS["window"])
        btn_row.pack(fill=tk.X, pady=(8, 0))
        tk.Button(btn_row, text="Save Game", command=lambda: (SaveManager.save(self.game), sounds.play("success")),
                  bg=COLORS["accent_dim"], fg="white", relief=tk.FLAT, padx=12).pack(side=tk.LEFT)
        tk.Button(btn_row, text="Load Game", command=self._gui_load_game,
                  bg=COLORS["border"], fg=COLORS["text"], relief=tk.FLAT, padx=12).pack(side=tk.LEFT, padx=8)
        tk.Button(btn_row, text="Restore Backup", command=self._gui_restore_backup,
                  bg=COLORS["border"], fg=COLORS["warn"], relief=tk.FLAT, padx=12).pack(side=tk.LEFT, padx=8)
        if p.phase == "career":
            tk.Button(
                btn_row, text="Defend ON", command=lambda: (
                    self._gui_run_command("defend on"),
                    self.root.after(100, self._refresh_status_panel),
                ),
                bg=COLORS["border"], fg=COLORS["success"], relief=tk.FLAT, padx=10,
            ).pack(side=tk.LEFT, padx=(8, 2))
            tk.Button(
                btn_row, text="Defend OFF", command=lambda: (
                    self._gui_run_command("defend off"),
                    self.root.after(100, self._refresh_status_panel),
                ),
                bg=COLORS["border"], fg=COLORS["muted"], relief=tk.FLAT, padx=10,
            ).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_row, text="Chaos Mode (terminal: chaos)", command=self.open_terminal,
                  bg=COLORS["border"], fg=COLORS["warn"], relief=tk.FLAT, padx=12).pack(side=tk.LEFT, padx=8)
        if p.phase == "career":
            tk.Button(btn_row, text="Endless Run (endless start)", command=self.open_terminal,
                      bg=COLORS["border"], fg=COLORS["accent"], relief=tk.FLAT, padx=12).pack(side=tk.LEFT, padx=8)
        self._built_panels.add("status")

    def _show_graduation_popup(self) -> None:
        from tkinter import messagebox
        p = self.game.player
        sounds.play("success")
        messagebox.showinfo(
            "CAREER CLEARED",
            "Training complete — you are cleared for live operations.\n\n"
            f"Starting balance: ${p.money}\n\n"
            "• Check Mail — your first contracts are waiting\n"
            "• Open Job Board for live paid ops\n"
            "• ☠ Chaos dock — loud runs, botnet map, ghost raids (type: chaos status)\n"
            "• chaos run — roguelike endless floors when you want pure mayhem\n"
            "• Shop: buy gear and defense consumables (burner, zero-day, decoy)\n"
            "• Botnet payloads: dead drops from shard@null.dark (check Mail)\n"
            "• Firewall is ALWAYS on — Defense off only means passive mode\n"
            "• defend on in Terminal for active defense (+rep on blocks)\n"
            "• Rivals probe weak firewalls — upgrade FW in Shop\n\n"
            "Traces and fines now hit your real wallet. Wipe your logs.",
        )
        self._save_restore_notice = ""
        self._run_onboarding()
        self._close_window("shop")
        self.root.after(300, self.open_mail)
        self.root.after(900, self.open_job_board)

    def _finish_training_from_shop(self) -> None:
        phase_before = self.game.player.phase
        self.game.tutorial.reconcile_stuck_lessons()
        self.game.tutorial.check_advance()
        self.game.autosave(force=True)
        self.refresh_taskbar()
        if phase_before == "tutorial" and self.game.player.phase == "career":
            if self.game.defer_career_session:
                self._run_deferred_career_session()
            self._show_graduation_popup()
        else:
            from tkinter import messagebox
            p = self.game.player
            messagebox.showwarning(
                "Not quite yet",
                f"Need firewall level 2+ to graduate.\n"
                f"Current: firewall L{p.firewall_level}\n"
                f"Tutorial budget: ${p.tutorial_credits}",
            )

    def _gui_load_game(self) -> None:
        from progression import SaveManager
        if SaveManager.load(self.game):
            self.game.player._game_ref = self.game
            sounds.play("success")
            self._save_restore_notice = ""
            self.refresh_taskbar()
            self._run_onboarding()

    def _gui_restore_backup(self) -> None:
        from progression import SaveManager
        if SaveManager.restore_backup(self.game):
            self.game.player._game_ref = self.game
            sounds.play("success")
            self._save_restore_notice = "Restored from save backup."
            self.refresh_taskbar()
            self._run_onboarding()

    def run(self) -> None:
        import signal

        def on_sigint(_signum: int, _frame: object) -> None:
            self._on_quit()

        signal.signal(signal.SIGINT, on_sigint)
        # Let Python process SIGINT while tkinter mainloop is blocking.
        self.root.after(200, self._sigint_pump)
        self.root.mainloop()

    def _sigint_pump(self) -> None:
        self.root.after(200, self._sigint_pump)


def run_gui() -> None:
    DesktopApp().run()
