#!/usr/bin/env python3
"""
TerminalHacker — a single-player, text-based hacking simulator.

Inspired by retro games like Slavehack. Teaches networking/OS concepts through
realistic mechanics plus an upgrade economy, contract missions, and rival NPC
hackers that probe your localhost if your defenses are weak.
"""

from __future__ import annotations

import random
import re
import time
from dataclasses import dataclass, field
from typing import Callable


# ---------------------------------------------------------------------------
# Terminal output helpers
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


def syslog_line(hostname: str, process: str, message: str, priority: int = 13) -> str:
    ts = time.strftime("%b %d %H:%M:%S")
    return f"<{priority}>{ts} {hostname} {process}: {message}"


# ---------------------------------------------------------------------------
# Virtual filesystem
# ---------------------------------------------------------------------------

@dataclass
class VirtualFile:
    path: str
    content: str = ""
    owner: str = "root"
    group: str = "root"
    mode: str = "rw-r--r--"

    @property
    def name(self) -> str:
        return self.path.rsplit("/", 1)[-1]

    def append(self, line: str) -> None:
        if self.content and not self.content.endswith("\n"):
            self.content += "\n"
        self.content += line

    def read(self) -> str:
        return self.content or ""


# ---------------------------------------------------------------------------
# Network service model
# ---------------------------------------------------------------------------

@dataclass
class NetworkService:
    port: int
    name: str
    banner: str
    requires_auth: bool = True


# ---------------------------------------------------------------------------
# Remote server
# ---------------------------------------------------------------------------

@dataclass
class Server:
    ip: str
    hostname: str
    security_level: int
    os_name: str = "Linux 5.15.0-generic x86_64"
    cracked: bool = False
    ssh_user: str = "admin"
    ssh_password: str = "changeme"
    ids_alert_level: int = 0
    services: list[NetworkService] = field(default_factory=list)
    files: dict[str, VirtualFile] = field(default_factory=dict)
    extra_files: dict[str, str] = field(default_factory=dict)

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
                "Rotate passwords monthly.\n",
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

    def service_on_port(self, port: int) -> NetworkService | None:
        return next((svc for svc in self.services if svc.port == port), None)

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


# ---------------------------------------------------------------------------
# Missions
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
    """NPC contract board — brokers message in with paid jobs."""

    def __init__(self) -> None:
        self.missions: list[Mission] = [
            Mission(
                mission_id="ghost-001",
                broker="ghost_broker",
                briefing=(
                    "Go to IP 10.0.0.42, download corporate_secrets.txt, "
                    "and wipe your logs."
                ),
                target_ip="10.0.0.42",
                target_file="/home/admin/corporate_secrets.txt",
                reward=750,
            ),
            Mission(
                mission_id="cipher-002",
                broker="cipher7",
                briefing="Crack vault-server (10.0.0.55) and exfil payroll.csv.",
                target_ip="10.0.0.55",
                target_file="/home/admin/payroll.csv",
                reward=1200,
            ),
        ]
        self._login_announced = False

    def announce_login(self) -> None:
        if self._login_announced:
            return
        divider("INCOMING MESSAGE — MISSION BOARD")
        print("  [ghost_broker] has logged in to the contract channel.")
        print('  "New runner needed. Type missions to view open contracts."\n')
        self._login_announced = True

    def active_missions(self) -> list[Mission]:
        return [m for m in self.missions if not m.completed]

    def check_completion(self, player: "Player", network: "VirtualNetwork") -> None:
        for mission in self.active_missions():
            local_name = mission.target_file.rsplit("/", 1)[-1]
            local_path = f"/home/hacker/downloads/{local_name}"
            file_ok = local_path in player.files

            server = network.get_server(mission.target_ip)
            logs_clean = True
            if mission.require_log_wipe and server:
                logs_clean = not server.logs_contain_ip(player.public_ip)

            if file_ok and logs_clean:
                mission.completed = True
                player.money += mission.reward
                divider("MISSION COMPLETE")
                success(f"{mission.broker} transferred ${mission.reward}.")
                print(f'  "{mission.briefing}" — DONE.\n')


