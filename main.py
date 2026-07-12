#!/usr/bin/env python3
"""
TerminalHacker — educational text-based hacking simulator.

Teaches real-world networking, OS, and security concepts through a guided
tutorial phase (safe sandbox budget) that graduates into career mode where
players run contracts, upgrade gear, and balance offense vs defense.
"""

from __future__ import annotations

import random
import re
import time
from dataclasses import dataclass, field
from datetime import date
from typing import Callable


# ---------------------------------------------------------------------------
# Output bridge (CLI print or GUI text widget)
# ---------------------------------------------------------------------------

NOTES_PATH = "/home/hacker/notes.txt"


class Console:
    handler: Callable[[str, str], None] | None = None  # (text, tag)
    fast_mode: bool = False

    @staticmethod
    def out(text: str = "", tag: str = "normal") -> None:
        if Console.handler:
            Console.handler(text, tag)
        else:
            print(text)

    @staticmethod
    def pause(seconds: float) -> None:
        if not Console.fast_mode:
            time.sleep(seconds)


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def divider(title: str = "") -> None:
    if title:
        Console.out(f"\n── {title} " + "─" * max(4, 54 - len(title)), "info")
    else:
        Console.out("─" * 62, "info")


def muted(message: str) -> None:
    Console.out(message, "muted")


def info(message: str) -> None:
    Console.out(f"[*] {message}", "info")


def success(message: str) -> None:
    Console.out(f"[+] {message}", "success")


def warn(message: str) -> None:
    Console.out(f"[!] {message}", "warn")


def error(message: str) -> None:
    Console.out(f"[-] {message}", "error")


def teach(message: str) -> None:
    if _teach_suppressed():
        return
    Console.out(f"[?] {message}", "teach")


_teach_suppress_chaos = False


def set_teach_suppress_chaos(on: bool) -> None:
    global _teach_suppress_chaos
    _teach_suppress_chaos = on


def _teach_suppressed() -> bool:
    return _teach_suppress_chaos


def syslog_line(hostname: str, process: str, message: str, priority: int = 13) -> str:
    ts = time.strftime("%b %d %H:%M:%S")
    return f"<{priority}>{ts} {hostname} {process}: {message}"


def ip_in_subnet(ip: str, cidr: str) -> bool:
    network = cidr.split("/")[0]
    prefix = ".".join(network.split(".")[:3])
    return ip.startswith(prefix + ".")


# ---------------------------------------------------------------------------
# Filesystem
# ---------------------------------------------------------------------------

@dataclass
class VirtualFile:
    path: str
    content: str = ""
    owner: str = "root"
    group: str = "root"
    mode: str = "rw-r--r--"
    requires_root: bool = False

    def append(self, line: str) -> None:
        if self.content and not self.content.endswith("\n"):
            self.content += "\n"
        self.content += line

    def read(self) -> str:
        return self.content or ""


# ---------------------------------------------------------------------------
# Network models
# ---------------------------------------------------------------------------

@dataclass
class NetworkService:
    port: int
    name: str
    banner: str


@dataclass
class Route:
    destination: str
    gateway: str
    iface: str = "eth0"


@dataclass
class Server:
    ip: str
    hostname: str
    security_level: int
    subnet: str = "192.168.1.0/24"
    os_name: str = "Linux 5.15.0-generic x86_64"
    cracked: bool = False
    ssh_user: str = "admin"
    ssh_password: str = "changeme"
    ids_alert_level: int = 0
    privesc_available: bool = False
    services: list[NetworkService] = field(default_factory=list)
    files: dict[str, VirtualFile] = field(default_factory=dict)
    extra_files: dict[str, str] = field(default_factory=dict)
    root_only_files: dict[str, str] = field(default_factory=dict)
    company: str = ""
    story: str = ""
    min_rep: int = 0
    chaos_only: bool = False
    endless_only: bool = False
    puzzle_id: str = ""

    def __post_init__(self) -> None:
        if not self.services:
            self.services = [
                NetworkService(22, "ssh", "OpenSSH_8.9p1 Ubuntu-3ubuntu0.6"),
                NetworkService(80, "http", "nginx/1.18.0"),
            ]
        self._seed_files()

    def _seed_files(self) -> None:
        if self.files:
            return
        self.files = {
            "/etc/hostname": VirtualFile("/etc/hostname", f"{self.hostname}\n"),
            "/etc/passwd": VirtualFile(
                "/etc/passwd",
                f"root:x:0:0:root:/root:/bin/bash\n"
                f"{self.ssh_user}:x:1000:1000:{self.ssh_user}:/home/{self.ssh_user}:/bin/bash\n",
            ),
            f"/home/{self.ssh_user}/notes.txt": VirtualFile(
                f"/home/{self.ssh_user}/notes.txt",
                "Standard user account — limited privileges.\n",
                owner=self.ssh_user,
                mode="rw-------",
            ),
            "/var/log/syslog": VirtualFile(
                "/var/log/syslog",
                syslog_line(self.hostname, "systemd", "System boot complete.") + "\n",
                mode="rw-r-----",
            ),
            "/var/log/auth.log": VirtualFile(
                "/var/log/auth.log",
                syslog_line(self.hostname, "sshd", "Server listening on 0.0.0.0 port 22.") + "\n",
                mode="rw-r-----",
            ),
        }
        for path, body in self.extra_files.items():
            self.files[path] = VirtualFile(path, body)
        for path, body in self.root_only_files.items():
            self.files[path] = VirtualFile(path, body, owner="root", mode="rw-------", requires_root=True)

    def service_on_port(self, port: int) -> NetworkService | None:
        return next((s for s in self.services if s.port == port), None)

    def write_syslog(self, process: str, message: str) -> None:
        self.files["/var/log/syslog"].append(syslog_line(self.hostname, process, message))

    def write_auth(self, message: str) -> None:
        self.files["/var/log/auth.log"].append(syslog_line(self.hostname, "sshd", message))

    def raise_ids_alert(self, points: int) -> None:
        self.ids_alert_level = min(10, self.ids_alert_level + points)

    def logs_contain_ip(self, ip: str) -> bool:
        for path in ("/var/log/syslog", "/var/log/auth.log"):
            if path in self.files and ip in self.files[path].content:
                return True
        return False

    def player_left_traces(self, player: "Player") -> bool:
        return any(self.logs_contain_ip(ip) for ip in player.traceable_ips())


# ---------------------------------------------------------------------------
# Tutorial curriculum
# ---------------------------------------------------------------------------

@dataclass
class TutorialLesson:
    step: int
    title: str
    concept: str
    objective: str
    hint: str


TUTORIAL_CURRICULUM: list[TutorialLesson] = [
    TutorialLesson(
        0, "Network Boot",
        "Before you touch anything remote, confirm your interfaces and routing table. "
        "Defenders log both your LAN address and your public NAT egress.",
        "Run: ifconfig  then  route",
        "ifconfig shows your IP and NAT address; route shows how packets leave the lab.",
    ),
    TutorialLesson(
        1, "Host Discovery",
        "Pen testers enumerate live hosts with port scanners (nmap). Open ports reveal "
        "attack surface (SSH/HTTP/etc.).",
        "Run: scan   (or nmap 192.168.1.0/24)",
        "Scan the lab subnet to find training-node — your first target.",
    ),
    TutorialLesson(
        2, "TCP Sessions",
        "TCP uses a 3-way handshake (SYN, SYN-ACK, ACK) before SSH can authenticate.",
        "Run: connect 192.168.1.50 22",
        "Connect to the training host you discovered.",
    ),
    TutorialLesson(
        3, "Service Fingerprinting",
        "Probing banners and versions helps choose exploits. IDS systems log probes.",
        "Run: probe",
        "Probe the host you are connected to.",
    ),
    TutorialLesson(
        4, "Credential Attacks",
        "Brute-force tries passwords until SSH accepts. Failed attempts land in auth.log.",
        "Run: crack",
        "Crack SSH on the training host — your first real shell.",
    ),
    TutorialLesson(
        5, "Log Forensics",
        "Blue teams investigate auth.log/syslog. Your public IP is evidence.",
        "Run: cat /var/log/auth.log",
        "Read the remote auth log and find your IP address recorded.",
    ),
    TutorialLesson(
        6, "Covering Tracks",
        "Deleting log files is illegal in the real world — here it teaches why wiping "
        "matters before disconnecting.",
        "Run: rm /var/log/syslog  then  rm /var/log/auth.log",
        "Remove BOTH log files on the remote training host.",
    ),
    TutorialLesson(
        7, "Data Exfiltration",
        "Attackers copy stolen files to their machine via SFTP/SCP equivalents.",
        "Run: download /home/trainee/training_flag.txt",
        "Download the flag file, then disconnect safely.",
    ),
    TutorialLesson(
        8, "VPN / Proxy Routing",
        "VPNs tunnel traffic through an exit node so victims log the VPN IP, not yours. "
        "Critical for anonymity.",
        "Run: vpn connect  then reconnect and crack without exposing your real public IP.",
        "Activate VPN before your next connection to training-node.",
    ),
    TutorialLesson(
        9, "Subnet Segmentation",
        "Enterprises segment networks (192.168.x vs 10.x). You need a route via the "
        "gateway to reach other subnets.",
        "Run: route add 10.0.0.0/24 via 192.168.1.1  then  scan 10.0.0.0/24",
        "Add the corporate route and scan the 10.0.0.0/24 subnet.",
    ),
    TutorialLesson(
        10, "Privilege Escalation",
        "Initial access is often a low-privilege user. Misconfigured sudo lets you become root.",
        "Connect to 10.0.0.99, crack, run: sudo -l  then  privesc  then download /root/classified.txt",
        "Escalate to root on tutorial-dmz and steal the root-only file.",
    ),
    TutorialLesson(
        11, "Defense & Blue Team",
        "Rivals attack weak firewalls. Blue team upgrades defenses. Tutorial budget absorbs "
        "training losses — NOT your career money.",
        "Run: buy firewall  (uses tutorial credits) and survive rival probes.",
        "Purchase a firewall upgrade. Rival attacks will drain tutorial credits only.",
    ),
]


