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
from typing import Callable


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def divider(title: str = "") -> None:
    line = "=" * 62
    if title:
        print(f"\n{line}\n  {title}\n{line}")
    else:
        print(line)


def info(message: str) -> None:
    print(f"[*] {message}")


def success(message: str) -> None:
    print(f"[+] {message}")


def warn(message: str) -> None:
    print(f"[!] {message}")


def error(message: str) -> None:
    print(f"[-] {message}")


def teach(message: str) -> None:
    print(f"[?] {message}")


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
        0, "Network Identity",
        "Every machine has a private LAN address (RFC 1918) and, behind NAT, a public IP "
        "that victims see in logs. Defenders monitor both.",
        "Run: ifconfig",
        "ifconfig shows eth0, your LAN IP, gateway, and NAT/public address.",
    ),
    TutorialLesson(
        1, "Routing Tables",
        "Routers forward packets using routing tables. Without a route to a subnet, "
        "traffic never leaves your gateway.",
        "Run: route",
        "route prints destinations, gateways, and interfaces.",
    ),
    TutorialLesson(
        2, "Host Discovery",
        "Pen testers enumerate live hosts with port scanners (nmap). Open ports reveal "
        "attack surface (SSH/HTTP/etc.).",
        "Run: scan   (or nmap)",
        "Scan your lab subnet 192.168.1.0/24 to find training-node.",
    ),
    TutorialLesson(
        3, "TCP Sessions",
        "TCP uses a 3-way handshake (SYN, SYN-ACK, ACK) before SSH can authenticate.",
        "Run: connect 192.168.1.50 22",
        "Connect to the training host discovered in the previous step.",
    ),
    TutorialLesson(
        4, "Service Fingerprinting",
        "Probing banners and versions helps choose exploits. IDS systems log probes.",
        "Run: probe",
        "Probe the host you are connected to.",
    ),
    TutorialLesson(
        5, "Credential Attacks",
        "Brute-force tries passwords until SSH accepts. Failed attempts land in auth.log.",
        "Run: crack",
        "Crack SSH on the training host. CPU level affects speed.",
    ),
    TutorialLesson(
        6, "Log Forensics",
        "Blue teams investigate auth.log/syslog. Your public IP is evidence.",
        "Run: cat /var/log/auth.log",
        "Read the remote auth log and find your IP address recorded.",
    ),
    TutorialLesson(
        7, "Covering Tracks",
        "Deleting log files is illegal in the real world — here it teaches why wiping "
        "matters before disconnecting.",
        "Run: rm /var/log/syslog  then  rm /var/log/auth.log",
        "Remove BOTH log files on the remote training host.",
    ),
    TutorialLesson(
        8, "Data Exfiltration",
        "Attackers copy stolen files to their machine via SFTP/SCP equivalents.",
        "Run: download /home/trainee/training_flag.txt",
        "Download the flag file, then disconnect safely.",
    ),
    TutorialLesson(
        9, "VPN / Proxy Routing",
        "VPNs tunnel traffic through an exit node so victims log the VPN IP, not yours. "
        "Critical for anonymity.",
        "Run: vpn connect  then reconnect and crack without exposing your real public IP.",
        "Activate VPN before your next connection to training-node.",
    ),
    TutorialLesson(
        10, "Subnet Segmentation",
        "Enterprises segment networks (192.168.x vs 10.x). You need a route via the "
        "gateway to reach other subnets.",
        "Run: route add 10.0.0.0/24 via 192.168.1.1  then  scan 10.0.0.0/24",
        "Add the corporate route and scan the 10.0.0.0/24 subnet.",
    ),
    TutorialLesson(
        11, "Privilege Escalation",
        "Initial access is often a low-privilege user. Misconfigured sudo lets you become root.",
        "Connect to 10.0.0.99, crack, run: sudo -l  then  privesc  then download /root/classified.txt",
        "Escalate to root on tutorial-dmz and steal the root-only file.",
    ),
    TutorialLesson(
        12, "Defense & Blue Team",
        "Rivals attack weak firewalls. Blue team upgrades defenses. Tutorial budget absorbs "
        "training losses — NOT your career money.",
        "Run: buy firewall  (uses tutorial credits) and survive rival probes.",
        "Purchase a firewall upgrade. Rival attacks will drain tutorial credits only.",
    ),
]


