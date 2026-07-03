#!/usr/bin/env python3
"""Rival personality helpers — territory, mail voice, race tension."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Game, Mission

from depth_systems import RIVAL_PROFILES, RivalHeatManager

RIVAL_RACE_GOAL = 28

RIVAL_BLOCK_MAIL: dict[str, list[tuple[str, str]]] = {
    "acid_k": [
        ("FW held — for now", "Corp IDS logged your block. I'm mapping your stack.\n\n— acid_k"),
        ("Nice patch", "Firewall stopped that probe. Won't stop the next one.\n\n— acid_k"),
    ],
    "phantom_pkt": [
        ("You blocked me", "Slows me down. Doesn't stop the clock on your contracts.\n\n— phantom_pkt"),
        ("Firewall luck", "I race contracts, not firewalls. You'll lose on time.\n\n— phantom_pkt"),
    ],
    "nyx_root": [
        ("Perimeter held", "I fingerprinted your rule set anyway. Ghost runs won't save you.\n\n— nyx_root"),
        ("Blocked", "Logged your egress pattern while I bounced off FW.\n\n— nyx_root"),
    ],
    "zero_cool": [
        ("Lol no", "Firewall ate that probe. Burn louder — I'll be back.\n\n— zero_cool"),
        ("Cute FW", "Block recorded. Chaos subnet remembers.\n\n— zero_cool"),
    ],
}

RIVAL_BREACH_MAIL: dict[str, list[tuple[str, str]]] = {
    "acid_k": [
        ("Corp bounty cashed", "NovaDyne paid for your egress IP. Wallet lighter, reputation stained.\n\n— acid_k"),
        ("You're in my segment", "Firewall L{fw} won't hold against corp-grade scans. Pay up.\n\n— acid_k"),
    ],
    "phantom_pkt": [
        ("Contract tax", "Consider this a fee for racing me on {subnet}. Too slow.\n\n— phantom_pkt"),
        ("Sniped your box", "While you were grinding contracts I drained ${loss}.\n\n— phantom_pkt"),
    ],
    "nyx_root": [
        ("Ghost broken", "Found your localhost. Traces don't lie — neither do I.\n\n— nyx_root"),
        ("Perimeter breach", "FW L{fw} is a suggestion. ${loss} gone.\n\n— nyx_root"),
    ],
    "zero_cool": [
        ("Burn", "Your box was wide open. Chaos tax: ${loss}.\n\n— zero_cool"),
        ("Loud and soft", "You make noise but FW L{fw} is paper. Enjoy the probe.\n\n— zero_cool"),
    ],
}

RIVAL_RACE_HALF_MAIL: dict[str, str] = {
    "acid_k": "I'm mapping {target} while you fumble logs. Halfway to sniping {mission_id}.",
    "phantom_pkt": "Clock's ticking on {mission_id}. I'm at 50% — you're behind.",
    "nyx_root": "Quiet operators don't win races. I'm halfway done with {target}.",
    "zero_cool": "Loud AND slow? I'm halfway through {mission_id}. Embarrassing.",
}

RIVAL_RACE_LATE_MAIL: dict[str, str] = {
    "acid_k": "Almost done with {mission_id}. Corp intel already routed.",
    "phantom_pkt": "75% on {mission_id}. You should abandon and take the L.",
    "nyx_root": "Three-quarters through {target}. Your window is closing.",
    "zero_cool": "One more push and {mission_id} is mine. Hurry up or don't.",
}

RIVAL_RACE_WIN_MAIL: dict[str, str] = {
    "acid_k": "Contract {mission_id} is mine. Corp thanks you for the warmup.",
    "phantom_pkt": "Sniped {mission_id} before you finished. Speed kills.",
    "nyx_root": "Ghosted through {target} and closed {mission_id} first.",
    "zero_cool": "Too slow on {mission_id}. Chaos subnet pays winners.",
}


class RivalAIManager:
    @staticmethod
    def rival_for_subnet(cidr: str) -> str:
        for rival, prof in RIVAL_PROFILES.items():
            if prof["subnet"] == cidr:
                return rival
        return random.choice(list(RIVAL_PROFILES.keys()))

    @staticmethod
    def context_subnet(game: Game) -> str:
        p = game.player
        if not p.is_local() and p.connection:
            server = game.network.get_server(p.connection)
            if server:
                return server.subnet
            return RivalHeatManager.subnet_for_ip(p.connection)
        for m in game.missions.missions:
            if not m.completed and m.target_ip:
                return RivalHeatManager.subnet_for_ip(m.target_ip)
        hottest = max(
            ("192.168.1.0/24", "10.0.0.0/24", "172.16.0.0/24", "203.0.113.0/24"),
            key=lambda c: game.meta.subnet_heat.get(c, 0),
            default="192.168.1.0/24",
        )
        if game.meta.subnet_heat.get(hottest, 0) > 0:
            return hottest
        return "192.168.1.0/24"

    @staticmethod
    def pick_rival(game: Game, *, prefer_last: bool = True) -> str:
        r = game.retention
        subnet = RivalAIManager.context_subnet(game)
        weights: dict[str, float] = {}
        for rival, prof in RIVAL_PROFILES.items():
            w = 1.0
            if prof["subnet"] == subnet:
                w += 3.5
            if prefer_last and r.last_rival == rival:
                w += 2.0
            if game.meta.notoriety > 30 and rival == "zero_cool":
                w += 1.5
            weights[rival] = w
        rivals = list(weights.keys())
        total = sum(weights.values())
        roll = random.random() * total
        acc = 0.0
        for rival in rivals:
            acc += weights[rival]
            if roll <= acc:
                return rival
        return rivals[-1]

    @staticmethod
    def assign_race_rival(game: Game, mission: Mission) -> str:
        cidr = RivalHeatManager.subnet_for_ip(mission.target_ip)
        rival = RivalAIManager.rival_for_subnet(cidr)
        game.meta.rival_race_rival[mission.mission_id] = rival
        game.meta.rival_race_prog[mission.mission_id] = 0
        game.meta.rival_race_warned[mission.mission_id] = []
        return rival

    @staticmethod
    def race_progress_line(game: Game, mission: Mission) -> str:
        if "rival_race" not in getattr(mission, "modifiers", []):
            return ""
        if mission.completed:
            return ""
        prog = game.meta.rival_race_prog.get(mission.mission_id, 0)
        rival = game.meta.rival_race_rival.get(mission.mission_id, "?")
        return f" [RACE: {rival} {prog}/{RIVAL_RACE_GOAL}]"

    @staticmethod
    def on_race_tick(game: Game, mission: Mission) -> None:
        from main import warn

        rid = mission.mission_id
        prog = game.meta.rival_race_prog.get(rid, 0)
        rival = game.meta.rival_race_rival.get(rid, RivalAIManager.rival_for_subnet(
            RivalHeatManager.subnet_for_ip(mission.target_ip),
        ))
        warned: list[str] = game.meta.rival_race_warned.setdefault(rid, [])
        target = mission.target_ip or "target"

        if prog >= RIVAL_RACE_GOAL:
            mission.completed = True
            warn(f"{rival} SNIPED {rid} — contract lost to rival race.")
            body = RIVAL_RACE_WIN_MAIL.get(rival, RIVAL_RACE_WIN_MAIL["phantom_pkt"]).format(
                mission_id=rid, target=target,
            )
            from chaos_system import CareerPressureManager
            CareerPressureManager.send_or_queue_rival_mail(
                game, f"{rival}@rival.net", f"sniped — {rid}", f"{body}\n\n— {rival}",
            )
            game.retention.last_rival = rival
            game.retention.rival_aggression = min(10, game.retention.rival_aggression + 1)
            game.meta.rival_race_prog.pop(rid, None)
            game.meta.rival_race_rival.pop(rid, None)
            game.meta.rival_race_warned.pop(rid, None)
            return

        if prog >= 21 and "late" not in warned:
            warned.append("late")
            warn(f"{rival} at 75% on {rid} — finish NOW or lose the contract.")
            body = RIVAL_RACE_LATE_MAIL.get(rival, RIVAL_RACE_LATE_MAIL["phantom_pkt"]).format(
                mission_id=rid, target=target,
            )
            from chaos_system import CareerPressureManager
            CareerPressureManager.send_or_queue_rival_mail(
                game, f"{rival}@rival.net", f"almost got {rid}", f"{body}\n\n— {rival}",
            )
        elif prog >= 14 and "half" not in warned:
            warned.append("half")
            warn(f"{rival} at 50% on {rid} — rival race heating up.")
            body = RIVAL_RACE_HALF_MAIL.get(rival, RIVAL_RACE_HALF_MAIL["phantom_pkt"]).format(
                mission_id=rid, target=target,
            )
            from chaos_system import CareerPressureManager
            CareerPressureManager.send_or_queue_rival_mail(
                game, f"{rival}@rival.net", f"racing you — {rid}", f"{body}\n\n— {rival}",
            )

    @staticmethod
    def send_block_taunt(game: Game, rival: str, fw: int) -> None:
        from chaos_system import CareerPressureManager
        if not CareerPressureManager.can_trash_talk(game):
            return
        if random.random() > 0.38:
            return
        pool = RIVAL_BLOCK_MAIL.get(rival, RIVAL_BLOCK_MAIL["nyx_root"])
        subject, body = random.choice(pool)
        game.mail.send(f"{rival}@rival.net", subject, body)

    @staticmethod
    def send_breach_mail(game: Game, rival: str, fw: int, loss: int) -> None:
        from chaos_system import CareerPressureManager
        if not CareerPressureManager.can_trash_talk(game):
            return
        subnet = RivalAIManager.context_subnet(game)
        pool = RIVAL_BREACH_MAIL.get(rival, RIVAL_BREACH_MAIL["nyx_root"])
        subject, body = random.choice(pool)
        body = body.format(fw=fw, loss=loss, subnet=subnet)
        game.mail.send(f"{rival}@rival.net", subject, body)

    @staticmethod
    def dossier_extra_lines(game: Game) -> list[str]:
        lines: list[str] = []
        active_races = [
            m for m in game.missions.missions
            if not m.completed and "rival_race" in getattr(m, "modifiers", [])
        ]
        if active_races:
            lines.append("  Active rival races:")
            for m in active_races:
                prog = game.meta.rival_race_prog.get(m.mission_id, 0)
                rival = game.meta.rival_race_rival.get(m.mission_id, "?")
                lines.append(f"    {rival} {prog}/{RIVAL_RACE_GOAL} on {m.mission_id}")
        if game.retention.last_rival:
            prof = RIVAL_PROFILES.get(game.retention.last_rival, {})
            lines.append(
                f"  Territory focus: {game.retention.last_rival} "
                f"({prof.get('label', 'rival')}) — {prof.get('subnet', '?')}",
            )
        return lines

    @staticmethod
    def should_react_in_career(game: Game) -> bool:
        from chaos_system import CareerPressureManager
        if CareerPressureManager.rookie_grace(game):
            return False
        if game.meta.chaos_mode:
            return True
        if game.meta.notoriety > 0:
            return True
        if sum(game.meta.subnet_heat.values()) >= 3:
            return True
        if game.retention.rival_aggression >= 2:
            return True
        return False