# ---------------------------------------------------------------------------
# Shop
# ---------------------------------------------------------------------------

@dataclass
class ShopItem:
    key: str
    name: str
    description: str
    base_cost: int
    max_level: int = 1
    category: str = "upgrade"

    def cost_for_level(self, current_level: int) -> int:
        return self.base_cost * (current_level + 1)


SHOP_CATALOG: list[ShopItem] = [
    ShopItem("cpu", "CPU Upgrade", "Faster brute-force (fewer attempts, less delay).", 200, max_level=6),
    ShopItem("firewall", "Firewall Upgrade", "Blocks rival NPC hackers targeting localhost.", 175, max_level=5),
    ShopItem("hydra", "Hydra Lite", "Tier-1 cracking suite — smarter wordlist ordering.", 350, max_level=1),
    ShopItem("hashcat", "Hashcat Pro", "Tier-2 cracking suite — cuts failed attempts ~40%.", 800, max_level=1),
]


class Shop:
    @staticmethod
    def list_items(player: Player) -> None:
        divider("BLACK MARKET SHOP")
        print(f"  Balance: ${player.money}\n")
        for item in SHOP_CATALOG:
            if item.key in ("cpu", "firewall"):
                level = player.cpu_level if item.key == "cpu" else player.firewall_level
                if level >= item.max_level:
                    print(f"  {item.key:<10} {item.name:<16} MAXED (level {level})")
                else:
                    cost = item.cost_for_level(level)
                    print(f"  {item.key:<10} {item.name:<16} ${cost:<6} → level {level + 1}")
            else:
                owned = item.key in player.owned_tools
                status = "OWNED" if owned else f"${item.base_cost}"
                print(f"  {item.key:<10} {item.name:<16} {status}")
            print(f"             {item.description}")
        print("\n  Usage: buy [item]   (shop only works on localhost)\n")

    @staticmethod
    def buy(player: Player, item_key: str) -> bool:
        item = next((i for i in SHOP_CATALOG if i.key == item_key), None)
        if item is None:
            error(f"Unknown shop item '{item_key}'.")
            return False

        if item.key == "cpu":
            if player.cpu_level >= item.max_level:
                warn("CPU already maxed.")
                return False
            cost = item.cost_for_level(player.cpu_level)
            if player.money < cost:
                error(f"Need ${cost}, you have ${player.money}.")
                return False
            player.money -= cost
            player.cpu_level += 1
            success(f"CPU upgraded to level {player.cpu_level} (-${cost}).")
            return True

        if item.key == "firewall":
            if player.firewall_level >= item.max_level:
                warn("Firewall already maxed.")
                return False
            cost = item.cost_for_level(player.firewall_level)
            if player.money < cost:
                error(f"Need ${cost}, you have ${player.money}.")
                return False
            player.money -= cost
            player.firewall_level += 1
            success(f"Firewall upgraded to level {player.firewall_level} (-${cost}).")
            return True

        if item.key in player.owned_tools:
            warn(f"You already own {item.name}.")
            return False
        if item.key == "hashcat" and "hydra" not in player.owned_tools:
            error("Requires Hydra Lite first.")
            return False
        if player.money < item.base_cost:
            error(f"Need ${item.base_cost}, you have ${player.money}.")
            return False

        player.money -= item.base_cost
        player.owned_tools.add(item.key)
        player.cracker_tier = max(player.cracker_tier, 1 if item.key == "hydra" else 2)
        success(f"Purchased {item.name} (-${item.base_cost}). Cracker tier: {player.cracker_tier}.")
        return True


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------

