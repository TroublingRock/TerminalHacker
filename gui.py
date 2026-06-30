#!/usr/bin/env python3
"""TerminalHacker desktop GUI — computer-style interface for the simulator."""

from __future__ import annotations

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
from retention import SEASON_TIERS

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


class DesktopApp:
    """Simulated hacker workstation desktop."""

    ANIM_MS = 14
    ANIM_STEPS = 12

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("TerminalHacker OS")
        self.root.geometry("1100x720")
        self.root.minsize(900, 600)
        self.root.configure(bg=COLORS["desktop"])

        self.game = Game()
        self.game.gui_mode = True
        Console.fast_mode = True
        self.game.mail.on_new_mail = self._on_new_mail

        self.open_windows: dict[str, tk.Toplevel] = {}
        self.terminal_booted = False
        self.mail_badge: tk.Label | None = None
        self._mail_listbox: tk.Listbox | None = None

        self._build_desktop()
        self._build_taskbar()
        self.refresh_taskbar()

    # ----- mail notifications -----

    def _on_new_mail(self, msg: MailMessage) -> None:
        sounds.play("mail")
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
        title_font = tkfont.Font(family="Helvetica", size=22, weight="bold")
        tk.Label(
            header, text="TERMINALHACKER OS", fg=COLORS["accent"],
            bg=COLORS["desktop"], font=title_font,
        ).pack(side=tk.LEFT)
        tk.Label(
            header, text="  v1.1 — Cybersecurity Training Environment",
            fg=COLORS["muted"], bg=COLORS["desktop"], font=("Helvetica", 11),
        ).pack(side=tk.LEFT, padx=(8, 0))

        icons = tk.Frame(self.root, bg=COLORS["desktop"])
        icons.pack(fill=tk.BOTH, expand=True, padx=32, pady=16)

        apps = [
            ("terminal", ">_", "Terminal", "SSH shell & hacking commands", self.open_terminal),
            ("mail", "@", "Mail", "NPC brokers & training messages", self.open_mail),
            ("jobs", "[]", "Job Board", "Paid contracts & missions", self.open_job_board),
            ("shop", "$", "Black Market", "CPU, firewall & tools", self.open_shop),
            ("training", "?", "Training", "Tutorial lessons & objectives", self.open_training),
            ("achieve", "*", "Achievements", "Badges & daily challenges", self.open_achievements),
            ("status", "#", "System Status", "Hardware, VPN, save/load", self.open_status),
        ]

        for i, app in enumerate(apps):
            row, col = divmod(i, 3)
            self._desktop_icon(icons, *app, row=row, col=col)

        hint = tk.Label(
            self.root,
            text="Double-click an icon to launch. New Mail arrives from brokers and trainers.",
            fg=COLORS["muted"], bg=COLORS["desktop"], font=("Helvetica", 10),
        )
        hint.pack(pady=(0, 12))

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
            font=("Courier", 28, "bold"), width=4, height=2,
            relief=tk.RAISED, bd=2,
        )
        box.pack()

        if key == "mail":
            self.mail_badge = tk.Label(
                icon_wrap, text="", fg="white", bg=COLORS["error"],
                font=("Helvetica", 8, "bold"),
            )
            self._refresh_mail_badge()

        tk.Label(frame, text=name, fg=COLORS["text"], bg=COLORS["desktop"],
                 font=("Helvetica", 11, "bold")).pack(pady=(6, 0))
        tk.Label(frame, text=desc, fg=COLORS["muted"], bg=COLORS["desktop"],
                 font=("Helvetica", 9), wraplength=150, justify=tk.CENTER).pack()

        def launch(_e=None) -> None:
            sounds.play("click")
            command()

        for widget in (frame, box, icon_wrap):
            widget.bind("<Double-Button-1>", launch)
            widget.bind("<Enter>", lambda _e, b=box: b.configure(bg=COLORS["border"]))
            widget.bind("<Leave>", lambda _e, b=box: b.configure(bg=COLORS["window"]))

    def _build_taskbar(self) -> None:
        bar = tk.Frame(self.root, bg=COLORS["taskbar"], height=36)
        bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.taskbar_label = tk.Label(
            bar, text="", fg=COLORS["text"], bg=COLORS["taskbar"],
            font=("Helvetica", 10), anchor=tk.W, padx=12,
        )
        self.taskbar_label.pack(fill=tk.X, side=tk.LEFT)

    def refresh_taskbar(self) -> None:
        p = self.game.player
        phase = "TRAINING" if p.phase == "tutorial" else "CAREER"
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
        self.taskbar_label.configure(
            text=(
                f"  {phase}{lesson}{rank_txt}  |  {wallet}  |  CPU L{p.cpu_level}  |  "
                f"FW L{p.firewall_level}  |  {vpn}{mail_txt}"
            )
        )

    def _window(self, key: str, title: str, width: int, height: int) -> tk.Toplevel:
        if key in self.open_windows and self.open_windows[key].winfo_exists():
            win = self.open_windows[key]
            win.lift()
            win.focus_force()
            sounds.play("click")
            return win

        win = tk.Toplevel(self.root)
        win.title(title)
        win.configure(bg=COLORS["window"])
        win.protocol("WM_DELETE_WINDOW", lambda k=key: self._close_window(k))

        titlebar = tk.Frame(win, bg=COLORS["border"], height=32)
        titlebar.pack(fill=tk.X)
        tk.Label(titlebar, text=f"  {title}", fg=COLORS["text"], bg=COLORS["border"],
                 font=("Helvetica", 10, "bold")).pack(side=tk.LEFT, pady=4)

        body = tk.Frame(win, bg=COLORS["window"])
        body.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        win._body = body  # type: ignore[attr-defined]
        self.open_windows[key] = win

        self._animate_window_open(win, width, height)
        sounds.play("open")
        return win

    def _animate_window_open(self, win: tk.Toplevel, width: int, height: int) -> None:
        self.root.update_idletasks()
        base_x = self.root.winfo_x() + 60 + len(self.open_windows) * 18
        base_y = self.root.winfo_y() + 50 + len(self.open_windows) * 14
        state = {"step": 0}

        def tick() -> None:
            step = state["step"]
            if step > self.ANIM_STEPS:
                win.geometry(f"{width}x{height}+{base_x}+{base_y}")
                return
            progress = step / self.ANIM_STEPS
            eased = 1 - (1 - progress) ** 3
            cur_w = max(80, int(width * eased))
            cur_h = max(40, int(height * eased))
            off_x = (width - cur_w) // 2
            off_y = height - cur_h
            win.geometry(f"{cur_w}x{cur_h}+{base_x + off_x}+{base_y + off_y}")
            state["step"] += 1
            win.after(self.ANIM_MS, tick)

        win.geometry(f"80x40+{base_x}+{base_y + height - 40}")
        win.after(self.ANIM_MS, tick)

    def _close_window(self, key: str) -> None:
        if key in self.open_windows:
            sounds.play("close")
            self.open_windows[key].destroy()
            del self.open_windows[key]
        if key == "terminal":
            self.game.close_terminal = False
        if key == "mail":
            self._mail_listbox = None

    # ----- apps -----

    def open_mail(self) -> None:
        win = self._window("mail", "Mail — Secure Inbox", 720, 500)
        body: tk.Frame = win._body  # type: ignore[attr-defined]

        tk.Label(body, text="INBOX", fg=COLORS["accent"], bg=COLORS["window"],
                 font=("Helvetica", 14, "bold")).pack(anchor=tk.W)

        panes = tk.Frame(body, bg=COLORS["window"])
        panes.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

        left = tk.Frame(panes, bg=COLORS["window"], width=240)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)

        listbox = tk.Listbox(
            left, bg=COLORS["terminal_bg"], fg=COLORS["text"],
            font=("Helvetica", 10), relief=tk.FLAT, selectbackground=COLORS["accent_dim"],
            activestyle="none",
        )
        listbox.pack(fill=tk.BOTH, expand=True)
        self._mail_listbox = listbox

        right = tk.Frame(panes, bg=COLORS["window"])
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))

        meta = tk.Label(right, text="Select a message", fg=COLORS["muted"],
                        bg=COLORS["window"], font=("Helvetica", 10), anchor=tk.W)
        meta.pack(fill=tk.X)

        viewer = scrolledtext.ScrolledText(
            right, bg=COLORS["terminal_bg"], fg=COLORS["text"],
            font=("Helvetica", 11), relief=tk.FLAT, wrap=tk.WORD,
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
        win = self._window("terminal", "Terminal — hacker@localhost", 780, 520)
        body: tk.Frame = win._body  # type: ignore[attr-defined]

        output = scrolledtext.ScrolledText(
            body, bg=COLORS["terminal_bg"], fg=COLORS["terminal_fg"],
            insertbackground=COLORS["accent"], font=("Courier", 11),
            relief=tk.FLAT, wrap=tk.WORD,
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
                              bg=COLORS["window"], font=("Courier", 11))
        prompt_lbl.pack(side=tk.LEFT)
        entry = tk.Entry(
            input_frame, bg=COLORS["terminal_bg"], fg=COLORS["text"],
            insertbackground=COLORS["accent"], font=("Courier", 11),
            relief=tk.FLAT, bd=4,
        )
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

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
        prompt_lbl.configure(text=self.game.prompt())
        entry.focus_set()

        if not self.terminal_booted:
            self.terminal_booted = True
            self.game.banner()

        win.after(120, entry.focus_set)

    def open_job_board(self) -> None:
        win = self._window("jobs", "Job Board — Secure Contracts", 620, 480)
        body: tk.Frame = win._body  # type: ignore[attr-defined]
        p = self.game.player

        tk.Label(body, text="CONTRACT CHANNEL", fg=COLORS["accent"], bg=COLORS["window"],
                 font=("Helvetica", 14, "bold")).pack(anchor=tk.W)
        tk.Label(body, text=p.wallet_label(), fg=COLORS["muted"], bg=COLORS["window"],
                 font=("Helvetica", 10)).pack(anchor=tk.W, pady=(4, 12))

        if p.phase == "tutorial":
            tk.Label(
                body,
                text="Complete training to unlock live contracts.\n"
                     "Check Mail for messages from your training officer.",
                fg=COLORS["warn"], bg=COLORS["window"], font=("Helvetica", 11),
                justify=tk.LEFT,
            ).pack(anchor=tk.W, pady=8)
            lesson = self.game.tutorial.current()
            tk.Label(body, text=f"Current: {lesson.title}", fg=COLORS["text"],
                     bg=COLORS["window"], font=("Helvetica", 10, "bold")).pack(anchor=tk.W, pady=(16, 4))
            tk.Label(body, text=lesson.objective, fg=COLORS["muted"], bg=COLORS["window"],
                     font=("Helvetica", 10), wraplength=560, justify=tk.LEFT).pack(anchor=tk.W)
            tk.Button(body, text="Open Training", command=self.open_training,
                      bg=COLORS["accent_dim"], fg="white", relief=tk.FLAT, padx=12, pady=4).pack(anchor=tk.W, pady=12)
            return

        scroll = scrolledtext.ScrolledText(body, height=16, bg=COLORS["terminal_bg"],
                                           fg=COLORS["text"], font=("Helvetica", 11), relief=tk.FLAT)
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
                 font=("Helvetica", 10), wraplength=560, justify=tk.LEFT).pack(anchor=tk.W, pady=(8, 4))
        tk.Label(body, text=f"Streak: {r.streak} days | Season {r.season_tier}/{len(SEASON_TIERS)} | Ops {len(r.completed_operations)} done",
                 fg=COLORS["muted"], bg=COLORS["window"], font=("Helvetica", 9)).pack(anchor=tk.W, pady=(0, 4))
        btn_row_intel = tk.Frame(body, bg=COLORS["window"])
        btn_row_intel.pack(fill=tk.X, pady=(0, 4))
        tk.Button(btn_row_intel, text="Intel (intel)", command=self.open_terminal,
                  bg=COLORS["border"], fg=COLORS["text"], relief=tk.FLAT, padx=8, pady=2).pack(side=tk.LEFT)
        tk.Button(btn_row_intel, text="Rival Dossier (rivals)", command=self.open_terminal,
                  bg=COLORS["border"], fg=COLORS["warn"], relief=tk.FLAT, padx=8, pady=2).pack(side=tk.LEFT, padx=6)

        tk.Label(body, text="Contract details also arrive via Mail from brokers.",
                 fg=COLORS["muted"], bg=COLORS["window"], font=("Helvetica", 9)).pack(anchor=tk.W, pady=(4, 0))

        btn_row = tk.Frame(body, bg=COLORS["window"])
        btn_row.pack(fill=tk.X, pady=(10, 0))
        tk.Button(btn_row, text="Request New Contract", command=self._request_contract,
                  bg=COLORS["accent_dim"], fg="white", relief=tk.FLAT, padx=12, pady=4).pack(side=tk.LEFT)

    def open_shop(self) -> None:
        win = self._window("shop", "Black Market — Upgrades", 640, 520)
        body: tk.Frame = win._body  # type: ignore[attr-defined]
        p = self.game.player

        tk.Label(body, text="BLACK MARKET SHOP", fg=COLORS["accent"], bg=COLORS["window"],
                 font=("Helvetica", 14, "bold")).pack(anchor=tk.W)
        wallet = tk.Label(body, text=p.wallet_label(), fg=COLORS["muted"], bg=COLORS["window"],
                          font=("Helvetica", 10))
        wallet.pack(anchor=tk.W, pady=(4, 12))

        if not p.is_local():
            tk.Label(body, text="Return to localhost (disconnect) to purchase upgrades.",
                     fg=COLORS["warn"], bg=COLORS["window"]).pack(anchor=tk.W)
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
            else:
                owned = item.key in p.owned_tools
                price_text = "OWNED" if owned else f"${item.base_cost}"
                state = tk.DISABLED if owned else tk.NORMAL

            tk.Label(row, text=item.name, fg=COLORS["text"], bg=COLORS["border"],
                     font=("Helvetica", 11, "bold"), width=16, anchor=tk.W).pack(side=tk.LEFT)
            tk.Label(row, text=item.description, fg=COLORS["muted"], bg=COLORS["border"],
                     font=("Helvetica", 9), wraplength=280, justify=tk.LEFT).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
            tk.Label(row, text=price_text, fg=COLORS["accent"], bg=COLORS["border"],
                     font=("Helvetica", 10, "bold"), width=8).pack(side=tk.RIGHT, padx=(4, 8))
            tk.Button(
                row, text="BUY", command=lambda k=item.key: buy_item(k),
                bg=COLORS["accent_dim"], fg="white", relief=tk.FLAT, padx=10,
                state=state,
            ).pack(side=tk.RIGHT)

    def _request_contract(self) -> None:
        self.game.cmd_contracts([])
        self.refresh_taskbar()
        self._close_window("jobs")
        self.open_job_board()

    def open_achievements(self) -> None:
        win = self._window("achieve", "Achievements & Daily", 560, 440)
        body: tk.Frame = win._body  # type: ignore[attr-defined]

        tk.Label(body, text="ACHIEVEMENTS", fg=COLORS["accent"], bg=COLORS["window"],
                 font=("Helvetica", 14, "bold")).pack(anchor=tk.W)
        scroll = scrolledtext.ScrolledText(body, height=12, bg=COLORS["terminal_bg"],
                                           fg=COLORS["text"], font=("Helvetica", 10), relief=tk.FLAT)
        scroll.pack(fill=tk.BOTH, expand=True, pady=8)
        for key, desc in ACHIEVEMENTS.items():
            mark = "[x]" if key in self.game.achievements.unlocked else "[ ]"
            scroll.insert(tk.END, f"{mark} {desc}\n")
        scroll.configure(state=tk.DISABLED)

        d = self.game.daily
        daily = "COMPLETE" if d.completed else f"{d.description} — ${d.reward}"
        r = self.game.retention
        tk.Label(body, text=f"TODAY'S CHALLENGE: {daily}", fg=COLORS["teach"],
                 bg=COLORS["window"], font=("Helvetica", 10), wraplength=520).pack(anchor=tk.W)
        tk.Label(body, text=f"Streak: {r.streak} days (best {r.longest_streak}) | Season tier {r.season_tier}/{len(SEASON_TIERS)}",
                 fg=COLORS["muted"], bg=COLORS["window"], font=("Helvetica", 10)).pack(anchor=tk.W, pady=(4, 0))

    def open_training(self) -> None:
        win = self._window("training", "Training Center", 640, 500)
        body: tk.Frame = win._body  # type: ignore[attr-defined]

        tk.Label(body, text="CYBERSECURITY CURRICULUM", fg=COLORS["accent"], bg=COLORS["window"],
                 font=("Helvetica", 14, "bold")).pack(anchor=tk.W, pady=(0, 8))

        scroll = scrolledtext.ScrolledText(body, bg=COLORS["terminal_bg"], fg=COLORS["text"],
                                           font=("Helvetica", 10), relief=tk.FLAT)
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

    def _lesson_to_terminal(self) -> None:
        self.open_terminal()
        self.game.cmd_lesson([])

    def open_status(self) -> None:
        win = self._window("status", "System Status", 480, 360)
        body: tk.Frame = win._body  # type: ignore[attr-defined]
        p = self.game.player

        lines = []
        if p.phase == "career":
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
        if p.phase == "career":
            lines.append(f"Rank:        {ReputationSystem.rank_name(p)} ({p.reputation} rep)")
            lines.append(f"Streak:      {self.game.retention.streak} days (best {self.game.retention.longest_streak})")
            lines.append(f"Season:      tier {self.game.retention.season_tier}/{len(SEASON_TIERS)} ({self.game.retention.season_xp} XP)")
            lines.append(f"Rival threat: {self.game.retention.rival_aggression}/10 ({self.game.retention.last_rival or 'none'})")
            lines.append(f"IDS level:   {self.game.blue.ids_level}")
            lines.append(f"Defense:     {'ON' if self.game.blue.defense_mode else 'off'}")
            nxt = RANKS[min(p.rank_index + 1, len(RANKS) - 1)]
            if p.rank_index < len(RANKS) - 1:
                lines.append(f"Next rank:   {nxt.name} at {nxt.rep_required} rep")

        tk.Label(body, text="\n".join(lines), fg=COLORS["text"], bg=COLORS["window"],
                 font=("Courier", 11), justify=tk.LEFT, anchor=tk.NW).pack(fill=tk.BOTH, expand=True)

        btn_row = tk.Frame(body, bg=COLORS["window"])
        btn_row.pack(fill=tk.X, pady=(8, 0))
        tk.Button(btn_row, text="Save Game", command=lambda: (SaveManager.save(self.game), sounds.play("success")),
                  bg=COLORS["accent_dim"], fg="white", relief=tk.FLAT, padx=12).pack(side=tk.LEFT)
        tk.Button(btn_row, text="Load Game", command=lambda: (SaveManager.load(self.game), self.refresh_taskbar()),
                  bg=COLORS["border"], fg=COLORS["text"], relief=tk.FLAT, padx=12).pack(side=tk.LEFT, padx=8)
        tk.Button(btn_row, text="Chaos Mode (terminal: chaos)", command=self.open_terminal,
                  bg=COLORS["border"], fg=COLORS["warn"], relief=tk.FLAT, padx=12).pack(side=tk.LEFT)

    def run(self) -> None:
        self.root.mainloop()


def run_gui() -> None:
    DesktopApp().run()
