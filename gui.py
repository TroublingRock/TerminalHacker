#!/usr/bin/env python3
"""TerminalHacker desktop GUI — computer-style interface for the simulator."""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import font as tkfont
from tkinter import scrolledtext

import sounds
from main import (
    SHOP_CATALOG,
    Console,
    Game,
    MailMessage,
    Shop,
    TUTORIAL_CURRICULUM,
)
from progression import ACHIEVEMENTS, RANKS, ReputationSystem, SaveManager
from retention import SEASON_TIERS, RetentionManager

# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------

COLORS = {
    "desktop": "#0d1117",
    "taskbar": "#161b22",
    "window": "#1c2128",
    "border": "#30363d",
    "text": "#e6edf3",
    "accent": "#00ff41",
    "accent_dim": "#238636",
    "muted": "#8b949e",
    "terminal_bg": "#0a0e14",
    "terminal_fg": "#00ff41",
    "info": "#79c0ff",
    "success": "#3fb950",
    "warn": "#d29922",
    "error": "#f85149",
    "teach": "#56d4dd",
}

# Text scale — set TERMINALHACKER_UI_SCALE=2.0 in env for even larger UI
UI_SCALE = float(os.environ.get("TERMINALHACKER_UI_SCALE", "1.55"))


def _fs(size: int) -> int:
    return max(10, int(round(size * UI_SCALE)))


def F(size: int, *, bold: bool = False) -> tuple[str, int] | tuple[str, int, str]:
    base: tuple[str, int] | tuple[str, int, str] = ("Helvetica", _fs(size))
    return (*base, "bold") if bold else base


def MONO(size: int, *, bold: bool = False) -> tuple[str, int] | tuple[str, int, str]:
    base: tuple[str, int] | tuple[str, int, str] = ("Courier", _fs(size))
    return (*base, "bold") if bold else base