class TutorialManager:
    TUTORIAL_BUDGET = 500
    DEFENSE_LESSON = 12

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

    def current(self) -> TutorialLesson:
        step = min(self.player.tutorial_step, len(TUTORIAL_CURRICULUM) - 1)
        return TUTORIAL_CURRICULUM[step]

    def show_lesson(self) -> None:
        lesson = self.current()
        divider(f"TUTORIAL {lesson.step + 1}/{len(TUTORIAL_CURRICULUM)} — {lesson.title}")
        teach(lesson.concept)
        print(f"\n  Objective: {lesson.objective}")
        print(f"  Hint:      {lesson.hint}")
        if self.in_tutorial():
            print(f"\n  Tutorial budget: ${self.player.tutorial_credits} (career funds protected)\n")

    def record_command(self, cmd: str) -> None:
        self.player.command_history.add(cmd)

    def check_advance(self) -> None:
        if not self.in_tutorial():
            return
        p = self.player
        step = p.tutorial_step
        g = self.game

        checks: dict[int, Callable[[], bool]] = {
            0: lambda: "ifconfig" in p.command_history,
            1: lambda: "route" in p.command_history,
            2: lambda: "scan" in p.command_history or "nmap" in p.command_history,
            3: lambda: p.connection == "192.168.1.50" or "connected_training" in p.tutorial_flags,
            4: lambda: "probed_training" in p.tutorial_flags,
            5: lambda: g.network.get_server("192.168.1.50") and g.network.get_server("192.168.1.50").cracked,
            6: lambda: "read_authlog" in p.tutorial_flags,
            7: lambda: "wiped_training_logs" in p.tutorial_flags,
            8: lambda: "/home/hacker/downloads/training_flag.txt" in p.files and p.is_local(),
            9: lambda: "vpn_success" in p.tutorial_flags and p.vpn_active,
            10: lambda: any(ip.startswith("10.0.0.") for ip in p.discovered_ips),
            11: lambda: "/home/hacker/downloads/classified.txt" in p.files and p.remote_was_root,
            12: lambda: self.defense_survived and p.firewall_level >= 2,
        }

        if step >= len(TUTORIAL_CURRICULUM):
            return
        if checks.get(step, lambda: False)():
            self._complete_step()

    def _complete_step(self) -> None:
        lesson = self.current()
        divider("LESSON COMPLETE")
        success(f"{lesson.title} mastered.")
        self.player.tutorial_step += 1
        if self.player.tutorial_step == self.DEFENSE_LESSON:
            self.defense_start_tick = self.player.ticks
            teach("Rivals will attack soon. Use tutorial credits to buy firewall BEFORE losses stack.")

        if self.player.tutorial_step >= len(TUTORIAL_CURRICULUM):
            self.graduate()
        else:
            self.show_lesson()

    def graduate(self) -> None:
        p = self.player
        p.phase = "career"
        p.money = max(500, 500 + p.tutorial_credits)
        p.tutorial_credits = 0
        self.game.network.add_career_hosts()
        divider("CAREER MODE UNLOCKED")
        success("Training complete. You are cleared for live contracts.")
        teach(
            "Career mode uses REAL money. Traces and rivals hit your wallet. "
            "Use VPN, wipe logs, upgrade CPU/firewall, and take missions."
        )
        print(f"  Starting career balance: ${p.money}\n")
        self.game.missions.announce_login()

    def on_defense_tick(self) -> None:
        if not self.in_tutorial() or self.player.tutorial_step != self.DEFENSE_LESSON:
            return
        if self.defense_survived:
            return
        if self.defense_start_tick is not None and self.player.ticks - self.defense_start_tick < 2:
            return
        if self.player.firewall_level >= 2 and self.defense_attacks_triggered >= 1:
            self.defense_survived = True
            success("Defense drill passed — firewall blocked rival probes.")
            self.check_advance()


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

    def status_line(self) -> str:
        mark = "[DONE]" if self.completed else "[OPEN]"
        return f"{mark} {self.broker}: {self.briefing} (reward ${self.reward})"


