#!/usr/bin/env python3
"""Roguelike endless mode — procedural floors, permadeath runs, meta progression."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from main import Game, Mission, Player, Server

RELIC_DEFS: dict[str, dict[str, Any]] = {
    "ghost_chip": {
        "name": "Ghost Chip",
        "desc": "Trace chance -8% on disconnect",
    },
    "overclock": {
        "name": "Overclock Module",
        "desc": "Crack speed +20%",
    },
    "run_wallet": {
        "name": "Crypto Cache",
        "desc": "+$250 run wallet immediately",
    },
    "shield": {
        "name": "Firewall Seed",
        "desc": "+1 firewall level for this run",
    },
}

FLOOR_ARCHETYPES = ("exfil", "ghost", "root_heist")


@dataclass
class EndlessState:
    active: bool = False
    floor: int = 0
    score: int = 0
    run_money: int = 0
    best_floor: int = 0
    total_runs: int = 0
    deaths: int = 0
    relics: list[str] = field(default_factory=list)
    floor_hosts: list[str] = field(default_factory=list)
    floor_subnet: str = ""
    floor_mission_id: str = ""
    career_money: int = 0
    pending_relic_pick: bool = False
    relic_options: list[str] = field(default_factory=list)


class EndlessManager:
    @staticmethod
    def can_start(game: Game) -> bool:
        return game.player.phase == "career" and not game.endless.active

    @staticmethod
    def start_run(game: Game) -> bool:
        from main import Route, error, success, teach

        if game.endless.active:
            error("Already in an endless run. Type 'endless quit' to bail.")
            return False
        if game.player.phase != "career":
            error("Endless mode unlocks after career graduation.")
            return False
        if not game.player.is_local():
            error("Return to localhost before starting a run.")
            return False

        e = game.endless
        e.active = True
        e.floor = 1
        e.score = 0
        e.run_money = 450
        e.relics = []
        e.floor_hosts = []
        e.floor_subnet = ""
        e.floor_mission_id = ""
        e.career_money = game.player.money
        e.pending_relic_pick = False
        e.relic_options = []
        e.total_runs += 1
        game.player.phase = "endless"
        game.player.connection = "localhost"
        game.player.reset_session()

        EndlessManager._purge_floor_hosts(game)
        game.missions.missions = [
            m for m in game.missions.missions
            if not getattr(m, "endless_floor", False)
        ]
        EndlessManager._spawn_floor(game)

        success("ENDLESS RUN STARTED — Floor 1")
        teach(
            "Roguelike rules: run wallet only, permadeath on bankruptcy or breach. "
            "Clear the floor contract to descend. 'endless' for status."
        )
        game.mail.send(
            "ghost_broker@darknet",
            "Endless subnet unlocked",
            "Operator,\n\nYou dropped into the procedural abyss. Each floor spawns fresh hosts.\n"
            "Die broke or traced and the run ends — best floor is recorded.\n\n— ghost_broker",
        )
        from social_board import SocialBoardManager
        SocialBoardManager.on_endless_start(game)
        return True

    @staticmethod
    def quit_run(game: Game, *, voluntary: bool = True) -> None:
        from main import success, warn

        if not game.endless.active:
            warn("No active endless run.")
            return
        floor = game.endless.floor
        EndlessManager._end_run(game, reason="quit" if voluntary else "death")
        if voluntary:
            success(f"Bailed at floor {floor}. Career wallet restored.")
        game.player.money = game.endless.career_money

    @staticmethod
    def on_death(game: Game, reason: str) -> None:
        from main import warn

        if not game.endless.active:
            return
        floor = game.endless.floor
        game.endless.deaths += 1
        warn(f"RUN OVER — {reason} at floor {floor}")
        EndlessManager._end_run(game, reason=reason)
        bonus = min(400, floor * 35)
        if bonus:
            game.player.money = game.endless.career_money + bonus
            from main import success
            success(f"Meta reward: +${bonus} career cash for reaching floor {floor}")
        else:
            game.player.money = game.endless.career_money

    @staticmethod
    def _end_run(game: Game, reason: str) -> None:
        e = game.endless
        e.best_floor = max(e.best_floor, e.floor)
        e.score += e.floor * 100
        if e.floor >= 10:
            game.achievements.unlock("endless_floor_10")
        if e.floor >= 25:
            game.achievements.unlock("endless_floor_25")
        e.active = False
        e.floor = 0
        e.pending_relic_pick = False
        e.relic_options = []
        game.player.phase = "career"
        EndlessManager._purge_floor_hosts(game)
        game.missions.missions = [
            m for m in game.missions.missions if not getattr(m, "endless_floor", False)
        ]
        from social_board import SocialBoardManager
        SocialBoardManager.on_endless_end(game, reason)

    @staticmethod
    def _purge_floor_hosts(game: Game) -> None:
        for ip in list(game.endless.floor_hosts):
            game.network.servers.pop(ip, None)
        game.endless.floor_hosts = []
        game.endless.floor_subnet = ""

    @staticmethod
    def _spawn_floor(game: Game) -> None:
        from main import Mission, Route, Server, VirtualFile

        e = game.endless
        EndlessManager._purge_floor_hosts(game)

        floor = e.floor
        octet = 40 + (floor % 200)
        cidr = f"10.{octet}.0/24"
        e.floor_subnet = cidr
        gw = "192.168.1.1"
        if not any(r.destination == cidr for r in game.player.routes):
            game.player.routes.append(Route(cidr, gw))

        host_count = 2 + (floor // 5)
        sec_base = 2 + floor // 2
        archetype = FLOOR_ARCHETYPES[floor % len(FLOOR_ARCHETYPES)]
        boss_idx = host_count - 1

        for i in range(host_count):
            ip = f"10.{octet}.{10 + i}"
            sec = sec_base + (1 if i == boss_idx else 0)
            privesc = archetype == "root_heist" and i == boss_idx
            hostname = f"abyss-node-{floor}-{i}"
            pwd = random.choice(["abyss42!", "floor_key", "rng_pass", f"deep{floor}"])
            s = Server(
                ip, hostname, sec, subnet=cidr,
                ssh_user="ops", ssh_password=pwd,
                privesc_available=privesc,
                company="AbyssNet",
                story=f"Procedural floor {floor} host",
            )
            s.endless_only = True  # type: ignore[attr-defined]
            loot = f"/home/ops/floor_{floor}_loot.txt"
            s.files[loot] = VirtualFile(
                loot, f"Floor {floor} exfil payload — hash {random.randint(1000, 9999)}\n",
            )
            if privesc:
                root_file = f"/root/floor_{floor}_root.txt"
                s.files[root_file] = VirtualFile(
                    root_file, f"ROOT LOOT floor {floor}\n", owner="root",
                    mode="rw-------", requires_root=True,
                )
            game.network.servers[ip] = s
            e.floor_hosts.append(ip)
            game.player.discovered_ips.add(ip)

        boss_ip = e.floor_hosts[boss_idx]
        boss = game.network.servers[boss_ip]
        if archetype == "ghost":
            target_file = ""
            briefing = f"[FLOOR {floor}] Ghost the boss host {boss.hostname} ({boss_ip}) — zero traces."
            mtype = "ghost"
            req_priv = False
        elif archetype == "root_heist":
            target_file = f"/root/floor_{floor}_root.txt"
            briefing = f"[FLOOR {floor}] Root heist on {boss.hostname} — privesc, exfil, wipe."
            mtype = "root_heist"
            req_priv = True
        else:
            target_file = f"/home/ops/floor_{floor}_loot.txt"
            briefing = f"[FLOOR {floor}] Crack {boss.hostname}, exfil loot, wipe logs."
            mtype = "exfil"
            req_priv = False

        reward = 200 + floor * 80
        mid = f"endless-f{floor}"
        e.floor_mission_id = mid
        game.missions.missions.insert(
            0,
            Mission(
                mid, "nullbyte", briefing, boss_ip, target_file, reward,
                rep_reward=0, mission_type=mtype, require_privesc=req_priv,
                endless_floor=True, procedural=True,
            ),
        )

    @staticmethod
    def on_mission_complete(game: Game, mission: Mission) -> None:
        if not getattr(mission, "endless_floor", False) or not game.endless.active:
            return
        if game.endless.pending_relic_pick:
            return
        e = game.endless
        e.score += mission.reward + e.floor * 50
        e.run_money += 100 + e.floor * 25
        from main import success
        success(f"Floor {e.floor} cleared! Score {e.score}")
        if e.floor % 5 == 0:
            EndlessManager._offer_relic(game)
        else:
            e.floor += 1
            EndlessManager._spawn_floor(game)

    @staticmethod
    def _offer_relic(game: Game) -> None:
        from main import teach

        e = game.endless
        pool = [k for k in RELIC_DEFS if k not in e.relics]
        if not pool:
            e.floor += 1
            EndlessManager._spawn_floor(game)
            return
        e.pending_relic_pick = True
        e.relic_options = random.sample(pool, min(3, len(pool)))
        teach("Relic drop! Type: endless relic <name>")
        from main import divider, Console
        divider("RELIC DROP — pick one")
        for key in e.relic_options:
            rel = RELIC_DEFS[key]
            Console.out(f"  {key}: {rel['name']} — {rel['desc']}")

    @staticmethod
    def pick_relic(game: Game, key: str) -> bool:
        from main import error, success

        e = game.endless
        if not e.pending_relic_pick:
            error("No relic pick pending.")
            return False
        if key not in e.relic_options:
            error(f"Choose one of: {', '.join(e.relic_options)}")
            return False
        e.relics.append(key)
        e.pending_relic_pick = False
        e.relic_options = []
        rel = RELIC_DEFS[key]
        success(f"Relic acquired: {rel['name']}")
        if key == "run_wallet":
            e.run_money += 250
        if key == "shield":
            game.player.firewall_level = min(6, game.player.firewall_level + 1)
        e.floor += 1
        EndlessManager._spawn_floor(game)
        return True

    @staticmethod
    def trace_modifier(game: Game) -> float:
        if "ghost_chip" in game.endless.relics:
            return -0.08
        return 0.0

    @staticmethod
    def crack_bonus(game: Player) -> float:
        if hasattr(player, "_game_ref") and player._game_ref:
            if "overclock" in player._game_ref.endless.relics:
                return 0.20
        return 0.0

    @staticmethod
    def check_bankruptcy(game: Game) -> None:
        if game.endless.active and game.endless.run_money <= 0:
            EndlessManager.on_death(game, "bankruptcy")

    @staticmethod
    def status_lines(game: Game) -> list[str]:
        e = game.endless
        lines = [
            f"  Run active:   {'YES' if e.active else 'no'}",
            f"  Floor:        {e.floor}",
            f"  Run wallet:   ${e.run_money}",
            f"  Score:        {e.score}",
            f"  Best floor:   {e.best_floor}",
            f"  Total runs:   {e.total_runs}",
            f"  Relics:       {', '.join(e.relics) or 'none'}",
        ]
        if e.pending_relic_pick:
            lines.append(f"  RELIC PICK: endless relic <{'|'.join(e.relic_options)}>")
        return lines

    @staticmethod
    def run_wallet_label(game: Game) -> str:
        e = game.endless
        return f"Endless run — Floor {e.floor} | ${e.run_money} | Score {e.score}"