class TutorialManager:
    TUTORIAL_BUDGET = 500
    DEFENSE_LESSON = 11
    CURRICULUM_VERSION = "v2"

    def __init__(self, game: "Game") -> None:
        self.game = game
        self.defense_attacks_triggered = 0
        self.defense_survived = False
        self.defense_start_tick: int | None = None

    @property
    def player(self) -> Player:
        return self.game.player

    def in_tutorial(self) -> bool:
        return self.player.phase == "tutorial"

    def training_complete(self) -> bool:
        return self.player.phase in ("career", "endless")

    def skipped_training(self) -> bool:
        return "chaos_career" in self.player.tutorial_flags

    def current(self) -> TutorialLesson | None:
        if self.training_complete():
            return None
        step = min(self.player.tutorial_step, len(TUTORIAL_CURRICULUM) - 1)
        return TUTORIAL_CURRICULUM[step]

    def show_lesson(self) -> None:
        if self.training_complete():
            self.show_career_training_status()
            return
        lesson = self.current()
        if lesson is None:
            return
        divider(f"TUTORIAL {lesson.step + 1}/{len(TUTORIAL_CURRICULUM)} — {lesson.title}")
        teach(lesson.concept)
        Console.out(f"\n  Objective: {lesson.objective}")
        Console.out(f"  Hint:      {lesson.hint}")
        Console.out(f"\n  Tutorial budget: ${self.player.tutorial_credits} (career funds protected)\n")

    def show_career_training_status(self) -> None:
        p = self.player
        divider("TRAINING COMPLETE")
        if self.skipped_training():
            success("You skipped boot camp via Chaos Career — loud ops, real wallet.")
            teach("Type chaos status for heat/notoriety. Rival trash talk starts after your first crack.")
        else:
            success("Tutorial graduated — you are cleared for live contracts.")
        Console.out(f"  Wallet: {p.wallet_label()}")
        Console.out(f"  Gear:   CPU L{p.cpu_level}  |  Firewall L{p.firewall_level}")
        if p.phase == "career":
            Console.out("  Type missions for contracts, or hint for your next move.\n")
        else:
            Console.out("  Endless run active — type endless status.\n")

    def skip_to_career(self, *, chaos: bool = False) -> bool:
        """Leave tutorial without completing every lesson."""
        if not self.in_tutorial():
            warn("Already past training.")
            return False
        if chaos:
            from chaos_system import ChaosCareerManager
            ChaosCareerManager.start(self.game)
            return True
        self.graduate()
        return True

    def record_command(self, cmd: str) -> None:
        self.player.command_history.add(cmd)

    def check_advance(self) -> None:
        if not self.in_tutorial():
            return
        p = self.player
        if p.tutorial_step >= len(TUTORIAL_CURRICULUM):
            self.graduate()
            return
        step = p.tutorial_step
        g = self.game

        checks = self._lesson_completion_checks()

        if step >= len(TUTORIAL_CURRICULUM):
            return
        if checks.get(step, lambda: False)():
            self._complete_step()

    def _complete_step(self) -> None:
        lesson = self.current()
        if lesson is None:
            return
        divider("LESSON COMPLETE")
        success(f"{lesson.title} mastered.")
        if lesson.step == 0:
            self.game.try_unlock("boot_camp")
        self.player.tutorial_step += 1
        if self.player.tutorial_step == 2:
            self.game.mail.send(
                "acid_k@rival.net",
                "I see your scans",
                "Nice port sweep on the lab subnet.\n"
                "Connect to something interesting and I'll rate your form.\n\n— acid_k",
            )
        if self.player.tutorial_step == self.DEFENSE_LESSON:
            self.defense_start_tick = self.player.ticks
            teach("Rivals will attack soon. Use tutorial credits to buy firewall BEFORE losses stack.")
            self.game.mail.send(
                "acid_k@rival.net",
                "Your firewall is trash",
                "I can see your public IP from here.\n"
                "Buy a real firewall from the Shop before I take your tutorial credits.\n\n— acid_k",
            )

        if self.player.tutorial_step >= len(TUTORIAL_CURRICULUM):
            self.graduate()
        else:
            self.game.autosave(force=True)
            next_lesson = self.current()
            self.game.mail.send(
                "training_officer@terminalhacker.local",
                f"Lesson passed: {lesson.title}",
                f"Good work.\n\nNext up: {next_lesson.title}\n"
                f"Objective: {next_lesson.objective}\n\n— Training Officer",
            )
            self.show_lesson()

    def graduate(self) -> None:
        p = self.player
        p.phase = "career"
        p.money = max(750, 500 + p.tutorial_credits)
        p.tutorial_credits = 0
        p.reputation = 100
        p.rank_index = 1
        from progression import PlayerProfile
        PlayerProfile.mark_veteran()
        self.game.meta.notoriety_baseline = self.game.meta.notoriety
        self.game.meta.rival_trash_talk_unlocked = False
        self.game.meta.pending_rival_mail = []
        if not any(r.destination == "10.0.0.0/24" for r in p.routes):
            p.routes.append(Route("10.0.0.0/24", "192.168.1.1"))
        self.game.network.deploy_company_hosts_with_puzzles(self.game, p.reputation, False)
        starter_ip = "192.168.1.10"
        if self.game.network.get_server(starter_ip):
            self.game.missions.missions.insert(
                0,
                Mission(
                    "starter-001", "ghost_broker",
                    f"Warm-up contract: crack {starter_ip}, download /home/admin/notes.txt, wipe logs.",
                    starter_ip, "/home/admin/notes.txt", 400, rep_reward=45,
                ),
            )
        divider("CAREER MODE UNLOCKED")
        success("Training complete. You are cleared for live contracts.")
        from chaos_system import ROOKIE_GRACE_TICKS
        teach(
            "Career mode uses REAL money. Traces and rivals hit your wallet. "
            f"Rival trash talk starts after your first crack; lockdowns wait ~{ROOKIE_GRACE_TICKS} commands."
        )
        Console.out(f"  Starting career balance: ${p.money}")
        Console.out("  Progress auto-saves. Type 'help' for career commands.\n")
        self.game.missions.announce_login(self.game.mail)
        self.game.mail.send(
            "security@terminalhacker.local",
            "Career mode active",
            "Training sandbox disabled. Traces and fines now affect your real balance.\n"
            "Use VPN, upgrade firewall, and read your Mail for contracts.",
        )
        if self.game.gui_mode:
            self.game.defer_career_session = True
        else:
            from retention import RetentionManager
            RetentionManager.on_career_session(self.game)
        self.game.autosave(force=True)

    def complete_defense_drill(self) -> None:
        self.player.tutorial_flags.add("defense_drill_done")
        if self.defense_survived:
            return
        self.defense_attacks_triggered = max(self.defense_attacks_triggered, 1)
        self.defense_survived = True
        success("Defense drill passed — firewall holding against rival probes.")

    def _lesson_completion_checks(self) -> dict[int, Callable[[], bool]]:
        p = self.player
        g = self.game
        return {
            0: lambda: "ifconfig" in p.command_history and "route" in p.command_history,
            1: lambda: "scan" in p.command_history or "nmap" in p.command_history,
            2: lambda: p.connection == "192.168.1.50" or "connected_training" in p.tutorial_flags,
            3: lambda: "probed_training" in p.tutorial_flags,
            4: lambda: g.network.get_server("192.168.1.50") and g.network.get_server("192.168.1.50").cracked,
            5: lambda: "read_authlog" in p.tutorial_flags,
            6: lambda: "wiped_training_logs" in p.tutorial_flags,
            7: lambda: "/home/hacker/downloads/training_flag.txt" in p.files and p.is_local(),
            8: lambda: "vpn_success" in p.tutorial_flags and p.vpn_active,
            9: lambda: any(ip.startswith("10.0.0.") for ip in p.discovered_ips),
            10: lambda: "/home/hacker/downloads/classified.txt" in p.files and p.remote_was_root,
            11: lambda: p.firewall_level >= 2,
        }

    def _inferred_tutorial_step(self) -> int:
        """Lowest step index consistent with recorded commands and flags."""
        checks = self._lesson_completion_checks()
        step = 0
        for s in range(len(TUTORIAL_CURRICULUM)):
            if checks.get(s, lambda: False)():
                step = s + 1
            else:
                break
        return min(step, len(TUTORIAL_CURRICULUM))

    def sync_tutorial_step_from_progress(self) -> None:
        """Never lower tutorial_step — only repair accidental resets from bad migrations."""
        if not self.in_tutorial():
            return
        inferred = self._inferred_tutorial_step()
        if inferred > self.player.tutorial_step:
            self.player.tutorial_step = inferred

    def reconcile_stuck_lessons(self) -> None:
        """Fix edge cases e.g. firewall bought via GUI Shop before rival attack fired."""
        self.migrate_curriculum_step_for()
        self.sync_tutorial_step_from_progress()
        if not self.in_tutorial():
            return
        p = self.player
        if p.tutorial_step >= len(TUTORIAL_CURRICULUM):
            if p.firewall_level >= 2:
                self.graduate()
            else:
                p.tutorial_step = self.DEFENSE_LESSON
            return
        if p.tutorial_step >= self.DEFENSE_LESSON and p.firewall_level >= 2:
            p.tutorial_flags.add("tutorial_firewall_upgraded")
            p.tutorial_flags.add("defense_drill_done")
            self.complete_defense_drill()
            self.check_advance()

    def migrate_curriculum_step_for(self) -> None:
        """One-time shift for saves started on the pre-v2 (13-lesson) curriculum."""
        p = self.player
        flag = f"tutorial_{self.CURRICULUM_VERSION}"
        if flag in p.tutorial_flags:
            return
        p.tutorial_flags.add(flag)
        if p.tutorial_step >= 2:
            p.tutorial_step -= 1
        elif p.tutorial_step == 1:
            # v2 lesson 0 ends at step 1 (scan). Only downgrade legacy saves that
            # have not yet finished Network Boot on the compressed curriculum.
            hist = p.command_history
            if "ifconfig" in hist and "route" in hist:
                pass
            else:
                p.tutorial_step = 0

    def send_opening_hook(self) -> None:
        p = self.player
        if p.phase != "tutorial" or p.tutorial_step != 0:
            return
        if "opening_hook_sent" in p.tutorial_flags:
            return
        p.tutorial_flags.add("opening_hook_sent")
        self.game.mail.send(
            "training_officer@terminalhacker.local",
            "URGENT — boot your workstation",
            "Trainee,\n\n"
            "We detected probe traffic on the lab subnet. Before you touch anything remote:\n\n"
            "  1. Open Terminal → type: lesson\n"
            "  2. Run: ifconfig\n"
            "  3. Run: route\n"
            "  4. Run: scan\n\n"
            "Your goal today: crack training-node and capture the flag (~30 min).\n"
            "Progress auto-saves. Job Board, Botnet, and contracts unlock after graduation.\n\n"
            "— Training Officer",
        )
        self.game.mail.send(
            "acid_k@rival.net",
            "new fish on the wire",
            "Another trainee just booted up.\n"
            "I'll be watching your scans. Try not to embarrass yourself.\n\n— acid_k",
        )

    def on_defense_tick(self) -> None:
        if not self.in_tutorial() or self.player.tutorial_step != self.DEFENSE_LESSON:
            return
        if self.defense_survived:
            return
        if self.defense_start_tick is not None and self.player.ticks - self.defense_start_tick < 2:
            return
        if self.player.firewall_level >= 2 and self.defense_attacks_triggered >= 1:
            self.complete_defense_drill()
            self.check_advance()


# ---------------------------------------------------------------------------
# Mail / NPC messaging
# ---------------------------------------------------------------------------

@dataclass
class MailMessage:
    mail_id: str
    sender: str
    subject: str
    body: str
    read: bool = False
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = time.strftime("%Y-%m-%d %H:%M")


class MailBox:
    """In-game email from NPCs — brokers, trainers, rivals."""

    def __init__(self) -> None:
        self.messages: list[MailMessage] = []
        self.trash: list[MailMessage] = []
        self.on_new_mail: Callable[[MailMessage], None] | None = None
        self._counter = 0

    def send(self, sender: str, subject: str, body: str) -> MailMessage:
        self._counter += 1
        msg = MailMessage(
            mail_id=f"mail-{self._counter:04d}",
            sender=sender,
            subject=subject,
            body=body,
        )
        self.messages.insert(0, msg)
        if self.on_new_mail:
            self.on_new_mail(msg)
        return msg

    def unread_count(self) -> int:
        return sum(1 for m in self.messages if not m.read)

    def mark_read(self, mail_id: str) -> None:
        for m in self.messages + self.trash:
            if m.mail_id == mail_id:
                m.read = True
                return

    def mark_all_read(self) -> None:
        for m in self.messages:
            m.read = True

    def trash_message(self, mail_id: str) -> bool:
        for i, m in enumerate(self.messages):
            if m.mail_id == mail_id:
                self.trash.insert(0, self.messages.pop(i))
                return True
        return False

    def trash_all_read(self) -> int:
        read_msgs = [m for m in self.messages if m.read]
        self.messages = [m for m in self.messages if not m.read]
        self.trash = read_msgs + self.trash
        return len(read_msgs)

    def permanent_delete(self, mail_id: str) -> bool:
        for i, m in enumerate(self.trash):
            if m.mail_id == mail_id:
                self.trash.pop(i)
                return True
        return False

    def empty_trash(self) -> int:
        count = len(self.trash)
        self.trash.clear()
        return count

    def restore_message(self, mail_id: str) -> bool:
        for i, m in enumerate(self.trash):
            if m.mail_id == mail_id:
                self.messages.insert(0, self.trash.pop(i))
                return True
        return False

    def message_by_id(self, mail_id: str) -> MailMessage | None:
        for m in self.messages + self.trash:
            if m.mail_id == mail_id:
                return m
        return None

    # Back-compat aliases
    def delete(self, mail_id: str) -> bool:
        return self.trash_message(mail_id)

    def delete_all_read(self) -> int:
        return self.trash_all_read()

    def clear_inbox(self) -> int:
        count = len(self.messages)
        self.messages.clear()
        return count


# ---------------------------------------------------------------------------
# Missions (career only)
# ---------------------------------------------------------------------------

@dataclass
class Mission:
    mission_id: str
    broker: str
    briefing: str
    target_ip: str
    target_file: str
    reward: int
    require_log_wipe: bool = True
    completed: bool = False
    rep_reward: int = 50
    procedural: bool = False
    mission_type: str = "exfil"
    require_privesc: bool = False
    weekly_bounty: bool = False
    operation_id: str = ""
    operation_step: int = 0
    lateral_chain_id: str = ""
    hourly_event: bool = False
    reward_multiplier: float = 1.0
    grade: str = ""
    endless_floor: bool = False
    puzzle_id: str = ""
    puzzle_secondary: str = ""
    social_file: str = ""
    pivot_host: str = ""
    timing_limit_ticks: int = 0
    timing_start_tick: int = 0
    modifiers: list[str] = field(default_factory=list)
    heist_id: str = ""
    heist_step: int = 0
    story_arc: str = ""
    rival_counter: bool = False

    def status_line(self) -> str:
        mark = "[DONE]" if self.completed else "[OPEN]"
        tag = ""
        if self.hourly_event:
            tag = f" [HOURLY {self.reward_multiplier}x]"
        elif self.lateral_chain_id:
            tag = " [LATERAL]"
        elif self.endless_floor:
            tag = " [ENDLESS]"
        elif self.weekly_bounty and self.heist_id:
            tag = f" [HEIST {self.heist_step}]"
        elif self.weekly_bounty:
            tag = " [WEEKLY]"
        elif self.modifiers:
            tag = f" [+{len(self.modifiers)} MOD]"
        elif self.operation_id:
            tag = f" [OP {self.operation_step}]"
        elif getattr(self, "story_arc", ""):
            tag = f" [ARC {self.story_arc}]"
        elif getattr(self, "rival_counter", False):
            tag = " [RIVAL]"
        elif self.mission_type not in ("exfil",):
            tag = f" [{self.mission_type.upper()}]"
        grade_tag = f" Grade:{self.grade}" if self.grade else ""
        return f"{mark}{tag} {self.broker}: {self.briefing} (reward ${self.reward}){grade_tag}"


