#!/usr/bin/env python3
"""TerminalHacker — a text-based hacking simulator played in the terminal."""

from __future__ import annotations

import random
import sys
import time
from dataclasses import dataclass, field


@dataclass
class Host:
    name: str
    ip: str
    firewall: int
    password: str
    logs: int = 3


@dataclass
class PlayerState:
    credits: int = 0
    reputation: int = 0
    connected: str | None = None
    cracked: set[str] = field(default_factory=set)
    logs_wiped: set[str] = field(default_factory=set)


HOSTS = [
    Host("corp-gateway", "10.0.0.1", firewall=2, password="admin123"),
    Host("research-node", "192.168.4.22", firewall=3, password="shadow"),
    Host("vault-server", "172.16.8.99", firewall=4, password="qu4ntum"),
]

MISSIONS = [
    {
        "id": "probe-network",
        "title": "Probe the Network",
        "description": "Scan all hosts on the subnet.",
        "check": lambda state, scanned: len(scanned) >= len(HOSTS),
        "reward": (50, 10),
    },
    {
        "id": "crack-gateway",
        "title": "Crack the Gateway",
        "description": "Crack corp-gateway and connect to it.",
        "check": lambda state, scanned: "corp-gateway" in state.cracked,
        "reward": (75, 15),
    },
    {
        "id": "bypass-firewall",
        "title": "Bypass the Firewall",
        "description": "Bypass research-node's firewall.",
        "check": lambda state, scanned: state.connected == "research-node",
        "reward": (100, 20),
    },
    {
        "id": "wipe-logs",
        "title": "Cover Your Tracks",
        "description": "Wipe syslogs on any compromised host.",
        "check": lambda state, scanned: len(state.logs_wiped) >= 1,
        "reward": (125, 25),
    },
]


def slow_print(text: str, delay: float = 0.02) -> None:
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write("\n")


def banner() -> None:
    art = r"""
 _____                   _             _   _            _
|_   _|__ _ __ _ __ ___ | |_ _ __ __ _| |_| | __ _  ___| | __
  | |/ _ \ '__| '_ ` _ \| __| '__/ _` | __| |/ _` |/ __| |/ /
  | |  __/ |  | | | | | | |_| | | (_| | |_| | (_| | (__|   <
  |_|\___|_|  |_| |_| |_|\__|_|  \__,_|\__|_|\__,_|\___|_|\_\
    """
    print(art)
    print("Text-based hacking simulator. Type 'help' for commands.\n")


def find_host(target: str) -> Host | None:
    for host in HOSTS:
        if target in (host.name, host.ip):
            return host
    return None


def cmd_help() -> None:
    print(
        """
Commands:
  help                 Show this help menu
  scan                 Probe the local network for hosts
  hosts                List discovered hosts
  crack <host>         Attempt password crack on a host
  bypass <host>        Bypass firewall on a cracked host
  connect <host>       Connect to a host after bypass
  wipe <host>          Wipe syslogs to cover tracks
  status               Show player stats
  missions             Show mission objectives
  quit                 Exit TerminalHacker
"""
    )


def cmd_scan(scanned: set[str]) -> None:
    slow_print("[*] Initiating network probe...")
    for host in HOSTS:
        time.sleep(0.4)
        scanned.add(host.name)
        slow_print(f"[+] Found host {host.name} ({host.ip}) firewall={host.firewall}")
    slow_print("[*] Scan complete.")


def cmd_hosts(scanned: set[str]) -> None:
    if not scanned:
        print("No hosts discovered. Run 'scan' first.")
        return
    print("\nDiscovered hosts:")
    for host in HOSTS:
        if host.name in scanned:
            print(f"  {host.name:16} {host.ip:15} firewall={host.firewall}")
    print()


def cmd_crack(target: str, state: PlayerState, scanned: set[str]) -> None:
    host = find_host(target)
    if host is None:
        print(f"Unknown host: {target}")
        return
    if host.name not in scanned:
        print("Host not discovered. Run 'scan' first.")
        return
    if host.name in state.cracked:
        print(f"{host.name} is already cracked.")
        return

    guesses = ["password", "letmein", host.password, "123456", "shadow"]
    random.shuffle(guesses)
    slow_print(f"[*] Running dictionary attack on {host.name}...")
    for guess in guesses[:4]:
        time.sleep(0.5)
        slow_print(f"    trying '{guess}'... denied")
    time.sleep(0.6)
    slow_print(f"[+] Password found: {host.password}")
    state.cracked.add(host.name)
    state.reputation += 5
    print(f"Reputation +5 (now {state.reputation})")


