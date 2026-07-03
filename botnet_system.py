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
PAYLOAD_RANSOM = "ransom"
PAYLOAD_DEFACE = "deface"
PAYLOAD_FRAME = "frame"
PAYLOAD_VIRUS = "virus"

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
    PAYLOAD_RANSOM: {
        "label": "Ransom locker",
        "heat": 5,
        "shop_key": "ransom_payload",
        "desc": "Encrypts user files — high passive ransom accrual, loud heat.",
    },
    PAYLOAD_DEFACE: {
        "label": "Web defacer",
        "heat": 4,
        "shop_key": "deface_payload",
        "desc": "Replaces public pages — instant notoriety and flex-board post.",
    },
    PAYLOAD_FRAME: {
        "label": "Frame kit",
        "heat": 6,
        "shop_key": "frame_payload",
        "desc": "Plant forged logs blaming a rival — infect frame <rival> [IP].",
    },
    PAYLOAD_VIRUS: {
        "label": "Autonomous virus",
        "heat": 3,
        "shop_key": "virus_payload",
        "desc": "Pure spreader — worms across subnets when heat is high.",
    },
}

PAYLOAD_COLORS: dict[str, str] = {
    PAYLOAD_MINER: "#3ddc84",
    PAYLOAD_DDOS: "#ff4444",
    PAYLOAD_LEAK: "#ffcc00",
    PAYLOAD_RANSOM: "#ff66cc",
    PAYLOAD_DEFACE: "#ff8800",
    PAYLOAD_FRAME: "#aa66ff",
    PAYLOAD_VIRUS: "#00cccc",
}

SUBNET_MAP_ORDER: tuple[str, ...] = (
    "192.168.1.0/24", "10.0.0.0/24", "172.16.0.0/24",
    "203.0.113.0/24", "198.18.0.0/24",
)

# Income scales with host security but stays modest vs contracts.
MINER_BASE_INCOME = 4
DDOS_DURATION = 14
PURGE_NODE_THRESHOLD = 3
COUNTER_ATTACK_THRESHOLD = 4