class MissionBoard:
    def __init__(self) -> None:
        self.missions = [
            Mission("ghost-001", "ghost_broker",
                    "Hack 10.0.0.42, download corporate_secrets.txt, wipe logs.", "10.0.0.42",
                    "/home/admin/corporate_secrets.txt", 750, rep_reward=80),
            Mission("cipher-002", "cipher7",
                    "Crack vault-server (10.0.0.55), privesc, exfil payroll.csv.", "10.0.0.55",
                    "/root/payroll.csv", 1500, rep_reward=120),
        ]
        self._announced = False

    def announce_login(self, mailbox: MailBox | None = None) -> None:
        if self._announced:
            return
        divider("INCOMING — MISSION BOARD")
        Console.out('  [ghost_broker] "You are cleared for live ops. Type missions."\n')
        self._announced = True
        if mailbox:
            mailbox.send(
                "ghost_broker@darknet",
                "You're cleared for live ops",
                "Trainee,\n\nGood work surviving the lab. I have contracts on the Job Board.\n"
                "Check Mail for details. Wipe your logs — always.\n\n— ghost_broker",
            )
            for mission in self.missions:
                mailbox.send(
                    f"{mission.broker}@darknet",
                    f"Contract offer: {mission.mission_id}",
                    f"{mission.briefing}\n\nReward: ${mission.reward}\n"
                    "Accept by completing the objective. Payment on delivery.",
                )

    def check_completion(self, game: "Game") -> None:
        from retention import RetentionManager
        from session_content import HourlyManager, MasteryGrader

        for mission in self.missions:
            if mission.completed:
                continue
            if game.player.phase == "endless" and not getattr(mission, "endless_floor", False):
                continue
            if game.player.phase != "endless" and getattr(mission, "endless_floor", False):
                continue
            if mission.mission_type == "timing":
                from variety_content import VarietyManager
                if VarietyManager.timing_expired(game, mission):
                    mission.completed = True
                    from main import warn
                    warn(f"TIMING FAILED: {mission.briefing[:50]}... — window closed.")
                    continue
            if not RetentionManager.mission_is_satisfied(game, mission):
                continue
            grade, mult, summary = MasteryGrader.grade(game, mission)
            mission.grade = grade
            payout = int(mission.reward * mult)
            from depth_systems import ModifierManager
            payout = int(payout * ModifierManager.payout_mult(mission, game))
            from faction_consumables import FactionRepManager
            payout = int(payout * FactionRepManager.payout_mult(game, mission))
            from llm_struct import LLMStructManager
            payout = int(payout * LLMStructManager.world_event_bounty_mult(game))
            from chaos_system import NotorietyManager
            style_mult, style_note = NotorietyManager.contract_style_mult(game, mission)
            payout = int(payout * style_mult)
            if mission.hourly_event and mission.reward_multiplier > 1:
                payout = int(payout * mission.reward_multiplier)
            rep = mission.rep_reward + MasteryGrader.rep_bonus(grade)
            mission.completed = True
            game.player.earn(payout, f"contract {mission.broker}")
            success(summary)
            if style_note:
                from main import info
                info(style_note)
            self.complete_mission_hooks(game, mission, payout, rep)
            if game.mail:
                game.mail.send(
                    f"{mission.broker}@darknet",
                    f"Payment confirmed — ${payout}",
                    f"Contract fulfilled.\n\n{mission.briefing}\n\n{summary}\n\nFunds transferred.",
                )

    def complete_mission_hooks(self, game: "Game", mission: Mission,
                               payout: int | None = None, rep: int | None = None) -> None:
        from progression import MissionGenerator, ReputationSystem
        from retention import RetentionManager
        from session_content import HourlyManager

        game.player.tutorial_flags.add("daily_contract_done")
        game.achievements.contracts_completed += 1
        if game.achievements.contracts_completed >= 10:
            game.achievements.unlock("contract_10")
        ReputationSystem.add_rep(game, rep if rep is not None else mission.rep_reward, mission.mission_id)
        RetentionManager.on_contract_complete(game, mission)
        RetentionManager.on_operation_step_complete(game, mission)
        HourlyManager.on_complete(game, mission)
        from endless_mode import EndlessManager
        EndlessManager.on_mission_complete(game, mission)
        if getattr(mission, "puzzle_id", "") or mission.mission_type in ("social", "timing", "pivot"):
            game.variety.puzzle_completions += 1
            if game.variety.puzzle_completions >= 5:
                game.achievements.unlock("puzzle_slayer")
        if mission.mission_type == "social":
            game.variety.social_completions += 1
            if game.variety.social_completions >= 3:
                game.achievements.unlock("social_engineer")
        if mission.mission_type == "pivot":
            game.variety.pivot_completions += 1
            if game.variety.pivot_completions >= 3:
                game.achievements.unlock("pivot_pro")
        if game.player.phase == "career":
            from depth_systems import RivalHeatManager, WeeklyHeistManager
            RivalHeatManager.on_contract_complete(game, mission)
            if getattr(mission, "heist_id", ""):
                WeeklyHeistManager.on_step_complete(game, mission)
            from social_board import SocialBoardManager
            SocialBoardManager.on_contract_complete(game, mission)
            from faction_consumables import FactionRepManager
            FactionRepManager.on_contract_complete(game, mission)
            from longevity_content import RivalCounterManager, StoryArcManager
            RivalCounterManager.on_contract_complete(game, mission)
            StoryArcManager.on_arc_mission_complete(game, mission)
        new_m = MissionGenerator.generate(game)
        if new_m:
            self.missions.append(new_m)
            game.mail.send(
                f"{new_m.broker}@darknet",
                f"New contract: {new_m.mission_id}",
                f"{new_m.briefing}\n\nReward: ${new_m.reward} + {new_m.rep_reward} rep",
            )
        from progression import SaveManager
        SaveManager.autosave(game, force=True)


# ---------------------------------------------------------------------------
# Shop
# ---------------------------------------------------------------------------

@dataclass
class ShopItem:
    key: str
    name: str
    description: str
    base_cost: int
    detail: str = ""
    max_level: int = 6
    consumable: bool = False


def defense_firewall_help(game: "Game") -> list[str]:
    """Explain passive firewall vs optional defense mode."""
    p = game.player
    mode = "ON — rivals probe more; blocks earn rep" if game.blue.defense_mode else "off — passive (fewer probes)"
    return [
        "FIREWALL vs DEFENSE MODE",
        f"  Firewall L{p.firewall_level} — ALWAYS ON. Blocks rivals when your level ≥ attack power.",
        "  Defense mode is separate — optional. Type: defend on | defend off",
        f"  Defense now: {mode}",
        "  'Defense off' does NOT mean you are unprotected — your firewall still blocks attacks.",
    ]


SHOP_CATALOG = [
    ShopItem(
        "cpu", "CPU Upgrade", "Faster brute-force attacks.", 200,
        detail="Upgrade gear. Higher CPU = fewer crack attempts and faster guesses on SSH targets.",
        max_level=6,
    ),
    ShopItem(
        "firewall", "Firewall Upgrade",
        "Passive protection — blocks rival attacks automatically.", 175,
        detail="Always active (no toggle). Rivals compare attack power vs your firewall level. "
        "Upgrade if you keep getting breached. Separate from 'Defense mode' (defend on).",
        max_level=5,
    ),
    ShopItem(
        "vpn_pro", "VPN Pro License", "Permanent VPN in career mode.", 300,
        detail="Tutorial VPN is free. Career needs this license for vpn connect. "
        "Victims log the VPN exit IP instead of your real public IP.",
        max_level=1,
    ),
    ShopItem(
        "hydra", "Hydra Lite", "Smarter password wordlist ordering.", 350,
        detail="Permanent tool. Tries the real password earlier during crack — fewer failed attempts.",
        max_level=1,
    ),
    ShopItem(
        "hashcat", "Hashcat Pro", "Cuts failed crack attempts ~40%.", 800,
        detail="Permanent tool. Requires Hydra Lite first. Greatly speeds up brute-force on tough hosts.",
        max_level=1,
    ),
    ShopItem(
        "burner_ip", "Burner IP Kit", "Mask egress IP for 8 commands.", 120,
        consumable=True,
        max_level=1,
        detail="Consumable. After buying: use burner_ip in Terminal. Masks the IP written to remote logs "
        "for 8 commands. Stacks with VPN.",
    ),
    ShopItem(
        "zero_day", "Zero-day Exploit", "Instant crack on current SSH target.", 450,
        consumable=True,
        max_level=1,
        detail="Consumable. connect to a host, then: use zero_day — skips brute-force once.",
    ),
    ShopItem(
        "decoy_log", "Decoy Log Pack", "6 commands of full trace immunity.", 200,
        consumable=True,
        max_level=1,
        detail="Consumable. use decoy_log — disconnect without leaving trace evidence for 6 commands.",
    ),
    ShopItem(
        "miner_payload", "Miner Payload", "Passive income via botnet.", 140,
        consumable=True,
        max_level=1,
        detail="Consumable. On a cracked host: infect miner. Run botnet / botnet collect in Terminal. "
        "Raises heat on that subnet.",
    ),
    ShopItem(
        "ddos_payload", "DDoS Payload", "Softens a rival target.", 220,
        consumable=True,
        max_level=1,
        detail="Consumable. On a cracked host: infect ddos <target IP>. Slows rival races and weakens FW on target.",
    ),
    ShopItem(
        "leak_payload", "Leak Worm", "Auto-dump host files to the board.", 160,
        consumable=True,
        max_level=1,
        detail="Consumable. infect leak on cracked host, then chaos leak while connected. Triggers meltdown chains.",
    ),
    ShopItem(
        "ransom_payload", "Ransom Locker", "High-yield encrypted hostage income.", 200,
        consumable=True,
        max_level=1,
        detail="Consumable. infect ransom on cracked host. Accrues ~2x miner income to botnet bank. Very loud.",
    ),
    ShopItem(
        "deface_payload", "Web Defacer", "Tag victim pages for notoriety.", 175,
        consumable=True,
        max_level=1,
        detail="Consumable. infect deface or chaos deface from shell. Posts to flex board, spikes heat.",
    ),
    ShopItem(
        "frame_payload", "Frame Kit", "Plant forged logs blaming a rival.", 240,
        consumable=True,
        max_level=1,
        detail="Consumable. infect frame <rival> [IP] — rivals: acid_k, phantom_pkt, nyx_root, zero_cool.",
    ),
    ShopItem(
        "virus_payload", "Autonomous Virus", "Cross-subnet worm spreader.", 190,
        consumable=True,
        max_level=1,
        detail="Consumable. infect virus — autospreads to discovered hosts on routed subnets when heat rises.",
    ),
]


class Shop:
    @staticmethod
    def list_items(player: Player) -> None:
        divider("BLACK MARKET SHOP")
        wallet = player.wallet_label()
        Console.out(f"  {wallet}\n")
        game = player._game_ref
        for item in SHOP_CATALOG:
            if item.consumable:
                from faction_consumables import ConsumableManager, FactionRepManager
                owned = ConsumableManager.inventory_count(game, item.key) if game else 0
                cost = int(item.base_cost * FactionRepManager.consumable_discount(game)) if game else item.base_cost
                Console.out(f"  {item.key:<10} {item.name:<18} ${cost} (own {owned})")
            elif item.key in ("cpu", "firewall"):
                lvl = player.cpu_level if item.key == "cpu" else player.firewall_level
                if lvl >= item.max_level:
                    Console.out(f"  {item.key:<10} {item.name:<18} MAXED (L{lvl})")
                else:
                    cost = item.base_cost * (lvl + 1)
                    Console.out(f"  {item.key:<10} {item.name:<18} ${cost} → L{lvl + 1}")
            else:
                owned = item.key in player.owned_tools
                Console.out(f"  {item.key:<10} {item.name:<18} {'OWNED' if owned else '$' + str(item.base_cost)}")
            Console.out(f"             {item.description}")
            if item.detail:
                Console.out(f"             → {item.detail}")
        Console.out("\n  buy [item]  |  use [consumable]  |  defend (firewall vs defense mode)\n")

    @staticmethod
    def buy(player: Player, key: str) -> bool:
        item = next((i for i in SHOP_CATALOG if i.key == key), None)
        if not item:
            error(f"Unknown item '{key}'.")
            return False
        if item.consumable:
            if not player._game_ref:
                error("Cannot buy consumables right now.")
                return False
            from faction_consumables import ConsumableManager
            return ConsumableManager.buy(player._game_ref, key)
        if item.key == "cpu":
            if player.cpu_level >= item.max_level:
                warn("CPU maxed.")
                return False
            cost = item.base_cost * (player.cpu_level + 1)
            if not player.spend(cost, f"CPU upgrade"):
                return False
            if player._game_ref:
                from session_content import MasteryGrader
                MasteryGrader.on_shop_spend(player._game_ref, cost)
            player.cpu_level += 1
            success(f"CPU level {player.cpu_level}")
            return True
        if item.key == "firewall":
            if player.firewall_level >= item.max_level:
                warn("Firewall maxed.")
                return False
            cost = item.base_cost * (player.firewall_level + 1)
            if not player.spend(cost, f"firewall upgrade"):
                return False
            if player._game_ref:
                from session_content import MasteryGrader
                MasteryGrader.on_shop_spend(player._game_ref, cost)
            player.firewall_level += 1
            success(f"Firewall level {player.firewall_level}")
            return True
        if item.key in player.owned_tools:
            warn("Already owned.")
            return False
        if item.key == "hashcat" and "hydra" not in player.owned_tools:
            error("Requires Hydra Lite.")
            return False
        if not player.spend(item.base_cost, item.name):
            return False
        if player._game_ref:
            from session_content import MasteryGrader
            MasteryGrader.on_shop_spend(player._game_ref, item.base_cost)
        player.owned_tools.add(item.key)
        if item.key == "hydra":
            player.cracker_tier = max(player.cracker_tier, 1)
        if item.key == "hashcat":
            player.cracker_tier = max(player.cracker_tier, 2)
        if item.key == "vpn_pro":
            player.vpn_licensed = True
        success(f"Purchased {item.name}.")
        return True


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------

@dataclass
class Player:
    username: str = "trainee"
    phase: str = "tutorial"
    tutorial_step: int = 0
    tutorial_credits: int = TutorialManager.TUTORIAL_BUDGET
    money: int = 0
    lan_ip: str = "192.168.1.100"
    public_ip: str = "73.42.118.9"
    gateway: str = "192.168.1.1"
    cpu_level: int = 1
    firewall_level: int = 1
    cracker_tier: int = 0
    vpn_active: bool = False
    vpn_licensed: bool = True  # free in tutorial
    vpn_exit_ip: str = "198.51.100.77"
    routes: list[Route] = field(default_factory=list)
    connection: str = "localhost"
    cwd: str = "/home/hacker"
    connected_port: int | None = None
    has_remote_shell: bool = False
    remote_is_root: bool = False
    remote_was_root: bool = False
    discovered_ips: set[str] = field(default_factory=set)
    owned_tools: set[str] = field(default_factory=set)
    command_history: set[str] = field(default_factory=set)
    tutorial_flags: set[str] = field(default_factory=set)
    files: dict[str, VirtualFile] = field(default_factory=dict)
    ticks: int = 0
    reputation: int = 0
    rank_index: int = 0
    chaos_unlocked: bool = False
    subnets_scanned: set[str] = field(default_factory=set)
    privesc_hosts: set[str] = field(default_factory=set)
    session_cracked: bool = False
    _game_ref: "Game | None" = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.routes:
            self.routes = [Route("192.168.1.0/24", self.gateway)]
        if not self.files:
            self.files = {
                "/home/hacker/notes.txt": VirtualFile(
                    "/home/hacker/notes.txt",
                    "Your personal scratchpad — IPs, passwords, targets.\n"
                    "  note add <text>   append a line\n"
                    "  note              show all notes\n"
                    "Or edit in Files app and click Save.\n",
                    owner=self.username,
                ),
                "/var/log/syslog": VirtualFile("/var/log/syslog", syslog_line("localhost", "systemd", "boot") + "\n", mode="rw-r-----"),
                "/var/log/auth.log": VirtualFile("/var/log/auth.log", syslog_line("localhost", "sshd", "listening") + "\n", mode="rw-r-----"),
            }

    @property
    def effective_egress_ip(self) -> str:
        if self._game_ref and self._game_ref.meta.burner_commands_left > 0 and self._game_ref.meta.burner_mask_ip:
            return self._game_ref.meta.burner_mask_ip
        return self.vpn_exit_ip if self.vpn_active else self.public_ip

    def traceable_ips(self) -> list[str]:
        ips = [self.effective_egress_ip]
        if self.public_ip not in ips:
            ips.append(self.public_ip)
        return ips

    def wallet_label(self) -> str:
        if self.phase == "tutorial":
            return f"Tutorial budget: ${self.tutorial_credits} | Career funds: ${self.money} (locked)"
        if self.phase == "endless" and self._game_ref:
            from endless_mode import EndlessManager
            return EndlessManager.run_wallet_label(self._game_ref)
        return f"Career balance: ${self.money}"

    def is_local(self) -> bool:
        return self.connection == "localhost"

    @property
    def prompt_host(self) -> str:
        return "localhost" if self.is_local() else self.connection

    def reset_session(self) -> None:
        self.connected_port = None
        self.has_remote_shell = False
        self.remote_is_root = False

    def spend(self, amount: int, reason: str) -> bool:
        if self.phase == "tutorial":
            if self.tutorial_credits >= amount:
                self.tutorial_credits -= amount
                success(f"{reason} (-${amount} tutorial credits, ${self.tutorial_credits} left)")
                teach("Career money was NOT charged — training budget only.")
                return True
            error(f"Need ${amount} tutorial credits (have ${self.tutorial_credits}).")
            return False
        if self.phase == "endless" and self._game_ref:
            e = self._game_ref.endless
            if e.run_money >= amount:
                e.run_money -= amount
                success(f"{reason} (-${amount}, run wallet ${e.run_money})")
                from endless_mode import EndlessManager
                EndlessManager.check_bankruptcy(self._game_ref)
                return True
            error(f"Need ${amount}, run wallet has ${e.run_money}.")
            return False
        if self.money >= amount:
            self.money -= amount
            success(f"{reason} (-${amount}, career balance ${self.money})")
            teach("Charged to your career wallet — not the tutorial budget.")
            return True
        error(f"Need ${amount}, have ${self.money}.")
        return False

    def earn(self, amount: int, reason: str) -> None:
        if self.phase == "tutorial":
            self.tutorial_credits += amount
            success(f"+${amount} tutorial credits ({reason})")
        elif self.phase == "endless" and self._game_ref:
            self._game_ref.endless.run_money += amount
            self._game_ref.endless.score += amount // 2
            success(f"+${amount} run wallet ({reason})")
        else:
            self.money += amount
            success(f"+${amount} ({reason})")
            if self._game_ref:
                from retention import RetentionManager
                RetentionManager.on_earn(self._game_ref, amount)

    def penalize(self, amount: int, reason: str) -> None:
        if self.phase == "tutorial":
            loss = min(amount, self.tutorial_credits)
            self.tutorial_credits -= loss
            warn(f"[TRAINING] {reason} — lost ${loss} from tutorial budget (${self.tutorial_credits} left)")
            teach("Your career wallet was protected during training.")
        elif self.phase == "endless" and self._game_ref:
            e = self._game_ref.endless
            e.run_money = max(0, e.run_money - amount)
            warn(f"{reason} — lost ${amount}. Run wallet: ${e.run_money}")
            from endless_mode import EndlessManager
            EndlessManager.check_bankruptcy(self._game_ref)
        else:
            self.money = max(0, self.money - amount)
            warn(f"{reason} — lost ${amount}. Balance: ${self.money}")

    def crack_speed_bonus(self) -> float:
        bonus = self.cpu_level * 0.05 + {0: 0, 1: 0.15, 2: 0.35}[self.cracker_tier]
        if self.phase == "endless":
            from endless_mode import EndlessManager
            bonus += EndlessManager.crack_bonus(self)
        return bonus

    def crack_attempt_reduction(self) -> float:
        return {0: 1.0, 1: 0.75, 2: 0.55}[self.cracker_tier]

    def has_route_to(self, ip: str) -> bool:
        return any(ip_in_subnet(ip, r.destination) for r in self.routes)