@dataclass
class Player:
    username: str = "hacker"
    lan_ip: str = "192.168.1.100"
    public_ip: str = "73.42.118.9"
    gateway: str = "192.168.1.1"
    subnet: str = "192.168.1.0/24"
    cpu_level: int = 2
    firewall_level: int = 1
    cracker_tier: int = 0
    ram: int = 8
    hdd_space: int = 256
    money: int = 500
    connection: str = "localhost"
    cwd: str = "/home/hacker"
    connected_port: int | None = None
    has_remote_shell: bool = False
    discovered_ips: set[str] = field(default_factory=set)
    scan_results: dict[str, dict[int, str]] = field(default_factory=dict)
    owned_tools: set[str] = field(default_factory=set)
    files: dict[str, VirtualFile] = field(default_factory=dict)
    ticks: int = 0

    def __post_init__(self) -> None:
        if not self.files:
            self.files = {
                "/home/hacker/notes.txt": VirtualFile(
                    "/home/hacker/notes.txt",
                    "Ops checklist:\n"
                    "  1) missions — check broker contracts\n"
                    "  2) shop / buy cpu — upgrade for faster cracks\n"
                    "  3) scan 10.0.0.0/24 for mission targets\n"
                    "  4) download files, wipe logs, collect pay\n"
                    "  5) buy firewall — rivals attack weak localhost defenses\n",
                    owner=self.username,
                    mode="rw-------",
                ),
                "/home/hacker/wordlist.txt": VirtualFile(
                    "/home/hacker/wordlist.txt",
                    "password\nadmin\n123456\nletmein\n",
                    owner=self.username,
                ),
                "/var/log/syslog": VirtualFile(
                    "/var/log/syslog",
                    syslog_line("localhost", "systemd", "localhost ready.") + "\n",
                    mode="rw-r-----",
                ),
                "/var/log/auth.log": VirtualFile(
                    "/var/log/auth.log",
                    syslog_line("localhost", "sshd", "Server listening on 0.0.0.0 port 22.") + "\n",
                    mode="rw-r-----",
                ),
            }

    @property
    def prompt_host(self) -> str:
        return "localhost" if self.is_local() else self.connection

    def is_local(self) -> bool:
        return self.connection == "localhost"

    def reset_session(self) -> None:
        self.connected_port = None
        self.has_remote_shell = False

    def apply_trace_penalty(self, ids_level: int) -> None:
        severity = 1 + ids_level // 3
        if random.choice((True, False)):
            loss = random.randint(40, 90) * severity
            self.money = max(0, self.money - loss)
            warn(f"ISP TRACE — fined ${loss}. Balance: ${self.money}")
        else:
            damage = min(2, severity)
            self.cpu_level = max(1, self.cpu_level - damage)
            warn(f"FORENSIC SEIZURE — CPU level -{damage} (now {self.cpu_level}).")

    def crack_speed_bonus(self) -> float:
        """Combined CPU + software speed multiplier for brute-force."""
        tool_bonus = {0: 0.0, 1: 0.15, 2: 0.35}[self.cracker_tier]
        return self.cpu_level * 0.04 + tool_bonus

    def crack_attempt_reduction(self) -> float:
        return {0: 1.0, 1: 0.75, 2: 0.55}[self.cracker_tier]


# ---------------------------------------------------------------------------
# Virtual network
# ---------------------------------------------------------------------------

