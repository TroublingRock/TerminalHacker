#!/usr/bin/env python3
"""Botnet payloads — miners, DDoS, passive income, rival countermeasures."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from main import Game, Server

PAYLOAD_MINER = "miner"
PAYLOAD_DDOS = "ddos"
PAYLOAD_LEAK = "leak"

PAYLOAD_SPECS: dict[str, dict[str, Any]] = {
    PAYLOAD_MINER: {
        "label": "Crypto miner",
        "heat": 2,
        "shop_key": "miner_payload",
        "desc": "Passive income while the node stays infected. Loud on subnet heat.",
    },
    PAYLOAD_DDOS: {
        "label": "DDoS flooder",
        "heat": 5,
        "shop_key": "ddos_payload",
        "duration_ticks": 14,
        "security_drop": 1,
        "desc": "Floods a target — easier cracks and slower rival race NPCs for a short window.",
    },
    PAYLOAD_LEAK: {
        "label": "Auto-leak worm",
        "heat": 4,
        "shop_key": "leak_payload",
        "desc": "Silently mirrors files — use chaos leak on that host to dump to the board.",
    },
}

# Income scales with host security but stays modest vs contracts.
MINER_BASE_INCOME = 4
DDOS_DURATION = 14
PURGE_NODE_THRESHOLD = 3
COUNTER_ATTACK_THRESHOLD = 4


class BotnetManager:
    @staticmethod
    def _career_only(game: Game) -> bool:
        from main import error

        if game.player.phase not in ("career", "endless"):
            error("Botnet payloads unlock in career mode.")
            return False
        return True

    @staticmethod
    def infection_count(game: Game) -> int:
        return len(game.meta.infections)

    @staticmethod
    def _resolve_target(game: Game, ip: str | None) -> Server | None:
        from main import error

        if ip:
            if ip not in game.player.discovered_ips:
                error("Unknown host — scan first.")
                return None
            server = game.network.get_server(ip)
            if not server:
                error("Invalid target.")
                return None
            if game.player.connection == ip and game.player.has_remote_shell:
                return server
            if ip in game.meta.backdoors:
                return server
            error("Need an active shell on target or a planted backdoor on that IP.")
            return None
        server = game.remote_server() if hasattr(game, "remote_server") else None
        if not server or not game.player.has_remote_shell:
            error("Connect and crack a host first, or: infect <type> <IP> via backdoor.")
            return None
        return server

    @staticmethod
    def _consume_payload(game: Game, shop_key: str) -> bool:
        from main import error

        count = game.meta.inventory.get(shop_key, 0)
        if count < 1:
            error(f"Need shop payload: buy {shop_key}  (then infect again)")
            return False
        game.meta.inventory[shop_key] = count - 1
        return True

    @staticmethod
    def _income_mult(game: Game) -> float:
        mult = 1.0
        if game.meta.specialization == "saboteur":
            mult *= 1.15
        from faction_consumables import FactionRepManager
        if FactionRepManager._rep(game, "rivals") >= 50:
            mult *= 1.08
        return mult

    @staticmethod
    def cmd_infect(game: Game, args: list[str]) -> None:
        from main import Console, divider, error, success, teach
        from depth_systems import RivalHeatManager

        if not BotnetManager._career_only(game):
            return
        if not args:
            divider("INFECT")
            Console.out("  Usage: infect miner [IP]  |  infect ddos <IP>  |  infect leak [IP]")
            Console.out("  Requires: active shell or backdoor on target.")
            Console.out("  Shop: buy miner_payload | buy ddos_payload")
            return

        kind = args[0].lower()
        if kind not in PAYLOAD_SPECS:
            error("Usage: infect miner [IP]  |  infect ddos <IP>")
            return

        spec = PAYLOAD_SPECS[kind]
        ip_arg = args[1] if len(args) > 1 else None
        if kind == PAYLOAD_DDOS and not ip_arg:
            error("Usage: infect ddos <IP>")
            return

        server = BotnetManager._resolve_target(game, ip_arg)
        if not server:
            return

        if kind == PAYLOAD_MINER and server.ip in game.meta.infections:
            from main import error as _err
            _err(f"{server.ip} already running {game.meta.infections[server.ip]}.")
            return
        if kind == PAYLOAD_LEAK and server.ip in game.meta.infections:
            from main import error as _err
            _err(f"{server.ip} already infected.")
            return

        if not BotnetManager._consume_payload(game, spec["shop_key"]):
            return

        divider(f"DEPLOY {spec['label'].upper()} — {server.hostname}")
        if kind == PAYLOAD_MINER:
            game.meta.infections[server.ip] = PAYLOAD_MINER
            income = BotnetManager._miner_tick_income(game, server)
            success(f"Miner installed on {server.ip} (~${income}/tick when banked).")
            teach("Run botnet to check nodes. botnet collect cashes out. Heat rises on that subnet.")
            game.meta.backdoors.add(server.ip)
        elif kind == PAYLOAD_LEAK:
            game.meta.infections[server.ip] = PAYLOAD_LEAK
            success(f"Leak worm on {server.ip} — connect and run: chaos leak")
            game.meta.backdoors.add(server.ip)
        else:
            duration = spec.get("duration_ticks", DDOS_DURATION)
            game.meta.ddos_targets[server.ip] = duration
            success(f"DDoS flood aimed at {server.ip} for ~{duration} commands.")
            teach("Target firewall softens while flooded. Rival race NPCs slow on that contract IP.")

        RivalHeatManager.spike(game, server.subnet, spec["heat"])
        from chaos_system import NotorietyManager
        NotorietyManager.add(game, 3 if kind == PAYLOAD_DDOS else 2, f"infect {kind} {server.ip}")
        game.player.tutorial_flags.add("daily_botnet_done")
        if BotnetManager.infection_count(game) >= 5:
            game.achievements.unlock("botnet_herder")

    @staticmethod
    def _miner_tick_income(game: Game, server: Server) -> int:
        base = MINER_BASE_INCOME + server.security_level
        return max(3, int(base * BotnetManager._income_mult(game)))

    @staticmethod
    def on_tick(game: Game) -> None:
        """Accrue miner revenue and decay DDoS timers (called from threat tick)."""
        if game.player.phase not in ("career", "endless") or not game.player.is_local():
            return

        for ip in list(game.meta.infections.keys()):
            server = game.network.get_server(ip)
            if not server:
                game.meta.infections.pop(ip, None)
                continue
            if game.meta.infections.get(ip) != PAYLOAD_MINER:
                continue
            game.meta.botnet_bank += BotnetManager._miner_tick_income(game, server)

        expired: list[str] = []
        for ip, ticks in list(game.meta.ddos_targets.items()):
            ticks -= 1
            if ticks <= 0:
                expired.append(ip)
            else:
                game.meta.ddos_targets[ip] = ticks
        for ip in expired:
            game.meta.ddos_targets.pop(ip, None)

    @staticmethod
    def on_post_command(game: Game) -> None:
        """Rival countermeasures — purge nodes, steal bank, force attacks."""
        if game.player.phase not in ("career", "endless"):
            return
        n = BotnetManager.infection_count(game)
        if n < PURGE_NODE_THRESHOLD:
            return

        from depth_systems import RivalHeatManager

        heat_bonus = sum(game.meta.subnet_heat.values())
        purge_chance = 0.04 + n * 0.015 + heat_bonus * 0.008
        if game.meta.specialization == "saboteur":
            purge_chance *= 1.12

        if random.random() < purge_chance:
            ip = random.choice(list(game.meta.infections.keys()))
            kind = game.meta.infections.pop(ip, PAYLOAD_MINER)
            game.meta.botnet_purges += 1
            server = game.network.get_server(ip)
            host = server.hostname if server else ip
            from main import warn

            warn(f"RIVAL COUNTER-OP: {host} ({ip}) cleaned your {kind} payload.")
            RivalHeatManager.spike(game, server.subnet if server else "192.168.1.0/24", 2)
            rival = __import__("retention").RetentionManager.pick_rival_attacker(game)
            game.mail.send(
                f"{rival}@rival.net",
                "Nice botnet — I scrubbed a node",
                f"Found your {kind} on {host}. I purged it. Keep counting your miners.\n\n— {rival}",
            )

        if n >= COUNTER_ATTACK_THRESHOLD and game.meta.botnet_bank > 80 and random.random() < 0.06:
            stolen = min(game.meta.botnet_bank, random.randint(40, 120))
            game.meta.botnet_bank -= stolen
            from main import warn

            warn(f"RIVAL SIPHON: ${stolen} drained from botnet wallet before you collected.")
            game.threat._maybe_attack(force=False)

    @staticmethod
    def threat_bonus(game: Game) -> float:
        n = BotnetManager.infection_count(game)
        if n < COUNTER_ATTACK_THRESHOLD:
            return 0.0
        return min(0.08, n * 0.012)

    @staticmethod
    def effective_security(game: Game, server: Server) -> int:
        sec = server.security_level
        if server.ip in game.meta.ddos_targets:
            drop = PAYLOAD_SPECS[PAYLOAD_DDOS].get("security_drop", 1)
            sec = max(1, sec - drop)
        return sec

    @staticmethod
    def rival_race_slow(game: Game, mission_ip: str) -> int:
        if mission_ip in game.meta.ddos_targets:
            return 2
        return 0

    @staticmethod
    def cmd_botnet(game: Game, args: list[str]) -> None:
        from main import Console, divider, error, success, teach

        if not BotnetManager._career_only(game):
            return
        action = (args[0].lower() if args else "status")

        if action == "collect":
            if game.meta.botnet_bank <= 0:
                error("Botnet bank is empty — miners accrue while you play.")
                return
            amount = game.meta.botnet_bank
            game.meta.botnet_bank = 0
            game.player.earn(amount, "botnet collect")
            success(f"Collected ${amount} from infected nodes.")
            return

        divider("BOTNET STATUS")
        bank = game.meta.botnet_bank
        Console.out(f"  Uncollected revenue: ${bank}  (botnet collect)")
        Console.out(f"  Active miners:       {sum(1 for v in game.meta.infections.values() if v == PAYLOAD_MINER)}")
        Console.out(f"  DDoS floods:         {len(game.meta.ddos_targets)}")
        Console.out(f"  Rival purges:        {game.meta.botnet_purges}")
        if not game.meta.infections and not game.meta.ddos_targets:
            Console.out("\n  No payloads deployed.")
            teach("Crack a host, buy miner_payload, then: infect miner")
            return
        Console.out("\n  Nodes:")
        for ip, kind in sorted(game.meta.infections.items()):
            server = game.network.get_server(ip)
            name = server.hostname if server else "?"
            sec = server.security_level if server else 0
            tick = BotnetManager._miner_tick_income(game, server) if server and kind == PAYLOAD_MINER else 0
            Console.out(f"    {ip:<16} {name:<18} {kind:<6} ~${tick}/tick")
        if game.meta.ddos_targets:
            Console.out("\n  Active DDoS:")
            for ip, ticks in sorted(game.meta.ddos_targets.items()):
                Console.out(f"    {ip} — {ticks} commands remaining (FW -1)")
        Console.out("\n  infect miner [IP] | infect ddos <IP> | botnet collect")

    @staticmethod
    def status_lines(game: Game) -> list[str]:
        n = BotnetManager.infection_count(game)
        return [
            f"  Botnet nodes: {n}  |  Bank: ${game.meta.botnet_bank}  |  DDoS: {len(game.meta.ddos_targets)}",
        ]
