#!/usr/bin/env python3
"""
TerminalHacker — a single-player, text-based hacking simulator.

Inspired by retro games like Slavehack, this CLI game teaches networking and
OS concepts through realistic mechanics: CIDR scanning, TCP handshakes, SSH
authentication, NAT/public IP exposure, syslog/auth.log forensics, and IDS
trace risk when logs are not wiped before disconnect.
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
    """
    RFC 5424-inspired syslog line.

    Priority 13 = user-level informational messages, matching real Linux defaults.
    """
    ts = time.strftime("%b %d %H:%M:%S")
    return f"<{priority}>{ts} {hostname} {process}: {message}"


# ---------------------------------------------------------------------------
# Virtual filesystem
# ---------------------------------------------------------------------------

@dataclass
class VirtualFile:
    """Unix file with path, permissions, owner, and mutable content."""

    path: str
    content: str = ""
    owner: str = "root"
    group: str = "root"
    mode: str = "rw-r--r--"  # simplified permission string

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
    """
    A host on the virtual LAN/WAN.

    security_level models firewall/IDS strength. open_services maps ports to
    daemons (SSH, HTTP, etc.) like output from nmap -sV.
    """

    ip: str
    hostname: str
    security_level: int
    os_name: str = "Linux 5.15.0-generic x86_64"
    subnet_mask: str = "255.255.255.0"
    cracked: bool = False
    ssh_user: str = "admin"
    ssh_password: str = "changeme"
    ids_alert_level: int = 0
    services: list[NetworkService] = field(default_factory=list)
    files: dict[str, VirtualFile] = field(default_factory=dict)

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
            "/etc/hostname": VirtualFile("/etc/hostname", f"{self.hostname}\n", mode="rw-r--r--"),
            "/etc/passwd": VirtualFile(
                "/etc/passwd",
                f"root:x:0:0:root:/root:/bin/bash\n"
                f"{self.ssh_user}:x:1000:1000:{self.ssh_user}:/home/{self.ssh_user}:/bin/bash\n",
                mode="rw-r--r--",
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

    def service_on_port(self, port: int) -> NetworkService | None:
        for svc in self.services:
            if svc.port == port:
                return svc
        return None

    def open_port_numbers(self) -> list[int]:
        return sorted(svc.port for svc in self.services)

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
# Player
# ---------------------------------------------------------------------------

@dataclass
class Player:
    """Local machine: hardware, wallet, network identity, and session state."""

    username: str = "hacker"
    lan_ip: str = "192.168.1.100"
    public_ip: str = "73.42.118.9"  # NAT address visible to remote hosts
    gateway: str = "192.168.1.1"
    subnet: str = "192.168.1.0/24"
    cpu_level: int = 2
    ram: int = 8
    hdd_space: int = 256
    money: int = 500
    connection: str = "localhost"
    cwd: str = "/home/hacker"
    connected_port: int | None = None
    has_remote_shell: bool = False
    discovered_ips: set[str] = field(default_factory=set)
    scan_results: dict[str, dict[int, str]] = field(default_factory=dict)
    files: dict[str, VirtualFile] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.files:
            self.files = {
                "/home/hacker/notes.txt": VirtualFile(
                    "/home/hacker/notes.txt",
                    "Ops checklist:\n"
                    "  1) nmap the subnet\n"
                    "  2) ssh to target port 22\n"
                    "  3) crack credentials\n"
                    "  4) cat /var/log/auth.log to verify traces\n"
                    "  5) rm BOTH /var/log/syslog and /var/log/auth.log\n",
                    owner=self.username,
                    mode="rw-------",
                ),
                "/home/hacker/wordlist.txt": VirtualFile(
                    "/home/hacker/wordlist.txt",
                    "password\nadmin\n123456\nletmein\n",
                    owner=self.username,
                ),
            }

    @property
    def prompt_host(self) -> str:
        if self.is_local():
            return "localhost"
        return self.connection

    def is_local(self) -> bool:
        return self.connection == "localhost"

    def current_files(self, network: VirtualNetwork) -> dict[str, VirtualFile]:
        if self.is_local():
            return self.files
        server = network.get_server(self.connection)
        return server.files if server else {}

    def reset_session(self) -> None:
        self.connected_port = None
        self.has_remote_shell = False

    def apply_trace_penalty(self, ids_level: int) -> None:
        severity = 1 + ids_level // 3
        penalty_type = random.choice(["money", "cpu"])
        if penalty_type == "money":
            loss = random.randint(40, 90) * severity
            self.money = max(0, self.money - loss)
            warn(
                f"ISP TRACE COMPLETE — law enforcement subpoenaed your account. "
                f"Fine: ${loss}. Balance: ${self.money}"
            )
        else:
            damage = min(2, severity)
            self.cpu_level = max(1, self.cpu_level - damage)
            warn(
                f"FORENSIC SEIZURE — local CPU equipment confiscated for analysis. "
                f"CPU level -{damage} (now {self.cpu_level})."
            )


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
            Server("10.0.0.55", "vault-server", 5, ssh_password="qu4ntum_vault"),
        ]
        seed[2].services = [
            NetworkService(22, "ssh", "OpenSSH_8.9p1"),
            NetworkService(443, "https", "nginx/1.24.0"),
        ]
        for server in seed:
            self.servers[server.ip] = server

    def get_server(self, ip: str) -> Server | None:
        return self.servers.get(ip)

    def list_targets(self) -> list[Server]:
        return list(self.servers.values())


# ---------------------------------------------------------------------------
# Game engine
# ---------------------------------------------------------------------------

class Game:
    BASE_TRACE_CHANCE = 0.35

    def __init__(self) -> None:
        self.player = Player()
        self.network = VirtualNetwork()
        self.running = True

    # ----- session helpers -------------------------------------------------

    def banner(self) -> None:
        divider("TERMINALHACKER")
        print(
            "Realistic terminal hacking simulator.\n"
            "Your LAN IP is private; remote hosts log your PUBLIC IP via NAT.\n"
            "Type 'help' to begin. Wipe ALL log files before disconnecting.\n"
        )

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

    def trace_chance(self, server: Server) -> float:
        return min(0.95, self.BASE_TRACE_CHANCE + server.ids_alert_level * 0.08)

    def resolve_path(self, path: str, files: dict[str, VirtualFile]) -> str | None:
        if path.startswith("/"):
            return path if path in files else None
        joined = re.sub(r"/+", "/", f"{self.player.cwd.rstrip('/')}/{path}")
        return joined if joined in files else None

    def tcp_handshake(self, target: str, port: int) -> bool:
        info(f"Sending SYN to {target}:{port} ...")
        time.sleep(0.15)
        info(f"Received SYN-ACK from {target}:{port}")
        time.sleep(0.1)
        info("Sending ACK — TCP session established.")
        return True

    def log_remote(self, server: Server, syslog_msg: str, auth_msg: str | None = None) -> None:
        server.write_syslog("kernel", syslog_msg)
        if auth_msg:
            server.write_auth(auth_msg)

    # ----- commands --------------------------------------------------------

    def cmd_help(self, _args: list[str]) -> None:
        divider("AVAILABLE COMMANDS")
        rows = [
            ("help", "Show commands."),
            ("ifconfig", "Show local NIC, LAN IP, gateway, and public (NAT) IP."),
            ("scan / nmap [CIDR]", "Host discovery + port scan (e.g. nmap 192.168.1.0/24)."),
            ("connect [IP] [port]", "Open TCP session (default port 22 / SSH)."),
            ("disconnect", "Close remote session and return home."),
            ("probe", "Service fingerprint on connected host (no shell required)."),
            ("crack", "SSH password brute-force (requires open SSH session)."),
            ("ls [path]", "List directory (shell required on remote)."),
            ("cat [path]", "Read file contents (shell required on remote)."),
            ("pwd / whoami / uname", "Standard Unix introspection."),
            ("rm [path]", "Delete file — wipe /var/log/* before disconnect."),
            ("status", "Hardware, money, and session info."),
            ("exit", "Quit."),
        ]
        for name, desc in rows:
            print(f"  {name:<24} {desc}")
        print()

    def cmd_ifconfig(self, _args: list[str]) -> None:
        divider("IFCONFIG — eth0")
        p = self.player
        print(f"  eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500")
        print(f"        inet {p.lan_ip}  netmask 255.255.255.0  broadcast 192.168.1.255")
        print(f"        gateway {p.gateway}")
        print(f"  NAT/public IP (seen by victims): {p.public_ip}")
        print()

    def cmd_scan(self, args: list[str]) -> None:
        divider("NMAP HOST DISCOVERY")
        cidr = args[0] if args else self.player.subnet
        info(f"Starting Nmap 7.94 scan of {cidr}")
        time.sleep(0.3)

        for server in self.network.list_targets():
            if not server.ip.startswith("192.168.1.") and cidr.startswith("192.168.1"):
                continue
            self.player.discovered_ips.add(server.ip)
            latency = random.randint(1, 18)
            print(f"Nmap scan report for {server.hostname} ({server.ip})")
            print(f"Host is up ({latency}ms latency).")
            ports: dict[int, str] = {}
            for svc in server.services:
                state = "open"
                line = f"{svc.port}/tcp  {state}  {svc.name}  {svc.banner}"
                print(f"  {line}")
                ports[svc.port] = f"{svc.name} ({svc.banner})"
            self.player.scan_results[server.ip] = ports
            print()
        info("Scan complete. Use: connect <IP> 22")

    def cmd_connect(self, args: list[str]) -> None:
        if not args:
            error("Usage: connect [IP] [port]")
            return
        if not self.player.is_local():
            error("Nested remote sessions are not supported. disconnect first.")
            return

        target_ip, port = args[0], int(args[1]) if len(args) > 1 else 22
        if target_ip not in self.player.discovered_ips:
            error("Unknown host. Run scan/nmap against the subnet first.")
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

        if svc.name == "ssh":
            info("SSH session open. Authentication required — use 'crack' or disconnect.")
        else:
            info(f"{svc.name.upper()} port reachable. probe for details.")

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
                warn(
                    f"Forensic review triggered (IDS level {server.ids_alert_level}, "
                    f"trace chance {chance:.0%})."
                )
                self.player.apply_trace_penalty(server.ids_alert_level)
            else:
                info("Trace attempted but evidence was inconclusive this time.")

        self.player.connection = "localhost"
        self.player.cwd = "/home/hacker"
        self.player.reset_session()
        success("Session closed. Back on localhost.")

    def cmd_probe(self, _args: list[str]) -> None:
        server = self.remote_server()
        if server is None:
            return

        divider("SERVICE PROBE")
        port = self.player.connected_port or 22
        svc = server.service_on_port(port)
        info(f"Fingerprinting {server.ip}:{port} ...")
        time.sleep(0.35)

        self.log_remote(
            server,
            f"Port scan/fingerprint from {self.player.public_ip}",
            f"Did not receive identification string from {self.player.public_ip}",
        )
        server.raise_ids_alert(2)

        print(f"  IP address:     {server.ip}")
        print(f"  Hostname:       {server.hostname}")
        print(f"  OS guess:       {server.os_name}")
        print(f"  Service:        {svc.name if svc else 'unknown'} on port {port}")
        print(f"  Banner:         {svc.banner if svc else 'n/a'}")
        print(f"  Firewall/IDS:   level {server.security_level} (alert {server.ids_alert_level}/10)")
        print(f"  SSH auth:       {'cracked' if server.cracked else 'required'}")
        warn("Probe activity written to /var/log/syslog and /var/log/auth.log")

    def cmd_crack(self, _args: list[str]) -> None:
        server = self.remote_server()
        if server is None:
            return
        if self.player.connected_port != 22:
            error("Brute-force is only implemented for SSH (port 22).")
            return
        if server.cracked:
            self.player.has_remote_shell = True
            warn("Host already cracked — shell access granted.")
            return

        divider("SSH BRUTE-FORCE")
        wordlist = [
            "password", "admin", "123456", "letmein", "root", server.ssh_password,
        ]
        random.shuffle(wordlist)

        difficulty = max(1, server.security_level - self.player.cpu_level + 1)
        attempts = difficulty * 4
        info(
            f"CPU level {self.player.cpu_level} vs target defense {server.security_level} "
            f"— {attempts} login attempts queued."
        )

        for i in range(1, attempts + 1):
            guess = wordlist[i % len(wordlist)]
            delay = 0.12 + server.security_level * 0.08 - self.player.cpu_level * 0.04
            time.sleep(max(0.04, delay))

            if guess != server.ssh_password:
                print(f"    [{i:02d}/{attempts}] ssh {server.ssh_user}@{server.ip} :: {guess} -> FAIL")
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
            server.write_syslog("systemd", f"New session opened for user {server.ssh_user}")
            success(f"Valid credentials: {server.ssh_user}:{guess}")
            success("Remote shell unlocked. Prompt switched to '#'.")
            return

        error("Wordlist exhausted. Upgrade CPU or try another target.")

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
            f = files[path]
            name = path[len(target_dir):].split("/")[0]
            if not name:
                continue
            if "/" in path[len(target_dir):]:
                print(f"  {name}/")
            else:
                tag = " [LOG]" if path.startswith("/var/log/") else ""
                print(f"  {f.mode}  {f.owner}:{f.group}  {path}{tag}")
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
        content = files[path].read()
        print(content if content else "(empty file)")
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
        if path.startswith("/var/log/") and not self.player.is_local():
            server = self.remote_server()
            if server and not server.logs_contain_ip(self.player.public_ip):
                info("No remaining log entries reference your public IP.")

    def cmd_status(self, _args: list[str]) -> None:
        divider("STATUS")
        p = self.player
        print(f"  Money:         ${p.money}")
        print(f"  CPU level:     {p.cpu_level}")
        print(f"  RAM:           {p.ram} GB")
        print(f"  HDD:           {p.hdd_space} GB")
        print(f"  LAN IP:        {p.lan_ip}")
        print(f"  Public IP:     {p.public_ip}")
        print(f"  Connected:     {p.prompt_host}")
        if p.connected_port:
            print(f"  Remote port:   {p.connected_port}")
        print(f"  Shell access:  {'yes' if p.has_remote_shell or p.is_local() else 'no'}")
        print()

    def cmd_exit(self, _args: list[str]) -> None:
        divider("SHUTDOWN")
        print("Powering off. Stay stealthy.\n")
        self.running = False

    # ----- dispatcher ------------------------------------------------------

    def dispatch(self, raw: str) -> None:
        parts = raw.strip().split()
        if not parts:
            return

        cmd, args = parts[0].lower(), parts[1:]
        handlers: dict[str, Callable[[list[str]], None]] = {
            "help": self.cmd_help,
            "ifconfig": self.cmd_ifconfig,
            "scan": self.cmd_scan,
            "nmap": self.cmd_scan,
            "connect": self.cmd_connect,
            "disconnect": self.cmd_disconnect,
            "probe": self.cmd_probe,
            "crack": self.cmd_crack,
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
