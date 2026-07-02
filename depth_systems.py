#!/usr/bin/env python3
"""Depth systems: contract modifiers, tools, rival heat, specs, weekly heists."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from main import Game, Mission, Player, Server

# ---------------------------------------------------------------------------
# 1. Contract modifiers
# ---------------------------------------------------------------------------

MODIFIERS: dict[str, dict[str, Any]] = {
    "air_gapped": {
        "label": "Air-gapped",
        "desc": "No curl — intel only on-host.",
        "payout": 1.2,
    },
    "honey_net": {
        "label": "Honey-net",
        "desc": "Decoy exfil triggers rival probe.",
        "payout": 1.35,
    },
    "split_tunnel": {
        "label": "Split-tunnel",
        "desc": "VPN required for payment.",
        "payout": 1.25,
    },
    "deadline": {
        "label": "Deadline",
        "desc": "Complete within command window.",
        "payout": 1.3,
    },
    "no_shop": {
        "label": "No-shop",
        "desc": "Shop locked until contract done.",
        "payout": 1.15,
    },
    "rival_race": {
        "label": "Rival-race",
        "desc": "Rival NPC races you — finish first.",
        "payout": 1.5,
    },
}

SUBNETS = ("192.168.1.0/24", "10.0.0.0/24", "172.16.0.0/24", "203.0.113.0/24")

RIVAL_PROFILES: dict[str, dict[str, Any]] = {
    "acid_k": {"subnet": "10.0.0.0/24", "heat_mult": 1.5, "label": "corp hunter"},
    "phantom_pkt": {"subnet": "172.16.0.0/24", "heat_mult": 1.4, "label": "finance shark"},
    "nyx_root": {"subnet": "192.168.1.0/24", "heat_mult": 1.2, "label": "perimeter stalker"},
    "zero_cool": {"subnet": "203.0.113.0/24", "heat_mult": 1.6, "label": "chaos enforcer"},
}

SPECIALIZATIONS: dict[str, dict[str, Any]] = {
    "ghost": {
        "name": "Ghost",
        "desc": "Mastery grades score +10 — favor clean runs.",
        "payout_mult": 1.0,
        "grade_bonus": 10,
    },
    "broker": {
        "name": "Broker",
        "desc": "+15% contract payouts.",
        "payout_mult": 1.15,
        "grade_bonus": 0,
    },
    "saboteur": {
        "name": "Saboteur",
        "desc": "Completing contracts spikes rival heat on contested subnets.",
        "payout_mult": 1.05,
        "heat_spike": 3,
    },
    "architect": {
        "name": "Architect",
        "desc": "+30% rep from defense blocks.",
        "payout_mult": 1.0,
        "defense_rep_mult": 1.3,
    },
}

WEEKLY_HEISTS: list[dict[str, Any]] = [
    {
        "id": "heist-helix",
        "name": "Helix Wire Heist",
        "broker": "shade_runner",
        "parts": [
            {
                "step": 1,
                "briefing": "HEIST P1: Probe fin-trading (172.16.0.20) — map the trading floor.",
                "target_ip": "172.16.0.20",
                "mission_type": "recon",
                "reward": 400,
                "rep_reward": 50,
            },
            {
                "step": 2,
                "branch": {
                    "steal": {
                        "briefing": "HEIST P2 [STEAL]: Exfil algo_config.yml from fin-trading, wipe logs.",
                        "target_ip": "172.16.0.20",
                        "target_file": "/home/admin/algo_config.yml",
                        "mission_type": "exfil",
                    },
                    "sabotage": {
                        "briefing": "HEIST P2 [SABOTAGE]: Ghost-run fin-trading — zero traces, no loot.",
                        "target_ip": "172.16.0.20",
                        "target_file": "",
                        "mission_type": "ghost",
                    },
                    "frame": {
                        "briefing": "HEIST P2 [FRAME]: Plant decoy on bank-core path — crack 172.16.0.33, exfil wire_keys.env.",
                        "target_ip": "172.16.0.33",
                        "target_file": "/root/wire_keys.env",
                        "mission_type": "root_heist",
                        "require_privesc": True,
                    },
                },
                "reward": 900,
                "rep_reward": 80,
            },
            {
                "step": 3,
                "briefing": "HEIST P3: Exfil bank-core proof-of-access — finish the legend.",
                "target_ip": "172.16.0.33",
                "target_file": "/root/wire_keys.env",
                "mission_type": "root_heist",
                "require_privesc": True,
                "reward": 2000,
                "rep_reward": 150,
            },
        ],
    },
    {
        "id": "heist-nova",
        "name": "Nova Shadow Raid",
        "broker": "ghost_broker",
        "parts": [
            {
                "step": 1,
                "briefing": "HEIST P1: Scan 10.0.0.0/24 — locate corp-dc and hr-portal.",
                "target_ip": "10.0.0.0/24",
                "mission_type": "scan_subnet",
                "reward": 350,
                "rep_reward": 45,
            },
            {
                "step": 2,
                "branch": {
                    "dc": {
                        "briefing": "HEIST P2 [DC]: Hit corp-dc — exfil corporate_secrets.txt clean.",
                        "target_ip": "10.0.0.42",
                        "target_file": "/home/admin/corporate_secrets.txt",
                        "mission_type": "exfil",
                    },
                    "hr": {
                        "briefing": "HEIST P2 [HR]: Spearphish hr-portal — read intel, exfil terminations.csv.",
                        "target_ip": "10.0.0.88",
                        "target_file": "/home/admin/terminations.csv",
                        "mission_type": "social",
                    },
                    "vault": {
                        "briefing": "HEIST P2 [VAULT]: Root heist vault-server payroll.csv.",
                        "target_ip": "10.0.0.55",
                        "target_file": "/root/payroll.csv",
                        "mission_type": "root_heist",
                        "require_privesc": True,
                    },
                },
                "reward": 1100,
                "rep_reward": 100,
            },
            {
                "step": 3,
                "briefing": "HEIST P3: Ghost egress from NovaDyne segment — zero traces on last host.",
                "target_ip": "10.0.0.42",
                "target_file": "",
                "mission_type": "ghost",
                "reward": 1800,
                "rep_reward": 130,
            },
        ],
    },
]


@dataclass
class MetaState:
    specialization: str = ""
    spec_unlock_pending: bool = False
    backdoors: set[str] = field(default_factory=set)
    forged_servers: set[str] = field(default_factory=set)
    phished_ips: set[str] = field(default_factory=set)
    tunnels: dict[int, tuple[str, int]] = field(default_factory=dict)
    subnet_heat: dict[str, int] = field(default_factory=dict)
    rival_race_prog: dict[str, int] = field(default_factory=dict)
    weekly_heist_id: str = ""
    weekly_heist_step: int = 0
    weekly_heist_week: str = ""
    weekly_heist_done: bool = False
    heist_branch: str = ""
    heist_score: int = 0
    heists_cleared: int = 0
    heists_first_cleared: set[str] = field(default_factory=set)
    heist_clear_counts: dict[str, int] = field(default_factory=dict)
    heist_branches_cleared: dict[str, set[str]] = field(default_factory=dict)
    heist_month_key: str = ""
    heist_rotation_key: str = ""
    inventory: dict[str, int] = field(default_factory=dict)
    infections: dict[str, str] = field(default_factory=dict)
    botnet_bank: int = 0
    ddos_targets: dict[str, int] = field(default_factory=dict)
    botnet_purges: int = 0
    burner_commands_left: int = 0
    burner_mask_ip: str = ""
    decoy_trace_immunity: int = 0
    faction_rep: dict[str, int] = field(
        default_factory=lambda: {"brokers": 0, "rivals": 0, "corps": 0},
    )
    faction_perks_unlocked: set[str] = field(default_factory=set)
    contracts_since_free_consumable: int = 0
    consumables_used: int = 0
    notoriety: int = 0
    chaos_mode: bool = False
    chaos_flags: set[str] = field(default_factory=set)
    chaos_headlines: list[str] = field(default_factory=list)
    meltdown: dict[str, Any] = field(default_factory=dict)
    ghost_raid_cd: int = 0
    faction_war_cd: int = 0


class ModifierManager:
    @staticmethod
    def roll(count: int = 2) -> list[str]:
        pool = list(MODIFIERS.keys())
        n = min(count, len(pool))
        return random.sample(pool, k=random.randint(1, n))

    @staticmethod
    def apply_to_mission(mission: Mission, game: Game) -> None:
        if getattr(mission, "weekly_bounty", False) or getattr(mission, "heist_id", ""):
            return
        if random.random() > 0.55 and not getattr(mission, "procedural", False):
            return
        mods = ModifierManager.roll(2)
        mission.modifiers = mods
        tags = ", ".join(MODIFIERS[m]["label"] for m in mods)
        mission.briefing += f" [MODS: {tags}]"
        if "deadline" in mods and not mission.timing_limit_ticks:
            mission.timing_limit_ticks = random.randint(14, 24)
            mission.timing_start_tick = game.player.ticks
        if "rival_race" in mods:
            game.meta.rival_race_prog[mission.mission_id] = 0

    @staticmethod
    def payout_mult(mission: Mission, game: Game) -> float:
        mult = 1.0
        for m in getattr(mission, "modifiers", []):
            mult *= MODIFIERS.get(m, {}).get("payout", 1.0)
        spec = game.meta.specialization
        if spec:
            mult *= SPECIALIZATIONS.get(spec, {}).get("payout_mult", 1.0)
        return mult

    @staticmethod
    def blocks_curl(game: Game, ip: str) -> bool:
        for m in game.missions.missions:
            if m.completed or ip != m.target_ip:
                continue
            if "air_gapped" in getattr(m, "modifiers", []):
                return True
        return False

    @staticmethod
    def shop_blocked(game: Game) -> bool:
        for m in game.missions.missions:
            if not m.completed and "no_shop" in getattr(m, "modifiers", []):
                return True
        return False

    @staticmethod
    def requires_vpn(mission: Mission) -> bool:
        return "split_tunnel" in getattr(mission, "modifiers", [])

    @staticmethod
    def on_post_command(game: Game) -> None:
        from main import warn

        for m in game.missions.missions:
            if m.completed or "rival_race" not in getattr(m, "modifiers", []):
                continue
            rid = m.mission_id
            from faction_consumables import FactionRepManager
            step = random.randint(1, 3)
            step = max(1, int(step * FactionRepManager.rival_race_slow_mult(game)))
            game.meta.rival_race_prog[rid] = game.meta.rival_race_prog.get(rid, 0) + step
            from botnet_system import BotnetManager
            if BotnetManager.rival_race_slow(game, m.target_ip):
                game.meta.rival_race_prog[rid] = max(0, game.meta.rival_race_prog[rid] - 1)
            if game.meta.rival_race_prog[rid] >= 28:
                m.completed = True
                warn(f"RIVAL WON RACE: {m.broker} contract sniped before you finished.")
                game.meta.rival_race_prog.pop(rid, None)

    @staticmethod
    def on_decoy_download(game: Game, server: Server, path: str) -> None:
        if "/tmp/decoy" in path or "decoy" in path.rsplit("/", 1)[-1]:
            for m in game.missions.missions:
                if m.completed or m.target_ip != server.ip:
                    continue
                if "honey_net" in getattr(m, "modifiers", []):
                    from faction_consumables import FactionRepManager
                    if FactionRepManager.honey_net_immunity(game):
                        from main import teach
                        teach("Corp faction perk: honey-net decoy ignored.")
                        return
                    RivalHeatManager.spike(game, server.subnet, 4)
                    game.threat._maybe_attack(force=True)
                    from main import warn
                    warn("HONEY-NET: decoy triggered IDS — rival alerted!")


class ToolManager:
    @staticmethod
    def cmd_phish(game: Game, ip: str) -> None:
        from main import Console, divider, error, success, teach

        if game.player.phase not in ("career", "endless"):
            error("Career mode only.")
            return
        if ip not in game.player.discovered_ips:
            error("Unknown host — scan first.")
            return
        server = game.network.get_server(ip)
        if not server:
            error("Invalid target.")
            return
        divider(f"PHISH {ip}")
        Console.out(f"  Crafting lure targeting {server.hostname}...")
        game.meta.phished_ips.add(ip)
        success(f"Spearphish deployed against {ip} — password intel likely in inbox/logs.")
        teach("Crack may succeed faster. Some contracts count this as social intel.")
        game.player.tutorial_flags.add("daily_phish_done")

    @staticmethod
    def cmd_tunnel(game: Game, args: list[str]) -> None:
        from main import error, success, teach

        if len(args) < 3:
            error("Usage: tunnel <local_port> <remote_ip> <remote_port>")
            return
        try:
            lport = int(args[0])
            rip = args[1]
            rport = int(args[2])
        except ValueError:
            error("Usage: tunnel <local_port> <remote_ip> <remote_port>")
            return
        if rip not in game.player.discovered_ips:
            error("Remote host unknown — scan first.")
            return
        if not game.player.has_route_to(rip):
            error(f"No route to {rip}.")
            return
        game.meta.tunnels[lport] = (rip, rport)
        success(f"Tunnel localhost:{lport} → {rip}:{rport}")
        teach("connect localhost <local_port> to traverse the tunnel.")

    @staticmethod
    def resolve_connect(game: Game, ip: str, port: int) -> tuple[str, int]:
        if ip in ("localhost", "127.0.0.1") and port in game.meta.tunnels:
            rip, rport = game.meta.tunnels[port]
            return rip, rport
        return ip, port

    @staticmethod
    def cmd_plant(game: Game) -> None:
        from main import error, success, teach

        s = game.remote_server() if hasattr(game, "remote_server") else None
        if not s or not game.player.has_remote_shell:
            error("Need active shell on target.")
            return
        game.meta.backdoors.add(s.ip)
        success(f"Backdoor planted on {s.ip} — future cracks skip brute-force.")
        teach("Rivals may find backdoors if heat rises on this subnet.")

    @staticmethod
    def cmd_forge(game: Game) -> None:
        from main import error, success, teach

        s = game.remote_server() if hasattr(game, "remote_server") else None
        if not s or not game.player.has_remote_shell:
            error("Need active shell on target.")
            return
        game.meta.forged_servers.add(s.ip)
        success(f"Forged log entries on {s.ip} — traces obscured (not perfect).")
        teach("Forged logs pass most checks but mastery grade may suffer.")

    @staticmethod
    def has_backdoor(game: Game, ip: str) -> bool:
        return ip in game.meta.backdoors

    @staticmethod
    def logs_clean_enough(game: Game, server: Server, player: Player) -> bool:
        from faction_consumables import ConsumableManager
        if ConsumableManager.logs_clean_enough(game):
            return True
        if server.ip in game.meta.forged_servers:
            return True
        return not server.player_left_traces(player)


class RivalHeatManager:
    @staticmethod
    def subnet_for_ip(ip: str) -> str:
        from main import ip_in_subnet
        for cidr in SUBNETS:
            if ip_in_subnet(ip, cidr):
                return cidr
        return "192.168.1.0/24"

    @staticmethod
    def heat(game: Game, cidr: str) -> int:
        return game.meta.subnet_heat.get(cidr, 0)

    @staticmethod
    def spike(game: Game, cidr: str, amount: int) -> None:
        game.meta.subnet_heat[cidr] = min(10, game.meta.subnet_heat.get(cidr, 0) + amount)

    @staticmethod
    def decay_on_login(game: Game) -> None:
        for cidr in list(game.meta.subnet_heat.keys()):
            game.meta.subnet_heat[cidr] = max(0, game.meta.subnet_heat[cidr] - 1)

    @staticmethod
    def trace_bonus(game: Game, server: Server) -> float:
        cidr = server.subnet if server.subnet in SUBNETS else RivalHeatManager.subnet_for_ip(server.ip)
        return game.meta.subnet_heat.get(cidr, 0) * 0.04

    @staticmethod
    def threat_bonus(game: Game) -> float:
        return sum(game.meta.subnet_heat.values()) * 0.015

    @staticmethod
    def on_contract_complete(game: Game, mission: Mission) -> None:
        cidr = RivalHeatManager.subnet_for_ip(mission.target_ip)
        RivalHeatManager.spike(game, cidr, 1)
        spec = game.meta.specialization
        if spec == "saboteur":
            RivalHeatManager.spike(game, cidr, SPECIALIZATIONS["saboteur"].get("heat_spike", 3))
        for rival, prof in RIVAL_PROFILES.items():
            if prof["subnet"] == cidr and game.meta.subnet_heat.get(cidr, 0) >= 4:
                game.retention.rival_aggression = min(10, game.retention.rival_aggression + 1)
                game.retention.last_rival = rival
                game.mail.send(
                    f"{rival}@rival.net",
                    f"Heat on {cidr}",
                    f"You are lighting up {prof['label']} territory.\n\n— {rival}",
                )
                break

    @staticmethod
    def pick_attacker(game: Game) -> str:
        hottest = max(SUBNETS, key=lambda c: game.meta.subnet_heat.get(c, 0))
        if game.meta.subnet_heat.get(hottest, 0) >= 3:
            for rival, prof in RIVAL_PROFILES.items():
                if prof["subnet"] == hottest:
                    return rival
        from retention import RetentionManager
        return RetentionManager.pick_rival_attacker(game)

    @staticmethod
    def status_lines(game: Game) -> list[str]:
        lines = ["  Subnet heat (0-10):"]
        for cidr in SUBNETS:
            h = game.meta.subnet_heat.get(cidr, 0)
            bar = "#" * h + "." * (10 - h)
            lines.append(f"    {cidr:<18} [{bar}] {h}")
        if game.retention.last_rival:
            lines.append(f"  Angriest rival: {game.retention.last_rival}")
        return lines


class SpecializationManager:
    @staticmethod
    def on_rank_up(game: Game, rank_index: int) -> None:
        if rank_index in (1, 3) and not game.meta.specialization:
            game.meta.spec_unlock_pending = True
            game.mail.send(
                "ghost_broker@darknet",
                "SPECIALIZATION unlocked",
                "Pick your lane: spec pick ghost|broker|saboteur|architect\n"
                "Respec later: spec respec (500 rep)",
            )

    @staticmethod
    def pick(game: Game, key: str) -> bool:
        from main import error, success

        if key not in SPECIALIZATIONS:
            error(f"Unknown spec. Choose: {', '.join(SPECIALIZATIONS)}")
            return False
        game.meta.specialization = key
        game.meta.spec_unlock_pending = False
        success(f"Specialization: {SPECIALIZATIONS[key]['name']} — {SPECIALIZATIONS[key]['desc']}")
        return True

    @staticmethod
    def respec(game: Game) -> bool:
        from main import error, success

        if game.player.reputation < 500:
            error("Respec costs 500 rep.")
            return False
        game.player.reputation -= 500
        game.meta.specialization = ""
        game.meta.spec_unlock_pending = True
        success("Specialization cleared — pick again with spec pick <lane>")
        return True

    @staticmethod
    def grade_bonus(game: Game) -> int:
        spec = game.meta.specialization
        return SPECIALIZATIONS.get(spec, {}).get("grade_bonus", 0)

    @staticmethod
    def defense_rep_mult(game: Game) -> float:
        spec = game.meta.specialization
        return SPECIALIZATIONS.get(spec, {}).get("defense_rep_mult", 1.0)


class WeeklyHeistManager:
    @staticmethod
    def week_key() -> str:
        from retention import RetentionManager
        return RetentionManager.week_key()

    @staticmethod
    def refresh(game: Game) -> None:
        from main import Mission

        if game.player.phase != "career":
            return
        wk = WeeklyHeistManager.week_key()
        from longevity_content import HeistRotationManager, heist_branch_choices, all_weekly_heists
        rot_key = HeistRotationManager.rotation_key()
        if game.meta.heist_rotation_key == rot_key:
            return
        game.meta.heist_rotation_key = rot_key
        game.meta.weekly_heist_week = wk
        game.meta.weekly_heist_done = False
        game.meta.weekly_heist_step = 0
        game.meta.heist_branch = ""
        game.missions.missions = [m for m in game.missions.missions if not getattr(m, "heist_id", "")]
        from longevity_content import HeistRotationManager, heist_branch_choices, all_weekly_heists
        heist = HeistRotationManager.current_heist()
        game.meta.heist_month_key = HeistRotationManager.month_key()
        game.meta.weekly_heist_id = heist["id"]
        part = heist["parts"][0]
        mid = f"{heist['id']}-s1"
        heist_mods = list(heist.get("modifiers", ["deadline"]))
        m = Mission(
            mid, heist["broker"], part["briefing"],
            part.get("target_ip", ""), part.get("target_file", ""),
            part.get("reward", 500), rep_reward=part.get("rep_reward", 60),
            mission_type=part.get("mission_type", "exfil"),
            require_privesc=part.get("require_privesc", False),
            heist_id=heist["id"], heist_step=1, weekly_bounty=True,
            modifiers=heist_mods,
        )
        if "deadline" in heist_mods and not m.timing_limit_ticks:
            m.timing_limit_ticks = 30
            m.timing_start_tick = game.player.ticks
        if "rival_race" in heist_mods:
            game.meta.rival_race_prog[mid] = 0
        game.missions.missions.insert(0, m)
        game.mail.send(
            f"{heist['broker']}@darknet",
            f"WEEKLY HEIST: {heist['name']}",
            f"{part['briefing']}\n\nType 'heist' for status. Phase 2 offers a branch choice.\n\n— {heist['broker']}",
        )

    @staticmethod
    def on_step_complete(game: Game, mission: Mission) -> None:
        from main import Mission, success
        from longevity_content import all_weekly_heists, heist_branch_choices

        hid = getattr(mission, "heist_id", "")
        if not hid:
            return
        heist = next((h for h in all_weekly_heists() if h["id"] == hid), None)
        if not heist:
            return
        step = getattr(mission, "heist_step", 0)
        game.meta.heist_score += mission.reward // 10

        if step == 1:
            game.meta.weekly_heist_step = 2
            part = heist["parts"][1]
            game.mail.send(
                f"{heist['broker']}@darknet",
                f"HEIST branch — {heist['name']}",
                f"Choose path:\n{heist_branch_choices(heist)}\n",
            )
            success("Heist phase 1 done — type 'heist choose <branch>'")
            return

        if step == 2 and not game.meta.heist_branch:
            return

        if step == 2:
            game.meta.weekly_heist_step = 3
            part = heist["parts"][2]
            mid = f"{hid}-s3"
            m = Mission(
                mid, heist["broker"], part["briefing"],
                part.get("target_ip", ""), part.get("target_file", ""),
                part.get("reward", 1500), rep_reward=part.get("rep_reward", 100),
                mission_type=part.get("mission_type", "exfil"),
                require_privesc=part.get("require_privesc", False),
                heist_id=hid, heist_step=3, weekly_bounty=True,
            )
            game.missions.missions.insert(0, m)
            game.mail.send(f"{heist['broker']}@darknet", f"HEIST final phase", part["briefing"])
            return

        if step >= 3:
            game.meta.weekly_heist_done = True
            game.meta.heists_cleared += 1
            from longevity_content import HeistRewardManager
            bonus, tag = HeistRewardManager.on_complete(game, hid, game.meta.heist_branch)
            from retention import RetentionManager
            RetentionManager.add_season_xp(game, 200, "weekly heist")
            success(f"WEEKLY HEIST COMPLETE — bonus ${bonus} ({tag})")

    @staticmethod
    def choose_branch(game: Game, branch: str) -> bool:
        from main import Mission, error, success
        from longevity_content import all_weekly_heists

        hid = game.meta.weekly_heist_id
        if game.meta.weekly_heist_step != 2 or game.meta.heist_branch:
            error("No heist branch choice pending.")
            return False
        heist = next((h for h in all_weekly_heists() if h["id"] == hid), None)
        if not heist:
            return False
        part = heist["parts"][1]
        branch_opts = part.get("branch", {})
        if branch not in branch_opts:
            error(f"Choose: {', '.join(branch_opts.keys())}")
            return False
        spec = branch_opts[branch]
        game.meta.heist_branch = branch
        mid = f"{hid}-s2-{branch}"
        m = Mission(
            mid, heist["broker"], spec["briefing"],
            spec.get("target_ip", ""), spec.get("target_file", ""),
            part.get("reward", 800), rep_reward=part.get("rep_reward", 70),
            mission_type=spec.get("mission_type", "exfil"),
            require_privesc=spec.get("require_privesc", False),
            heist_id=hid, heist_step=2, weekly_bounty=True,
        )
        game.missions.missions.insert(0, m)
        success(f"Heist branch: {branch}")
        return True

    @staticmethod
    def status_lines(game: Game) -> list[str]:
        from longevity_content import HeistRotationManager, all_weekly_heists

        hid = game.meta.weekly_heist_id
        heist = next((h for h in all_weekly_heists() if h["id"] == hid), None)
        name = heist["name"] if heist else "—"
        lines = [
            f"  Heist:     {name}",
            f"  Phase:     {game.meta.weekly_heist_step}/3",
            f"  Branch:    {game.meta.heist_branch or '—'}",
            f"  Done:      {'yes' if game.meta.weekly_heist_done else 'no'}",
            f"  Score:     {game.meta.heist_score}",
        ]
        lines.extend(HeistRotationManager.pool_status_lines(game))
        return lines