class VirtualNetwork:
    def __init__(self) -> None:
        self.servers: dict[str, Server] = {}
        self._seed_network()

    def _seed_network(self) -> None:
        seed = [
            Server("192.168.1.10", "corp-gateway", 2, ssh_password="gateway22"),
            Server("192.168.1.25", "research-node", 3, ssh_password="lab_secret"),
            Server(
                "10.0.0.42",
                "corp-dc",
                3,
                ssh_password="corp42!",
                extra_files={
                    "/home/admin/corporate_secrets.txt": (
                        "Q4 acquisition target: NovaDyne Inc.\n"
                        "Board vote scheduled: 2026-07-15\n"
                    ),
                },
            ),
            Server(
                "10.0.0.55",
                "vault-server",
                5,
                ssh_password="qu4ntum_vault",
                extra_files={
                    "/home/admin/payroll.csv": "employee,salary\nalice,92000\nbob,105000\n",
                },
            ),
        ]
        seed[-1].services = [
            NetworkService(22, "ssh", "OpenSSH_8.9p1"),
            NetworkService(443, "https", "nginx/1.24.0"),
        ]
        for server in seed:
            self.servers[server.ip] = server

    def get_server(self, ip: str) -> Server | None:
        return self.servers.get(ip)

    def list_targets(self) -> list[Server]:
        return list(self.servers.values())

    def hosts_in_cidr(self, cidr: str) -> list[Server]:
        prefix = cidr.rsplit("/", 1)[0]
        octets = prefix.split(".")
        if len(octets) < 3:
            return self.list_targets()
        network_prefix = ".".join(octets[:3])
        return [s for s in self.list_targets() if s.ip.startswith(network_prefix + ".")]


# ---------------------------------------------------------------------------
# NPC threat system (game-tick based)
# ---------------------------------------------------------------------------

RIVAL_HACKERS = ["zero_cool", "acid_k", "phantom_pkt", "nyx_root", "stack_smash"]


class ThreatSystem:
    """
    Simulates rival hackers probing the player's localhost.

    Uses a per-command game tick (safe with blocking input()) rather than a
    background thread, which would fight with input() on the terminal.
    """

    TICKS_BETWEEN_ROLLS = 3
    BASE_ATTACK_CHANCE = 0.22

    def __init__(self, game: "Game") -> None:
        self.game = game

    def on_tick(self) -> None:
        player = self.game.player
        player.ticks += 1

        if player.ticks % self.TICKS_BETWEEN_ROLLS != 0:
            return
        if not player.is_local():
            return  # rivals strike your home machine when you're back

        defense_gap = max(0, 3 - player.firewall_level)
        if defense_gap <= 0:
            return

        chance = self.BASE_ATTACK_CHANCE * defense_gap
        if random.random() > chance:
            return

        self._launch_attack()

    def _launch_attack(self) -> None:
        player = self.game.player
        rival = random.choice(RIVAL_HACKERS)
        divider("!!! INTRUSION ALERT — LOCALHOST !!!")
        warn(f"Rival hacker '{rival}' is probing your public IP {player.public_ip}")

        attack_power = random.randint(2, 4)
        if player.firewall_level >= attack_power:
            success(f"Firewall L{player.firewall_level} blocked {rival}'s exploit attempt.")
            return

        player.files["/var/log/auth.log"].append(
            syslog_line("localhost", "sshd", f"Failed password for {player.username} from 203.0.113.{random.randint(10,250)} ssh2")
        )
        player.files["/var/log/syslog"].append(
            syslog_line("localhost", "kernel", f"INTRUSION ATTEMPT from {rival} ({attack_power} vs FW {player.firewall_level})")
        )

        penalty = random.choice(("money", "cpu"))
        if penalty == "money":
            loss = random.randint(30, 80) * (attack_power - player.firewall_level + 1)
            player.money = max(0, player.money - loss)
            warn(f"{rival} stole wallet credentials. Lost ${loss}. Balance: ${player.money}")
        else:
            player.cpu_level = max(1, player.cpu_level - 1)
            warn(f"{rival} deployed a resource hog. CPU level -1 (now {player.cpu_level}).")

        warn("Upgrade firewall in shop or wipe /var/log/* on localhost.")


# ---------------------------------------------------------------------------
# Game engine
# ---------------------------------------------------------------------------

