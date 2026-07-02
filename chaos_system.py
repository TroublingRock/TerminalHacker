#!/usr/bin/env python3
"""Chaos / mischief mode — notoriety, loud runs, botnet spread, heat fallout."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from main import Game, Mission, Server

NOTORIETY_THRESHOLDS: tuple[tuple[int, str, str], ...] = (
    (10, "script_kiddie", "Local scanners noticed your noise."),
    (25, "subnet_menace", "Corp SOC filed a ticket about your subnet."),
    (45, "wanted", "Rivals are sharing your egress IP on the board."),
    (70, "chaos_agent", "Chaos subnet brokers want to meet you."),
    (100, "burn_it_down", "You're on every rival's hit list."),
)

HEAT_EVENT_THRESHOLDS: tuple[tuple[int, str], ...] = (
    (6, "lockdown"),
    (9, "bounty"),
    (12, "raid"),
)


class ChaosCareerManager:
    """Skip tutorial — start in loud career mode immediately."""

    @staticmethod
    def can_start(game: Game) -> bool:
        return game.player.phase == "tutorial"

    @staticmethod
    def start(game: Game) -> None:
        from main import Mission, Route, divider, success, warn

        if not ChaosCareerManager.can_start(game):
            warn("Chaos career only available from tutorial (or type: chaos start).")
            return

        p = game.player
        p.phase = "career"
        p.tutorial_step = len(__import__("main").TUTORIAL_CURRICULUM)
        p.tutorial_credits = 0
        p.money = 1200
        p.reputation = 150
        p.rank_index = 1
        p.cpu_level = 2
        p.firewall_level = 2
        p.chaos_unlocked = True
        p.tutorial_flags.add("tutorial_v2")
        p.tutorial_flags.add("chaos_career")

        game.meta.chaos_mode = True
        game.meta.notoriety = 8
        game.meta.inventory["miner_payload"] = game.meta.inventory.get("miner_payload", 0) + 2
        game.meta.inventory["ddos_payload"] = game.meta.inventory.get("ddos_payload", 0) + 1

        if not any(r.destination == "10.0.0.0/24" for r in p.routes):
            p.routes.append(Route("10.0.0.0/24", "192.168.1.1"))
        if not any(r.destination == "203.0.113.0/24" for r in p.routes):
            p.routes.append(Route("203.0.113.0/24", "192.168.1.1"))

        game.network.deploy_company_hosts_with_puzzles(game, p.reputation, True)

        starter_ip = "192.168.1.10"
        if game.network.get_server(starter_ip):
            game.missions.missions.insert(
                0,
                Mission(
                    "chaos-001", "nullbyte",
                    f"LOUD JOB: crack {starter_ip}, steal /home/admin/notes.txt, leave traces optional.",
                    starter_ip, "/home/admin/notes.txt", 550, rep_reward=35,
                    require_log_wipe=False,
                ),
            )

        divider("CHAOS CAREER — NO TRAINING WHEELS")
        success("You skipped the sandbox. Traces, heat, and rivals are live.")
        warn("Loud runs pay more. Ghost runs are for cowards.")

        game.mail.send(
            "zero_cool@rival.net",
            "fresh meat on chaos wire",
            "Skipped boot camp? Respect.\n"
            "Scan loud. Infect everything. I'll be watching.\n\n— zero_cool",
        )
        game.mail.send(
            "ghost_broker@darknet",
            "Chaos contract queue open",
            "No hand-holding. Contracts pay extra if you leave the subnet burning.\n"
            "Type: chaos status  |  infect miner  |  chaos provoke\n\n— ghost_broker",
        )

        if game.gui_mode:
            game.defer_career_session = True
        else:
            from retention import RetentionManager
            RetentionManager.on_career_session(game)

        game.missions.announce_login(game.mail)
        game.autosave(force=True)


class NotorietyManager:
    @staticmethod
    def add(game: Game, amount: int, reason: str = "") -> None:
        if amount <= 0 or game.player.phase not in ("career", "endless"):
            return
        old = game.meta.notoriety
        game.meta.notoriety = min(150, game.meta.notoriety + amount)
        for threshold, flag, blurb in NOTORIETY_THRESHOLDS:
            if old < threshold <= game.meta.notoriety and flag not in game.meta.chaos_flags:
                game.meta.chaos_flags.add(flag)
                from main import info
                info(f"NOTORIETY {threshold}: {blurb}")
                from retention import RetentionManager
                rival = RetentionManager.pick_rival_attacker(game)
                game.mail.send(
                    f"{rival}@rival.net",
                    f"You're getting loud ({threshold})",
                    f"{blurb}\n\nReason: {reason or 'general mayhem'}\n\n— {rival}",
                )

    @staticmethod
    def contract_style_mult(game: Game, mission: Mission) -> tuple[float, str]:
        """Loud contracts (traces left) pay more in chaos mode."""
        server = game.network.get_server(mission.target_ip) if mission.target_ip else None
        if not server:
            return 1.0, ""
        p = game.player
        dirty = server.player_left_traces(p) and not __import__(
            "depth_systems", fromlist=["ToolManager"]
        ).ToolManager.logs_clean_enough(game, server, p)

        if game.meta.chaos_mode or game.player.chaos_unlocked:
            if dirty:
                NotorietyManager.add(game, 4, f"loud contract {mission.mission_id}")
                return 1.35, "LOUD RUN (+35% — traces left)"
            if mission.require_log_wipe:
                return 0.92, "ghost run (-8% in chaos mode)"
            return 1.1, "messy run (+10%)"

        if dirty:
            return 0.85, "sloppy (-15%)"
        return 1.0, ""

    @staticmethod
    def status_lines(game: Game) -> list[str]:
        lines = [
            f"  Notoriety:   {game.meta.notoriety}/150",
            f"  Chaos mode:  {'ON' if game.meta.chaos_mode else 'off'}",
        ]
        if game.meta.chaos_flags:
            lines.append(f"  Tags:        {', '.join(sorted(game.meta.chaos_flags))}")
        return lines


class ChaosEventManager:
    """Heat on subnets triggers escalating world reactions."""

    @staticmethod
    def on_post_command(game: Game) -> None:
        if game.player.phase not in ("career", "endless"):
            return
        for subnet, heat in list(game.meta.subnet_heat.items()):
            for threshold, event_id in HEAT_EVENT_THRESHOLDS:
                key = f"heat_{subnet}_{event_id}"
                if heat >= threshold and key not in game.meta.chaos_flags:
                    ChaosEventManager._fire(game, subnet, heat, event_id, key)

    @staticmethod
    def _fire(game: Game, subnet: str, heat: int, event_id: str, flag_key: str) -> None:
        from main import warn
        from retention import RetentionManager

        game.meta.chaos_flags.add(flag_key)
        rival = RetentionManager.pick_rival_attacker(game)

        if event_id == "lockdown":
            warn(f"SUBNET LOCKDOWN on {subnet} — IDS sensitivity spiked.")
            game.mail.send(
                "security@corp.local",
                f"Anomaly on {subnet}",
                f"Automated lockdown triggered (heat {heat}/10).\n"
                "Expect heavier logging on all hosts in range.",
            )
            NotorietyManager.add(game, 2, f"heat lockdown {subnet}")
        elif event_id == "bounty":
            warn(f"BOUNTY POSTED — your traffic on {subnet} is flagged.")
            game.mail.send(
                f"{rival}@rival.net",
                f"Bounty: noisy operator on {subnet}",
                f"Heat hit {heat}. I'm telling everyone.\n\n— {rival}",
            )
            NotorietyManager.add(game, 5, f"bounty {subnet}")
        elif event_id == "raid":
            warn(f"RIVAL RAID — {rival} hits your localhost.")
            game.mail.send(
                f"{rival}@rival.net",
                "Raid incoming",
                f"You turned {subnet} into a bonfire (heat {heat}). Enjoy.\n\n— {rival}",
            )
            NotorietyManager.add(game, 8, f"raid {subnet}")
            game.threat._maybe_attack(force=True)


class BotnetSpreadManager:
    """Infections worm to neighbors on hot subnets."""

    SPREAD_BASE = 0.06

    @staticmethod
    def try_spread(game: Game) -> None:
        if game.player.phase not in ("career", "endless"):
            return
        if not game.meta.infections:
            return
        heat_total = sum(game.meta.subnet_heat.values())
        chance = BotnetSpreadManager.SPREAD_BASE + len(game.meta.infections) * 0.012
        chance += heat_total * 0.004
        if game.meta.chaos_mode:
            chance *= 1.35
        if random.random() >= chance:
            return

        source_ip = random.choice(list(game.meta.infections.keys()))
        source = game.network.get_server(source_ip)
        if not source:
            return

        candidates: list[Server] = []
        for s in game.network.servers.values():
            if s.ip == source_ip or s.ip in game.meta.infections:
                continue
            if s.subnet != source.subnet:
                continue
            if s.ip not in game.player.discovered_ips:
                continue
            if s.security_level > game.player.cpu_level + 2:
                continue
            candidates.append(s)

        if not candidates:
            return

        target = random.choice(candidates)
        game.meta.infections[target.ip] = game.meta.infections[source_ip]
        game.meta.backdoors.add(target.ip)
        from depth_systems import RivalHeatManager
        from main import success, warn

        RivalHeatManager.spike(game, target.subnet, 3)
        NotorietyManager.add(game, 3, f"worm spread {source_ip} → {target.ip}")
        success(f"WORM SPREAD: {game.meta.infections[target.ip]} jumped {source_ip} → {target.hostname}")
        warn(f"{target.ip} auto-infected — rivals will notice the subnet.")
        rival = __import__("retention").RetentionManager.pick_rival_attacker(game)
        game.mail.send(
            f"{rival}@rival.net",
            "your worm just lit up my scan",
            f"Payload copied from {source_ip} to {target.ip} on {target.subnet}.\n"
            f"Cute. I'm coming.\n\n— {rival}",
        )


class ChaosCommandManager:
    @staticmethod
    def cmd_chaos(game: Game, args: list[str]) -> None:
        from main import Console, divider, error, success, teach, warn

        if not args:
            divider("CHAOS / MISCHIEF")
            for line in NotorietyManager.status_lines(game):
                Console.out(line)
            Console.out("  Usage: chaos start | status | provoke | run")
            Console.out("  Loud contracts (traces left) pay +35% in chaos mode.")
            Console.out("  High subnet heat triggers lockdowns, bounties, rival raids.")
            return

        action = args[0].lower()
        if action == "start":
            ChaosCareerManager.start(game)
            return
        if action == "status":
            divider("CHAOS STATUS")
            for line in NotorietyManager.status_lines(game):
                Console.out(line)
            from depth_systems import RivalHeatManager
            for line in RivalHeatManager.status_lines(game):
                Console.out(line)
            from botnet_system import BotnetManager
            for line in BotnetManager.status_lines(game):
                Console.out(line)
            return
        if action == "provoke":
            if game.player.phase not in ("career", "endless"):
                error("Career only.")
                return
            NotorietyManager.add(game, 6, "chaos provoke")
            warn("You poked the hornet nest on purpose.")
            game.threat._maybe_attack(force=True)
            from retention import RetentionManager
            rival = RetentionManager.pick_rival_attacker(game)
            game.mail.send(
                f"{rival}@rival.net",
                "you asked for this",
                "Saw your provoke ping. Enjoy the probe.\n\n— {rival}",
            )
            success("Rival provoked — check localhost defenses.")
            return
        if action == "run":
            if game.player.phase != "career":
                error("Need career mode. Try: chaos start")
                return
            from endless_mode import EndlessManager
            EndlessManager.start_run(game)
            teach("Chaos Run = roguelike floors. Die and retry. Go loud.")
            return
        error("Usage: chaos [start|status|provoke|run]")