class DesktopApp:
    """Simulated hacker workstation desktop."""

    ANIM_MS = 14
    ANIM_STEPS = 12

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("TerminalHacker OS")
        self.root.geometry("1280x860")
        self.root.minsize(1024, 720)
        self.root.tk.call("tk", "scaling", UI_SCALE)
        self.root.configure(bg=COLORS["desktop"])

        self.game = Game()
        self.game.gui_mode = True
        self.game.player._game_ref = self.game
        Console.fast_mode = True
        self.game.mail.on_new_mail = self._on_new_mail

        self.open_windows: dict[str, object] = {}
        self.terminal_booted = False
        self.mail_badge: tk.Label | None = None
        self._mail_listbox: tk.Listbox | None = None
        self.taskbar_label: tk.Label | None = None
        self.desktop_view: tk.Frame | None = None
        self.app_shell: tk.Frame | None = None
        self._built_panels: set[str] = set()
        self.hint_label: tk.Label | None = None
        self.onboarding_banner: tk.Frame | None = None
        self._terminal_entry: tk.Entry | None = None

        self._try_resume_save()
        self._build_desktop()
        self._build_taskbar()
        self._run_onboarding()
        self.root.protocol("WM_DELETE_WINDOW", self._on_quit)
        self._schedule_autosave()
        self.refresh_taskbar()

    def _try_resume_save(self) -> None:
        from progression import SAVE_PATH, SaveManager
        if SAVE_PATH.exists():
            SaveManager.load(self.game, quiet=True)

    def _on_quit(self) -> None:
        self.game.autosave(force=True)
        self.root.destroy()

    def _schedule_autosave(self) -> None:
        self.game.autosave(force=True)
        self.refresh_taskbar()
        self.root.after(120_000, self._schedule_autosave)

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

    # ----- layout -----

    def _build_desktop(self) -> None:
        header = tk.Frame(self.root, bg=COLORS["desktop"])
        header.pack(fill=tk.X, padx=24, pady=(20, 8))
        title_font = tkfont.Font(family="Helvetica", size=_fs(22), weight="bold")
        tk.Label(
            header, text="TERMINALHACKER OS", fg=COLORS["accent"],
            bg=COLORS["desktop"], font=title_font,
        ).pack(side=tk.LEFT)
        tk.Label(
            header, text="  v1.9 — Cybersecurity Training Environment",
            fg=COLORS["muted"], bg=COLORS["desktop"], font=F(12),
        ).pack(side=tk.LEFT, padx=(8, 0))

        self.content = tk.Frame(self.root, bg=COLORS["desktop"])
        self.content.pack(fill=tk.BOTH, expand=True)

        self.desktop_view = tk.Frame(self.content, bg=COLORS["desktop"])
        self.desktop_view.pack(fill=tk.BOTH, expand=True)

        icons = tk.Frame(self.desktop_view, bg=COLORS["desktop"])
        icons.pack(fill=tk.BOTH, expand=True, padx=32, pady=16)

        self.app_shell = tk.Frame(self.content, bg=COLORS["window"])

        apps = [
            ("training", "?", "Training", "START HERE — tutorial lessons", self.open_training),
            ("terminal", ">_", "Terminal", "SSH shell & hacking commands", self.open_terminal),
            ("mail", "@", "Mail", "NPC brokers & training messages", self.open_mail),
            ("jobs", "[]", "Job Board", "Paid contracts & missions", self.open_job_board),
            ("board", "//", "Darknet Board", "Intel, rivals, flex & LFG posts", self.open_social_board),
            ("shop", "$", "Black Market", "CPU, firewall & tools", self.open_shop),
            ("achieve", "*", "Achievements", "Badges & daily challenges", self.open_achievements),
            ("status", "#", "System Status", "Hardware, VPN, save/load", self.open_status),
        ]

        for i, app in enumerate(apps):
            row, col = divmod(i, 4)
            self._desktop_icon(icons, *app, row=row, col=col)

        hint = tk.Label(
            self.desktop_view,
            text="Click an icon to launch. Use ← Desktop to return from any app.",
            fg=COLORS["muted"], bg=COLORS["desktop"], font=F(11),
        )
        hint.pack(pady=(0, 12))
        self.hint_label = hint

    def _run_onboarding(self) -> None:
        """Guide new tutorial players — auto-open Training on first launch."""
        p = self.game.player
        if p.phase != "tutorial":
            if self.hint_label:
                self.hint_label.configure(
                    text="Career mode: Terminal for commands, Job Board for contracts, Mail for intel."
                )
            return

        lesson = self.game.tutorial.current()
        if self.onboarding_banner:
            self.onboarding_banner.destroy()

        banner = tk.Frame(self.desktop_view, bg=COLORS["window"], padx=16, pady=12)
        banner.pack(fill=tk.X, padx=24, pady=(0, 4), before=self.hint_label)
        self.onboarding_banner = banner

        tk.Label(
            banner, text="TRAINING MODE — START HERE",
            fg=COLORS["accent"], bg=COLORS["window"],
            font=F(14, bold=True),
        ).pack(anchor=tk.W)
        tk.Label(
            banner,
            text=(
                f"Lesson {p.tutorial_step + 1}/{len(TUTORIAL_CURRICULUM)}: {lesson.title}\n"
                f"{lesson.objective}\n\n"
                "1. Open Training for the full curriculum\n"
                "2. Open Terminal and type commands (start with: lesson)\n"
                "3. Read Mail from your training officer"
            ),
            fg=COLORS["text"], bg=COLORS["window"],
            font=F(12), justify=tk.LEFT, wraplength=int(900 * UI_SCALE),
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
            btn_row, text="Read Mail", command=self.open_mail,
            bg=COLORS["border"], fg=COLORS["text"], relief=tk.FLAT, padx=14, pady=4,
        ).pack(side=tk.LEFT)

        if self.hint_label:
            self.hint_label.configure(
                text="Tutorial uses a $500 training budget — career money unlocks after graduation."
            )
        self.root.after(400, self.open_training)

    def _desktop_icon(
        self, parent: tk.Frame, key: str, glyph: str, name: str, desc: str,
        command, row: int, col: int,
    ) -> None:
        frame = tk.Frame(parent, bg=COLORS["desktop"], cursor="hand2")
        frame.grid(row=row, column=col, padx=24, pady=16, sticky="n")

        icon_wrap = tk.Frame(frame, bg=COLORS["desktop"])
        icon_wrap.pack()

        box = tk.Label(
            icon_wrap, text=glyph, fg=COLORS["accent"], bg=COLORS["window"],
            font=MONO(30, bold=True), width=4, height=2,
            relief=tk.RAISED, bd=2,
        )
        if key == "training" and self.game.player.phase == "tutorial":
            box.configure(bg=COLORS["accent_dim"], fg="white")
        box.pack()

        if key == "mail":
            self.mail_badge = tk.Label(
                icon_wrap, text="", fg="white", bg=COLORS["error"],
                font=F(8, bold=True),
            )
            self._refresh_mail_badge()

        tk.Label(frame, text=name, fg=COLORS["text"], bg=COLORS["desktop"],
                 font=F(11, bold=True)).pack(pady=(6, 0))
        tk.Label(frame, text=desc, fg=COLORS["muted"], bg=COLORS["desktop"],
                 font=F(9), wraplength=150, justify=tk.CENTER).pack()

        def launch(_e=None) -> None:
            sounds.play("click")
            command()

        widgets: list[tk.Widget] = []

        def collect(w: tk.Widget) -> None:
            widgets.append(w)
            for child in w.winfo_children():
                collect(child)

        collect(frame)
        for widget in widgets:
            widget.bind("<Button-1>", launch)
            widget.configure(cursor="hand2")
        box.bind("<Enter>", lambda _e, b=box: b.configure(bg=COLORS["border"]))
        box.bind("<Leave>", lambda _e, b=box: b.configure(bg=COLORS["window"]))

    def _build_taskbar(self) -> None:
        bar = tk.Frame(self.root, bg=COLORS["taskbar"], height=36)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.taskbar_label = tk.Label(
            bar, text="", fg=COLORS["text"], bg=COLORS["taskbar"],
            font=F(10), anchor=tk.W, padx=12,
        )
        self.taskbar_label.pack(fill=tk.X, side=tk.LEFT)

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
        save_txt = ""
        if self.game.last_autosave:
            save_txt = f" | Saved {self.game.last_autosave}"
        self.taskbar_label.configure(
            text=(
                f"  {phase}{lesson}{rank_txt}{save_txt}  |  {wallet}  |  CPU L{p.cpu_level}  |  "
                f"FW L{p.firewall_level}  |  {vpn}{mail_txt}"
            )
        )

    def _show_desktop(self) -> None:
        if self.app_shell:
            self.app_shell.pack_forget()
        if self.desktop_view:
            self.desktop_view.pack(fill=tk.BOTH, expand=True)

    def _window(self, key: str, title: str, width: int, height: int) -> object:
        if key in self.open_windows:
            panel = self.open_windows[key]
            self._show_app(key)
            sounds.play("click")
            return panel

        for other in list(self.open_windows.keys()):
            if other != key:
                self._close_window(other)

        if self.desktop_view:
            self.desktop_view.pack_forget()
        assert self.app_shell is not None

        shell = tk.Frame(self.app_shell, bg=COLORS["window"])
        shell.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)

        titlebar = tk.Frame(shell, bg=COLORS["border"], height=36)
        titlebar.pack(fill=tk.X)
        tk.Label(
            titlebar, text=f"  {title}", fg=COLORS["text"], bg=COLORS["border"],
            font=F(10, bold=True),
        ).pack(side=tk.LEFT, pady=6)
        tk.Button(
            titlebar, text="← Desktop", command=lambda: self._close_window(key),
            bg=COLORS["accent_dim"], fg="white", relief=tk.FLAT, padx=10,
        ).pack(side=tk.RIGHT, padx=8, pady=4)

        body = tk.Frame(shell, bg=COLORS["window"])
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        panel = type("Panel", (), {})()
        panel._body = body
        panel._shell = shell
        panel._key = key
        self.open_windows[key] = panel

        self.app_shell.pack(fill=tk.BOTH, expand=True)
        sounds.play("open")
        return panel

    def _show_app(self, key: str) -> None:
        if self.desktop_view:
            self.desktop_view.pack_forget()
        if self.app_shell:
            self.app_shell.pack(fill=tk.BOTH, expand=True)
        for k, panel in self.open_windows.items():
            shell = panel._shell
            if k == key:
                shell.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)
            else:
                shell.pack_forget()
        if key == "terminal" and self._terminal_entry:
            self.root.after(80, self._focus_terminal_input)

    def _focus_terminal_input(self) -> None:
        if self._terminal_entry and self._terminal_entry.winfo_exists():
            self._terminal_entry.focus_force()

    def _close_window(self, key: str) -> None:
        if key in self.open_windows:
            sounds.play("close")
            self.open_windows[key]._shell.destroy()
            del self.open_windows[key]
            self._built_panels.discard(key)
        if key == "terminal":
            self.game.close_terminal = False
            self._terminal_entry = None
        if key == "mail":
            self._mail_listbox = None
        if not self.open_windows:
            self._show_desktop()

    # ----- apps -----

    def open_mail(self) -> None:
        if "mail" in self._built_panels:
            self._show_app("mail")
            return
        win = self._window("mail", "Mail — Secure Inbox", 720, 500)
        body: tk.Frame = win._body  # type: ignore[attr-defined]

        tk.Label(body, text="INBOX", fg=COLORS["accent"], bg=COLORS["window"],
                 font=F(14, bold=True)).pack(anchor=tk.W)

        panes = tk.Frame(body, bg=COLORS["window"])
        panes.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        left = tk.Frame(panes, bg=COLORS["window"], width=240)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)

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

        def show_message(_event=None) -> None:
            sel = listbox.curselection()
            if not sel:
                return
            msg = self.game.mail.messages[sel[0]]
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

        btn_row = tk.Frame(body, bg=COLORS["window"])
        btn_row.pack(fill=tk.X, pady=(8, 0))
        tk.Button(btn_row, text="Mark All Read", command=self._mark_all_mail_read,
                  bg=COLORS["border"], fg=COLORS["text"], relief=tk.FLAT, padx=10).pack(side=tk.LEFT)
        tk.Button(btn_row, text="Open Job Board", command=self.open_job_board,
                  bg=COLORS["accent_dim"], fg="white", relief=tk.FLAT, padx=10).pack(side=tk.LEFT, padx=8)

        self._populate_mail_list(listbox)
        if self.game.mail.messages:
            listbox.selection_set(0)
            show_message()
        self._built_panels.add("mail")

    def _populate_mail_list(self, listbox: tk.Listbox) -> None:
        listbox.delete(0, tk.END)
        for msg in self.game.mail.messages:
            prefix = "● " if not msg.read else "   "
            listbox.insert(tk.END, f"{prefix}{msg.subject[:42]}")

    def _mark_all_mail_read(self) -> None:
        self.game.mail.mark_all_read()
        self._refresh_mail_badge()
        self.refresh_taskbar()
        if self._mail_listbox:
            self._populate_mail_list(self._mail_listbox)

    def open_terminal(self) -> None:
        if "terminal" in self._built_panels:
            self._show_app("terminal")
            self.root.after(80, self._focus_terminal_input)
            return
        win = self._window("terminal", "Terminal — hacker@localhost", 780, 520)
        body: tk.Frame = win._body  # type: ignore[attr-defined]

        tk.Label(
            body,
            text="Click the command line below, then type. Press Enter to run.",
            fg=COLORS["muted"], bg=COLORS["window"], font=F(10),
        ).pack(anchor=tk.W, pady=(0, 4))

        output = scrolledtext.ScrolledText(
            body, bg=COLORS["terminal_bg"], fg=COLORS["terminal_fg"],
            insertbackground=COLORS["accent"], font=MONO(14),
            relief=tk.FLAT, wrap=tk.WORD, takefocus=0,
        )
        output.pack(fill=tk.BOTH, expand=True)
        output.configure(state=tk.DISABLED)

        for tag, color in (
            ("normal", COLORS["terminal_fg"]), ("info", COLORS["info"]),
            ("success", COLORS["success"]), ("warn", COLORS["warn"]),
            ("error", COLORS["error"]), ("teach", COLORS["teach"]), ("prompt", "#ffffff"),
        ):
            output.tag_configure(tag, foreground=color)

        input_frame = tk.Frame(body, bg=COLORS["window"])
        input_frame.pack(fill=tk.X, pady=(6, 0))
        prompt_lbl = tk.Label(input_frame, text="", fg=COLORS["accent"],
                              bg=COLORS["window"], font=MONO(14))
        prompt_lbl.pack(side=tk.LEFT)
        entry = tk.Entry(
            input_frame, bg=COLORS["terminal_bg"], fg=COLORS["text"],
            insertbackground=COLORS["accent"], font=MONO(14),
            relief=tk.SOLID, bd=2,
            highlightthickness=2, highlightcolor=COLORS["accent"],
            highlightbackground=COLORS["border"],
            takefocus=True,
        )
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6)
        self._terminal_entry = entry

        def focus_input(_event=None) -> None:
            entry.focus_force()
            return "break"

        output.bind("<Button-1>", focus_input)
        body.bind("<Button-1>", lambda e: entry.focus_force() if e.widget == body else None)
        input_frame.bind("<Button-1>", focus_input)

        def append_line(text: str, tag: str = "normal") -> None:
            output.configure(state=tk.NORMAL)
            output.insert(tk.END, text + "\n", tag)
            output.see(tk.END)
            output.configure(state=tk.DISABLED)

        def console_handler(text: str, tag: str = "normal") -> None:
            append_line(text, tag)
            self.refresh_taskbar()
            if tag == "error":
                sounds.play("error")
            elif tag == "warn" and "INTRUSION" in text:
                sounds.play("alert")

        Console.handler = console_handler

        def run_command(_event=None) -> None:
            cmd = entry.get().strip()
            entry.delete(0, tk.END)
            if not cmd:
                return
            sounds.play("click")
            append_line(self.game.prompt() + cmd, "prompt")
            self.game.close_terminal = False
            self.game.dispatch(cmd)
            self.refresh_taskbar()
            if self.game.close_terminal:
                self._close_window("terminal")
                return
            prompt_lbl.configure(text=self.game.prompt())
            entry.focus_set()

        entry.bind("<Return>", run_command)
        entry.bind("<Button-1>", lambda _e: entry.focus_force())
        prompt_lbl.configure(text=self.game.prompt())
        self.root.after(200, self._focus_terminal_input)
        if not self.terminal_booted:
            self.terminal_booted = True
            self.game.banner()

        self._built_panels.add("terminal")

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
            scroll.insert(tk.END, f"{m.status_line()}\n\n")
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
            return
        win = self._window("shop", "Black Market — Upgrades", 640, 520)
        body: tk.Frame = win._body  # type: ignore[attr-defined]
        p = self.game.player

        tk.Label(body, text="BLACK MARKET SHOP", fg=COLORS["accent"], bg=COLORS["window"],
                 font=F(14, bold=True)).pack(anchor=tk.W)
        wallet = tk.Label(body, text=p.wallet_label(), fg=COLORS["muted"], bg=COLORS["window"],
                          font=F(10))
        wallet.pack(anchor=tk.W, pady=(4, 12))

        if not p.is_local():
            tk.Label(body, text="Return to localhost (disconnect) to purchase upgrades.",
                     fg=COLORS["warn"], bg=COLORS["window"]).pack(anchor=tk.W)
            self._built_panels.add("shop")
            return

        list_frame = tk.Frame(body, bg=COLORS["window"])
        list_frame.pack(fill=tk.BOTH, expand=True)

        def refresh_wallet() -> None:
            wallet.configure(text=p.wallet_label())
            self.refresh_taskbar()

        def refresh_shop() -> None:
            self._close_window("shop")
            self.open_shop()

        def buy_item(key: str) -> None:
            sounds.play("click")
            if Shop.buy(p, key):
                sounds.play("success")
                refresh_wallet()
                refresh_shop()

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
            tk.Label(row, text=item.description, fg=COLORS["muted"], bg=COLORS["border"],
                     font=F(9), wraplength=280, justify=tk.LEFT).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
            tk.Label(row, text=price_text, fg=COLORS["accent"], bg=COLORS["border"],
                     font=F(10, bold=True), width=8).pack(side=tk.RIGHT, padx=(4, 8))
            tk.Button(
                row, text="BUY", command=lambda k=item.key: buy_item(k),
                bg=COLORS["accent_dim"], fg="white", relief=tk.FLAT, padx=10,
                state=state,
            ).pack(side=tk.RIGHT)
        self._built_panels.add("shop")

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
                 font=F(14, bold=True)).pack(anchor=tk.W, pady=(0, 8))

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

    def open_status(self) -> None:
        if "status" in self._built_panels:
            self._show_app("status")
            return
        win = self._window("status", "System Status", 480, 360)
        body: tk.Frame = win._body  # type: ignore[attr-defined]
        p = self.game.player

        lines = []
        if p.phase == "endless":
            lines.append("Phase:       endless (roguelike run)")
        elif p.phase == "career":
            lines.append("Phase:       career (training complete)")
        else:
            lines.append(f"Phase:       tutorial (lesson {p.tutorial_step + 1}/{len(TUTORIAL_CURRICULUM)})")
        lines.append(p.wallet_label())
        lines.append(f"CPU level:   {p.cpu_level}")
        lines.append(f"Firewall:    {p.firewall_level}")
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
            lines.append(f"Rank:        {ReputationSystem.rank_name(p)} ({p.reputation} rep)")
            lines.append(f"Streak:      {self.game.retention.streak} days (best {self.game.retention.longest_streak})")
            lines.append(f"Season:      tier {self.game.retention.season_tier}/{len(SEASON_TIERS)} ({self.game.retention.season_xp} XP)")
            lines.append(f"Story flags: {', '.join(sorted(self.game.story.flags)) or 'none'}")
            lines.append(f"Board karma: {self.game.board.karma}")
            lines.append(f"Rival threat: {self.game.retention.rival_aggression}/10 ({self.game.retention.last_rival or 'none'})")
            lines.append(f"IDS level:   {self.game.blue.ids_level}")
            lines.append(f"Defense:     {'ON' if self.game.blue.defense_mode else 'off'}")
            nxt = RANKS[min(p.rank_index + 1, len(RANKS) - 1)]
            if p.rank_index < len(RANKS) - 1:
                lines.append(f"Next rank:   {nxt.name} at {nxt.rep_required} rep")
        elif p.phase == "endless":
            lines.append(f"Best floor:  {self.game.endless.best_floor} (meta)")

        tk.Label(body, text="\n".join(lines), fg=COLORS["text"], bg=COLORS["window"],
                 font=MONO(14), justify=tk.LEFT, anchor=tk.NW).pack(fill=tk.BOTH, expand=True)

        btn_row = tk.Frame(body, bg=COLORS["window"])
        btn_row.pack(fill=tk.X, pady=(8, 0))
        tk.Button(btn_row, text="Save Game", command=lambda: (SaveManager.save(self.game), sounds.play("success")),
                  bg=COLORS["accent_dim"], fg="white", relief=tk.FLAT, padx=12).pack(side=tk.LEFT)
        tk.Button(btn_row, text="Load Game", command=lambda: (SaveManager.load(self.game), self.refresh_taskbar()),
                  bg=COLORS["border"], fg=COLORS["text"], relief=tk.FLAT, padx=12).pack(side=tk.LEFT, padx=8)
        tk.Button(btn_row, text="Chaos Mode (terminal: chaos)", command=self.open_terminal,
                  bg=COLORS["border"], fg=COLORS["warn"], relief=tk.FLAT, padx=12).pack(side=tk.LEFT)
        if p.phase == "career":
            tk.Button(btn_row, text="Endless Run (endless start)", command=self.open_terminal,
                      bg=COLORS["border"], fg=COLORS["accent"], relief=tk.FLAT, padx=12).pack(side=tk.LEFT, padx=8)
        self._built_panels.add("status")

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