class MissionBoard:
    def __init__(self) -> None:
        self.missions = [
            Mission("ghost-001", "ghost_broker",
                    "Hack 10.0.0.42, download corporate_secrets.txt, wipe logs.", "10.0.0.42",
                    "/home/admin/corporate_secrets.txt", 750),
            Mission("cipher-002", "cipher7",
                    "Crack vault-server (10.0.0.55), privesc, exfil payroll.csv.", "10.0.0.55",
                    "/root/payroll.csv", 1500),
        ]
        self._announced = False

    def announce_login(self) -> None:
        if self._announced:
            return
        divider("INCOMING — MISSION BOARD")
        print('  [ghost_broker] "You are cleared for live ops. Type missions."\n')
        self._announced = True

    def check_completion(self, player: Player, network: VirtualNetwork) -> None:
        for mission in self.missions:
            if mission.completed:
                continue
            fname = mission.target_file.rsplit("/", 1)[-1]
            if f"/home/hacker/downloads/{fname}" not in player.files:
                continue
            server = network.get_server(mission.target_ip)
            logs_ok = not server or not server.player_left_traces(player)
            if logs_ok:
                mission.completed = True
                player.earn(mission.reward, f"contract {mission.broker}")


# ---------------------------------------------------------------------------
# Shop
# ---------------------------------------------------------------------------

@dataclass
class ShopItem:
    key: str
    name: str
    description: str
    base_cost: int
    max_level: int = 6


SHOP_CATALOG = [
    ShopItem("cpu", "CPU Upgrade", "Faster brute-force attacks.", 200, 6),
    ShopItem("firewall", "Firewall Upgrade", "Blocks rival hackers & reduces trace risk.", 175, 5),
    ShopItem("vpn_pro", "VPN Pro License", "Permanent VPN access in career mode.", 300, 1),
    ShopItem("hydra", "Hydra Lite", "Smarter password wordlist ordering.", 350, 1),
    ShopItem("hashcat", "Hashcat Pro", "Cuts failed crack attempts ~40%.", 800, 1),
]