# ---------------------------------------------------------------------------
# Virtual network
# ---------------------------------------------------------------------------

class VirtualNetwork:
    def __init__(self, career: bool = False) -> None:
        self.servers: dict[str, Server] = {}
        self._seed(career)

    def _seed(self, career: bool) -> None:
        # Tutorial lab hosts (always available)
        lab = [
            Server(
                "192.168.1.50", "training-node", 1, ssh_user="trainee", ssh_password="training123",
                extra_files={"/home/trainee/training_flag.txt": "FLAG{you_understand_exfiltration}\n"},
            ),
            Server(
                "10.0.0.99", "tutorial-dmz", 2, subnet="10.0.0.0/24",
                ssh_user="operator", ssh_password="dmz_ops",
                privesc_available=True,
                root_only_files={"/root/classified.txt": "CLASSIFIED: merger dossier alpha\n"},
            ),
        ]
        for s in lab:
            self.servers[s.ip] = s

        if career:
            self.deploy_company_hosts(150, False)

    def deploy_company_hosts(self, reputation: int, chaos: bool) -> None:
        from progression import COMPANY_HOSTS, build_company_server

        for spec in COMPANY_HOSTS:
            if spec["ip"] in self.servers:
                continue
            if spec.get("chaos_only") and not chaos:
                continue
            if reputation < spec.get("min_rep", 0):
                continue
            self.servers[spec["ip"]] = build_company_server(spec)

    def deploy_mission_targets(self, game: "Game") -> list[str]:
        """Ensure open contract targets exist even below normal rep gates."""
        from progression import COMPANY_HOSTS, build_company_server

        spawned: list[str] = []
        for mission in game.missions.missions:
            if mission.completed:
                continue
            ip = getattr(mission, "target_ip", "") or ""
            if not ip or "/" in ip or ip in self.servers:
                continue
            spec = next((s for s in COMPANY_HOSTS if s["ip"] == ip), None)
            if not spec:
                continue
            self.servers[ip] = build_company_server(spec)
            spawned.append(ip)
        return spawned

    def deploy_company_hosts_with_puzzles(self, game: "Game", reputation: int, chaos: bool) -> None:
        self.deploy_company_hosts(reputation, chaos)
        self.deploy_mission_targets(game)
        from variety_content import VarietyManager
        VarietyManager.deploy_puzzles(game)
        from longevity_content import ExtendedHostManager
        ExtendedHostManager.deploy(game, reputation, chaos)
        ExtendedHostManager.apply_rank_routes(game)

    def add_career_hosts(self) -> None:
        self.deploy_company_hosts(150, False)

    def get_server(self, ip: str) -> Server | None:
        return self.servers.get(ip)

    def hosts_in_cidr(self, cidr: str, player: Player) -> list[Server]:
        from progression import ReputationSystem

        return [
            s for s in self.servers.values()
            if ip_in_subnet(s.ip, cidr) and player.has_route_to(s.ip)
            and player.reputation >= s.min_rep
            and (not s.chaos_only or ReputationSystem.chaos_available(player))
        ]


# ---------------------------------------------------------------------------
# Threat system
# ---------------------------------------------------------------------------

RIVALS = ["zero_cool", "acid_k", "phantom_pkt", "nyx_root"]


