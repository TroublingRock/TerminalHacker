#!/usr/bin/env python3
"""
TerminalHacker — a single-player, text-based hacking simulator.

Inspired by retro games like Slavehack, this CLI game teaches basic networking
and OS concepts: IP addressing, remote connections, firewalls, log files, and
covering your tracks after an intrusion.
"""

from __future__ import annotations

import random
import sys
import time
from dataclasses import dataclass, field
from typing import Callable


# ---------------------------------------------------------------------------
# Terminal output helpers
# ---------------------------------------------------------------------------

def divider(title: str = "") -> None:
    """Print a scannable section divider for terminal output."""
    line = "=" * 58
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


# ---------------------------------------------------------------------------
# Virtual filesystem primitives
# ---------------------------------------------------------------------------

@dataclass
class VirtualFile:
    """A named file stored on a virtual host (local or remote)."""

    name: str
    content: str = ""

    def append(self, line: str) -> None:
        """Append a line to the file — mirrors how real syslog entries are written."""
        if self.content and not self.content.endswith("\n"):
            self.content += "\n"
        self.content += line

    def read(self) -> str:
        return self.content or "(empty file)"


# ---------------------------------------------------------------------------
# Remote server model
# ---------------------------------------------------------------------------

@dataclass
class Server:
    """
    A machine on the virtual network.

    security_level acts like a firewall rating: higher values slow brute-force
    attacks and represent stronger perimeter defenses.
    """

    ip: str
    hostname: str
    security_level: int
    cracked: bool = False
    files: dict[str, VirtualFile] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Every remote host keeps a syslog — a realistic artifact left behind
        # when someone connects, probes, or cracks the system.
        if "syslog" not in self.files:
            self.files["syslog"] = VirtualFile("syslog", "SYSTEM BOOT COMPLETE\n")

    @property
    def syslog(self) -> VirtualFile:
        return self.files["syslog"]

    def log_action(self, action: str, source_ip: str) -> None:
        """Record player activity in this server's syslog."""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self.syslog.append(f"[{timestamp}] {action} FROM {source_ip}")


# ---------------------------------------------------------------------------
# Player state
# ---------------------------------------------------------------------------

@dataclass
class Player:
    """
  Local player machine and credentials.

  Hardware stats influence crack speed. Money can be lost if a trace succeeds.
  connection holds the IP of the currently attached host ("localhost" = home).
    """

    local_ip: str = "127.0.0.1"
    cpu_level: int = 2
    ram: int = 4
    hdd_space: int = 120
    money: int = 500
    connection: str = "localhost"
    files: dict[str, VirtualFile] = field(default_factory=dict)
    discovered_ips: set[str] = field(default_factory=set)
    # Tracks whether this session wrote traceable entries to the remote syslog.
    left_footprint: bool = False

    def __post_init__(self) -> None:
        if not self.files:
            self.files = {
                "notes.txt": VirtualFile(
                    "notes.txt",
                    "Welcome to TerminalHacker.\n"
                    "Tip: scan the network, connect to targets, and always rm syslog.\n",
                ),
                "tools.sh": VirtualFile("tools.sh", "#!/bin/bash\necho 'script toolkit'\n"),
            }

    @property
    def prompt_host(self) -> str:
        """Return the host segment shown in the shell prompt."""
        return "localhost" if self.connection == "localhost" else self.connection

    def is_local(self) -> bool:
        return self.connection == "localhost"

    def current_files(self, network: VirtualNetwork) -> dict[str, VirtualFile]:
        """Files visible on whichever system the player is connected to."""
        if self.is_local():
            return self.files
        server = network.get_server(self.connection)
        return server.files if server else {}

    def apply_trace_penalty(self) -> None:
        """Penalty when law enforcement traces activity via uncleared logs."""
        penalty_type = random.choice(["money", "cpu"])
        if penalty_type == "money":
            loss = random.randint(50, 150)
            self.money = max(0, self.money - loss)
            warn(f"TRACE SUCCESSFUL — fined ${loss}. Balance: ${self.money}")
        else:
            damage = 1
            self.cpu_level = max(1, self.cpu_level - damage)
            warn(
                f"TRACE SUCCESSFUL — CPU damaged by {damage} level. "
                f"CPU now level {self.cpu_level}."
            )


# ---------------------------------------------------------------------------
# Virtual network
# ---------------------------------------------------------------------------