class BotnetMapRenderer:
    """ASCII + canvas data for infected-node subnet map."""

    @staticmethod
    def _subnet_hosts(game: Game, cidr: str) -> list[str]:
        ips: list[str] = []
        for ip in sorted(game.player.discovered_ips):
            server = game.network.get_server(ip)
            if server and server.subnet == cidr:
                ips.append(ip)
            elif not server and cidr == "192.168.1.0/24" and ip.startswith("192.168.1."):
                ips.append(ip)
        for ip, server in game.network.servers.items():
            if server.subnet == cidr and ip in game.player.discovered_ips and ip not in ips:
                ips.append(ip)
        return sorted(ips)[:12]

    @staticmethod
    def map_lines(game: Game) -> list[str]:
        lines = ["  BOTNET MAP (discovered hosts)",]
        if not game.meta.infections and not game.meta.ddos_targets:
            lines.append("    (no payloads — infect a cracked host)")
            return lines
        for cidr in SUBNET_MAP_ORDER:
            hosts = BotnetMapRenderer._subnet_hosts(game, cidr)
            if not hosts and cidr not in game.meta.subnet_heat:
                continue
            heat = game.meta.subnet_heat.get(cidr, 0)
            row = f"    {cidr:<18} heat {heat}/10"
            lines.append(row)
            for ip in hosts:
                kind = game.meta.infections.get(ip, "")
                ddos = "⚡" if ip in game.meta.ddos_targets else " "
                defaced = "☠" if ip in game.meta.defaced_hosts else " "
                framed = game.meta.framed_rivals.get(ip, "")
                tag = kind[:6] if kind else "clean"
                extra = f" frame→{framed}" if framed else ""
                lines.append(f"      {ip:<16} {tag:<6}{ddos}{defaced}{extra}")
        lines.append("    Legend: miner leak ransom deface frame virus | ⚡=DDoS ☠=defaced")
        return lines

    @staticmethod
    def draw_tk(canvas: Any, game: Game, width: int, height: int) -> None:
        canvas.delete("all")
        canvas.configure(bg="#1a1a2e", highlightthickness=0)
        pad = 8
        cols = len(SUBNET_MAP_ORDER)
        if cols == 0:
            return
        col_w = max(60, (width - pad * 2) // cols)
        for i, cidr in enumerate(SUBNET_MAP_ORDER):
            x0 = pad + i * col_w
            short = cidr.split(".")[0] + "." + cidr.split(".")[1]
            heat = game.meta.subnet_heat.get(cidr, 0)
            canvas.create_text(
                x0 + col_w // 2, 12, text=short, fill="#8888aa", font=("DejaVu Sans Mono", 8),
            )
            canvas.create_text(
                x0 + col_w // 2, 24, text=f"h{heat}", fill="#ff6644" if heat >= 6 else "#666688",
                font=("DejaVu Sans Mono", 7),
            )
            hosts = BotnetMapRenderer._subnet_hosts(game, cidr)
            y = 36
            for ip in hosts[:8]:
                kind = game.meta.infections.get(ip, "")
                color = PAYLOAD_COLORS.get(kind, "#334455")
                if ip in game.meta.defaced_hosts:
                    color = "#ff8800"
                canvas.create_oval(x0 + 4, y, x0 + 14, y + 10, fill=color, outline="#ffffff")
                tail = ip.rsplit(".", 1)[-1]
                canvas.create_text(
                    x0 + 18, y + 5, text=tail, anchor="w", fill="#ccccdd",
                    font=("DejaVu Sans Mono", 8),
                )
                y += 14
            if not hosts:
                canvas.create_text(x0 + col_w // 2, 50, text="—", fill="#444466", font=("DejaVu Sans Mono", 9))


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
            from payload_drops import PayloadDropManager
            hint = PayloadDropManager.hint_when_empty(game, shop_key)
            error(hint or f"No {shop_key} in inventory.")
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
            Console.out("          infect ransom [IP]  |  infect deface [IP]  |  infect frame <rival> [IP]")
            Console.out("          infect virus [IP]")
            Console.out("  Requires: active shell or backdoor on target.")
            Console.out("  Payloads: hunt dead drops — Mail from shard@null.dark has coords.")
            return

        kind = args[0].lower()
        if kind not in PAYLOAD_SPECS:
            error("Usage: infect miner|ddos|leak|ransom|deface|frame|virus [IP]")
            return

        spec = PAYLOAD_SPECS[kind]
        ip_arg: str | None = None
        frame_rival = ""
        if kind == PAYLOAD_FRAME:
            if len(args) < 2:
                error("Usage: infect frame <rival> [IP]  — rivals: acid_k, phantom_pkt, nyx_root, zero_cool")
                return
            frame_rival = args[1].lower()
            from depth_systems import RIVAL_PROFILES
            if frame_rival not in RIVAL_PROFILES:
                error(f"Unknown rival. Pick: {', '.join(RIVAL_PROFILES)}")
                return
            ip_arg = args[2] if len(args) > 2 else None
        else:
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
        if kind in (PAYLOAD_LEAK, PAYLOAD_RANSOM, PAYLOAD_DEFACE, PAYLOAD_FRAME, PAYLOAD_VIRUS):
            if server.ip in game.meta.infections:
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
        elif kind == PAYLOAD_RANSOM:
            game.meta.infections[server.ip] = PAYLOAD_RANSOM
            game.meta.ransom_accrual[server.ip] = 0
            success(f"Ransom locker on {server.ip} — files encrypted, botnet collect cashes out.")
            game.meta.backdoors.add(server.ip)
        elif kind == PAYLOAD_DEFACE:
            game.meta.infections[server.ip] = PAYLOAD_DEFACE
            BotnetManager._apply_deface(game, server)
            game.meta.backdoors.add(server.ip)
        elif kind == PAYLOAD_FRAME:
            game.meta.infections[server.ip] = PAYLOAD_FRAME
            BotnetManager._apply_frame(game, server, frame_rival)
            game.meta.backdoors.add(server.ip)
        elif kind == PAYLOAD_VIRUS:
            game.meta.infections[server.ip] = PAYLOAD_VIRUS
            success(f"Virus seeded on {server.ip} — will autospread across routed subnets.")
            game.meta.backdoors.add(server.ip)
        else:
            duration = spec.get("duration_ticks", DDOS_DURATION)
            game.meta.ddos_targets[server.ip] = duration
            success(f"DDoS flood aimed at {server.ip} for ~{duration} commands.")
            teach("Target firewall softens while flooded. Rival race NPCs slow on that contract IP.")

        RivalHeatManager.spike(game, server.subnet, spec["heat"])
        from chaos_system import NotorietyManager
        NotorietyManager.add(game, 3 if kind == PAYLOAD_DDOS else 2, f"infect {kind} {server.ip}", player_action=True)
        game.player.tutorial_flags.add("daily_botnet_done")
        if BotnetManager.infection_count(game) >= 5:
            game.achievements.unlock("botnet_herder")

    @staticmethod
    def _miner_tick_income(game: Game, server: Server) -> int:
        base = MINER_BASE_INCOME + server.security_level
        return max(3, int(base * BotnetManager._income_mult(game)))

    @staticmethod
    def _ransom_tick_income(game: Game, server: Server) -> int:
        base = MINER_BASE_INCOME + server.security_level * 2
        return max(6, int(base * 1.8 * BotnetManager._income_mult(game)))

    @staticmethod
    def _apply_deface(game: Game, server: Server) -> None:
        from main import success, warn
        from social_board import SocialBoardManager
        from chaos_system import ChaosNewsManager, NotorietyManager

        tag = f"HACKED BY {game.player.username.upper()}"
        server.extra_files["/var/www/index.html"] = (
            f"<html><body><h1>{tag}</h1><p>Your security is a joke.</p></body></html>\n"
        )
        game.meta.defaced_hosts.add(server.ip)
        SocialBoardManager.seed_if_needed(game)
        SocialBoardManager.player_post(
            game, "flex", f"DEFACED: {server.hostname}",
            f"{server.ip} now serves: {tag}",
        )
        NotorietyManager.add(game, 6, f"deface {server.ip}", player_action=True)
        ChaosNewsManager.push(game, f"WEB DEFACE: {server.hostname} ({server.ip}) tagged by operator")
        success(f"Defaced {server.hostname} — {tag}")
        warn("Corp SOC will notice. Heat rising.")

    @staticmethod
    def _apply_frame(game: Game, server: Server, rival: str) -> None:
        from depth_systems import RIVAL_PROFILES
        from faction_consumables import FactionRepManager
        from main import success, warn
        from chaos_system import CareerPressureManager, ChaosNewsManager, NotorietyManager

        profile = RIVAL_PROFILES[rival]
        game.meta.forged_servers.add(server.ip)
        game.meta.framed_rivals[server.ip] = rival
        server.extra_files["/var/log/auth.log"] = (
            server.extra_files.get("/var/log/auth.log", "")
            + f"\nFAILED: brute-force from {rival}@rival.net on sshd\n"
        )
        FactionRepManager.shift(game, {"rivals": 12, "corps": -6})
        NotorietyManager.add(game, 8, f"frame {rival} on {server.ip}", player_action=True)
        ChaosNewsManager.push(
            game, f"FRAME JOB: forged logs on {server.ip} blame {rival}",
        )
        CareerPressureManager.send_or_queue_rival_mail(
            game,
            f"{rival}@rival.net",
            "someone framed me on your subnet",
            f"Your logs on {server.hostname} say I hit it. I didn't.\n"
            f"I'm coming for the real operator.\n\n— {rival}",
        )
        success(f"Framed {rival} on {server.hostname} — forged logs planted.")
        warn(f"{profile['label']} faction heat spiked — expect counter-probes.")

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
                if game.meta.infections.get(ip) == PAYLOAD_RANSOM:
                    game.meta.botnet_bank += BotnetManager._ransom_tick_income(game, server)
                    game.meta.ransom_accrual[ip] = game.meta.ransom_accrual.get(ip, 0) + 1
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
            from chaos_system import CareerPressureManager
            CareerPressureManager.send_or_queue_rival_mail(
                game,
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
        miners = sum(1 for v in game.meta.infections.values() if v == PAYLOAD_MINER)
        ransoms = sum(1 for v in game.meta.infections.values() if v == PAYLOAD_RANSOM)
        Console.out(f"  Active miners:       {miners}")
        Console.out(f"  Ransom lockers:      {ransoms}")
        Console.out(f"  DDoS floods:         {len(game.meta.ddos_targets)}")
        Console.out(f"  Defaced hosts:       {len(game.meta.defaced_hosts)}")
        Console.out(f"  Framed hosts:        {len(game.meta.framed_rivals)}")
        Console.out(f"  Rival purges:        {game.meta.botnet_purges}")
        for line in BotnetMapRenderer.map_lines(game):
            Console.out(line)
        if not game.meta.infections and not game.meta.ddos_targets:
            Console.out("\n  No payloads deployed.")
            teach("Crack a host, hunt a dead drop from shard@null.dark, then: infect miner")
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
        Console.out("\n  infect miner|ransom|deface|frame|virus|leak|ddos  |  botnet collect")

    @staticmethod
    def status_lines(game: Game) -> list[str]:
        n = BotnetManager.infection_count(game)
        return [
            f"  Botnet nodes: {n}  |  Bank: ${game.meta.botnet_bank}  |  DDoS: {len(game.meta.ddos_targets)}",
        ]