class Shop:
    @staticmethod
    def list_items(player: Player) -> None:
        divider("BLACK MARKET SHOP")
        wallet = player.wallet_label()
        print(f"  {wallet}\n")
        for item in SHOP_CATALOG:
            if item.key in ("cpu", "firewall"):
                lvl = player.cpu_level if item.key == "cpu" else player.firewall_level
                if lvl >= item.max_level:
                    print(f"  {item.key:<10} {item.name:<18} MAXED (L{lvl})")
                else:
                    cost = item.base_cost * (lvl + 1)
                    print(f"  {item.key:<10} {item.name:<18} ${cost} → L{lvl + 1}")
            else:
                owned = item.key in player.owned_tools
                print(f"  {item.key:<10} {item.name:<18} {'OWNED' if owned else '$' + str(item.base_cost)}")
            print(f"             {item.description}")
        print("\n  buy [item]\n")

    @staticmethod
    def buy(player: Player, key: str) -> bool:
        item = next((i for i in SHOP_CATALOG if i.key == key), None)
        if not item:
            error(f"Unknown item '{key}'.")
            return False
        if item.key == "cpu":
            if player.cpu_level >= item.max_level:
                warn("CPU maxed.")
                return False
            cost = item.base_cost * (player.cpu_level + 1)
            if not player.spend(cost, f"CPU upgrade"):
                return False
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

    def __post_init__(self) -> None:
        if not self.routes:
            self.routes = [Route("192.168.1.0/24", self.gateway)]
        if not self.files:
            self.files = {
                "/home/hacker/notes.txt": VirtualFile(
                    "/home/hacker/notes.txt",
                    "Type 'lesson' at any time for your current training objective.\n",
                    owner=self.username,
                ),
                "/var/log/syslog": VirtualFile("/var/log/syslog", syslog_line("localhost", "systemd", "boot") + "\n", mode="rw-r-----"),
                "/var/log/auth.log": VirtualFile("/var/log/auth.log", syslog_line("localhost", "sshd", "listening") + "\n", mode="rw-r-----"),
            }

    @property
    def effective_egress_ip(self) -> str:
        return self.vpn_exit_ip if self.vpn_active else self.public_ip

    def traceable_ips(self) -> list[str]:
        ips = [self.effective_egress_ip]
        if self.public_ip not in ips:
            ips.append(self.public_ip)
        return ips

    def wallet_label(self) -> str:
        if self.phase == "tutorial":
            return f"Tutorial budget: ${self.tutorial_credits} | Career funds: ${self.money} (locked)"
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
        if self.money >= amount:
            self.money -= amount
            success(f"{reason} (-${amount}, balance ${self.money})")
            return True
        error(f"Need ${amount}, have ${self.money}.")
        return False

    def earn(self, amount: int, reason: str) -> None:
        if self.phase == "tutorial":
            self.tutorial_credits += amount
            success(f"+${amount} tutorial credits ({reason})")
        else:
            self.money += amount
            success(f"+${amount} ({reason})")

    def penalize(self, amount: int, reason: str) -> None:
        if self.phase == "tutorial":
            loss = min(amount, self.tutorial_credits)
            self.tutorial_credits -= loss
            warn(f"[TRAINING] {reason} — lost ${loss} from tutorial budget (${self.tutorial_credits} left)")
            teach("Your career wallet was protected during training.")
        else:
            self.money = max(0, self.money - amount)
            warn(f"{reason} — lost ${amount}. Balance: ${self.money}")

    def crack_speed_bonus(self) -> float:
        return self.cpu_level * 0.05 + {0: 0, 1: 0.15, 2: 0.35}[self.cracker_tier]

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
            career_hosts = [
                Server("192.168.1.10", "corp-gateway", 2, ssh_password="gateway22"),
                Server("192.168.1.25", "research-node", 3, ssh_password="lab_secret"),
                Server(
                    "10.0.0.42", "corp-dc", 3, subnet="10.0.0.0/24", ssh_password="corp42!",
                    extra_files={"/home/admin/corporate_secrets.txt": "Acquisition: NovaDyne\n"},
                    privesc_available=True,
                ),
                Server(
                    "10.0.0.55", "vault-server", 5, subnet="10.0.0.0/24", ssh_password="qu4ntum_vault",
                    privesc_available=True,
                    root_only_files={"/root/payroll.csv": "ceo,2.1M\n"},
                ),
            ]
            career_hosts[-1].services = [
                NetworkService(22, "ssh", "OpenSSH_8.9p1"),
                NetworkService(443, "https", "nginx/1.24.0"),
            ]
            for s in career_hosts:
                self.servers[s.ip] = s

    def add_career_hosts(self) -> None:
        if "10.0.0.42" in self.servers:
            return
        career_hosts = [
            Server("192.168.1.10", "corp-gateway", 2, ssh_password="gateway22"),
            Server("192.168.1.25", "research-node", 3, ssh_password="lab_secret"),
            Server(
                "10.0.0.42", "corp-dc", 3, subnet="10.0.0.0/24", ssh_password="corp42!",
                extra_files={"/home/admin/corporate_secrets.txt": "Acquisition: NovaDyne\n"},
                privesc_available=True,
            ),
            Server(
                "10.0.0.55", "vault-server", 5, subnet="10.0.0.0/24", ssh_password="qu4ntum_vault",
                privesc_available=True,
                root_only_files={"/root/payroll.csv": "ceo,2.1M\n"},
            ),
        ]
        career_hosts[-1].services = [
            NetworkService(22, "ssh", "OpenSSH_8.9p1"),
            NetworkService(443, "https", "nginx/1.24.0"),
        ]
        for s in career_hosts:
            self.servers[s.ip] = s

    def get_server(self, ip: str) -> Server | None:
        return self.servers.get(ip)

    def hosts_in_cidr(self, cidr: str, player: Player) -> list[Server]:
        return [
            s for s in self.servers.values()
            if ip_in_subnet(s.ip, cidr) and player.has_route_to(s.ip)
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

        if p.ticks % 4 != 0:
            return
        if p.firewall_level >= 4:
            return
        gap = max(0, 3 - p.firewall_level)
        if random.random() < 0.18 * gap:
            self._maybe_attack(force=False)

    def _maybe_attack(self, force: bool) -> None:
        p = self.game.player
        rival = random.choice(RIVALS)
        power = random.randint(2, 4)
        if not force and p.firewall_level >= power:
            return

        divider("!!! RIVAL INTRUSION — LOCALHOST !!!")
        warn(f"'{rival}' targeting {p.public_ip} (firewall L{p.firewall_level} vs attack {power})")

        if p.firewall_level >= power:
            success(f"Firewall blocked {rival}.")
            if self.game.tutorial.in_tutorial():
                self.game.tutorial.defense_attacks_triggered += 1
            return

        loss = random.randint(40, 100) * max(1, power - p.firewall_level)
        p.penalize(loss, f"{rival} breached your defenses")
        if self.game.tutorial.in_tutorial():
            self.game.tutorial.defense_attacks_triggered += 1


# ---------------------------------------------------------------------------
# Game engine
# ---------------------------------------------------------------------------

class Game:
    BASE_TRACE_CHANCE = 0.35

    def __init__(self) -> None:
        self.player = Player()
        self.network = VirtualNetwork(career=False)
        self.missions = MissionBoard()
        self.tutorial = TutorialManager(self)
        self.threat = ThreatSystem(self)
        self.running = True

    def banner(self) -> None:
        divider("TERMINALHACKER — CYBERSECURITY TRAINING SIMULATOR")
        print(
            "You begin in the TUTORIAL phase with a $500 training budget.\n"
            "Losses during training come from tutorial credits — NOT career money.\n"
            "Type 'lesson' for objectives. Graduate to career mode after all lessons.\n"
        )
        self.tutorial.show_lesson()

    def prompt(self) -> str:
        p = self.player
        if p.is_local():
            user = p.username
        elif p.remote_is_root:
            user = "root"
        else:
            user = self.remote_server().ssh_user if self.remote_server() else p.username
        host = p.prompt_host
        path = p.cwd if p.has_remote_shell or p.is_local() else "~"
        sym = "#" if p.is_local() or p.has_remote_shell else ">"
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

    def post_command(self, cmd: str) -> None:
        self.tutorial.record_command(cmd)
        self.threat.on_tick()
        if self.player.phase == "career":
            self.missions.check_completion(self.player, self.network)
        self.tutorial.check_advance()

    # ----- commands -----

    def cmd_lesson(self, _a: list[str]) -> None:
        self.tutorial.show_lesson()

    def cmd_help(self, _a: list[str]) -> None:
        divider("COMMANDS")
        cmds = [
            "lesson", "help", "ifconfig", "route", "route add [net] via [gw]",
            "vpn [connect|disconnect|status]", "scan/nmap [CIDR]", "connect [IP] [port]",
            "disconnect", "probe", "crack", "sudo -l", "privesc",
            "ls", "cat", "rm", "download [path]", "pwd", "whoami", "uname",
            "shop", "buy [item]", "missions", "status", "exit",
        ]
        print("  " + "\n  ".join(cmds) + "\n")

    def cmd_ifconfig(self, _a: list[str]) -> None:
        divider("IFCONFIG")
        p = self.player
        print(f"  inet {p.lan_ip}  netmask 255.255.255.0  gateway {p.gateway}")
        print(f"  NAT public IP:  {p.public_ip}")
        if p.vpn_active:
            print(f"  VPN exit IP:    {p.vpn_exit_ip}  (active — victims see this)")
        teach("LAN addresses (192.168.x) are private. NAT translates to your public IP.")

    def cmd_route(self, args: list[str]) -> None:
        if len(args) >= 4 and args[0] == "add" and args[2] == "via":
            cidr, gw = args[1], args[3]
            if any(r.destination == cidr for r in self.player.routes):
                warn(f"Route to {cidr} already exists.")
                return
            self.player.routes.append(Route(cidr, gw))
            success(f"Route added: {cidr} via {gw}")
            teach("Packets to that subnet now flow through the gateway router.")
            return

        divider("ROUTING TABLE")
        for r in self.player.routes:
            print(f"  {r.destination:<18} via {r.gateway:<15} dev {r.iface}")
        teach("Without a route, remote subnets (e.g. 10.0.0.0/24) are unreachable.")

    def cmd_vpn(self, args: list[str]) -> None:
        if not args:
            error("Usage: vpn [connect|disconnect|status]")
            return
        action = args[0].lower()
        p = self.player

        if action == "status":
            print(f"  VPN: {'ON' if p.vpn_active else 'OFF'}  exit={p.vpn_exit_ip}")
            return

        if action == "connect":
            if p.phase == "career" and not p.vpn_licensed and "vpn_pro" not in p.owned_tools:
                error("VPN license required. buy vpn_pro in shop.")
                return
            p.vpn_active = True
            success(f"VPN tunnel up. Exit node: {p.vpn_exit_ip}")
            teach("Remote logs will now record the VPN IP instead of your public address.")
            if self.tutorial.in_tutorial() and p.tutorial_step == 9:
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
        if not targets:
            warn(f"No reachable hosts in {cidr}. Add a route? (route add 10.0.0.0/24 via 192.168.1.1)")
            return
        for s in targets:
            self.player.discovered_ips.add(s.ip)
            print(f"  {s.ip} ({s.hostname}) — open: " + ", ".join(str(svc.port) for svc in s.services))
        info("Use connect <IP> 22")

    def cmd_connect(self, args: list[str]) -> None:
        if not args or not self.player.is_local():
            error("Usage: connect [IP] [port]  (from localhost)")
            return
        ip = args[0]
        port = int(args[1]) if len(args) > 1 else 22
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
        time.sleep(0.2)
        self.player.connection = ip
        self.player.connected_port = port
        self.player.has_remote_shell = False
        self.player.remote_is_root = False
        self.player.cwd = f"/home/{server.ssh_user}"
        self.log_remote(server, f"TCP connection to {ip}:{port}", f"Connection from port {random.randint(40000, 60000)}")

        if ip == "192.168.1.50":
            self.player.tutorial_flags.add("connected_training")

        success(f"Connected to {server.hostname}. Run crack for shell.")

    def cmd_disconnect(self, _a: list[str]) -> None:
        if self.player.is_local():
            warn("Already localhost.")
            return
        server = self.remote_server()
        if server and server.player_left_traces(self.player):
            if random.random() < self.BASE_TRACE_CHANCE + (server.ids_alert_level * 0.08):
                self.player.penalize(random.randint(50, 120), "Forensic trace after sloppy disconnect")
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
        print(f"  {s.hostname} | FW L{s.security_level} | cracked={s.cracked}")
        if s.ip == "192.168.1.50":
            self.player.tutorial_flags.add("probed_training")

    def cmd_crack(self, _a: list[str]) -> None:
        s = self.remote_server()
        if not s or self.player.connected_port != 22:
            return
        if s.cracked:
            self.player.has_remote_shell = True
            return

        divider("SSH BRUTE-FORCE")
        words = ["password", "admin", "123456", s.ssh_password]
        if "hydra" in self.player.owned_tools:
            words = [s.ssh_password] + [w for w in words if w != s.ssh_password]
        attempts = max(2, int((s.security_level - self.player.cpu_level + 2) * 3 * self.player.crack_attempt_reduction()))

        for i in range(1, attempts + 1):
            guess = words[i % len(words)]
            time.sleep(max(0.03, 0.1 - self.player.crack_speed_bonus()))
            if guess != s.ssh_password:
                print(f"    try {guess} FAIL")
                s.write_auth(f"Failed password for {s.ssh_user} from {self.egress_ip()}")
                continue
            s.cracked = True
            self.player.has_remote_shell = True
            s.write_auth(f"Accepted password for {s.ssh_user} from {self.egress_ip()}")
            success(f"Shell access: {s.ssh_user}:{guess}")
            if self.player.phase == "career":
                self.player.earn(50 + s.security_level * 25, "crack bounty")
            return
        error("Failed — upgrade CPU or buy hydra/hashcat.")

    def cmd_sudo(self, args: list[str]) -> None:
        s = self.require_shell()
        if not s:
            return
        if args and args[0] == "-l":
            divider("SUDO -L")
            if s.privesc_available:
                print(f"  (ALL) NOPASSWD: /usr/bin/cat /root/*")
                teach("Misconfigured sudo is a common real-world privesc vector.")
            else:
                print("  User may not run sudo.")
            return
        error("Usage: sudo -l")

    def cmd_privesc(self, _a: list[str]) -> None:
        s = self.require_shell()
        if not s or not s.privesc_available:
            error("No privilege escalation path found.")
            return
        divider("PRIVILEGE ESCALATION")
        info("Exploiting NOPASSWD sudo misconfiguration...")
        time.sleep(0.3)
        self.player.remote_is_root = True
        self.player.remote_was_root = True
        self.player.cwd = "/root"
        success("You are now root. Prompt will show root@host#")
        teach("Root can read any file and persist malware — defend with least-privilege.")

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

    def cmd_ls(self, args: list[str]) -> None:
        files = self.player.files if self.player.is_local() else (self.require_shell() and self.remote_server().files)
        if not files:
            return
        d = (args[0] if args else self.player.cwd).rstrip("/") + "/"
        divider(f"LS {d}")
        for p in sorted(files):
            if p.startswith(d) and p != d:
                rel = p[len(d):]
                if "/" not in rel:
                    tag = " [root-only]" if files[p].requires_root else ""
                    print(f"  {p}{tag}")

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
        print(f.read())
        if path == "/var/log/auth.log" and not self.player.is_local():
            self.player.tutorial_flags.add("read_authlog")
            teach("That IP is forensic evidence tying you to this intrusion.")

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

    def cmd_pwd(self, _a: list[str]) -> None:
        print(self.player.cwd)

    def cmd_whoami(self, _a: list[str]) -> None:
        if self.player.is_local():
            print(self.player.username)
        elif self.player.remote_is_root:
            print("root")
        elif self.remote_server():
            print(self.remote_server().ssh_user)

    def cmd_uname(self, _a: list[str]) -> None:
        if self.player.is_local():
            print("Linux training-box 6.5.0 #1 x86_64")
        elif self.remote_server():
            print(self.remote_server().os_name)

    def cmd_shop(self, _a: list[str]) -> None:
        if not self.player.is_local():
            error("Shop on localhost only.")
            return
        Shop.list_items(self.player)

    def cmd_buy(self, args: list[str]) -> None:
        if not self.player.is_local() or not args:
            error("Usage: buy [item]")
            return
        Shop.buy(self.player, args[0].lower())

    def cmd_missions(self, _a: list[str]) -> None:
        if self.player.phase == "tutorial":
            warn("Missions unlock after tutorial graduation.")
            return
        divider("MISSIONS")
        for m in self.missions.missions:
            print(f"  {m.status_line()}")

    def cmd_status(self, _a: list[str]) -> None:
        p = self.player
        divider("STATUS")
        if p.phase == "career":
            print("  Phase:      career (training complete)")
        else:
            print(f"  Phase:      tutorial (lesson {p.tutorial_step + 1}/{len(TUTORIAL_CURRICULUM)})")
        print(f"  {p.wallet_label()}")
        print(f"  CPU/FW:     L{p.cpu_level} / L{p.firewall_level}")
        print(f"  VPN:        {'on' if p.vpn_active else 'off'} → {p.effective_egress_ip}")
        print(f"  Routes:     {len(p.routes)}")
        print(f"  Tools:      {', '.join(sorted(p.owned_tools)) or 'none'}")

    def cmd_exit(self, _a: list[str]) -> None:
        self.running = False
        print("Goodbye.")

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
            "lesson": self.cmd_lesson, "help": self.cmd_help, "ifconfig": self.cmd_ifconfig,
            "vpn": self.cmd_vpn, "scan": self.cmd_scan, "nmap": self.cmd_scan,
            "connect": self.cmd_connect, "disconnect": self.cmd_disconnect,
            "probe": self.cmd_probe, "crack": self.cmd_crack, "privesc": self.cmd_privesc,
            "download": self.cmd_download, "ls": self.cmd_ls, "cat": self.cmd_cat,
            "rm": self.cmd_rm, "pwd": self.cmd_pwd, "whoami": self.cmd_whoami,
            "uname": self.cmd_uname, "shop": self.cmd_shop, "buy": self.cmd_buy,
            "missions": self.cmd_missions, "status": self.cmd_status,
            "exit": self.cmd_exit, "quit": self.cmd_exit,
        }
        if cmd in handlers:
            handlers[cmd](args)
            self.post_command(cmd)
        else:
            error("Unknown command. Try lesson or help.")

    def run(self) -> None:
        self.banner()
        while self.running:
            try:
                self.dispatch(input(self.prompt()))
            except (EOFError, KeyboardInterrupt):
                self.cmd_exit([])
                break


def main() -> None:
    Game().run()


if __name__ == "__main__":
    main()