def cmd_bypass(target: str, state: PlayerState) -> None:
    host = find_host(target)
    if host is None:
        print(f"Unknown host: {target}")
        return
    if host.name not in state.cracked:
        print("Crack the host before bypassing its firewall.")
        return

    slow_print(f"[*] Mapping firewall rules on {host.name}...")
    for level in range(1, host.firewall + 1):
        time.sleep(0.5)
        slow_print(f"    bypassing layer {level}/{host.firewall}...")
    slow_print(f"[+] Firewall bypassed on {host.name}")
    state.connected = host.name
    state.reputation += 10
    print(f"Reputation +10 (now {state.reputation})")


def cmd_connect(target: str, state: PlayerState) -> None:
    host = find_host(target)
    if host is None:
        print(f"Unknown host: {target}")
        return
    if host.name not in state.cracked:
        print("You must crack this host before connecting.")
        return
    state.connected = host.name
    slow_print(f"[+] Connected to {host.name} ({host.ip})")
    state.credits += 25
    print(f"Credits +25 (now {state.credits})")


def cmd_wipe(target: str, state: PlayerState) -> None:
    host = find_host(target)
    if host is None:
        print(f"Unknown host: {target}")
        return
    if host.name not in state.cracked:
        print("You can only wipe logs on compromised hosts.")
        return
    if host.name in state.logs_wiped:
        print(f"Logs on {host.name} are already wiped.")
        return

    slow_print(f"[*] Wiping syslog entries on {host.name}...")
    for remaining in range(host.logs, 0, -1):
        time.sleep(0.4)
        slow_print(f"    shredding entry {remaining}/{host.logs}")
    state.logs_wiped.add(host.name)
    slow_print("[+] Tracks covered.")
    state.credits += 40
    state.reputation += 15
    print(f"Credits +40 (now {state.credits}), Reputation +15 (now {state.reputation})")


def cmd_status(state: PlayerState) -> None:
    print("\n--- Player Status ---")
    print(f"Credits:     {state.credits}")
    print(f"Reputation:  {state.reputation}")
    print(f"Connected:   {state.connected or 'none'}")
    print(f"Compromised: {', '.join(sorted(state.cracked)) or 'none'}")
    print(f"Logs wiped:  {', '.join(sorted(state.logs_wiped)) or 'none'}")
    print()


def cmd_missions(state: PlayerState, scanned: set[str], completed: set[str]) -> None:
    print("\n--- Missions ---")
    for mission in MISSIONS:
        done = mission["id"] in completed
        marker = "[x]" if done else "[ ]"
        print(f"{marker} {mission['title']}")
        print(f"    {mission['description']}")
    print()


def check_missions(state: PlayerState, scanned: set[str], completed: set[str]) -> None:
    for mission in MISSIONS:
        if mission["id"] in completed:
            continue
        if mission["check"](state, scanned):
            credits, rep = mission["reward"]
            completed.add(mission["id"])
            print(f"\n*** Mission complete: {mission['title']} ***")
            state.credits += credits
            state.reputation += rep
            print(f"Reward: +{credits} credits, +{rep} reputation\n")


def game_loop() -> None:
    state = PlayerState()
    scanned: set[str] = set()
    completed: set[str] = set()

    banner()

    while True:
        try:
            raw = input("terminalhacker> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nConnection terminated.")
            break

        if not raw:
            continue

        parts = raw.split()
        command = parts[0].lower()
        args = parts[1:]

        if command == "help":
            cmd_help()
        elif command == "scan":
            cmd_scan(scanned)
        elif command == "hosts":
            cmd_hosts(scanned)
        elif command == "crack" and args:
            cmd_crack(args[0], state, scanned)
        elif command == "bypass" and args:
            cmd_bypass(args[0], state)
        elif command == "connect" and args:
            cmd_connect(args[0], state)
        elif command == "wipe" and args:
            cmd_wipe(args[0], state)
        elif command == "status":
            cmd_status(state)
        elif command == "missions":
            cmd_missions(state, scanned, completed)
        elif command in {"quit", "exit"}:
            print("Shutting down TerminalHacker. Stay stealthy.")
            break
        else:
            print(f"Unknown command: {command}. Type 'help' for available commands.")

        check_missions(state, scanned, completed)

        if len(completed) == len(MISSIONS):
            print("\n*** All missions complete. You are a terminal legend. ***")
            print(f"Final score — Credits: {state.credits}, Reputation: {state.reputation}")
            break


def main() -> None:
    game_loop()


if __name__ == "__main__":
    main()
