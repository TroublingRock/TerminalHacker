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
    (8, "bounty"),
    (10, "raid"),
)

# Commands with no hostile player action — rivals observe but don't punish yet.
ROOKIE_GRACE_TICKS = 18


class CareerPressureManager:
    """Hold rival heat / notoriety fallout until the player has actually operated."""

    @staticmethod
    def rookie_grace(game: Game) -> bool:
        p = game.player
        if p.phase not in ("career", "endless"):
            return True
        if p.ticks >= ROOKIE_GRACE_TICKS:
            return False
        if any(m.completed for m in game.missions.missions):
            return False
        if game.meta.infections:
            return False
        for ip in p.discovered_ips:
            srv = game.network.get_server(ip)
            if srv and srv.cracked:
                return False
        return True

    @staticmethod
    def consequences_enabled(game: Game) -> bool:
        return not CareerPressureManager.rookie_grace(game)

    @staticmethod
    def has_cracked_host(game: Game) -> bool:
        for ip in game.player.discovered_ips:
            srv = game.network.get_server(ip)
            if srv and srv.cracked:
                return True
        return False

    @staticmethod
    def can_trash_talk(game: Game) -> bool:
        """Rivals posture and mail — after first crack, when notoriety becomes real."""
        if game.player.phase not in ("career", "endless"):
            return False
        return game.meta.rival_trash_talk_unlocked or CareerPressureManager.has_cracked_host(game)

    @staticmethod
    def queue_rival_mail(game: Game, sender: str, subject: str, body: str) -> None:
        game.meta.pending_rival_mail.append(
            {"sender": sender, "subject": subject, "body": body},
        )

    @staticmethod
    def send_or_queue_rival_mail(game: Game, sender: str, subject: str, body: str) -> None:
        if CareerPressureManager.can_trash_talk(game):
            game.mail.send(sender, subject, body)
        else:
            CareerPressureManager.queue_rival_mail(game, sender, subject, body)

    @staticmethod
    def on_first_crack(game: Game, server: Server) -> None:
        if not CareerPressureManager.has_cracked_host(game):
            return
        first_unlock = not game.meta.rival_trash_talk_unlocked
        game.meta.rival_trash_talk_unlocked = True
        if first_unlock:
            from main import info
            info(
                f"NOTORIETY LIVE — {server.hostname} cracked. "
                "Rivals are watching; trash talk incoming."
            )
        for mail in game.meta.pending_rival_mail:
            game.mail.send(mail["sender"], mail["subject"], mail["body"])
        game.meta.pending_rival_mail = []

    @staticmethod
    def sync_unlock_from_save(game: Game) -> None:
        """Returning saves with prior cracks skip the pre-crack quiet period."""
        if not CareerPressureManager.has_cracked_host(game):
            return
        game.meta.rival_trash_talk_unlocked = True
        for mail in game.meta.pending_rival_mail:
            game.mail.send(mail["sender"], mail["subject"], mail["body"])
        game.meta.pending_rival_mail = []


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
        from progression import PlayerProfile
        PlayerProfile.mark_veteran()

        game.meta.chaos_mode = True
        game.meta.notoriety = 4
        game.meta.notoriety_baseline = 4
        game.meta.rival_trash_talk_unlocked = False
        game.meta.pending_rival_mail = []
        game.meta.inventory["miner_payload"] = game.meta.inventory.get("miner_payload", 0) + 2
        game.meta.inventory["ddos_payload"] = game.meta.inventory.get("ddos_payload", 0) + 1
        game.meta.inventory["leak_payload"] = game.meta.inventory.get("leak_payload", 0) + 1
        game.meta.inventory["virus_payload"] = game.meta.inventory.get("virus_payload", 0) + 1
        game.meta.inventory["deface_payload"] = game.meta.inventory.get("deface_payload", 0) + 1

        if not any(r.destination == "10.0.0.0/24" for r in p.routes):
            p.routes.append(Route("10.0.0.0/24", "192.168.1.1"))
        if not any(r.destination == "203.0.113.0/24" for r in p.routes):
            p.routes.append(Route("203.0.113.0/24", "192.168.1.1"))
        if not any(r.destination == "198.18.0.0/24" for r in p.routes):
            p.routes.append(Route("198.18.0.0/24", "192.168.1.1"))

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
        from main import info
        info(
            f"Rookie window: ~{ROOKIE_GRACE_TICKS} commands before heat lockdowns bite. "
            "Rival trash talk waits until your first crack."
        )

        game.mail.send(
            "ghost_broker@darknet",
            "Chaos contract queue open",
            "No hand-holding. Contracts pay extra if you leave the subnet burning.\n"
            "Type: chaos status  |  infect miner  |  chaos provoke\n\n— ghost_broker",
        )
        CareerPressureManager.send_or_queue_rival_mail(
            game,
            "zero_cool@rival.net",
            "fresh meat on chaos wire",
            "Skipped boot camp? Respect.\n"
            "Scan loud. Infect everything. I'll be watching.\n\n— zero_cool",
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
    def add(game: Game, amount: int, reason: str = "", *, player_action: bool = False) -> None:
        if amount <= 0 or game.player.phase not in ("career", "endless"):
            return
        if not player_action and CareerPressureManager.rookie_grace(game):
            return
        old = game.meta.notoriety
        game.meta.notoriety = min(150, game.meta.notoriety + amount)
        if amount >= 3 and CareerPressureManager.can_trash_talk(game):
            ChaosNewsManager.push(game, f"Notoriety +{amount}: {reason or 'mayhem'}")
        for threshold, flag, blurb in NOTORIETY_THRESHOLDS:
            if not CareerPressureManager.can_trash_talk(game):
                continue
            if game.meta.notoriety <= game.meta.notoriety_baseline and not player_action:
                continue
            if old < threshold <= game.meta.notoriety and flag not in game.meta.chaos_flags:
                game.meta.chaos_flags.add(flag)
                from main import info
                info(f"NOTORIETY {threshold}: {blurb}")
                from retention import RetentionManager
                rival = RetentionManager.pick_rival_attacker(game)
                CareerPressureManager.send_or_queue_rival_mail(
                    game,
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
                NotorietyManager.add(game, 4, f"loud contract {mission.mission_id}", player_action=True)
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
        if CareerPressureManager.rookie_grace(game):
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
            CareerPressureManager.send_or_queue_rival_mail(
                game,
                f"{rival}@rival.net",
                f"Bounty: noisy operator on {subnet}",
                f"Heat hit {heat}. I'm telling everyone.\n\n— {rival}",
            )
            NotorietyManager.add(game, 5, f"bounty {subnet}")
        elif event_id == "raid":
            warn(f"RIVAL RAID — {rival} hits your localhost.")
            CareerPressureManager.send_or_queue_rival_mail(
                game,
                f"{rival}@rival.net",
                "Raid incoming",
                f"You turned {subnet} into a bonfire (heat {heat}). Enjoy.\n\n— {rival}",
            )
            NotorietyManager.add(game, 8, f"raid {subnet}")
            game.threat._maybe_attack(force=True)


class BotnetSpreadManager:
    """Infections worm to neighbors on hot subnets; virus jumps routed subnets."""

    SPREAD_BASE = 0.06
    CROSS_SUBNET_BASE = 0.03

    @staticmethod
    def try_spread(game: Game) -> None:
        if game.player.phase not in ("career", "endless"):
            return
        if CareerPressureManager.rookie_grace(game):
            return
        if not game.meta.infections:
            return
        BotnetSpreadManager._try_neighbor_spread(game)
        virus_count = sum(1 for v in game.meta.infections.values() if v == "virus")
        if virus_count or game.meta.notoriety >= 20 or game.meta.chaos_mode:
            BotnetSpreadManager._try_cross_subnet_spread(game)

    @staticmethod
    def _spread_chance(game: Game, source_ip: str) -> float:
        heat_total = sum(game.meta.subnet_heat.values())
        chance = BotnetSpreadManager.SPREAD_BASE + len(game.meta.infections) * 0.012
        chance += heat_total * 0.004
        kind = game.meta.infections.get(source_ip, "")
        if kind == "virus":
            chance *= 2.2
        elif kind in ("leak", "ransom"):
            chance *= 1.15
        if game.meta.chaos_mode:
            chance *= 1.35
        return chance

    @staticmethod
    def _try_neighbor_spread(game: Game) -> None:
        source_ip = random.choice(list(game.meta.infections.keys()))
        if random.random() >= BotnetSpreadManager._spread_chance(game, source_ip):
            return

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
        payload = game.meta.infections[source_ip]
        if payload == "virus":
            payload = random.choice(["virus", "miner", "leak"])
        game.meta.infections[target.ip] = payload
        game.meta.backdoors.add(target.ip)
        BotnetSpreadManager._announce_spread(game, source_ip, target, payload, "worm")

    @staticmethod
    def _routed_subnets(game: Game) -> set[str]:
        return {r.destination for r in game.player.routes}

    @staticmethod
    def _try_cross_subnet_spread(game: Game) -> None:
        virus_nodes = [ip for ip, k in game.meta.infections.items() if k == "virus"]
        sources = virus_nodes or list(game.meta.infections.keys())
        if not sources:
            return
        source_ip = random.choice(sources)
        chance = BotnetSpreadManager.CROSS_SUBNET_BASE
        if game.meta.infections.get(source_ip) == "virus":
            chance *= 2.5
        chance += game.meta.notoriety * 0.001
        if random.random() >= chance:
            return

        source = game.network.get_server(source_ip)
        if not source:
            return

        routed = BotnetSpreadManager._routed_subnets(game)
        candidates: list[Server] = []
        for s in game.network.servers.values():
            if s.ip == source_ip or s.ip in game.meta.infections:
                continue
            if s.subnet == source.subnet:
                continue
            if s.subnet not in routed and s.subnet != "198.18.0.0/24":
                continue
            if s.ip not in game.player.discovered_ips:
                continue
            if s.security_level > game.player.cpu_level + 3:
                continue
            candidates.append(s)

        if not candidates:
            return

        target = random.choice(candidates)
        src_kind = game.meta.infections[source_ip]
        payload = "virus" if src_kind == "virus" else random.choice(["virus", "miner", "leak"])
        game.meta.infections[target.ip] = payload
        game.meta.backdoors.add(target.ip)
        BotnetSpreadManager._announce_spread(game, source_ip, target, payload, "cross-subnet virus")

    @staticmethod
    def _announce_spread(game: Game, source_ip: str, target: Server, payload: str, tag: str) -> None:
        from depth_systems import RivalHeatManager
        from main import success, warn

        RivalHeatManager.spike(game, target.subnet, 4 if tag == "cross-subnet virus" else 3)
        NotorietyManager.add(game, 4 if tag == "cross-subnet virus" else 3, f"{tag} {source_ip} → {target.ip}")
        success(f"{tag.upper()}: {payload} jumped {source_ip} → {target.hostname}")
        warn(f"{target.ip} auto-infected on {target.subnet} — rivals will notice.")
        rival = __import__("retention").RetentionManager.pick_rival_attacker(game)
        game.mail.send(
            f"{rival}@rival.net",
            "your worm just lit up my scan",
            f"Payload ({payload}) copied from {source_ip} to {target.ip} on {target.subnet}.\n"
            f"Cute. I'm coming.\n\n— {rival}",
        )
        RivalReactionManager.on_botnet_spread(game, source_ip, target.ip)
        ChaosNewsManager.push(game, f"{tag.upper()}: {payload} spread {source_ip} → {target.ip}")


class ChaosNewsManager:
    """Rolling headline feed of your crimes — optional LLM flavor."""

    MAX_HEADLINES = 24

    @staticmethod
    def push(game: Game, headline: str) -> None:
        if not headline:
            return
        game.meta.chaos_headlines.append(headline[:200])
        if len(game.meta.chaos_headlines) > ChaosNewsManager.MAX_HEADLINES:
            game.meta.chaos_headlines = game.meta.chaos_headlines[-ChaosNewsManager.MAX_HEADLINES:]

    @staticmethod
    def maybe_llm_headline(game: Game, context: str) -> None:
        try:
            from llm_content import LLMContentManager, LLMClient
            if not LLMClient.available() or not game.llm.user_enabled:
                return
            text = LLMContentManager.generate(
                game, "chaos_news", context[:40], context, limit=120,
            )
            if text:
                ChaosNewsManager.push(game, text.strip())
        except Exception:
            pass

    @staticmethod
    def latest(game: Game) -> str:
        return game.meta.chaos_headlines[-1] if game.meta.chaos_headlines else ""

    @staticmethod
    def status_lines(game: Game) -> list[str]:
        if not game.meta.chaos_headlines:
            return ["  News wire:   (quiet — go make trouble)"]
        lines = ["  CHAOS NEWS WIRE",]
        for h in game.meta.chaos_headlines[-8:]:
            lines.append(f"    • {h}")
        return lines


class RivalReactionManager:
    """Extra rival mail when you cause trouble — chaos mode only."""

    @staticmethod
    def _react(game: Game, chance: float, subject: str, body: str, notoriety: int = 1) -> None:
        if game.player.phase not in ("career", "endless"):
            return
        if not CareerPressureManager.can_trash_talk(game):
            return
        if random.random() > chance:
            return
        from retention import RetentionManager
        rival = RetentionManager.pick_rival_attacker(game)
        game.mail.send(f"{rival}@rival.net", subject, f"{body}\n\n— {rival}")
        if not CareerPressureManager.rookie_grace(game):
            NotorietyManager.add(game, notoriety, subject.lower(), player_action=True)

    @staticmethod
    def on_scan_chaos_subnet(game: Game, cidr: str) -> None:
        if cidr != "203.0.113.0/24":
            return
        RivalReactionManager._react(
            game, 0.55,
            "stop scanning chaos edge",
            "203.0.113.x is not a playground. Back off or burn.",
            3,
        )
        ChaosNewsManager.push(game, f"Operator scanned chaos subnet {cidr} — IDS lit up.")

    @staticmethod
    def on_crack(game: Game, server: Server) -> None:
        if server.security_level >= 2:
            RivalReactionManager._react(
                game, 0.35,
                f"saw you crack {server.hostname}",
                f"{server.ip} just went down. I'm logging your style.",
                2,
            )
            ChaosNewsManager.push(
                game, f"Breach: {server.hostname} ({server.ip}) cracked by {game.player.effective_egress_ip}",
            )
            MeltdownManager.on_crack(game, server)

    @staticmethod
    def on_dirty_disconnect(game: Game, server: Server) -> None:
        RivalReactionManager._react(
            game, 0.45,
            "sloppy disconnect",
            f"You left logs on {server.hostname}. Amateur hour.",
            2,
        )

    @staticmethod
    def on_botnet_spread(game: Game, src: str, dst: str) -> None:
        ChaosNewsManager.push(game, f"WORM: payload spread {src} → {dst}")
        ChaosNewsManager.maybe_llm_headline(
            game, f"Breaking: worm spread between {src} and {dst} on the darknet.",
        )


class MeltdownManager:
    """Corp meltdown chains — crack → leak → flash payout."""

    @staticmethod
    def on_crack(game: Game, server: Server) -> None:
        if not game.meta.chaos_mode or server.security_level < 2:
            return
        if game.meta.meltdown.get("ip"):
            return
        company = server.company or server.hostname
        game.meta.meltdown = {
            "ip": server.ip,
            "company": company,
            "step": 1,
            "need": "leak",
        }
        from main import info
        info(f"MELTDOWN CHAIN started — {company}. Leak intel: chaos leak")

    @staticmethod
    def on_leak(game: Game, server: Server, snippet: str) -> None:
        md = game.meta.meltdown
        if not md or md.get("ip") != server.ip:
            return
        if md.get("step") != 1:
            return
        from social_board import SocialBoardManager
        SocialBoardManager.seed_if_needed(game)
        SocialBoardManager.player_post(
            game, "flex",
            f"LEAKED: {md.get('company', server.hostname)}",
            snippet[:400],
        )
        md["step"] = 2
        NotorietyManager.add(game, 8, f"meltdown leak {server.ip}", player_action=True)
        ChaosNewsManager.push(game, f"DATA LEAK: {md.get('company')} files posted to flex board")
        ChaosNewsManager.maybe_llm_headline(
            game, f"Corp meltdown: leaked files from {md.get('company')} hit the darknet boards.",
        )
        from main import Mission, success
        from variety_content import VarietyMissionGenerator

        flash = VarietyMissionGenerator.generate(game)
        if flash:
            flash.reward = int(flash.reward * 1.6)
            flash.briefing = f"FLASH CHAOS — {flash.briefing} (meltdown fallout)"
            game.missions.missions.insert(0, flash)
            game.mail.send(
                "nullbyte@darknet",
                f"Meltdown bonus contract — {flash.mission_id}",
                f"{md.get('company')} is bleeding. Cash in while they're panicking.\n\n{flash.briefing}",
            )
        success(f"MELTDOWN step 2 — {md.get('company')} leak live. Flash contract dropped.")
        game.meta.meltdown = {}

    @staticmethod
    def status_lines(game: Game) -> list[str]:
        md = game.meta.meltdown
        if not md:
            return []
        return [
            f"  Meltdown:    {md.get('company', '?')} @ {md.get('ip')} — step {md.get('step')} ({md.get('need', '?')})",
        ]


class FactionWarManager:
    """Instigate faction wars — heat + rivals + rep shifts."""

    COOLDOWN = 25

    @staticmethod
    def start(game: Game, faction: str) -> None:
        from main import error, success, warn

        if game.player.phase not in ("career", "endless"):
            error("Career only.")
            return
        faction = faction.lower()
        targets = {"rivals": "rivals", "corps": "corps", "brokers": "brokers"}
        if faction not in targets:
            error("Usage: chaos war <rivals|corps|brokers>")
            return
        if game.meta.faction_war_cd > 0:
            error(f"Faction war cooling down ({game.meta.faction_war_cd} commands).")
            return

        from faction_consumables import FactionRepManager
        deltas = {"rivals": {"rivals": 20, "corps": -8, "brokers": -5},
                  "corps": {"corps": 20, "rivals": -10, "brokers": 5},
                  "brokers": {"brokers": 20, "rivals": -5, "corps": -8}}[faction]
        FactionRepManager.shift(game, deltas)

        from depth_systems import RivalHeatManager, RIVAL_PROFILES
        subnet = {"rivals": "203.0.113.0/24", "corps": "10.0.0.0/24", "brokers": "172.16.0.0/24"}[faction]
        RivalHeatManager.spike(game, subnet, 6)
        NotorietyManager.add(game, 10, f"faction war {faction}", player_action=True)
        game.meta.faction_war_cd = FactionWarManager.COOLDOWN

        warn(f"FACTION WAR — you stirred up {faction}. Heat spiked on {subnet}.")
        success("Rivals mobilizing. Expect probes and flash contracts.")
        ChaosNewsManager.push(game, f"FACTION WAR: operator declared war on {faction} — {subnet} burning")
        from retention import RetentionManager
        rival = RetentionManager.pick_rival_attacker(game)
        CareerPressureManager.send_or_queue_rival_mail(
            game,
            f"{rival}@rival.net",
            f"war on {faction}",
            f"You picked a side fight. I'm joining in.\n\n— {rival}",
        )
        game.threat._maybe_attack(force=True)
        game.threat._maybe_attack(force=False)

    @staticmethod
    def tick_cooldown(game: Game) -> None:
        if game.meta.faction_war_cd > 0:
            game.meta.faction_war_cd -= 1
        if game.meta.ghost_raid_cd > 0:
            game.meta.ghost_raid_cd -= 1


class GhostRaidManager:
    """Raid abandoned ghost nodes — procedural loot piñatas."""

    COOLDOWN = 18

    @staticmethod
    def launch(game: Game) -> None:
        from main import Mission, Route, Server, error, success, warn

        if game.player.phase not in ("career", "endless"):
            error("Career only.")
            return
        if game.meta.ghost_raid_cd > 0:
            error(f"Ghost raid cooling down ({game.meta.ghost_raid_cd} commands).")
            return

        p = game.player
        if not any(r.destination == "198.18.0.0/24" for r in p.routes):
            p.routes.append(Route("198.18.0.0/24", p.gateway))
        octet = random.randint(40, 250)
        ip = f"198.18.{random.randint(1, 254)}.{octet}"
        loot = random.choice([
            "/home/ghost/wallet.dat",
            "/home/ghost/keys.txt",
            "/var/backups/abandoned.db",
        ])
        reward = random.randint(380, 720)
        if ip not in game.network.servers:
            game.network.servers[ip] = Server(
                ip, f"ghost-{octet}", 1,
                subnet="198.18.0.0/24",
                ssh_user="ghost",
                ssh_password=random.choice(["ghost123", "abandoned", "leftbehind"]),
                extra_files={loot: "ghost loot — grab before purge\n"},
            )
        game.player.discovered_ips.add(ip)
        game.missions.missions.insert(
            0,
            Mission(
                f"ghost-{octet}", "shade_runner",
                f"GHOST RAID: abandoned node {ip} — crack, download {loot}, traces optional.",
                ip, loot, reward, rep_reward=40, require_log_wipe=False, procedural=True,
            ),
        )
        game.meta.ghost_raid_cd = GhostRaidManager.COOLDOWN
        NotorietyManager.add(game, 5, f"ghost raid {ip}", player_action=True)
        warn(f"GHOST SIGNAL — abandoned host {ip} spotted on darknet.")
        success("Contract added. Loud run pays extra.")
        ChaosNewsManager.push(game, f"Ghost raid queued on abandoned node {ip}")
        game.mail.send(
            "shade_runner@darknet",
            f"Ghost raid — {ip}",
            f"Old operator went dark. Node still pinging.\n"
            f"Grab {loot} before someone else does.\n\n— shade_runner",
        )


class FlashChaosManager:
    """Random high-voltage contracts when notoriety is high."""

    @staticmethod
    def maybe_spawn(game: Game) -> None:
        if CareerPressureManager.rookie_grace(game):
            return
        if game.player.phase != "career" or game.meta.notoriety < 20:
            return
        if random.random() > 0.04:
            return
        from variety_content import VarietyMissionGenerator
        m = VarietyMissionGenerator.generate(game)
        if not m:
            return
        m.reward = int(m.reward * 1.45)
        m.briefing = f"⚡ CHAOS FLASH — {m.briefing} (loud bonus)"
        m.require_log_wipe = False
        game.missions.missions.insert(0, m)
        from main import info
        info(f"FLASH CONTRACT: {m.mission_id} — ${m.reward}")
        ChaosNewsManager.push(game, f"Flash contract {m.mission_id} dropped (${m.reward})")
        game.mail.send(
            f"{m.broker}@darknet",
            f"Flash chaos — {m.mission_id}",
            f"You're hot right now. Fast money, no rules.\n\n{m.briefing}",
        )


class ChaosStrikeManager:
    """Offensive strike — hammer a rival's turf."""

    @staticmethod
    def strike(game: Game, target: str = "") -> None:
        from depth_systems import RIVAL_PROFILES, RivalHeatManager
        from main import error, success, warn
        from retention import RetentionManager

        if game.player.phase not in ("career", "endless"):
            error("Career only.")
            return

        rival = target.lower() if target else RetentionManager.pick_rival_attacker(game)
        if rival not in RIVAL_PROFILES:
            error(f"Unknown rival. Pick: {', '.join(RIVAL_PROFILES)}")
            return

        profile = RIVAL_PROFILES[rival]
        subnet = profile["subnet"]
        RivalHeatManager.spike(game, subnet, 8)
        NotorietyManager.add(game, 7, f"strike {rival}", player_action=True)
        warn(f"CHAOS STRIKE — flooding {rival}'s turf ({subnet}).")
        success("Rival infrastructure softened. DDoS timers boosted on random targets.")
        for ip in list(game.network.servers.keys())[:3]:
            if ip.startswith(subnet.split(".")[0]):
                game.meta.ddos_targets[ip] = max(game.meta.ddos_targets.get(ip, 0), 10)
        CareerPressureManager.send_or_queue_rival_mail(
            game,
            f"{rival}@rival.net",
            "you struck my subnet",
            f"Heat on {subnet} just spiked. Enjoy the counterattack.\n\n— {rival}",
        )
        ChaosNewsManager.push(game, f"Chaos strike on {rival}'s {subnet} by {game.player.username}")
        game.threat._maybe_attack(force=False)


class ChaosDefaceManager:
    """Deface a host from shell — or trigger deface payload."""

    @staticmethod
    def deface(game: Game) -> None:
        from botnet_system import BotnetManager, PAYLOAD_DEFACE
        from main import error, success

        server = game.remote_server() if hasattr(game, "remote_server") else None
        if not server or not game.player.has_remote_shell:
            error("Need shell on target. Or: infect deface on host first.")
            return
        if server.ip in game.meta.defaced_hosts:
            error(f"{server.hostname} already defaced.")
            return
        BotnetManager._apply_deface(game, server)
        if server.ip not in game.meta.infections:
            game.meta.infections[server.ip] = PAYLOAD_DEFACE


class ChaosFrameManager:
    """Frame a rival — plant forged logs from shell."""

    @staticmethod
    def frame(game: Game, target: str = "") -> None:
        from botnet_system import BotnetManager, PAYLOAD_FRAME
        from depth_systems import RIVAL_PROFILES
        from main import error
        from retention import RetentionManager

        server = game.remote_server() if hasattr(game, "remote_server") else None
        if not server or not game.player.has_remote_shell:
            error("Need shell on target. Or: infect frame <rival> [IP]")
            return
        rival = target.lower() if target else RetentionManager.pick_rival_attacker(game)
        if rival not in RIVAL_PROFILES:
            error(f"Unknown rival. Pick: {', '.join(RIVAL_PROFILES)}")
            return
        if server.ip in game.meta.framed_rivals:
            error(f"{server.hostname} already framed ({game.meta.framed_rivals[server.ip]}).")
            return
        BotnetManager._apply_frame(game, server, rival)
        game.meta.infections[server.ip] = PAYLOAD_FRAME


class ChaosLeakManager:
    """Leak host data to the board — needs shell on target."""

    @staticmethod
    def leak(game: Game) -> None:
        from main import error

        server = game.remote_server() if hasattr(game, "remote_server") else None
        if not server or not game.player.has_remote_shell:
            error("Need shell on target to leak. Or: infect leak on host first.")
            return
        if server.ip in game.meta.infections and game.meta.infections[server.ip] == "leak":
            snippet = ""
            for path, f in list(server.files.items())[:4]:
                if not f.requires_root:
                    snippet += f"{path}: {f.read()[:80]}...\n"
            MeltdownManager.on_leak(game, server, snippet or f"Intel dump from {server.hostname}")
            return
        files = server.files
        paths = [p for p in files if "/home/" in p or "/var/log" in p][:3]
        snippet = "\n".join(f"{p}: {files[p].read()[:60]}..." for p in paths)
        from social_board import SocialBoardManager
        SocialBoardManager.seed_if_needed(game)
        SocialBoardManager.player_post(
            game, "flex", f"dump from {server.hostname}",
            snippet or "(empty host)",
        )
        NotorietyManager.add(game, 5, f"leak {server.ip}", player_action=True)
        from main import success
        success(f"Leaked {server.hostname} intel to flex board.")
        ChaosNewsManager.push(game, f"Manual leak from {server.ip} posted to flex board")
        MeltdownManager.on_leak(game, server, snippet)


class ChaosCommandManager:
    @staticmethod
    def cmd_chaos(game: Game, args: list[str]) -> None:
        from main import Console, divider, error, success, warn

        if not args:
            divider("CHAOS / MISCHIEF")
            for line in NotorietyManager.status_lines(game):
                Console.out(line)
            for line in MeltdownManager.status_lines(game):
                Console.out(line)
            Console.out("  Usage: chaos start | status | provoke | run | unlock")
            Console.out("          chaos leak | war <rivals|corps|brokers> | raid | strike [rival]")
            Console.out("          chaos deface | frame [rival] | news")
            Console.out("  Loud contracts pay +35%. Heat triggers raids. Infections can spread.")
            return

        action = args[0].lower()
        if action == "start":
            ChaosCareerManager.start(game)
            return
        if action == "status":
            divider("CHAOS STATUS")
            for line in NotorietyManager.status_lines(game):
                Console.out(line)
            for line in MeltdownManager.status_lines(game):
                Console.out(line)
            from depth_systems import RivalHeatManager
            for line in RivalHeatManager.status_lines(game):
                Console.out(line)
            from botnet_system import BotnetManager
            for line in BotnetManager.status_lines(game):
                Console.out(line)
            for line in ChaosNewsManager.status_lines(game):
                Console.out(line)
            return
        if action == "news":
            divider("CHAOS NEWS WIRE")
            for line in ChaosNewsManager.status_lines(game):
                Console.out(line)
            return
        if action == "leak":
            ChaosLeakManager.leak(game)
            return
        if action == "deface":
            ChaosDefaceManager.deface(game)
            return
        if action == "frame":
            ChaosFrameManager.frame(game, args[1] if len(args) > 1 else "")
            return
        if action == "war":
            FactionWarManager.start(game, args[1] if len(args) > 1 else "")
            return
        if action == "raid":
            GhostRaidManager.launch(game)
            return
        if action == "strike":
            ChaosStrikeManager.strike(game, args[1] if len(args) > 1 else "")
            return
        if action == "provoke":
            if game.player.phase not in ("career", "endless"):
                error("Career only.")
                return
            NotorietyManager.add(game, 6, "chaos provoke", player_action=True)
            warn("You poked the hornet nest on purpose.")
            game.threat._maybe_attack(force=True)
            from retention import RetentionManager
            rival = RetentionManager.pick_rival_attacker(game)
            provoke_lines = {
                "acid_k": "Provoke logged on corp wire. I'm billing NovaDyne for your IP.",
                "phantom_pkt": "You pinged me? I'm already halfway through your next contract.",
                "nyx_root": "Loud provoke. I ghost into boxes — you'll never see the breach coming.",
                "zero_cool": "You WANT heat? Chaos subnet is watching. Enjoy the raid.",
            }
            body = provoke_lines.get(rival, "Saw your provoke ping. Enjoy the probe.")
            CareerPressureManager.send_or_queue_rival_mail(
                game,
                f"{rival}@rival.net",
                "you asked for this",
                f"{body}\n\n— {rival}",
            )
            ChaosNewsManager.push(game, f"Operator provoked {rival} — localhost probe incoming")
            success("Rival provoked — check localhost defenses.")
            return
        if action == "run":
            if game.player.phase != "career":
                error("Need career mode. Try: chaos start")
                return
            from endless_mode import EndlessManager
            EndlessManager.start_run(game)
            success("Chaos Run started — roguelike floors. Die and retry.")
            return
        if action == "unlock":
            return  # handled in main.py cmd_chaos
        error("Usage: chaos [start|status|provoke|run|unlock|leak|deface|frame|war|raid|strike|news]")