class VirtualNetwork:
    """Registry of all remote servers reachable from the player's subnet."""

    def __init__(self) -> None:
        self.servers: dict[str, Server] = {}
        self._seed_network()

    def _seed_network(self) -> None:
        """Populate the world with a few educational target machines."""
        seed_data = [
            ("192.168.1.10", "corp-gateway", 2, {"config.ini": "gateway_mode=strict\n"}),
            ("192.168.1.25", "research-node", 3, {"data.db": "encrypted_records\n"}),
            ("10.0.0.55", "vault-server", 4, {"vault.key": "REDACTED\n", "payroll.csv": "...\n"}),
        ]
        for ip, hostname, security, extra_files in seed_data:
            files = {name: VirtualFile(name, body) for name, body in extra_files.items()}
            self.servers[ip] = Server(ip=ip, hostname=hostname, security_level=security, files=files)

    def get_server(self, ip: str) -> Server | None:
        return self.servers.get(ip)

    def list_targets(self) -> list[Server]:
        return list(self.servers.values())


# ---------------------------------------------------------------------------
# Game engine / command dispatcher
# ---------------------------------------------------------------------------

class Game:
    """Main loop, command parsing, and educational mechanics."""

    TRACE_CHANCE = 0.65  # Probability of getting caught if logs remain.

    def __init__(self) -> None:
        self.player = Player()
        self.network = VirtualNetwork()
        self.running = True

    # ----- prompt & banner -------------------------------------------------

    def banner(self) -> None:
        divider("TERMINALHACKER")
        print(
            "A text-based hacking simulator. Learn networking by doing.\n"
            "Scan hosts, connect over IP, crack firewalls, and wipe your logs.\n"
            "Type 'help' to begin.\n"
        )

    def prompt(self) -> str:
        return f"user@{self.player.prompt_host}:~# "

    # ----- logging side-effects --------------------------------------------

    def _log_remote(self, server: Server, action: str) -> None:
        """Append a traceable syslog entry and flag the session."""
        server.log_action(action, self.player.local_ip)
        self.player.left_footprint = True

    # ----- commands --------------------------------------------------------

    def cmd_help(self, _args: list[str]) -> None:
        divider("AVAILABLE COMMANDS")
        commands = [
            ("help", "Show this help menu."),
            ("scan", "Probe the subnet and reveal target IP addresses."),
            ("connect [IP]", "Open a remote session to the given IP address."),
            ("disconnect", "Close the remote session and return to localhost."),
            ("probe", "Inspect firewall level and crack status (remote only)."),
            ("crack", "Brute-force the remote firewall (remote only)."),
            ("ls", "List files on the current system (local or remote)."),
            ("rm [filename]", "Delete a file — use this to wipe syslog traces."),
            ("status", "Show local hardware, money, and connection info."),
            ("exit", "Quit the game."),
        ]
        for name, desc in commands:
            print(f"  {name:<22} {desc}")
        print()

    def cmd_scan(self, _args: list[str]) -> None:
        divider("NETWORK SCAN")
        info("Broadcasting ARP probe on 192.168.1.0/24 and 10.0.0.0/24...")
        time.sleep(0.4)
        for server in self.network.list_targets():
            self.player.discovered_ips.add(server.ip)
            success(f"Host found: {server.ip} ({server.hostname})")
        info(f"{len(self.player.discovered_ips)} host(s) discovered. Use 'connect <IP>'.")

    def cmd_connect(self, args: list[str]) -> None:
        if not args:
            error("Usage: connect [IP]")
            return
        if not self.player.is_local():
            error("Disconnect from the current host before opening a new connection.")
            return

        target_ip = args[0]
        if target_ip not in self.player.discovered_ips:
            error("Unknown host. Run 'scan' to discover addresses on the network.")
            return

        server = self.network.get_server(target_ip)
        if server is None:
            error(f"No route to host {target_ip}.")
            return

        divider("CONNECT")
        info(f"Initiating TCP handshake to {target_ip}...")
        time.sleep(0.5)
        self.player.connection = target_ip
        self.player.left_footprint = False
        self._log_remote(server, "CONNECTION")
        success(f"Connected to {server.hostname} ({server.ip}).")
        info("Remote syslog updated — your local IP may now be recorded.")

    def cmd_disconnect(self, _args: list[str]) -> None:
        if self.player.is_local():
            warn("Already on localhost.")
            return

        remote_ip = self.player.connection
        server = self.network.get_server(remote_ip)

        divider("DISCONNECT")
        info(f"Closing session to {remote_ip}...")

        # Educational mechanic: uncleared logs can lead to a trace.
        if server and self.player.left_footprint and "syslog" in server.files:
            if random.random() < self.TRACE_CHANCE:
                warn("Remote syslog still contains your activity!")
                self.player.apply_trace_penalty()
            else:
                info("You got lucky — no trace this time. Wipe logs next time.")

        self.player.connection = "localhost"
        self.player.left_footprint = False
        success("Back on localhost.")

    def cmd_probe(self, _args: list[str]) -> None:
        if self.player.is_local():
            error("Probe requires an active remote connection.")
            return

        server = self.network.get_server(self.player.connection)
        if server is None:
            error("Connection lost — host unreachable.")
            return

        divider("PROBE")
        info(f"Fingerprinting {server.hostname} ({server.ip})...")
        time.sleep(0.4)
        self._log_remote(server, "PROBE")
        print(f"  Hostname:       {server.hostname}")
        print(f"  Firewall level: {server.security_level}")
        print(f"  Cracked:        {'yes' if server.cracked else 'no'}")
        info("Probe logged to remote syslog.")

    def cmd_crack(self, _args: list[str]) -> None:
        if self.player.is_local():
            error("Crack requires an active remote connection.")
            return

        server = self.network.get_server(self.player.connection)
        if server is None:
            error("Connection lost — host unreachable.")
            return
        if server.cracked:
            warn(f"{server.hostname} is already cracked.")
            return

        divider("BRUTE-FORCE ATTACK")
        # CPU level reduces delay; firewall level increases required work.
        difficulty = max(1, server.security_level - self.player.cpu_level + 1)
        attempts = difficulty * 3
        info(
            f"CPU level {self.player.cpu_level} vs firewall {server.security_level} "
            f"— running {attempts} attempts..."
        )

        charset = "abcdefghijklmnopqrstuvwxyz0123456789"
        for i in range(1, attempts + 1):
            guess = "".join(random.choice(charset) for _ in range(6))
            delay = 0.15 + (server.security_level * 0.1) - (self.player.cpu_level * 0.05)
            time.sleep(max(0.05, delay))
            print(f"    attempt {i:02d}/{attempts}: {guess} ... denied")

        server.cracked = True
        self._log_remote(server, "CRACK SUCCESS")
        success(f"Firewall breached on {server.hostname}.")
        info("Crack attempt recorded in syslog — cover your tracks!")

    def cmd_ls(self, _args: list[str]) -> None:
        files = self.player.current_files(self.network)
        location = self.player.prompt_host
        divider(f"FILE LISTING — {location}")
        if not files:
            info("No files found.")
            return
        for name in sorted(files):
            marker = " (log)" if name == "syslog" else ""
            print(f"  {name}{marker}")
        print()

    def cmd_rm(self, args: list[str]) -> None:
        if not args:
            error("Usage: rm [filename]")
            return

        filename = args[0]
        files = self.player.current_files(self.network)
        location = self.player.prompt_host

        divider("REMOVE FILE")
        if filename not in files:
            error(f"'{filename}' not found on {location}.")
            return

        del files[filename]
        success(f"Deleted '{filename}' on {location}.")
        if filename == "syslog" and not self.player.is_local():
            self.player.left_footprint = False
            info("Footprint cleared — safe to disconnect.")

    def cmd_status(self, _args: list[str]) -> None:
        divider("LOCAL STATUS")
        print(f"  Money:      ${self.player.money}")
        print(f"  CPU level:  {self.player.cpu_level}")
        print(f"  RAM:        {self.player.ram} GB")
        print(f"  HDD space:  {self.player.hdd_space} GB")
        print(f"  Local IP:   {self.player.local_ip}")
        print(f"  Connected:  {self.player.prompt_host}")
        print()

    def cmd_exit(self, _args: list[str]) -> None:
        divider("SHUTDOWN")
        print("Connection terminated. Stay stealthy.\n")
        self.running = False

    # ----- dispatcher ------------------------------------------------------

    def dispatch(self, raw: str) -> None:
        parts = raw.strip().split()
        if not parts:
            return

        command = parts[0].lower()
        args = parts[1:]

        handlers: dict[str, Callable[[list[str]], None]] = {
            "help": self.cmd_help,
            "scan": self.cmd_scan,
            "connect": self.cmd_connect,
            "disconnect": self.cmd_disconnect,
            "probe": self.cmd_probe,
            "crack": self.cmd_crack,
            "ls": self.cmd_ls,
            "rm": self.cmd_rm,
            "status": self.cmd_status,
            "exit": self.cmd_exit,
            "quit": self.cmd_exit,
        }

        handler = handlers.get(command)
        if handler:
            handler(args)
        else:
            error(f"Unknown command '{command}'. Type 'help' for options.")

    def run(self) -> None:
        self.banner()
        while self.running:
            try:
                raw = input(self.prompt())
            except (EOFError, KeyboardInterrupt):
                print("\n")
                self.cmd_exit([])
                break
            self.dispatch(raw)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    Game().run()


if __name__ == "__main__":
    main()