class Game:
    BASE_TRACE_CHANCE = 0.35

    def __init__(self) -> None:
        self.player = Player()
        self.network = VirtualNetwork()
        self.missions = MissionBoard()
        self.threat = ThreatSystem(self)
        self.running = True

    def banner(self) -> None:
        divider("TERMINALHACKER")
        print(
            "Realistic terminal hacking simulator with economy and rivals.\n"
            "Check missions for paid contracts. Visit shop on localhost to upgrade.\n"
            "Rival hackers attack weak firewalls — balance offense and defense.\n"
        )
        self.missions.announce_login()

    def prompt(self) -> str:
        host = self.player.prompt_host
        path = self.player.cwd if self.player.has_remote_shell or self.player.is_local() else "~"
        shell = "#" if self.player.has_remote_shell or self.player.is_local() else ">"
        return f"{self.player.username}@{host}:{path}{shell} "

    def remote_server(self) -> Server | None:
        if self.player.is_local():
            return None
        return self.network.get_server(self.player.connection)

    def require_remote_shell(self) -> Server | None:
        server = self.remote_server()
        if server is None:
            error("Not connected to a remote host.")
            return None
        if not self.player.has_remote_shell:
            error("Shell access denied. Crack SSH credentials first (command: crack).")
            return None
        return server

    def require_localhost(self) -> bool:
        if not self.player.is_local():
            error("This command only works on localhost. Type disconnect first.")
            return False
        return True

    def trace_chance(self, server: Server) -> float:
        return min(0.95, self.BASE_TRACE_CHANCE + server.ids_alert_level * 0.08)

    def resolve_path(self, path: str, files: dict[str, VirtualFile]) -> str | None:
        if path.startswith("/"):
            return path if path in files else None
        joined = re.sub(r"/+", "/", f"{self.player.cwd.rstrip('/')}/{path}")
        return joined if joined in files else None

    def tcp_handshake(self, target: str, port: int) -> None:
        info(f"Sending SYN to {target}:{port} ...")
        time.sleep(0.12)
        info(f"Received SYN-ACK from {target}:{port}")
        time.sleep(0.08)
        info("Sending ACK — TCP session established.")

    def log_remote(self, server: Server, syslog_msg: str, auth_msg: str | None = None) -> None:
        server.write_syslog("kernel", syslog_msg)
        if auth_msg:
            server.write_auth(auth_msg)

    def post_command(self) -> None:
        self.threat.on_tick()
        self.missions.check_completion(self.player, self.network)

  # ----- commands --------------------------------------------------------

    def cmd_help(self, _args: list[str]) -> None:
        divider("AVAILABLE COMMANDS")
        rows = [
            ("help", "Show commands."),
            ("missions", "View NPC contract board."),
            ("shop", "Black market upgrades (localhost only)."),
            ("buy [item]", "Purchase cpu, firewall, hydra, or hashcat."),
            ("ifconfig", "Show NIC, LAN IP, gateway, public NAT IP."),
            ("scan / nmap [CIDR]", "Host discovery + port scan."),
            ("connect [IP] [port]", "Open TCP/SSH session."),
            ("disconnect", "Return to localhost."),
            ("probe", "Fingerprint connected host."),
            ("crack", "SSH brute-force (uses CPU + cracking tools)."),
            ("download [path]", "Exfil file from remote to ~/downloads/."),
            ("ls / cat / rm", "Filesystem operations."),
            ("pwd / whoami / uname", "Unix introspection."),
            ("status", "Hardware, money, tools, defenses."),
            ("exit", "Quit."),
        ]
        for name, desc in rows:
            print(f"  {name:<24} {desc}")
        print()

    def cmd_missions(self, _args: list[str]) -> None:
        divider("MISSION BOARD — SECURE CHANNEL")
        for mission in self.missions.missions:
            print(f"  {mission.status_line()}")
        if not self.missions.active_missions():
            success("All contracts fulfilled. Brokers will message new jobs soon.")
        print()

    def cmd_shop(self, _args: list[str]) -> None:
        if not self.require_localhost():
            return
        Shop.list_items(self.player)

    def cmd_buy(self, args: list[str]) -> None:
        if not self.require_localhost():
            return
        if not args:
            error("Usage: buy [item]   items: cpu, firewall, hydra, hashcat")
            return
        Shop.buy(self.player, args[0].lower())

    def cmd_ifconfig(self, _args: list[str]) -> None:
        divider("IFCONFIG — eth0")
        p = self.player
        print("  eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500")
        print(f"        inet {p.lan_ip}  netmask 255.255.255.0  broadcast 192.168.1.255")
        print(f"        gateway {p.gateway}")
        print(f"  NAT/public IP (seen by victims): {p.public_ip}")
        print(f"  Firewall level: {p.firewall_level}")
        print()

    def cmd_scan(self, args: list[str]) -> None:
        divider("NMAP HOST DISCOVERY")
        cidr = args[0] if args else self.player.subnet
        info(f"Starting Nmap 7.94 scan of {cidr}")
        time.sleep(0.25)

        targets = self.network.hosts_in_cidr(cidr)
        if not targets:
            warn(f"No hosts found in {cidr}.")
            return

        for server in targets:
            self.player.discovered_ips.add(server.ip)
            latency = random.randint(1, 18)
            print(f"Nmap scan report for {server.hostname} ({server.ip})")
            print(f"Host is up ({latency}ms latency).")
            for svc in server.services:
                print(f"  {svc.port}/tcp  open  {svc.name}  {svc.banner}")
            print()
        info("Scan complete. Use: connect <IP> 22")

    def cmd_connect(self, args: list[str]) -> None:
        if not args:
            error("Usage: connect [IP] [port]")
            return
        if not self.player.is_local():
            error("Disconnect first.")
            return

        target_ip = args[0]
        port = int(args[1]) if len(args) > 1 else 22
        if target_ip not in self.player.discovered_ips:
            error("Unknown host. Run scan/nmap first.")
            return

        server = self.network.get_server(target_ip)
        if server is None:
            error(f"No route to host {target_ip}")
            return

        svc = server.service_on_port(port)
        if svc is None:
            error(f"Connection refused — nothing listening on {target_ip}:{port}")
            return

        divider(f"CONNECT {target_ip}:{port}")
        self.tcp_handshake(target_ip, port)
        print(f"\n{svc.banner}")

        self.player.connection = target_ip
        self.player.connected_port = port
        self.player.has_remote_shell = False
        self.player.cwd = f"/home/{server.ssh_user}"

        self.log_remote(
            server,
            f"Connection from {self.player.public_ip} to {target_ip}:{port}",
            f"Connection from {self.player.public_ip} port {random.randint(40000, 60000)}",
        )
        server.raise_ids_alert(1)
        success(f"Transport connected to {server.hostname} ({target_ip}:{port}).")

    def cmd_disconnect(self, _args: list[str]) -> None:
        if self.player.is_local():
            warn("Already on localhost.")
            return

        server = self.remote_server()
        divider("DISCONNECT")
        info("Sending FIN — closing TCP session...")

        if server and server.logs_contain_ip(self.player.public_ip):
            chance = self.trace_chance(server)
            if random.random() < chance:
                warn(f"Forensic review triggered (trace chance {chance:.0%}).")
                self.player.apply_trace_penalty(server.ids_alert_level)
            else:
                info("Trace attempted but evidence was inconclusive.")

        self.player.connection = "localhost"
        self.player.cwd = "/home/hacker"
        self.player.reset_session()
        success("Session closed. Back on localhost.")
        self.missions.check_completion(self.player, self.network)

    def cmd_probe(self, _args: list[str]) -> None:
        server = self.remote_server()
        if server is None:
            return

        divider("SERVICE PROBE")
        port = self.player.connected_port or 22
        svc = server.service_on_port(port)
        info(f"Fingerprinting {server.ip}:{port} ...")
        time.sleep(0.3)

        self.log_remote(
            server,
            f"Port scan/fingerprint from {self.player.public_ip}",
            f"Did not receive identification string from {self.player.public_ip}",
        )
        server.raise_ids_alert(2)

        print(f"  Hostname:       {server.hostname}")
        print(f"  Firewall/IDS:   level {server.security_level} (alert {server.ids_alert_level}/10)")
        print(f"  SSH auth:       {'cracked' if server.cracked else 'required'}")
        print(f"  Service:        {svc.name if svc else 'unknown'} / {svc.banner if svc else 'n/a'}")

    def cmd_crack(self, _args: list[str]) -> None:
        server = self.remote_server()
        if server is None:
            return
        if self.player.connected_port != 22:
            error("Brute-force only supported on SSH port 22.")
            return
        if server.cracked:
            self.player.has_remote_shell = True
            warn("Host already cracked — shell granted.")
            return

        divider("SSH BRUTE-FORCE")
        wordlist = ["password", "admin", "123456", "letmein", "root", server.ssh_password]
        if "hydra" in self.player.owned_tools:
            wordlist = [server.ssh_password] + [w for w in wordlist if w != server.ssh_password]
        random.shuffle(wordlist[1:])

        difficulty = max(1, server.security_level - self.player.cpu_level + 1)
        attempts = max(2, int(difficulty * 4 * self.player.crack_attempt_reduction()))
        tool_name = {0: "builtin", 1: "Hydra Lite", 2: "Hashcat Pro"}[self.player.cracker_tier]
        info(f"Tool: {tool_name} | CPU L{self.player.cpu_level} vs FW {server.security_level} | {attempts} tries")

        speed = self.player.crack_speed_bonus()
        for i in range(1, attempts + 1):
            guess = wordlist[i % len(wordlist)]
            delay = max(0.03, 0.14 + server.security_level * 0.07 - speed)
            time.sleep(delay)

            if guess != server.ssh_password:
                print(f"    [{i:02d}/{attempts}] {guess} -> FAIL")
                server.write_auth(
                    f"Failed password for {server.ssh_user} from {self.player.public_ip} port "
                    f"{random.randint(40000, 60000)} ssh2"
                )
                server.raise_ids_alert(1)
                continue

            server.cracked = True
            self.player.has_remote_shell = True
            server.write_auth(
                f"Accepted password for {server.ssh_user} from {self.player.public_ip} port "
                f"{random.randint(40000, 60000)} ssh2"
            )
            success(f"Valid credentials: {server.ssh_user}:{guess}")
            self.player.money += 50 + server.security_level * 25
            success(f"Bounty wired: +${50 + server.security_level * 25} (cracking payout)")
            return

        error("Wordlist exhausted. Visit shop — buy cpu or hydra/hashcat.")

    def cmd_download(self, args: list[str]) -> None:
        server = self.require_remote_shell()
        if server is None:
            return
        if not args:
            error("Usage: download [remote_path]")
            return

        path = self.resolve_path(args[0], server.files)
        if path is None:
            error(f"Remote file not found: {args[0]}")
            return

        filename = path.rsplit("/", 1)[-1]
        local_path = f"/home/hacker/downloads/{filename}"
        divider("EXFILTRATION")
        info(f"SFTP pull {path} -> {local_path}")
        time.sleep(0.4)
        self.player.files[local_path] = VirtualFile(
            local_path,
            server.files[path].read(),
            owner=self.player.username,
        )
        success(f"Downloaded {filename} to localhost.")
        self.missions.check_completion(self.player, self.network)

    def cmd_ls(self, args: list[str]) -> None:
        if self.player.is_local():
            files = self.player.files
        else:
            server = self.require_remote_shell()
            if server is None:
                return
            files = server.files

        target_dir = args[0] if args else self.player.cwd
        if not target_dir.endswith("/"):
            target_dir += "/"

        divider(f"LS {target_dir}")
        matches = sorted(p for p in files if p.startswith(target_dir))
        if not matches:
            info("Directory empty or path not found.")
            return
        for path in matches:
            name = path[len(target_dir):].split("/")[0]
            if not name or "/" in path[len(target_dir):]:
                if name:
                    print(f"  {name}/")
                continue
            tag = " [LOG]" if path.startswith("/var/log/") else ""
            print(f"  {files[path].mode}  {path}{tag}")
        print()

    def cmd_cat(self, args: list[str]) -> None:
        if not args:
            error("Usage: cat [path]")
            return
        if self.player.is_local():
            files = self.player.files
        else:
            server = self.require_remote_shell()
            if server is None:
                return
            files = server.files

        path = self.resolve_path(args[0], files)
        if path is None:
            error(f"No such file: {args[0]}")
            return
        divider(f"CAT {path}")
        print(files[path].read() or "(empty file)")
        print()

    def cmd_pwd(self, _args: list[str]) -> None:
        print(self.player.cwd)

    def cmd_whoami(self, _args: list[str]) -> None:
        if self.player.is_local() or not self.player.has_remote_shell:
            print(self.player.username)
            return
        server = self.remote_server()
        print(server.ssh_user if server else self.player.username)

    def cmd_uname(self, _args: list[str]) -> None:
        if self.player.is_local():
            print("Linux localhost 6.5.0-hacker #1 SMP x86_64 GNU/Linux")
            return
        server = self.remote_server()
        print(server.os_name if server else "unknown")

    def cmd_rm(self, args: list[str]) -> None:
        if not args:
            error("Usage: rm [path]")
            return

        if self.player.is_local():
            files = self.player.files
        else:
            server = self.require_remote_shell()
            if server is None:
                return
            files = server.files

        path = self.resolve_path(args[0], files)
        if path is None:
            error(f"No such file: {args[0]}")
            return

        divider(f"RM {path}")
        del files[path]
        success(f"Removed {path}")
        self.missions.check_completion(self.player, self.network)

    def cmd_status(self, _args: list[str]) -> None:
        divider("STATUS")
        p = self.player
        tools = ", ".join(sorted(p.owned_tools)) or "none"
        print(f"  Money:           ${p.money}")
        print(f"  CPU level:       {p.cpu_level}")
        print(f"  Firewall level:  {p.firewall_level}")
        print(f"  Cracker tier:    {p.cracker_tier} ({tools})")
        print(f"  LAN / Public:    {p.lan_ip} / {p.public_ip}")
        print(f"  Connected:       {p.prompt_host}")
        print(f"  Game ticks:      {p.ticks}")
        print()

    def cmd_exit(self, _args: list[str]) -> None:
        divider("SHUTDOWN")
        print("Powering off. Stay stealthy.\n")
        self.running = False

    def dispatch(self, raw: str) -> None:
        parts = raw.strip().split()
        if not parts:
            return

        cmd, args = parts[0].lower(), parts[1:]
        handlers: dict[str, Callable[[list[str]], None]] = {
            "help": self.cmd_help,
            "missions": self.cmd_missions,
            "shop": self.cmd_shop,
            "buy": self.cmd_buy,
            "ifconfig": self.cmd_ifconfig,
            "scan": self.cmd_scan,
            "nmap": self.cmd_scan,
            "connect": self.cmd_connect,
            "disconnect": self.cmd_disconnect,
            "probe": self.cmd_probe,
            "crack": self.cmd_crack,
            "download": self.cmd_download,
            "ls": self.cmd_ls,
            "cat": self.cmd_cat,
            "pwd": self.cmd_pwd,
            "whoami": self.cmd_whoami,
            "uname": self.cmd_uname,
            "rm": self.cmd_rm,
            "status": self.cmd_status,
            "exit": self.cmd_exit,
            "quit": self.cmd_exit,
        }
        handler = handlers.get(cmd)
        if handler:
            handler(args)
            self.post_command()
        else:
            error(f"Unknown command '{cmd}'. Type 'help'.")

    def run(self) -> None:
        self.banner()
        while self.running:
            try:
                raw = input(self.prompt())
            except (EOFError, KeyboardInterrupt):
                print()
                self.cmd_exit([])
                break
            self.dispatch(raw)


def main() -> None:
    Game().run()


if __name__ == "__main__":
    main()