class ThreatSystem:
    def __init__(self, game: "Game") -> None:
        self.game = game

    def on_tick(self) -> None:
        p = self.game.player
        p.ticks += 1
        if not p.is_local():
            return

        tutorial = self.game.tutorial
        if tutorial.in_tutorial():
            if p.tutorial_step == TutorialManager.DEFENSE_LESSON and p.ticks % 2 == 0:
                self._maybe_attack(force=False)
                tutorial.on_defense_tick()
            return

        from botnet_system import BotnetManager
        if p.phase in ("career", "endless"):
            BotnetManager.on_tick(self.game)

        if p.phase == "endless":
            if p.ticks % 3 == 0 and random.random() < 0.22:
                self._maybe_attack(force=False)
            return

        if p.ticks % 4 != 0:
            return
        if self.game.blue.defense_mode and random.random() < 0.28:
            self._maybe_attack(force=False)
            return
        if p.firewall_level >= 4:
            return
        gap = max(0, 3 - p.firewall_level)
        from retention import RetentionManager
        threat_bonus = RetentionManager.rival_threat_bonus(self.game)
        from depth_systems import RivalHeatManager
        threat_bonus += RivalHeatManager.threat_bonus(self.game)
        threat_bonus += BotnetManager.threat_bonus(self.game)
        # Rookie grace: first ~20 commands in career, rivals probe less often
        rookie = p.ticks < 20 and len(self.game.retention.completed_operations) == 0
        chance = (0.12 if rookie else 0.16) * gap + threat_bonus
        if random.random() < chance:
            self._maybe_attack(force=False)

    def _maybe_attack(self, force: bool) -> None:
        p = self.game.player
        from retention import RetentionManager
        rival = RetentionManager.pick_rival_attacker(self.game)
        from depth_systems import RivalHeatManager
        if sum(self.game.meta.subnet_heat.values()) >= 3:
            rival = RivalHeatManager.pick_attacker(self.game)
        power = RetentionManager.rival_attack_power(
            self.game, random.randint(2, 4),
        )
        if not force and p.firewall_level >= power:
            in_defense_lesson = (
                self.game.tutorial.in_tutorial()
                and p.tutorial_step == TutorialManager.DEFENSE_LESSON
            )
            if not in_defense_lesson:
                return

        divider("!!! RIVAL INTRUSION — LOCALHOST !!!")
        warn(f"'{rival}' targeting {p.public_ip} (firewall L{p.firewall_level} vs attack {power})")

        if p.firewall_level >= power:
            success(f"Firewall blocked {rival}.")
            self.game.retention.last_rival = rival
            if self.game.tutorial.in_tutorial():
                self.game.tutorial.defense_attacks_triggered += 1
            else:
                from progression import ReputationSystem
                self.game.achievements.blocks_this_session += 1
                self.game.blue.attacks_blocked += 1
                if self.game.blue.defense_mode:
                    from depth_systems import SpecializationManager
                    from faction_consumables import FactionRepManager
                    rep = int(
                        (25 + self.game.blue.block_bonus())
                        * SpecializationManager.defense_rep_mult(self.game)
                        * FactionRepManager.defense_rep_mult(self.game)
                    )
                    ReputationSystem.add_rep(self.game, rep, "defense block")
                if self.game.achievements.blocks_this_session >= 3:
                    self.game.achievements.unlock("fortress")
                self.game.player.tutorial_flags.add("daily_block_done")
                if self.game.blue.defense_mode:
                    self.game.player.tutorial_flags.add("daily_defend_block_done")
                    self.game.player.tutorial_flags.add("daily_active_defense_done")
                self.game.player.tutorial_flags.add("daily_survive_done")
                from retention import RetentionManager
                RetentionManager.on_defense_block(self.game)
                from rival_ai import RivalAIManager
                RivalAIManager.send_block_taunt(self.game, rival, p.firewall_level)
            return

        loss = random.randint(40, 100) * max(1, power - p.firewall_level)
        if p.phase == "career" and p.money < 1200:
            loss = min(loss, max(35, p.money // 3))
        p.penalize(loss, f"{rival} breached your defenses")
        self.game.retention.last_rival = rival
        self.game.retention.rival_aggression = min(
            10, self.game.retention.rival_aggression + 1,
        )
        if p.phase == "endless" and self.game.endless.active:
            from endless_mode import EndlessManager
            EndlessManager.on_death(self.game, f"{rival} breach")
        from rival_ai import RivalAIManager
        RivalAIManager.send_breach_mail(self.game, rival, p.firewall_level, loss)
        if self.game.tutorial.in_tutorial():
            self.game.tutorial.defense_attacks_triggered += 1


# ---------------------------------------------------------------------------
# Game engine
# ---------------------------------------------------------------------------

class Game:
    BASE_TRACE_CHANCE = 0.28

    def __init__(self) -> None:
        from progression import AchievementTracker, BlueTeamState
        from retention import RetentionManager, RetentionState
        from session_content import SessionState
        from endless_mode import EndlessState
        from story_system import StoryState
        from social_board import SocialBoardState
        from variety_content import VarietyState

        self.player = Player()
        self.player._game_ref = self
        self.player.tutorial_flags.add(f"tutorial_{TutorialManager.CURRICULUM_VERSION}")
        self.network = VirtualNetwork(career=False)
        self.missions = MissionBoard()
        self.mail = MailBox()
        self.tutorial = TutorialManager(self)
        self.threat = ThreatSystem(self)
        self.achievements = AchievementTracker()
        self.retention = RetentionState()
        self.session = SessionState()
        self.endless = EndlessState()
        self.story = StoryState()
        self.board = SocialBoardState()
        self.variety = VarietyState()
        from llm_content import LLMState
        self.llm = LLMState()
        from depth_systems import MetaState
        self.meta = MetaState()
        self.daily = RetentionManager.make_daily_challenge()
        self.blue = BlueTeamState()
        self.running = True
        self.gui_mode = False
        self.defer_career_session = False
        self.close_terminal = False
        self.quit_game = False
        self._cmds_since_autosave = 0
        self.last_autosave = ""
        self._seed_mail()

    def autosave(self, force: bool = False) -> None:
        from progression import SaveManager
        SaveManager.autosave(self, force=force)

    def _seed_mail(self) -> None:
        self.mail.send(
            "training_officer@terminalhacker.local",
            "Welcome to TerminalHacker Training",
            "Trainee,\n\nYou are enrolled in the cybersecurity lab.\n"
            "Open Training on the desktop (or type 'lesson' in Terminal).\n\n"
            "Your $500 tutorial budget covers training losses — career funds stay locked "
            "until graduation.\n\n— Training Officer",
        )

    def banner(self) -> None:
        Console.out("Welcome to Ubuntu 24.04.2 LTS (GNU/Linux 6.8.0-generic x86_64)", "info")
        Console.out("")
        muted(" * Documentation:  https://help.ubuntu.com")
        muted(" * Management:     https://landscape.canonical.com")
        muted(" * Support:        https://ubuntu.com/pro")
        Console.out("")
        Console.out("Last login: " + time.strftime("%a %b %d %H:%M:%S on tty1"), "muted")
        Console.out("")
        divider("TERMINALHACKER TRAINING ENVIRONMENT")
        Console.out(
            "Tutorial phase uses a $500 training budget — career funds stay protected.\n"
            "Type 'lesson' for objectives. Progress saves to ~/.terminalhacker/save.json",
            "normal",
        )
        self.tutorial.show_lesson()

    def _display_path(self, path: str) -> str:
        home = "/home/hacker"
        if path == home:
            return "~"
        if path.startswith(home + "/"):
            return "~" + path[len(home):]
        return path

    def prompt(self) -> str:
        p = self.player
        if p.is_local():
            user = p.username
        elif p.remote_is_root:
            user = "root"
        else:
            user = self.remote_server().ssh_user if self.remote_server() else p.username
        host = p.prompt_host
        if p.has_remote_shell or p.is_local():
            path = self._display_path(p.cwd)
        else:
            path = "~"
        sym = "#" if (p.is_local() or p.has_remote_shell) and p.remote_is_root else "$"
        if not p.is_local() and not p.has_remote_shell:
            sym = ">"
        vpn = " [VPN]" if p.vpn_active else ""
        return f"{user}@{host}:{path}{sym}{vpn} "

    def remote_server(self) -> Server | None:
        return None if self.player.is_local() else self.network.get_server(self.player.connection)

    def require_shell(self) -> Server | None:
        s = self.remote_server()
        if not s:
            error("Not connected.")
            return None
        if not self.player.has_remote_shell:
            error("Need shell access — run crack first.")
            return None
        return s

    def egress_ip(self) -> str:
        return self.player.effective_egress_ip

    def log_remote(self, server: Server, syslog_msg: str, auth_msg: str | None = None) -> None:
        ip = self.egress_ip()
        server.write_syslog("kernel", f"{syslog_msg} [{ip}]")
        if auth_msg:
            server.write_auth(f"{auth_msg} [{ip}]")

    def resolve_path(self, path: str, files: dict[str, VirtualFile]) -> str | None:
        if path.startswith("/"):
            full = path
        else:
            full = re.sub(r"/+", "/", f"{self.player.cwd.rstrip('/')}/{path}")
        return full if full in files else None

    def can_access_file(self, f: VirtualFile) -> bool:
        if f.requires_root and not self.player.remote_is_root:
            error("Permission denied — root privileges required. Try privesc.")
            return False
        return True

    def on_shop_purchase(self, item_key: str) -> bool:
        """Called after any successful shop purchase (terminal or GUI). Returns True if just graduated."""
        key = item_key.lower()
        p = self.player
        phase_before = p.phase
        if key in ("cpu", "firewall"):
            p.tutorial_flags.add("daily_buy_done")
            p.tutorial_flags.add("daily_shop_bought")
            p.tutorial_flags.add("daily_gear_up_done")
            if key == "firewall" and self.tutorial.in_tutorial():
                p.tutorial_flags.add("tutorial_firewall_upgraded")
            if self.player.phase == "career":
                from retention import RetentionManager
                RetentionManager.on_bridge_event(self, "gear")
        self.tutorial.reconcile_stuck_lessons()
        self.tutorial.check_advance()
        self.autosave(force=True)
        return phase_before == "tutorial" and p.phase == "career"

    def post_command(self, cmd: str) -> None:
        from session_content import HourlyManager, MasteryGrader
        from main import set_teach_suppress_chaos

        set_teach_suppress_chaos(self.meta.chaos_mode)
        self.tutorial.record_command(cmd)
        MasteryGrader.on_command(self)
        self.threat.on_tick()
        if self.player.phase == "career":
            HourlyManager.refresh(self)
            self.missions.check_completion(self)
        if self.player.phase == "endless":
            self.missions.check_completion(self)
            from endless_mode import EndlessManager
            EndlessManager.check_bankruptcy(self)
            EndlessManager.on_post_command(self)
        self.tutorial.check_advance()
        self._check_daily(cmd)
        self._check_achievements()
        if self.player.phase == "tutorial" or cmd in ("save", "exit", "quit", "load"):
            self.autosave(force=True)
        else:
            self.autosave()
        if self.player.phase in ("career", "endless"):
            from retention import RetentionManager
            if self.player.phase == "career":
                RetentionManager.check_bridge_triggers(self)
            from depth_systems import ModifierManager
            ModifierManager.on_post_command(self)
            from faction_consumables import ConsumableManager
            ConsumableManager.on_post_command(self)
            from botnet_system import BotnetManager
            BotnetManager.on_post_command(self)
            from chaos_system import (
                BotnetSpreadManager, ChaosEventManager, FactionWarManager, FlashChaosManager,
            )
            from depth_systems import BrokerHeatScrub
            BotnetSpreadManager.try_spread(self)
            ChaosEventManager.on_post_command(self, cmd)
            FactionWarManager.tick_cooldown(self)
            BrokerHeatScrub.tick_cooldown(self)
            FlashChaosManager.maybe_spawn(self)

    def try_unlock(self, key: str) -> None:
        from progression import ACHIEVEMENTS
        if self.achievements.unlock(key):
            success(f"ACHIEVEMENT UNLOCKED: {ACHIEVEMENTS.get(key, key)}")

    def _check_daily(self, _cmd: str) -> None:
        from retention import DAILY_FLAGS, RetentionManager

        if self.daily.completed or self.player.phase != "career":
            return
        flag = DAILY_FLAGS.get(self.daily.flag, "")
        if flag and flag in self.player.tutorial_flags:
            self.daily.completed = True
            self.player.earn(self.daily.reward, "daily challenge")
            self.achievements.dailies_completed += 1
            RetentionManager.on_daily_complete(self)
            if self.achievements.dailies_completed >= 30:
                self.try_unlock("daily_master")
            success(f"Daily complete: {self.daily.description} (+${self.daily.reward})")
            self.autosave(force=True)

    def _check_achievements(self) -> None:
        p = self.player
        if p.cpu_level >= 6 and p.firewall_level >= 5:
            self.try_unlock("max_gear")

    # ----- commands -----

    def cmd_lesson(self, _a: list[str]) -> None:
        self.tutorial.show_lesson()

    def cmd_skip(self, args: list[str]) -> None:
        if not args or args[0].lower() not in ("tutorial", "training"):
            error("Usage: skip tutorial   — jump to career (standard or chaos)")
            teach("Standard skip: skip tutorial")
            teach("Loud skip: chaos start  (or ☠ CHAOS CAREER on the desktop banner)")
            return
        if args[0].lower() == "tutorial":
            chaos = len(args) > 1 and args[1].lower() in ("chaos", "loud")
            if self.tutorial.skip_to_career(chaos=chaos):
                self.autosave(force=True)

    def cmd_hint(self, _a: list[str]) -> None:
        from hint_system import HintManager

        cmd, why = HintManager.infer(self)
        divider("NEXT COMMAND")
        success(f"Try: {cmd}")
        teach(why)

    def cmd_help(self, _a: list[str]) -> None:
        divider("COMMANDS")
        cmds = [
            "lesson", "hint", "skip tutorial", "help", "ifconfig", "route", "route add [net] via [gw]",
            "vpn [connect|disconnect|status]", "scan/nmap [CIDR]", "connect [IP] [port]",
            "curl http://IP/path", "disconnect", "probe", "crack", "sudo -l", "privesc",
            "ls", "cat", "rm", "download [path]", "pwd", "whoami", "uname",
            "note [add|clear|set] [text]",
            "shop", "buy [item]", "missions", "contracts", "mail [list|trash|delete|restore]",
            "status", "rank",
            "achievements", "daily", "chaos", "defend", "streak", "season", "operation", "bridge",
            "intel", "rivals", "chains", "hourly", "grades",
            "endless", "story", "board", "spec", "heist", "heat", "heat cool [subnet]",
            "chaos [start|status|provoke|run|unlock|leak|war|raid|strike|news]",
            "phish", "tunnel", "plant", "forge", "infect", "botnet",
            "use [item]", "factions", "llm [test|on|off]", "world",
            "save", "load", "exit",
        ]
        Console.out("  " + "\n  ".join(cmds) + "\n")

    def cmd_ifconfig(self, _a: list[str]) -> None:
        divider("IFCONFIG")
        p = self.player
        Console.out(f"  inet {p.lan_ip}  netmask 255.255.255.0  gateway {p.gateway}")
        Console.out(f"  NAT public IP:  {p.public_ip}")
        if p.vpn_active:
            Console.out(f"  VPN exit IP:    {p.vpn_exit_ip}  (active — victims see this)")
        teach("LAN addresses (192.168.x) are private. NAT translates to your public IP.")

    def cmd_route(self, args: list[str]) -> None:
        if len(args) >= 4 and args[0] == "add" and args[2] == "via":
            cidr, gw = args[1], args[3]
            if any(r.destination == cidr for r in self.player.routes):
                warn(f"Route to {cidr} already exists.")
                return
            self.player.routes.append(Route(cidr, gw))
            success(f"Route added: {cidr} via {gw}")
            self.player.tutorial_flags.add("daily_new_route_done")
            teach("Packets to that subnet now flow through the gateway router.")
            return

        divider("ROUTING TABLE")
        for r in self.player.routes:
            Console.out(f"  {r.destination:<18} via {r.gateway:<15} dev {r.iface}")
        teach("Without a route, remote subnets (e.g. 10.0.0.0/24) are unreachable.")

    def cmd_vpn(self, args: list[str]) -> None:
        if not args:
            error("Usage: vpn [connect|disconnect|status]")
            return
        action = args[0].lower()
        p = self.player

        if action == "status":
            Console.out(f"  VPN: {'ON' if p.vpn_active else 'OFF'}  exit={p.vpn_exit_ip}")
            return

        if action == "connect":
            if p.phase == "career" and not p.vpn_licensed and "vpn_pro" not in p.owned_tools:
                error("VPN license required. buy vpn_pro in shop.")
                return
            p.vpn_active = True
            success(f"VPN tunnel up. Exit node: {p.vpn_exit_ip}")
            teach("Remote logs will now record the VPN IP instead of your public address.")
            if self.tutorial.in_tutorial() and p.tutorial_step == 8:
                p.tutorial_flags.add("vpn_success")
            return

        if action == "disconnect":
            p.vpn_active = False
            success("VPN disconnected. Traffic uses public IP again.")
            return
        error("Usage: vpn [connect|disconnect|status]")

    def cmd_scan(self, args: list[str]) -> None:
        cidr = args[0] if args else "192.168.1.0/24"
        divider(f"NMAP {cidr}")
        targets = self.network.hosts_in_cidr(cidr, self.player)
        spawned = self.network.deploy_mission_targets(self)
        for ip in spawned:
            srv = self.network.get_server(ip)
            if srv and ip_in_subnet(ip, cidr) and self.player.has_route_to(ip):
                if srv not in targets:
                    targets.append(srv)
        if not targets:
            warn(f"No reachable hosts in {cidr}. Add a route? (route add 10.0.0.0/24 via 192.168.1.1)")
            return
        for s in targets:
            self.player.discovered_ips.add(s.ip)
            company = f" [{s.company}]" if s.company else ""
            story = f" — {s.story[:50]}..." if s.story else ""
            Console.out(
                f"  {s.ip} ({s.hostname}){company} — ports: "
                + ", ".join(str(svc.port) for svc in s.services) + story
            )
        self.player.subnets_scanned.add(cidr)
        if len(self.player.subnets_scanned) >= 3:
            self.player.tutorial_flags.add("daily_scan3_done")
        if cidr == "172.16.0.0/24":
            self.player.tutorial_flags.add("daily_scan_finance_done")
        if cidr == "203.0.113.0/24":
            self.player.tutorial_flags.add("daily_scan_chaos_done")
            from chaos_system import RivalReactionManager
            RivalReactionManager.on_scan_chaos_subnet(self, cidr)
        from retention import RetentionManager
        RetentionManager.on_scan_subnet(self, cidr)
        RetentionManager.on_bridge_event(self, "scan")
        from session_content import LateralManager
        LateralManager.on_scan(self, cidr)
        self.missions.check_completion(self)
        info("Use connect <IP> 22")

    def cmd_connect(self, args: list[str]) -> None:
        if not args or not self.player.is_local():
            error("Usage: connect [IP] [port]  (from localhost)")
            return
        ip = args[0]
        port = int(args[1]) if len(args) > 1 else 22
        from depth_systems import ToolManager
        ip, port = ToolManager.resolve_connect(self, ip, port)
        if ip not in self.player.discovered_ips:
            error("Unknown host — scan first.")
            return
        if not self.player.has_route_to(ip):
            error(f"No route to {ip}. Check routing table.")
            return
        server = self.network.get_server(ip)
        if not server or not server.service_on_port(port):
            error("Connection refused.")
            return

        divider(f"CONNECT {ip}:{port}")
        info("SYN → SYN-ACK → ACK")
        Console.pause(0.2)
        self.player.connection = ip
        self.player.connected_port = port
        self.player.cwd = f"/home/{server.ssh_user}"
        self.log_remote(server, f"TCP connection to {ip}:{port}", f"Connection from port {random.randint(40000, 60000)}")

        if server.cracked:
            self.player.has_remote_shell = True
            self.player.remote_is_root = server.ip in self.player.privesc_hosts
            success(
                f"Connected to {server.hostname}. "
                f"Shell restored — already cracked{f' as root' if self.player.remote_is_root else ''}."
            )
        else:
            self.player.has_remote_shell = False
            self.player.remote_is_root = False
            success(f"Connected to {server.hostname}. Run crack for shell.")

        if ip == "192.168.1.50":
            self.player.tutorial_flags.add("connected_training")

        if self.player.phase == "career":
            from session_content import MasteryGrader
            for m in self.missions.missions:
                if not m.completed and m.target_ip == ip:
                    MasteryGrader.begin(self, m.mission_id)
                    break

    def cmd_disconnect(self, _a: list[str]) -> None:
        if self.player.is_local():
            warn("Already localhost.")
            return
        server = self.remote_server()
        from faction_consumables import ConsumableManager
        if ConsumableManager.has_trace_immunity(self):
            clean = True
        else:
            clean = not server or not server.player_left_traces(self.player)
        if server and not clean:
            from chaos_system import NotorietyManager, RivalReactionManager
            if self.meta.chaos_mode:
                NotorietyManager.add(self, 2, f"dirty disconnect {server.ip}", player_action=True)
                RivalReactionManager.on_dirty_disconnect(self, server)
            from progression import ReputationSystem
            chance = self.BASE_TRACE_CHANCE + (server.ids_alert_level * 0.08)
            if getattr(server, "chaos_only", False):
                chance = min(0.95, chance * 2)
            from depth_systems import RivalHeatManager
            chance += RivalHeatManager.trace_bonus(self, server)
            from llm_struct import LLMStructManager
            chance += LLMStructManager.world_event_trace_bonus(self)
            from faction_consumables import FactionRepManager
            chance = max(0.05, chance - FactionRepManager.trace_reduction(self, server))
            if self.player.phase == "endless":
                from endless_mode import EndlessManager
                chance = max(0.05, chance + EndlessManager.trace_modifier(self))
            if random.random() < chance:
                if self.player.phase == "endless":
                    from endless_mode import EndlessManager
                    EndlessManager.on_death(self, "forensic trace")
                else:
                    self.player.penalize(random.randint(50, 120), "Forensic trace")
        else:
            self.try_unlock("ghost_hands")
            self.player.tutorial_flags.add("daily_zero_trace_done")
            if server and server.cracked and self.player.has_remote_shell:
                from retention import RetentionManager
                RetentionManager.on_ghost_complete(self, server.ip)
                from session_content import LateralManager
                LateralManager.on_ghost(self, server.ip)
        if server:
            from retention import RetentionManager
            RetentionManager.on_disconnect_checks(self, server.ip, clean)
        self.player.connection = "localhost"
        self.player.cwd = "/home/hacker"
        self.player.reset_session()
        success("Disconnected.")

    def cmd_probe(self, _a: list[str]) -> None:
        s = self.remote_server()
        if not s:
            return
        divider("PROBE")
        self.log_remote(s, "Service fingerprint", "Probe scan")
        s.raise_ids_alert(1)
        from retention import RetentionManager
        RetentionManager.on_probe(self, s.ip)
        from variety_content import PuzzleManager
        PuzzleManager.on_probe(self, s)
        Console.out(f"  {s.hostname} | FW L{s.security_level} | cracked={s.cracked}")
        hint = PuzzleManager.puzzle_hint(s)
        if hint:
            teach(hint)
        if s.ip == "192.168.1.50":
            self.player.tutorial_flags.add("probed_training")

    def cmd_crack(self, _a: list[str]) -> None:
        s = self.remote_server()
        if not s or self.player.connected_port != 22:
            return
        if s.cracked:
            self.player.has_remote_shell = True
            if self.player.remote_is_root or s.ip in self.player.privesc_hosts:
                self.player.remote_is_root = True
            success(f"Shell access restored on {s.hostname}.")
            return

        from session_content import LateralManager
        block_msg = LateralManager.pivot_blocked(self, s.ip)
        if block_msg:
            error(block_msg)
            return
        from variety_content import PuzzleManager
        puzzle_msg = PuzzleManager.can_crack(self, s)
        if puzzle_msg:
            error(puzzle_msg)
            return
        from depth_systems import ToolManager
        from botnet_system import BotnetManager
        if ToolManager.has_backdoor(self, s.ip):
            s.cracked = True
            self.player.has_remote_shell = True
            success(f"Backdoor shell on {s.hostname} — no brute-force needed.")
            from chaos_system import CareerPressureManager, RivalReactionManager
            CareerPressureManager.on_first_crack(self, s)
            RivalReactionManager.on_crack(self, s)
            return

        divider("SSH BRUTE-FORCE")
        words = ["password", "admin", "123456", s.ssh_password]
        if s.ip in self.meta.phished_ips:
            words = [s.ssh_password] + words
        if "hydra" in self.player.owned_tools:
            words = [s.ssh_password] + [w for w in words if w != s.ssh_password]
        attempts = max(2, int((BotnetManager.effective_security(self, s) - self.player.cpu_level + 2) * 3 * self.player.crack_attempt_reduction()))

        for i in range(1, attempts + 1):
            guess = words[i % len(words)]
            Console.pause(max(0.03, 0.1 - self.player.crack_speed_bonus()))
            if guess != s.ssh_password:
                Console.out(f"    try {guess} FAIL")
                s.write_auth(f"Failed password for {s.ssh_user} from {self.egress_ip()}")
                continue
            s.cracked = True
            self.player.has_remote_shell = True
            s.write_auth(f"Accepted password for {s.ssh_user} from {self.egress_ip()}")
            success(f"Shell access: {s.ssh_user}:{guess}")
            self.player.session_cracked = True
            self.try_unlock("first_blood")
            if self.player.vpn_active:
                self.try_unlock("vpn_shadow")
                self.player.tutorial_flags.add("daily_vpn_crack_done")
                from retention import RetentionManager
                RetentionManager.on_bridge_event(self, "vpn_crack")
            else:
                self.player.tutorial_flags.add("daily_no_vpn_done")
            from retention import RetentionManager
            RetentionManager.on_crack(self, s.ip, s.security_level)
            from session_content import LateralManager
            LateralManager.on_crack(self, s.ip)
            from variety_content import VarietyManager
            VarietyManager.on_pivot_crack(self, s.ip)
            if "daily_shop_bought" not in self.player.tutorial_flags:
                self.player.tutorial_flags.add("daily_no_shop_done")
            if self.player.phase == "career":
                self.player.earn(40 + s.security_level * 20, "crack bounty")
                from progression import ReputationSystem
                ReputationSystem.add_rep(self, 15 + s.security_level * 5, "intrusion")
            from chaos_system import CareerPressureManager, RivalReactionManager
            CareerPressureManager.on_first_crack(self, s)
            RivalReactionManager.on_crack(self, s)
            return
        error("Failed — upgrade CPU or buy hydra/hashcat.")

    def cmd_sudo(self, args: list[str]) -> None:
        s = self.require_shell()
        if not s:
            return
        if args and args[0] == "-l":
            divider("SUDO -L")
            if s.privesc_available:
                Console.out(f"  (ALL) NOPASSWD: /usr/bin/cat /root/*")
                teach("Misconfigured sudo is a common real-world privesc vector.")
            else:
                Console.out("  User may not run sudo.")
            return
        error("Usage: sudo -l")

    def cmd_privesc(self, _a: list[str]) -> None:
        s = self.require_shell()
        if not s or not s.privesc_available:
            error("No privilege escalation path found.")
            return
        divider("PRIVILEGE ESCALATION")
        info("Exploiting NOPASSWD sudo misconfiguration...")
        Console.pause(0.3)
        self.player.remote_is_root = True
        self.player.remote_was_root = True
        self.player.cwd = "/root"
        if self.remote_server():
            self.player.privesc_hosts.add(self.remote_server().ip)
        success("You are now root. Prompt will show root@host#")
        self.try_unlock("root_queen")
        self.player.tutorial_flags.add("daily_privesc_done")
        from retention import RetentionManager
        RetentionManager.on_bridge_event(self, "privesc")
        from session_content import LateralManager
        if self.remote_server():
            LateralManager.on_privesc(self, self.remote_server().ip)
        if self.remote_server() and self.player.remote_was_root:
            self.player.tutorial_flags.add("daily_privesc_dl_done")
        teach("Root can read any file and persist malware — defend with least-privilege.")

    def cmd_curl(self, args: list[str]) -> None:
        if not args:
            error("Usage: curl http://IP/path")
            return
        url = args[0]
        m = re.match(r"https?://([^/]+)(/.*)?", url, re.I)
        if not m:
            error("Usage: curl http://IP/path")
            return
        ip, path = m.group(1), m.group(2) or "/"
        if ip not in self.player.discovered_ips:
            error("Unknown host — scan first.")
            return
        if not self.player.has_route_to(ip):
            error(f"No route to {ip}.")
            return
        from depth_systems import ModifierManager
        from variety_content import PuzzleManager, VarietyManager

        if ModifierManager.blocks_curl(self, ip):
            error("Air-gapped target — curl blocked for active contract.")
            return
        body = VarietyManager.fetch_http(self, ip, path)
        divider(f"CURL {url}")
        if body is None:
            warn("404 Not Found")
            return
        Console.out(body)
        server = self.network.get_server(ip)
        if server:
            self.log_remote(server, f"HTTP GET {path}", f"GET {path}")
            PuzzleManager.on_curl(self, server, path, body)
        info("HTTP fetch complete — check intel before SSH.")

    def cmd_download(self, args: list[str]) -> None:
        s = self.require_shell()
        if not s or not args:
            error("Usage: download [remote_path]")
            return
        path = self.resolve_path(args[0], s.files)
        if not path:
            error("File not found.")
            return
        f = s.files[path]
        if not self.can_access_file(f):
            return
        name = path.rsplit("/", 1)[-1]
        local = f"/home/hacker/downloads/{name}"
        self.player.files[local] = VirtualFile(local, f.read(), owner=self.player.username)
        success(f"Exfiltrated to {local}")
        from depth_systems import ModifierManager
        if self.remote_server():
            ModifierManager.on_decoy_download(self, self.remote_server(), path)
        from session_content import LateralManager
        LateralManager.on_exfil_step(self, s.ip, path)
        if s.chaos_only:
            self.try_unlock("chaos_walker")
        if "/root/" in path and self.player.remote_was_root:
            self.player.tutorial_flags.add("daily_root_exfil_done")
        if s.ip.startswith("10.0.0."):
            self.player.tutorial_flags.add("daily_corp_exfil_done")
        if "/var/log/auth.log" in args[0] or path.endswith("auth.log"):
            pass
        self.missions.check_completion(self)

    def cmd_ls(self, args: list[str]) -> None:
        files = self.player.files if self.player.is_local() else (self.require_shell() and self.remote_server().files)
        if not files:
            return
        target = args[0] if args else self.player.cwd
        d = target.rstrip("/") + "/" if target != "/" else "/"
        label = target.rstrip("/") or "/"
        divider(f"LS {label}")

        subdirs: set[str] = set()
        direct_files: list[str] = []
        for p in sorted(files):
            if not p.startswith(d) or p == label:
                continue
            rel = p[len(d):]
            if not rel:
                continue
            if "/" in rel:
                subdirs.add(d + rel.split("/")[0] + "/")
            else:
                direct_files.append(p)

        for subdir in sorted(subdirs):
            Console.out(f"  {subdir}")
        for path in direct_files:
            tag = " [root-only]" if files[path].requires_root else ""
            Console.out(f"  {path}{tag}")
        if not subdirs and not direct_files:
            muted("  (empty)")
        elif (
            not self.player.is_local()
            and self.player.has_remote_shell
            and not args
            and self.player.cwd.startswith("/home")
            and any("/var/log/" in p for p in files)
        ):
            teach("System logs live under /var/log — try: ls /var/log")

    def cmd_cat(self, args: list[str]) -> None:
        if not args:
            return
        files = self.player.files if self.player.is_local() else (self.require_shell() and self.remote_server().files)
        if not files:
            return
        path = self.resolve_path(args[0], files)
        if not path:
            error("Not found.")
            return
        f = files[path]
        if not self.can_access_file(f):
            return
        divider(f"CAT {path}")
        Console.out(f.read())
        if not self.player.is_local():
            from session_content import LateralManager
            LateralManager.on_read_intel(self, path)
            from variety_content import PuzzleManager, VarietyManager
            PuzzleManager.on_cat(self, self.remote_server(), path)
            if self.remote_server():
                for m in self.missions.missions:
                    if m.mission_type == "pivot" and path.endswith("pivot_bridge.txt"):
                        if self.remote_server().ip == m.pivot_host:
                            self.variety.pivot_step[m.mission_id] = 2
                            success("Pivot creds acquired — breach the target host.")
        if path == "/var/log/auth.log" and not self.player.is_local():
            self.player.tutorial_flags.add("read_authlog")
            self.player.tutorial_flags.add("daily_read_auth_done")
            teach("That IP is forensic evidence tying you to this intrusion.")

    def _local_notes_file(self) -> VirtualFile:
        if NOTES_PATH not in self.player.files:
            self.player.files[NOTES_PATH] = VirtualFile(NOTES_PATH, "", owner=self.player.username)
        return self.player.files[NOTES_PATH]

    def cmd_note(self, args: list[str]) -> None:
        if not self.player.is_local():
            error("Notes only editable on localhost — type disconnect first.")
            return
        notes = self._local_notes_file()
        if not args:
            divider("NOTES")
            body = notes.read().strip()
            Console.out(body if body else "(empty — use: note add 192.168.1.10 gateway)")
            Console.out("\n  note add <text>  |  note clear")
            return
        sub = args[0].lower()
        if sub == "add":
            line = " ".join(args[1:]).strip()
            if not line:
                error("Usage: note add <text>")
                return
            notes.append(line)
            success(f"Saved: {line}")
            return
        if sub == "clear":
            notes.content = ""
            success("Notes cleared.")
            return
        if sub == "set":
            text = " ".join(args[1:])
            notes.content = text + ("\n" if text and not text.endswith("\n") else "")
            success("Notes replaced.")
            return
        notes.append(" ".join(args))
        success("Saved.")

    def cmd_rm(self, args: list[str]) -> None:
        if not args:
            return
        files = self.player.files if self.player.is_local() else (self.require_shell() and self.remote_server().files)
        if not files:
            return
        path = self.resolve_path(args[0], files)
        if not path:
            return
        del files[path]
        success(f"Removed {path}")
        s = self.remote_server()
        if s and s.ip == "192.168.1.50" and not s.player_left_traces(self.player):
            self.player.tutorial_flags.add("wiped_training_logs")
        if s and not s.player_left_traces(self.player):
            if "/var/log/syslog" not in s.files and "/var/log/auth.log" not in s.files:
                self.player.tutorial_flags.add("daily_double_wipe_done")
                self.player.tutorial_flags.add("daily_exfil_wipe_done")

    def cmd_pwd(self, _a: list[str]) -> None:
        Console.out(self.player.cwd)

    def cmd_whoami(self, _a: list[str]) -> None:
        if self.player.is_local():
            Console.out(self.player.username)
        elif self.player.remote_is_root:
            Console.out("root")
        elif self.remote_server():
            Console.out(self.remote_server().ssh_user)

    def cmd_uname(self, _a: list[str]) -> None:
        if self.player.is_local():
            Console.out("Linux training-box 6.5.0 #1 x86_64")
        elif self.remote_server():
            Console.out(self.remote_server().os_name)

    def cmd_shop(self, _a: list[str]) -> None:
        if not self.player.is_local():
            error("Shop on localhost only.")
            return
        from depth_systems import ModifierManager
        if ModifierManager.shop_blocked(self):
            error("Active no-shop contract — finish it before buying gear.")
            return
        Shop.list_items(self.player)

    def cmd_buy(self, args: list[str]) -> None:
        if not self.player.is_local() or not args:
            error("Usage: buy [item]")
            return
        from depth_systems import ModifierManager
        if ModifierManager.shop_blocked(self):
            error("Active no-shop contract — finish it before buying gear.")
            return
        if Shop.buy(self.player, args[0].lower()):
            graduated = self.on_shop_purchase(args[0].lower())
            if graduated:
                teach("Training complete — career mode unlocked!")

    def cmd_missions(self, _a: list[str]) -> None:
        if self.player.phase == "tutorial":
            warn("Missions unlock after tutorial graduation.")
            return
        divider("MISSIONS")
        from rival_ai import RivalAIManager
        for m in self.missions.missions:
            line = m.status_line() + RivalAIManager.race_progress_line(self, m)
            Console.out(f"  {line}")

    def cmd_mail(self, args: list[str]) -> None:
        divider("MAIL")
        action = args[0].lower() if args else "list"
        if action in ("list", "inbox"):
            if not self.mail.messages:
                Console.out("  Inbox empty.")
                return
            for m in self.mail.messages:
                mark = "● " if not m.read else "  "
                Console.out(f"  {mark}{m.mail_id:<12} {m.subject[:44]}")
            Console.out(f"\n  {self.mail.unread_count()} unread  |  Trash: {len(self.mail.trash)}")
            Console.out("  mail read <id>  |  mail trash <id>  |  mail delete <id>  |  mail empty")
            return
        if action == "trash":
            if len(args) < 2:
                if not self.mail.trash:
                    Console.out("  Trash empty.")
                    return
                for m in self.mail.trash:
                    Console.out(f"    {m.mail_id:<12} {m.subject[:44]}")
                Console.out("\n  mail delete <id>  |  mail restore <id>  |  mail empty")
                return
            if args[1].lower() == "read":
                removed = self.mail.trash_all_read()
                success(f"Moved {removed} read message(s) to Trash." if removed else "No read messages to trash.")
                return
            if self.mail.trash_message(args[1]):
                success(f"Moved {args[1]} to Trash.")
            else:
                error(f"No inbox message {args[1]!r}.")
            return
        if action == "read":
            if len(args) < 2:
                error("Usage: mail read <mail-id>")
                return
            msg = self.mail.message_by_id(args[1])
            if not msg:
                error("Message not found.")
                return
            self.mail.mark_read(msg.mail_id)
            Console.out(f"  From: {msg.sender}")
            Console.out(f"  Subj: {msg.subject}")
            Console.out(f"  Date: {msg.timestamp}\n")
            Console.out(msg.body)
            return
        if action == "delete":
            if len(args) < 2:
                error("Usage: mail delete <mail-id>  (must be in Trash)")
                return
            if self.mail.permanent_delete(args[1]):
                success(f"Permanently deleted {args[1]}.")
            else:
                error("Message not in Trash — use: mail trash <id> first.")
            return
        if action == "restore":
            if len(args) < 2:
                error("Usage: mail restore <mail-id>")
                return
            if self.mail.restore_message(args[1]):
                success(f"Restored {args[1]} to Inbox.")
            else:
                error("Message not in Trash.")
            return
        if action == "empty":
            removed = self.mail.empty_trash()
            success(f"Emptied trash ({removed} message(s))." if removed else "Trash already empty.")
            return
        error("Usage: mail [list|read <id>|trash <id>|delete <id>|restore <id>|empty]")

    def cmd_status(self, _a: list[str]) -> None:
        p = self.player
        divider("STATUS")
        if p.phase == "career":
            Console.out("  Phase:      career (training complete)")
        else:
            Console.out(f"  Phase:      tutorial (lesson {p.tutorial_step + 1}/{len(TUTORIAL_CURRICULUM)})")
        Console.out(f"  {p.wallet_label()}")
        Console.out(f"  CPU/FW:     L{p.cpu_level} / L{p.firewall_level}")
        Console.out(f"  VPN:        {'on' if p.vpn_active else 'off'} → {p.effective_egress_ip}")
        Console.out(f"  Routes:     {len(p.routes)}")
        Console.out(f"  Tools:      {', '.join(sorted(p.owned_tools)) or 'none'}")
        if p.phase == "career":
            from progression import ReputationSystem
            Console.out(f"  Rank:       {ReputationSystem.rank_name(p)} ({p.reputation} rep)")
            Console.out(f"  Streak:     {self.retention.streak} days (best {self.retention.longest_streak})")
            Console.out(f"  Season:     tier {self.retention.season_tier}/30 ({self.retention.season_xp} XP)")
            Console.out("")
            for line in defense_firewall_help(self):
                Console.out(f"  {line}" if not line.startswith("FIREWALL") else f"\n  {line}")
            Console.out(f"  IDS level:  {self.blue.ids_level}  |  Blocks total: {self.blue.attacks_blocked}")
            d = "DONE" if self.daily.completed else self.daily.description
            Console.out(f"  Daily:      {d}")
            from faction_consumables import ConsumableManager
            for line in ConsumableManager.inventory_lines(self):
                Console.out(line)
            from botnet_system import BotnetManager
            for line in BotnetManager.status_lines(self):
                Console.out(line)

    def cmd_rank(self, _a: list[str]) -> None:
        from progression import RANKS, ReputationSystem

        divider("REPUTATION & RANK")
        p = self.player
        Console.out(f"  Current: {ReputationSystem.rank_name(p)} — {p.reputation} rep")
        for i, rank in enumerate(RANKS):
            mark = ">" if i == p.rank_index else " "
            nxt = f" (need {rank.rep_required})" if i > p.rank_index else ""
            Console.out(f"  {mark} {rank.name}{nxt}")
            if rank.routes:
                for cidr, gw in rank.routes:
                    Console.out(f"      unlocks route {cidr} via {gw}")

    def cmd_achievements(self, _a: list[str]) -> None:
        from progression import ACHIEVEMENTS

        divider("ACHIEVEMENTS")
        for key, desc in ACHIEVEMENTS.items():
            mark = "[x]" if key in self.achievements.unlocked else "[ ]"
            Console.out(f"  {mark} {desc}")

    def cmd_daily(self, _a: list[str]) -> None:
        divider("DAILY CHALLENGE")
        if self.daily.completed:
            success(f"Completed: {self.daily.description}")
        else:
            Console.out(f"  {self.daily.description}")
            Console.out(f"  Reward: ${self.daily.reward}")

    def cmd_chaos(self, args: list[str]) -> None:
        from chaos_system import ChaosCommandManager

        if args and args[0].lower() in (
            "start", "status", "provoke", "run", "leak", "war", "raid", "strike", "news",
        ):
            ChaosCommandManager.cmd_chaos(self, args)
            return
        if args and args[0].lower() == "unlock":
            from progression import CHAOS_CPU, CHAOS_FW, CHAOS_REP, ReputationSystem

            divider("CHAOS SUBNET UNLOCK")
            if not ReputationSystem.chaos_available(self.player, self):
                from faction_consumables import FactionRepManager
                need = max(0, CHAOS_REP - FactionRepManager.chaos_rep_reduction(self))
                warn(f"Requires {need} rep, CPU L{CHAOS_CPU}, FW L{CHAOS_FW}")
                return
            self.player.chaos_unlocked = True
            self.network.deploy_company_hosts_with_puzzles(self, self.player.reputation, True)
            teach("Trace chance doubled. Rewards are extreme. You asked for chaos.")
            for s in self.network.servers.values():
                if s.chaos_only and self.player.has_route_to(s.ip):
                    Console.out(f"  {s.ip} {s.hostname} — FW L{s.security_level} — {s.story}")
            return
        ChaosCommandManager.cmd_chaos(self, args)
        if self.player.phase in ("career", "endless"):
            divider("CHAOS SUBNET")
            if self.player.chaos_unlocked:
                Console.out("  203.0.113.0/24 chaos hosts are live. Trace chance doubled there.")
            else:
                Console.out("  Type: chaos unlock  (needs rep + gear — see status)")

    def cmd_defend(self, args: list[str]) -> None:
        if not args:
            divider("BLUE TEAM — DEFENSE")
            for line in defense_firewall_help(self):
                Console.out(f"  {line}")
            Console.out(f"  IDS level:    {self.blue.ids_level}")
            Console.out(f"  Blocks total: {self.blue.attacks_blocked}")
            Console.out("  Usage: defend on | defend off | defend upgrade | defend block [IP]")
            return
        action = args[0].lower()
        if action == "on":
            self.blue.defense_mode = True
            success("Defense mode ON — rivals attack more often; blocks earn rep.")
            from retention import RetentionManager
            RetentionManager.on_bridge_event(self, "defend_on")
            return
        if action == "off":
            self.blue.defense_mode = False
            success("Defense mode off.")
            return
        if action == "upgrade":
            cost = 200 * self.blue.ids_level
            if not self.player.spend(cost, "IDS upgrade"):
                return
            self.blue.ids_level += 1
            success(f"IDS level {self.blue.ids_level}")
            return
        if action == "block" and len(args) > 1:
            ip = args[1]
            self.blue.blocked_ips.add(ip)
            success(f"Blocked {ip} on local firewall rules.")
            return
        error("Usage: defend [on|off|upgrade|block IP]")

    def cmd_contracts(self, _a: list[str]) -> None:
        if self.player.phase == "tutorial":
            warn("Career only.")
            return
        from progression import MissionGenerator

        self.player.tutorial_flags.add("daily_request_done")
        from retention import RetentionManager
        RetentionManager.on_bridge_event(self, "request")
        m = MissionGenerator.generate(self)
        if m:
            self.missions.missions.append(m)
            success(f"New contract: {m.briefing} (${m.reward})")
            self.mail.send(f"{m.broker}@darknet", f"Contract {m.mission_id}", m.briefing)
        else:
            warn("No contracts available — complete one first or rank up.")

    def cmd_streak(self, _a: list[str]) -> None:
        from retention import STREAK_MILESTONES

        r = self.retention
        divider("LOGIN STREAK")
        Console.out(f"  Current streak:  {r.streak} days")
        Console.out(f"  Longest streak:  {r.longest_streak} days")
        Console.out(f"  Last login:      {r.last_login or 'never'}")
        Console.out("\n  Milestones:")
        for day, (cash, xp, msg) in sorted(STREAK_MILESTONES.items()):
            mark = "[x]" if r.streak >= day else "[ ]"
            Console.out(f"  {mark} Day {day:2d} — ${cash} + {xp} season XP — {msg}")

    def cmd_season(self, _a: list[str]) -> None:
        from retention import SEASON_TIERS

        r = self.retention
        divider("30-DAY SEASON TRACK")
        Console.out(f"  Tier: {r.season_tier}/{len(SEASON_TIERS)}  |  XP bank: {r.season_xp}")
        if r.season_tier < len(SEASON_TIERS):
            nxt = SEASON_TIERS[r.season_tier]
            Console.out(f"  Next tier needs {nxt['xp']} XP — reward: ${nxt['cash']} + {nxt['rep']} rep")
        Console.out("\n  Upcoming rewards:")
        for i in range(r.season_tier, min(r.season_tier + 5, len(SEASON_TIERS))):
            t = SEASON_TIERS[i]
            Console.out(f"    Tier {i + 1}: {t['label']} — ${t['cash']}")

    def cmd_operation(self, _a: list[str]) -> None:
        from retention import OPERATIONS

        r = self.retention
        divider("ACTIVE OPERATION")
        if not r.active_operation:
            Console.out("  No active operation. Check Mail for new multi-day ops.")
            return
        op = next((o for o in OPERATIONS if o["id"] == r.active_operation), None)
        if not op:
            return
        Console.out(f"  {op['name']} — Phase {r.operation_step}/{len(op['parts'])}")
        if r.operation_unlock_day > date.today().isoformat():
            Console.out(f"  Next phase unlocks: {r.operation_unlock_day}")
        else:
            Console.out("  Current phase is active — check missions.")
        for m in self.missions.missions:
            if m.operation_id == r.active_operation and not m.completed:
                Console.out(f"  Objective: {m.briefing}")
        from retention import RetentionManager
        if RetentionManager.bridge_active(self):
            divider("TONIGHT'S PREP (same-day)")
            Console.out(RetentionManager.bridge_summary(self))
            Console.out("  Parallel tracks: daily challenge, weekly bounty, procedural contracts.")

    def cmd_bridge(self, _a: list[str]) -> None:
        from retention import BRIDGE_BONUS_CASH, BRIDGE_BONUS_XP, RetentionManager

        divider("PHASE PREP — SAME-DAY OBJECTIVES")
        r = self.retention
        if not RetentionManager.bridge_active(self):
            if r.bridge_claimed:
                Console.out("  Prep complete for tonight — next op phase unlocks tomorrow.")
            elif r.bridge_unlock_day and r.bridge_unlock_day <= date.today().isoformat():
                Console.out("  New op phase may be available. Type 'operation'.")
            else:
                Console.out("  No prep window active.")
                Console.out("  Finish an operation phase to unlock tonight's side objectives.")
            Console.out("\n  Always available: daily, contracts, weekly bounty, shop, defend.")
            return
        Console.out(f"  Unlocks: {r.bridge_unlock_day} (tomorrow's op phase)")
        Console.out(RetentionManager.bridge_summary(self))
        Console.out(
            f"\n  Complete all 3 for +${BRIDGE_BONUS_CASH} + {BRIDGE_BONUS_XP} season XP."
        )
        Console.out("  These stack with your daily challenge and weekly bounty.")

    def cmd_intel(self, _a: list[str]) -> None:
        from retention import OPERATIONS, RetentionManager, WEEKLY_RIVAL_MAIL, WEEKLY_STORY_MAIL

        story = RetentionManager.current_week_story()
        idx = date.today().isocalendar().week % len(WEEKLY_STORY_MAIL)
        rival = WEEKLY_RIVAL_MAIL[idx % len(WEEKLY_RIVAL_MAIL)]
        divider("WEEKLY INTEL BRIEFING")
        Console.out(f"  From: {story['sender']}")
        Console.out(f"  Re:   {story['subject']}\n")
        Console.out(story["body"])
        addendum = RetentionManager._story_addendum(self)
        if addendum:
            Console.out(f"\n--- Rival situation (your ops) ---\n{addendum}")
        Console.out(f"\n--- Rival chatter ({rival['sender']}) ---\n")
        Console.out(rival["body"])
        r = self.retention
        Console.out(
            f"\n  Streak: {r.streak}d | Season: {r.season_tier}/30 | "
            f"Ops done: {len(r.completed_operations)}/{len(OPERATIONS)}"
        )
        Console.out("\n  Type 'rivals' for full dossier.")

    def cmd_rivals(self, _a: list[str]) -> None:
        from retention import RetentionManager, OPERATIONS
        from rival_ai import RivalAIManager

        divider("RIVAL DOSSIER")
        r = self.retention
        Console.out(f"  Threat level: {r.rival_aggression}/10")
        Console.out(f"  Primary rival: {r.last_rival or 'none (territory-weighted picks)'}")
        for line in RivalAIManager.dossier_extra_lines(self):
            Console.out(line)
        if not r.completed_operations:
            Console.out("\n  No operation history yet — rivals still probe and race you.")
            Console.out("  Complete multi-day ops to unlock deeper dossier intel.")
            return
        for line in RetentionManager.rival_dossier_lines(self):
            Console.out(f"  {line}")
        from rival_ai import RivalAIManager
        for line in RivalAIManager.dossier_extra_lines(self):
            Console.out(line)
        Console.out("\n  Completed ops:")
        for op_id in r.completed_operations:
            Console.out(f"    [x] {op_id}")
        Console.out(f"\n  Aggression raises rival attack frequency and power.")
        Console.out(f"  Last angry rival: {r.last_rival or 'none'}")

    def cmd_chains(self, args: list[str]) -> None:
        from session_content import LateralManager

        divider("LATERAL MOVEMENT CHAINS")
        s = self.session
        if s.active_chain_id:
            chain = LateralManager.chain_by_id(s.active_chain_id)
            if chain:
                step = LateralManager.active_step(self)
                n = s.chain_step + 1
                total = len(chain["steps"])
                label = step["label"] if step else "complete"
                Console.out(f"  ACTIVE: {chain['name']} — step {n}/{total}: {label}")
        else:
            Console.out("  No active chain. Start one with: chains start <id>")
        Console.out("\n  Available chains:")
        for c in LateralManager.available_chains(self):
            mark = "[x]" if c["id"] in s.completed_chains else "[ ]"
            Console.out(
                f"  {mark} {c['id']}: {c['name']} — ${c['reward']} + {c['rep_reward']} rep "
                f"(min {c.get('min_rep', 0)} rep)"
            )
        if args and args[0] == "start" and len(args) > 1:
            LateralManager.start_chain(self, args[1])

    def cmd_hourly(self, _a: list[str]) -> None:
        from session_content import HourlyManager

        divider("HOURLY FLASH EVENT")
        if self.player.phase != "career":
            warn("Career mode only.")
            return
        HourlyManager.refresh(self)
        s = self.session
        remaining = HourlyManager.time_remaining()
        status = "COMPLETED this hour" if s.hourly_completed else "OPEN"
        Console.out(f"  Time left: {remaining}")
        for m in self.missions.missions:
            if m.hourly_event and not m.completed:
                Console.out(f"  [{status}] {m.briefing} (${m.reward} base, {m.reward_multiplier}x)")
                return
        Console.out("  No flash event this hour (rank too low or already cleared).")

    def cmd_grades(self, _a: list[str]) -> None:
        from session_content import GRADE_MULTIPLIERS

        divider("MASTERY GRADES")
        Console.out("  S=1.5x pay +40 rep | A=1.25x +20 | B=1.0x | C=0.85x")
        Console.out("  Graded on: log traces, command count, shop buys, VPN use.\n")
        if not self.session.best_grades:
            Console.out("  No graded contracts yet.")
            return
        for mid, grade in sorted(self.session.best_grades.items()):
            mult = GRADE_MULTIPLIERS.get(grade, 1.0)
            Console.out(f"  {mid}: {grade} ({mult}x)")
        Console.out(f"\n  S-ranks earned: {self.session.s_rank_total}")

    def cmd_endless(self, args: list[str]) -> None:
        from endless_mode import EndlessManager, RELIC_DEFS

        if not args:
            divider("ENDLESS MODE — ROGUELIKE RUN")
            for line in EndlessManager.status_lines(self):
                Console.out(line)
            if self.player.phase == "career":
                Console.out("\n  Type 'endless start' to begin a run (permadeath).")
            return
        action = args[0].lower()
        if action == "start":
            EndlessManager.start_run(self)
            return
        if action == "quit":
            EndlessManager.quit_run(self)
            return
        if action == "relic" and len(args) > 1:
            EndlessManager.pick_relic(self, args[1].lower())
            return
        error("Usage: endless [start|quit|relic <name>]")

    def cmd_story(self, args: list[str]) -> None:
        from story_system import StoryManager

        divider("BRANCHING STORY")
        for line in StoryManager.status_lines(self):
            Console.out(line)
        if args and args[0] == "choose" and len(args) > 1:
            StoryManager.make_choice(self, args[1].lower())
            return
        if self.player.phase == "career":
            Console.out("\n  Type 'story choose <ghost|rivals|solo|...>' when Mail prompts.")

    def cmd_board(self, args: list[str]) -> None:
        from social_board import BOARD_NAMES, SocialBoardManager

        if self.player.phase not in ("career", "endless"):
            warn("Board unlocks in career mode.")
            return
        SocialBoardManager.seed_if_needed(self)
        if not args:
            divider("DARKNET BOARDS — intel | rivals | flex | lfg")
            Console.out(f"  Karma: {self.board.karma}")
            for p in SocialBoardManager.list_posts(self):
                Console.out(f"  {SocialBoardManager.format_post(p)}")
            Console.out("\n  board <name> | board post <board> <title> | <body>")
            Console.out("  board upvote <post-id>")
            return
        action = args[0].lower()
        if action in BOARD_NAMES:
            divider(f"BOARD /{action}/")
            for p in SocialBoardManager.list_posts(self, action):
                Console.out(f"  {SocialBoardManager.format_post(p)}")
                Console.out(f"    {p.body[:120]}{'...' if len(p.body) > 120 else ''}\n")
            return
        if action == "post":
            if len(args) < 3:
                error("Usage: board post <board> <title> | <body>")
                return
            board = args[1].lower()
            rest = " ".join(args[2:])
            if "|" in rest:
                title, body = [x.strip() for x in rest.split("|", 1)]
            else:
                title, body = rest[:40], rest
            SocialBoardManager.player_post(self, board, title, body)
            return
        if action == "upvote" and len(args) > 1:
            SocialBoardManager.upvote(self, args[1])
            return
        error(f"Usage: board [<{'|'.join(BOARD_NAMES)}>|post|upvote]")

    def cmd_spec(self, args: list[str]) -> None:
        from depth_systems import SPECIALIZATIONS, SpecializationManager

        divider("SPECIALIZATION")
        spec = self.meta.specialization
        if spec:
            Console.out(f"  Active: {SPECIALIZATIONS[spec]['name']} — {SPECIALIZATIONS[spec]['desc']}")
        elif self.meta.spec_unlock_pending:
            Console.out("  UNLOCKED — pick with: spec pick <ghost|broker|saboteur|architect>")
        else:
            Console.out("  Unlocks at rank Packet Runner or Ghost in the Wires.")
        if args and args[0] == "pick" and len(args) > 1:
            SpecializationManager.pick(self, args[1].lower())
        elif args and args[0] == "respec":
            SpecializationManager.respec(self)

    def cmd_heist(self, args: list[str]) -> None:
        from depth_systems import WeeklyHeistManager

        divider("WEEKLY HEIST")
        for line in WeeklyHeistManager.status_lines(self):
            Console.out(line)
        if args and args[0] == "choose" and len(args) > 1:
            WeeklyHeistManager.choose_branch(self, args[1].lower())

    def cmd_heat(self, args: list[str]) -> None:
        from depth_systems import BrokerHeatScrub, RivalHeatManager

        if args and args[0].lower() == "cool":
            BrokerHeatScrub.cool(self, args[1] if len(args) > 1 else "")
            return

        divider("SUBNET HEAT — RIVAL PRESSURE")
        for line in RivalHeatManager.status_lines(self):
            Console.out(line)
        for line in BrokerHeatScrub.status_lines(self):
            Console.out(line)
        Console.out("\n  High heat = more traces and rival attacks on that subnet.")
        if self.player.phase in ("career", "endless"):
            Console.out(
                "  Emergency: heat cool [subnet] — pay brokers to drop heat "
                f"(min {BrokerHeatScrub.MIN_HEAT}/10, costly, ~{BrokerHeatScrub.COOLDOWN} cmd cooldown)."
            )

    def cmd_phish(self, args: list[str]) -> None:
        if not args:
            error("Usage: phish <IP>")
            return
        from depth_systems import ToolManager
        ToolManager.cmd_phish(self, args[0])

    def cmd_tunnel(self, args: list[str]) -> None:
        from depth_systems import ToolManager
        ToolManager.cmd_tunnel(self, args)

    def cmd_plant(self, _a: list[str]) -> None:
        from depth_systems import ToolManager
        ToolManager.cmd_plant(self)

    def cmd_forge(self, _a: list[str]) -> None:
        from depth_systems import ToolManager
        ToolManager.cmd_forge(self)

    def cmd_infect(self, args: list[str]) -> None:
        from botnet_system import BotnetManager
        BotnetManager.cmd_infect(self, args)

    def cmd_botnet(self, args: list[str]) -> None:
        from botnet_system import BotnetManager
        BotnetManager.cmd_botnet(self, args)

    def cmd_use(self, args: list[str]) -> None:
        if not args:
            error("Usage: use <burner_ip|zero_day|decoy_log>")
            return
        from faction_consumables import ConsumableManager
        ConsumableManager.use(self, args[0].lower())

    def cmd_factions(self, _a: list[str]) -> None:
        if self.player.phase not in ("career", "endless"):
            warn("Factions unlock in career mode.")
            return
        from faction_consumables import FactionRepManager
        divider("FACTION STANDING")
        for line in FactionRepManager.status_lines(self):
            Console.out(line)
        Console.out("\n  Shift rep via story choices, contracts, and board posts.")

    def cmd_llm(self, args: list[str]) -> None:
        from llm_content import LLMContentManager

        if not args:
            divider("LLM DYNAMIC CONTENT")
            for line in LLMContentManager.status_lines(self):
                Console.out(line)
            Console.out("\n  llm test | llm on | llm off")
            return
        action = args[0].lower()
        if action == "test":
            LLMContentManager.test_generation(self)
            return
        if action == "on":
            self.llm.user_enabled = True
            success("LLM flavor + structural generation enabled.")
            return
        if action == "off":
            self.llm.user_enabled = False
            success("LLM disabled (templates only).")
            return
        error("Usage: llm [test|on|off]")

    def cmd_world(self, _args: list[str]) -> None:
        from llm_struct import LLMStructManager

        divider("WEEKLY WORLD EVENT")
        ev = self.llm.world_event
        if not ev:
            ev = LLMStructManager.refresh_world_event(self)
        if not ev:
            Console.out("  No world event yet. Configure LLM (llm test) for dynamic weekly events.")
            Console.out("  Template bounties and rival heat still apply from retention.py.")
            return
        Console.out(f"  Week: {self.llm.world_event_week}")
        Console.out(f"  {ev.get('title', 'Unknown')}")
        if ev.get("briefing"):
            Console.out(f"\n  {ev['briefing']}")
        Console.out(
            f"\n  Heat Δ: {ev.get('heat_delta', 0)} | "
            f"Rival aggression Δ: {ev.get('rival_aggression_delta', 0)} | "
            f"Bounty mult: {ev.get('bounty_multiplier', 1.0)}x | "
            f"Trace bonus: {ev.get('trace_bonus', 0)}"
        )

    def cmd_save(self, _a: list[str]) -> None:
        from progression import SaveManager
        SaveManager.save(self)

    def cmd_load(self, _a: list[str]) -> None:
        from progression import SaveManager
        if SaveManager.load(self):
            self.player._game_ref = self

    def cmd_exit(self, _a: list[str]) -> None:
        if self.gui_mode:
            self.autosave(force=True)
            self.close_terminal = True
            Console.out("Back to desktop — progress saved. (Use quit to leave the game.)")
            return
        self.running = False
        self.autosave(force=True)
        Console.out("Goodbye.")

    def cmd_quit(self, _a: list[str]) -> None:
        self.autosave(force=True)
        if self.gui_mode:
            self.quit_game = True
            self.close_terminal = True
            Console.out("Saving and quitting...")
            return
        self.running = False
        Console.out("Goodbye.")

    def dispatch(self, raw: str) -> None:
        parts = raw.strip().split()
        if not parts:
            return
        cmd, args = parts[0].lower(), parts[1:]

        if cmd == "sudo" and args == ["-l"]:
            self.cmd_sudo(args)
            self.post_command("sudo")
            return
        if cmd == "route":
            self.cmd_route(args)
            self.post_command("route")
            return

        handlers: dict[str, Callable[[list[str]], None]] = {
            "lesson": self.cmd_lesson, "hint": self.cmd_hint, "skip": self.cmd_skip, "help": self.cmd_help, "ifconfig": self.cmd_ifconfig,
            "vpn": self.cmd_vpn, "scan": self.cmd_scan, "nmap": self.cmd_scan,
            "connect": self.cmd_connect, "disconnect": self.cmd_disconnect,
            "probe": self.cmd_probe, "crack": self.cmd_crack, "curl": self.cmd_curl, "privesc": self.cmd_privesc,
            "download": self.cmd_download, "ls": self.cmd_ls, "cat": self.cmd_cat,
            "note": self.cmd_note, "notes": self.cmd_note,
            "rm": self.cmd_rm, "pwd": self.cmd_pwd, "whoami": self.cmd_whoami,
            "uname": self.cmd_uname, "shop": self.cmd_shop, "buy": self.cmd_buy,
            "missions": self.cmd_missions, "contracts": self.cmd_contracts, "mail": self.cmd_mail,
            "status": self.cmd_status, "rank": self.cmd_rank,
            "achievements": self.cmd_achievements, "daily": self.cmd_daily,
            "chaos": self.cmd_chaos, "defend": self.cmd_defend,
            "streak": self.cmd_streak, "season": self.cmd_season, "operation": self.cmd_operation,
            "intel": self.cmd_intel, "rivals": self.cmd_rivals, "bridge": self.cmd_bridge,
            "chains": self.cmd_chains, "hourly": self.cmd_hourly, "grades": self.cmd_grades,
            "endless": self.cmd_endless, "story": self.cmd_story, "board": self.cmd_board,
            "spec": self.cmd_spec, "heist": self.cmd_heist, "heat": self.cmd_heat,
            "phish": self.cmd_phish, "tunnel": self.cmd_tunnel, "plant": self.cmd_plant,
            "forge": self.cmd_forge, "infect": self.cmd_infect, "botnet": self.cmd_botnet,
            "use": self.cmd_use, "factions": self.cmd_factions,
            "llm": self.cmd_llm,
            "world": self.cmd_world,
            "save": self.cmd_save, "load": self.cmd_load,
            "exit": self.cmd_exit, "quit": self.cmd_quit,
        }
        if cmd in handlers:
            handlers[cmd](args)
            self.post_command(cmd)
        else:
            error("Unknown command. Try lesson or help.")

    def run(self) -> None:
        try:
            import readline  # noqa: F401 — enables arrow-key history in CLI mode
        except ImportError:
            pass
        self.banner()
        while self.running:
            try:
                self.dispatch(input(self.prompt()))
            except (EOFError, KeyboardInterrupt):
                self.cmd_exit([])
                break


def main() -> None:
    import sys
    if "--cli" in sys.argv:
        Game().run()
        return
    try:
        from gui import run_gui
        run_gui()
    except ImportError as exc:
        Console.out(f"GUI unavailable ({exc}). Falling back to CLI.")
        Game().run()


if __name__ == "__main__":
    main()
