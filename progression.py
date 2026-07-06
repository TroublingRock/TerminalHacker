#!/usr/bin/env python3
"""Meta-progression: ranks, saves, procedural missions, achievements, chaos, blue-team."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from main import Game, Player, Server

SAVE_PATH = Path.home() / ".terminalhacker" / "save.json"
BACKUP_PATH = SAVE_PATH.with_suffix(".json.bak")
PROFILE_PATH = Path.home() / ".terminalhacker" / "profile.json"


class PlayerProfile:
    """Persistent flags across new games — returning player detection."""

    @staticmethod
    def _read() -> dict:
        if not PROFILE_PATH.exists():
            return {}
        try:
            return json.loads(PROFILE_PATH.read_text())
        except (OSError, json.JSONDecodeError):
            return {}

    @staticmethod
    def is_veteran() -> bool:
        return bool(PlayerProfile._read().get("veteran"))

    @staticmethod
    def mark_veteran() -> None:
        data = PlayerProfile._read()
        if data.get("veteran"):
            return
        data["veteran"] = True
        PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            PROFILE_PATH.write_text(json.dumps(data, indent=2))
        except OSError:
            pass

    @staticmethod
    def suggest_chaos_on_career_load() -> bool:
        data = PlayerProfile._read()
        if data.get("chaos_cta_shown"):
            return False
        return PlayerProfile.is_veteran()

# ---------------------------------------------------------------------------
# Ranks & subnet unlocks
# ---------------------------------------------------------------------------

@dataclass
class Rank:
    name: str
    rep_required: int
    routes: list[tuple[str, str]]
    flavor: str


RANKS: list[Rank] = [
    Rank("Script Kiddie", 0, [], "Learning the ropes on the lab subnet."),
    Rank("Packet Runner", 150, [("10.0.0.0/24", "192.168.1.1")],
         "Cleared for corporate DMZ — 10.0.0.0/24."),
    Rank("Shell Operator", 400, [("172.16.0.0/24", "10.0.0.1")],
         "Finance sector subnet unlocked — 172.16.0.0/24."),
    Rank("Ghost in the Wires", 750, [("203.0.113.0/24", "172.16.0.8")],
         "Darknet edge reachable. Chaos targets await the reckless."),
    Rank("Net God", 1200, [], "Legend status. Chaos mode fully unlocked."),
]

CHAOS_REP = 750
CHAOS_CPU = 4
CHAOS_FW = 3

COMPANY_HOSTS: list[dict[str, Any]] = [
    {"ip": "192.168.1.10", "hostname": "corp-gateway", "company": "NovaDyne Corp",
     "security_level": 2, "ssh_password": "gateway22", "subnet": "192.168.1.0/24",
     "story": "Perimeter router for NovaDyne.", "min_rep": 0},
    {"ip": "192.168.1.30", "hostname": "vendor-vpn", "company": "CipherLink MSP",
     "security_level": 2, "ssh_password": "vendor99", "subnet": "192.168.1.0/24",
     "story": "Managed service provider jump box.", "min_rep": 0},
    {"ip": "192.168.1.25", "hostname": "research-node", "company": "NovaDyne R&D",
     "security_level": 3, "ssh_password": "lab_secret", "subnet": "192.168.1.0/24",
     "story": "Prototype AI weights stored here.", "min_rep": 0,
     "extra_files": {"/home/admin/model_weights.bin": "ENCRYPTED_BLOB\n"}},
    {"ip": "10.0.0.42", "hostname": "corp-dc", "company": "NovaDyne Corp",
     "security_level": 3, "ssh_password": "corp42!", "subnet": "10.0.0.0/24",
     "story": "Domain controller. Board secrets.", "min_rep": 0, "privesc_available": True,
     "extra_files": {"/home/admin/corporate_secrets.txt": "Acquisition: Helix AI\n"}},
    {"ip": "10.0.0.55", "hostname": "vault-server", "company": "NovaDyne Treasury",
     "security_level": 5, "ssh_password": "qu4ntum_vault", "subnet": "10.0.0.0/24",
     "story": "Payroll and wire keys.", "min_rep": 150, "privesc_available": True,
     "root_only_files": {"/root/payroll.csv": "ceo,2.1M\n"}},
    {"ip": "10.0.0.88", "hostname": "hr-portal", "company": "NovaDyne HR",
     "security_level": 2, "ssh_password": "onboard!", "subnet": "10.0.0.0/24",
     "story": "Leaked resumes.", "min_rep": 150,
     "extra_files": {"/home/admin/terminations.csv": "bob,gross_misconduct\n"}},
    {"ip": "172.16.0.20", "hostname": "fin-trading", "company": "Helix Capital",
     "security_level": 4, "ssh_password": "bull_mkt", "subnet": "172.16.0.0/24",
     "story": "HFT trading configs.", "min_rep": 400, "privesc_available": True,
     "extra_files": {"/home/admin/algo_config.yml": "strategy: latency_arb\n"}},
    {"ip": "172.16.0.33", "hostname": "bank-core", "company": "Helix Capital",
     "security_level": 5, "ssh_password": "swift_key", "subnet": "172.16.0.0/24",
     "story": "SWIFT bridge staging.", "min_rep": 400, "privesc_available": True,
     "root_only_files": {"/root/wire_keys.env": "SWIFT_API=REDACTED\n"}},
    {"ip": "203.0.113.66", "hostname": "chaos-c2", "company": "UNKNOWN",
     "security_level": 6, "ssh_password": "l33t_h4x", "subnet": "203.0.113.0/24",
     "story": "CHAOS: Rival collective C2 node.", "min_rep": 750, "chaos_only": True,
     "privesc_available": True,
     "root_only_files": {"/root/rival_plans.txt": "Operation Blackout\n"}},
    {"ip": "203.0.113.99", "hostname": "dark-vault", "company": "UNKNOWN",
     "security_level": 7, "ssh_password": "n3t_g0d!", "subnet": "203.0.113.0/24",
     "story": "CHAOS: Cold wallet vault. Trace chance doubled.", "min_rep": 750,
     "chaos_only": True, "privesc_available": True,
     "root_only_files": {"/root/cold_wallet.dat": "BALANCE: classified\n"}},
]

BROKERS = ["ghost_broker", "cipher7", "nullbyte", "shade_runner", "packet_queen"]
FILE_TEMPLATES = [
    ("/home/{user}/client_list.csv", "client,sector\n"),
    ("/home/{user}/intel_{n}.txt", "Briefing #{n}\n"),
    ("/root/secret_{n}.txt", "CLASSIFIED #{n}\n"),
]

ACHIEVEMENTS: dict[str, str] = {
    "first_blood": "Crack your first remote host",
    "boot_camp": "Complete the network boot lesson",
    "ghost_hands": "Disconnect with zero log traces",
    "vpn_shadow": "Crack while VPN is active",
    "root_queen": "Privilege escalate to root",
    "rank_ghost": "Reach Ghost in the Wires rank",
    "chaos_walker": "Exfiltrate from a chaos target",
    "daily_master": "Complete 30 daily challenges",
    "fortress": "Block 3 rival attacks in one session",
    "max_gear": "Max CPU and firewall",
    "contract_10": "Complete 10 contracts",
    "streak_7": "Maintain a 7-day login streak",
    "streak_30": "Maintain a 30-day login streak",
    "season_complete": "Finish the 30-tier season track",
    "rival_magnet": "Anger 5+ rivals through completed operations",
    "prep_master": "Complete 5 phase-prep objective sets",
    "chain_master": "Complete all 5 lateral movement chains",
    "grade_s_master": "Earn 10 S-rank contract grades",
    "hourly_hunter": "Complete 10 hourly flash events",
    "endless_floor_10": "Reach floor 10 in endless mode",
    "endless_floor_25": "Reach floor 25 in endless mode",
    "story_fork": "Make 3 branching story choices",
    "board_karma_100": "Earn 100 board karma",
    "puzzle_slayer": "Complete 5 puzzle-host contracts",
    "social_engineer": "Complete 3 social engineering contracts",
    "pivot_pro": "Complete 3 multi-host pivot contracts",
    "heist_master": "Complete 12 weekly heist arcs",
    "heist_legend": "First-clear all 12 heist arcs",
    "arc_ghost": "Complete the ghost story contract arc",
    "arc_rivals": "Complete the rivals story contract arc",
    "arc_solo": "Complete the solo story contract arc",
    "season_veteran": "Survive 3 monthly season resets",
    "faction_broker": "Reach 50 rep with Darknet Brokers",
    "faction_rival": "Reach 50 rep with Rival Syndicate",
    "faction_corp": "Reach 50 rep with Corporate Security",
    "consumable_user": "Use 10 consumables",
    "botnet_herder": "Maintain 5 infected botnet nodes",
}

DAILY_POOL = [
    ("no_vpn_crack", "Crack a host without VPN", 250, "no_vpn"),
    ("zero_traces", "Disconnect leaving zero log traces", 300, "zero_trace"),
    ("buy_upgrade", "Purchase any shop upgrade", 150, "buy"),
    ("privesc_run", "Privilege escalate on a target", 350, "privesc"),
    ("block_rival", "Firewall blocks a rival attack", 200, "block"),
    ("scan_three", "Scan 3 different subnets", 175, "scan3"),
]

DAILY_FLAGS = {
    "no_vpn": "daily_no_vpn_done",
    "zero_trace": "daily_zero_trace_done",
    "buy": "daily_buy_done",
    "privesc": "daily_privesc_done",
    "block": "daily_block_done",
    "scan3": "daily_scan3_done",
}


@dataclass
class AchievementTracker:
    unlocked: set[str] = field(default_factory=set)
    blocks_this_session: int = 0
    contracts_completed: int = 0
    dailies_completed: int = 0
    bridge_completions: int = 0

    def unlock(self, key: str) -> bool:
        if key in self.unlocked:
            return False
        self.unlocked.add(key)
        return True


@dataclass
class DailyChallenge:
    challenge_id: str
    description: str
    reward: int
    flag: str
    completed: bool = False

    @staticmethod
    def for_today() -> DailyChallenge:
        seed = int(date.today().strftime("%Y%m%d"))
        cid, desc, reward, flag = random.Random(seed).choice(DAILY_POOL)
        return DailyChallenge(cid, desc, reward, flag)


@dataclass
class BlueTeamState:
    ids_level: int = 1
    blocked_ips: set[str] = field(default_factory=set)
    attacks_blocked: int = 0
    defense_mode: bool = False

    def block_bonus(self) -> int:
        return self.ids_level * 5


class ReputationSystem:
    @staticmethod
    def rank_name(player: Player) -> str:
        return RANKS[min(player.rank_index, len(RANKS) - 1)].name

    @staticmethod
    def add_rep(game: Game, amount: int, reason: str) -> None:
        from main import Route, success, teach

        p = game.player
        p.reputation += amount
        success(f"+{amount} rep ({reason}) — total {p.reputation}")
        from retention import RetentionManager
        RetentionManager.on_rep_gain(game, amount)
        while p.rank_index < len(RANKS) - 1 and p.reputation >= RANKS[p.rank_index + 1].rep_required:
            p.rank_index += 1
            rank = RANKS[p.rank_index]
            success(f"RANK UP: {rank.name}")
            teach(rank.flavor)
            for cidr, gw in rank.routes:
                if not any(r.destination == cidr for r in p.routes):
                    p.routes.append(Route(cidr, gw))
                    success(f"Route unlocked: {cidr} via {gw}")
            game.network.deploy_company_hosts_with_puzzles(game, p.reputation, p.chaos_unlocked)
            if p.rank_index >= 3:
                p.chaos_unlocked = True
            game.mail.send(
                "ghost_broker@darknet", f"Clearance: {rank.name}",
                f"New subnets are live. Check scan targets.\n— ghost_broker",
            )
            if p.rank_index >= 3:
                game.achievements.unlock("rank_ghost")
            from depth_systems import SpecializationManager
            SpecializationManager.on_rank_up(game, p.rank_index)

    @staticmethod
    def chaos_available(player: Player, game: "Game | None" = None) -> bool:
        if player.chaos_unlocked:
            return True
        rep_need = CHAOS_REP
        if game:
            from faction_consumables import FactionRepManager
            rep_need = max(0, CHAOS_REP - FactionRepManager.chaos_rep_reduction(game))
        return (
            player.reputation >= rep_need
            and player.cpu_level >= CHAOS_CPU
            and player.firewall_level >= CHAOS_FW
        )


class MissionGenerator:
    _counter = 100

    @classmethod
    def next_id(cls) -> str:
        cls._counter += 1
        return f"proc-{cls._counter}"

    @classmethod
    def generate(cls, game: Game):
        from variety_content import VarietyMissionGenerator
        return VarietyMissionGenerator.generate(game)


class SaveManager:
    AUTOSAVE_EVERY = 5

    @staticmethod
    def _progress_key(data: dict) -> tuple[int, ...]:
        """Higher = more progress. Used to detect accidental save overwrites."""
        p = data.get("player", {})
        missions = data.get("missions", [])
        completed = sum(1 for m in missions if m.get("completed"))
        phase_rank = {"tutorial": 0, "endless": 1, "career": 2}.get(p.get("phase", "tutorial"), 0)
        return (
            phase_rank,
            int(p.get("tutorial_step", 0)),
            completed,
            int(p.get("ticks", 0)),
            len(p.get("discovered_ips", [])),
            int(p.get("firewall_level", 0)),
            int(p.get("money", 0)),
            int(p.get("reputation", 0)),
        )

    @staticmethod
    def _would_regress(existing: dict, new_data: dict) -> bool:
        old = SaveManager._progress_key(existing)
        new = SaveManager._progress_key(new_data)
        if new < old:
            return True
        # Career save wiped back to fresh tutorial
        if old[0] >= 2 and new[0] == 0 and new[1] <= 1:
            return True
        return False

    @staticmethod
    def _repair_inflated_heat(game: Game, *, legacy_world_event: bool = False) -> list[str]:
        """Clamp subnet heat stacked by duplicate world-event application."""
        p = game.player
        completed = sum(1 for m in game.missions.missions if m.completed)
        if p.ticks > 80 and completed >= 3:
            return []

        repaired: list[str] = []
        for subnet, h in list(game.meta.subnet_heat.items()):
            cap = 4 if legacy_world_event else 5
            suspicious = h >= 7 and p.ticks < 60 and completed <= 2
            if suspicious or (legacy_world_event and h > cap):
                game.meta.subnet_heat[subnet] = min(h, cap)
                repaired.append(subnet)

        if not repaired:
            return []

        game.meta.chaos_flags = {
            f for f in game.meta.chaos_flags if not f.startswith("heat_")
        }
        baseline = game.meta.notoriety_baseline
        if game.meta.notoriety > baseline + 6 and p.ticks < 50:
            game.meta.notoriety = max(baseline, game.meta.notoriety - 6)

        return [
            "Save repair: clamped inflated subnet heat from a prior bug "
            f"({', '.join(repaired)}).",
        ]

    @staticmethod
    def _normalize_player_state(game: Game) -> None:
        """Clamp inconsistent tutorial_step values from older or partial saves."""
        from main import TUTORIAL_CURRICULUM

        p = game.player
        max_step = len(TUTORIAL_CURRICULUM) - 1
        if p.phase == "career":
            if p.tutorial_step > max_step:
                p.tutorial_step = max_step + 1
        elif p.phase == "tutorial" and p.tutorial_step > max_step:
            p.tutorial_step = max_step

    @staticmethod
    def _read_save_file(path: Path) -> dict | None:
        try:
            return json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            return None

    @staticmethod
    def backup_is_better(path: Path, game: Game) -> bool:
        data = SaveManager._read_save_file(path)
        if not data:
            return False
        current = SaveManager._serialize(game)
        return SaveManager._progress_key(data) > SaveManager._progress_key(current)

    @staticmethod
    def load_from_path(game: Game, path: Path, *, quiet: bool = False) -> bool:
        from main import error, success

        data = SaveManager._read_save_file(path)
        if not data:
            if not quiet:
                error(f"Could not read {path}")
            return False
        try:
            SaveManager._deserialize(game, data, quiet=quiet)
            if not quiet:
                success(f"Loaded from {path}")
            return True
        except (KeyError, TypeError, ValueError) as exc:
            if not quiet:
                error(f"Load failed: {exc}")
            return False

    @staticmethod
    def restore_backup(game: Game, *, quiet: bool = False) -> bool:
        if not BACKUP_PATH.exists():
            return False
        if not SaveManager.load_from_path(game, BACKUP_PATH, quiet=quiet):
            return False
        return SaveManager.save(game, quiet=quiet)

    @staticmethod
    def _load_primary(game: Game, *, quiet: bool = False) -> bool:
        from main import error

        if not SAVE_PATH.exists():
            return False
        try:
            SaveManager._deserialize(game, json.loads(SAVE_PATH.read_text()), quiet=quiet)
            return True
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            if not quiet:
                error(f"Load failed: {exc}")
            return False

    @staticmethod
    def load_best_available(game: Game, *, quiet: bool = False) -> bool:
        """Load primary save; auto-restore from backup if primary is an accidental reset."""
        from main import error, success, warn

        loaded = SaveManager._load_primary(game, quiet=True)
        if loaded and BACKUP_PATH.exists() and SaveManager.backup_is_better(BACKUP_PATH, game):
            if SaveManager.load_from_path(game, BACKUP_PATH, quiet=True):
                SaveManager.save(game, quiet=True)
                if not quiet:
                    warn("Restored your progress from save backup (primary save had regressed).")
                return True
        if loaded:
            if not quiet:
                success(f"Loaded from {SAVE_PATH}")
            return True
        if BACKUP_PATH.exists() and SaveManager.load_from_path(game, BACKUP_PATH, quiet=quiet):
            SaveManager.save(game, quiet=True)
            if not quiet:
                warn("Primary save missing or corrupt — restored from backup.")
            return True
        if not quiet:
            error("No save file found.")
        return False

    @staticmethod
    def save(game: Game, *, quiet: bool = False, allow_regression: bool = False) -> bool:
        from main import error, success, warn

        try:
            new_data = SaveManager._serialize(game)
            SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
            if SAVE_PATH.exists() and not allow_regression:
                existing = SaveManager._read_save_file(SAVE_PATH)
                if existing and SaveManager._would_regress(existing, new_data):
                    blocked = SAVE_PATH.with_suffix(".json.blocked")
                    blocked.write_text(json.dumps(new_data, indent=2))
                    if not quiet:
                        warn(
                            "Save blocked — would reset your progress. "
                            f"Backup kept at {BACKUP_PATH}. "
                            "Use System Status → Restore Backup, or type 'load' in Terminal."
                        )
                    return False
            if SAVE_PATH.exists():
                BACKUP_PATH.write_text(SAVE_PATH.read_text())
            SAVE_PATH.write_text(json.dumps(new_data, indent=2))
            if not quiet:
                success(f"Saved to {SAVE_PATH}")
            return True
        except OSError as exc:
            if not quiet:
                error(f"Save failed: {exc}")
            return False

    @staticmethod
    def autosave(game: Game, force: bool = False) -> bool:
        if not force:
            game._cmds_since_autosave = getattr(game, "_cmds_since_autosave", 0) + 1
            if game._cmds_since_autosave < SaveManager.AUTOSAVE_EVERY:
                return False
        ok = SaveManager.save(game, quiet=True)
        if ok:
            game._cmds_since_autosave = 0
            import time
            game.last_autosave = time.strftime("%H:%M:%S")
        return ok

    @staticmethod
    def load(game: Game, *, quiet: bool = False) -> bool:
        return SaveManager.load_best_available(game, quiet=quiet)

    @staticmethod
    def _serialize(game: Game) -> dict:
        from main import NOTES_PATH, TutorialManager
        p = game.player
        return {
            "player": {
                "phase": p.phase, "tutorial_step": p.tutorial_step,
                "tutorial_credits": p.tutorial_credits, "money": p.money,
                "cpu_level": p.cpu_level, "firewall_level": p.firewall_level,
                "cracker_tier": p.cracker_tier, "vpn_licensed": p.vpn_licensed,
                "reputation": p.reputation, "rank_index": p.rank_index,
                "handle": p.handle,
                "chaos_unlocked": p.chaos_unlocked,
                "routes": [(r.destination, r.gateway, r.iface) for r in p.routes],
                "discovered_ips": list(p.discovered_ips),
                "owned_tools": list(p.owned_tools),
                "command_history": list(p.command_history),
                "tutorial_flags": list(p.tutorial_flags),
                "ticks": p.ticks,
                "subnets_scanned": list(p.subnets_scanned),
                "privesc_hosts": list(p.privesc_hosts),
                "downloads": {
                    k: p.files[k].content
                    for k in p.files
                    if "/downloads/" in k
                },
                "exfil_sources": dict(p.exfil_sources),
                "notes_content": p.files[NOTES_PATH].content if NOTES_PATH in p.files else "",
                "daily": {
                    "challenge_id": game.daily.challenge_id,
                    "description": game.daily.description,
                    "reward": game.daily.reward,
                    "flag": game.daily.flag,
                    "completed": game.daily.completed,
                },
            },
            "missions": [
                {"mission_id": m.mission_id, "broker": m.broker, "briefing": m.briefing,
                 "target_ip": m.target_ip, "target_file": m.target_file,
                 "reward": m.reward, "rep_reward": getattr(m, "rep_reward", 0),
                 "completed": m.completed, "procedural": getattr(m, "procedural", False),
                 "mission_type": getattr(m, "mission_type", "exfil"),
                 "require_privesc": getattr(m, "require_privesc", False),
                 "require_log_wipe": getattr(m, "require_log_wipe", True),
                 "weekly_bounty": getattr(m, "weekly_bounty", False),
                 "operation_id": getattr(m, "operation_id", ""),
                 "operation_step": getattr(m, "operation_step", 0),
                 "lateral_chain_id": getattr(m, "lateral_chain_id", ""),
                 "hourly_event": getattr(m, "hourly_event", False),
                 "reward_multiplier": getattr(m, "reward_multiplier", 1.0),
                 "grade": getattr(m, "grade", ""),
                 "endless_floor": getattr(m, "endless_floor", False),
                 "puzzle_id": getattr(m, "puzzle_id", ""),
                 "puzzle_secondary": getattr(m, "puzzle_secondary", ""),
                 "social_file": getattr(m, "social_file", ""),
                 "pivot_host": getattr(m, "pivot_host", ""),
                 "timing_limit_ticks": getattr(m, "timing_limit_ticks", 0),
                 "timing_start_tick": getattr(m, "timing_start_tick", 0),
                 "modifiers": getattr(m, "modifiers", []),
                 "heist_id": getattr(m, "heist_id", ""),
                 "heist_step": getattr(m, "heist_step", 0),
                 "story_arc": getattr(m, "story_arc", ""),
                 "rival_counter": getattr(m, "rival_counter", False),
                "race_lost": getattr(m, "race_lost", False)}
                for m in game.missions.missions
            ],
            "mail": [{"mail_id": m.mail_id, "sender": m.sender, "subject": m.subject,
                      "body": m.body, "read": m.read, "timestamp": m.timestamp}
                     for m in game.mail.messages],
            "mail_trash": [{"mail_id": m.mail_id, "sender": m.sender, "subject": m.subject,
                            "body": m.body, "read": m.read, "timestamp": m.timestamp}
                           for m in game.mail.trash],
            "servers": {ip: {"cracked": s.cracked, "ids": s.ids_alert_level}
                        for ip, s in game.network.servers.items()},
            "achievements": list(game.achievements.unlocked),
            "ach_stats": {"contracts": game.achievements.contracts_completed,
                          "dailies": game.achievements.dailies_completed,
                          "bridges": game.achievements.bridge_completions},
            "blue": {"ids_level": game.blue.ids_level,
                     "attacks_blocked": game.blue.attacks_blocked,
                     "defense_mode": game.blue.defense_mode},
            "announced": game.missions._announced,
            "mail_counter": game.mail._counter,
            "retention": {
                "last_login": game.retention.last_login,
                "streak": game.retention.streak,
                "longest_streak": game.retention.longest_streak,
                "season_xp": game.retention.season_xp,
                "season_tier": game.retention.season_tier,
                "season_month": game.retention.season_month,
                "season_cycles": game.retention.season_cycles,
                "weekly_key": game.retention.weekly_key,
                "weekly_completed": game.retention.weekly_completed,
                "active_operation": game.retention.active_operation,
                "operation_step": game.retention.operation_step,
                "operation_unlock_day": game.retention.operation_unlock_day,
                "operation_parts_done": game.retention.operation_parts_done,
                "completed_operations": game.retention.completed_operations,
                "operation_cooldown_until": game.retention.operation_cooldown_until,
                "weekly_story_week": game.retention.weekly_story_week,
                "rival_aggression": game.retention.rival_aggression,
                "last_rival": game.retention.last_rival,
                "rival_anger": game.retention.rival_anger,
                "reactions_sent": game.retention.reactions_sent,
                "bridge_id": game.retention.bridge_id,
                "bridge_tasks": game.retention.bridge_tasks,
                "bridge_done": game.retention.bridge_done,
                "bridge_claimed": game.retention.bridge_claimed,
                "bridge_unlock_day": game.retention.bridge_unlock_day,
                "ghost_targets_done": list(game.retention.ghost_targets_done),
            },
            "session": {
                "active_chain_id": game.session.active_chain_id,
                "chain_step": game.session.chain_step,
                "chain_steps_done": game.session.chain_steps_done,
                "completed_chains": game.session.completed_chains,
                "unlocked_pivots": list(game.session.unlocked_pivots),
                "mastery_mission_id": game.session.mastery_mission_id,
                "mastery_commands": game.session.mastery_commands,
                "mastery_start_money": game.session.mastery_start_money,
                "mastery_shop_spent": game.session.mastery_shop_spent,
                "mastery_vpn_used": game.session.mastery_vpn_used,
                "best_grades": game.session.best_grades,
                "s_rank_total": game.session.s_rank_total,
                "hourly_slot": game.session.hourly_slot,
                "hourly_event_id": game.session.hourly_event_id,
                "hourly_mission_id": game.session.hourly_mission_id,
                "hourly_completed": game.session.hourly_completed,
                "hourly_completions": game.session.hourly_completions,
            },
            "endless": {
                "active": game.endless.active,
                "floor": game.endless.floor,
                "score": game.endless.score,
                "run_money": game.endless.run_money,
                "best_floor": game.endless.best_floor,
                "total_runs": game.endless.total_runs,
                "deaths": game.endless.deaths,
                "relics": game.endless.relics,
                "floor_hosts": game.endless.floor_hosts,
                "floor_subnet": game.endless.floor_subnet,
                "floor_mission_id": game.endless.floor_mission_id,
                "career_money": game.endless.career_money,
                "pending_relic_pick": game.endless.pending_relic_pick,
                "relic_options": game.endless.relic_options,
                "floor_modifier": game.endless.floor_modifier,
                "boss_floor": game.endless.boss_floor,
                "floor_commands": game.endless.floor_commands,
            },
            "story": {
                "current_node": game.story.current_node,
                "flags": list(game.story.flags),
                "choices_made": game.story.choices_made,
                "week_beat": game.story.week_beat,
                "intro_sent": game.story.intro_sent,
            },
            "board": {
                "posts": [
                    {"post_id": p.post_id, "board": p.board, "author": p.author,
                     "title": p.title, "body": p.body, "timestamp": p.timestamp,
                     "likes": p.likes, "player_post": p.player_post, "upvoted": p.upvoted}
                    for p in game.board.posts[:80]
                ],
                "karma": game.board.karma,
                "_counter": game.board._counter,
                "seeded": game.board.seeded,
            },
            "variety": {
                "puzzle_progress": {
                    ip: {
                        "probes": prog.get("probes", 0),
                        "flags": list(prog.get("flags", [])),
                    }
                    for ip, prog in game.variety.puzzle_progress.items()
                },
                "pivot_step": game.variety.pivot_step,
                "social_flags": list(game.variety.social_flags),
                "procedural_counter": game.variety.procedural_counter,
                "procedural_ips": game.variety.procedural_ips,
                "hosts_puzzled": list(game.variety.hosts_puzzled),
                "social_completions": game.variety.social_completions,
                "pivot_completions": game.variety.pivot_completions,
                "puzzle_completions": game.variety.puzzle_completions,
            },
            "llm": {
                "user_enabled": game.llm.user_enabled,
                "cache": game.llm.cache,
                "struct_cache": game.llm.struct_cache,
                "session_calls": game.llm.session_calls,
                "session_struct_calls": game.llm.session_struct_calls,
                "total_calls": game.llm.total_calls,
                "total_struct_calls": game.llm.total_struct_calls,
                "last_error": game.llm.last_error,
                "world_event": game.llm.world_event,
                "world_event_week": game.llm.world_event_week,
            },
            "meta": {
                "curriculum_version": TutorialManager.CURRICULUM_VERSION,
                "specialization": game.meta.specialization,
                "spec_unlock_pending": game.meta.spec_unlock_pending,
                "backdoors": list(game.meta.backdoors),
                "forged_servers": list(game.meta.forged_servers),
                "phished_ips": list(game.meta.phished_ips),
                "tunnels": {str(k): v for k, v in game.meta.tunnels.items()},
                "subnet_heat": game.meta.subnet_heat,
                "rival_race_prog": game.meta.rival_race_prog,
                "rival_race_rival": game.meta.rival_race_rival,
                "rival_race_warned": game.meta.rival_race_warned,
                "weekly_heist_id": game.meta.weekly_heist_id,
                "weekly_heist_step": game.meta.weekly_heist_step,
                "weekly_heist_week": game.meta.weekly_heist_week,
                "weekly_heist_done": game.meta.weekly_heist_done,
                "heist_branch": game.meta.heist_branch,
                "heist_score": game.meta.heist_score,
                "heists_cleared": game.meta.heists_cleared,
                "heists_first_cleared": list(game.meta.heists_first_cleared),
                "heist_clear_counts": game.meta.heist_clear_counts,
                "heist_branches_cleared": {
                    k: list(v) for k, v in game.meta.heist_branches_cleared.items()
                },
                "heist_month_key": game.meta.heist_month_key,
                "heist_rotation_key": game.meta.heist_rotation_key,
                "inventory": game.meta.inventory,
                "burner_commands_left": game.meta.burner_commands_left,
                "burner_mask_ip": game.meta.burner_mask_ip,
                "decoy_trace_immunity": game.meta.decoy_trace_immunity,
                "faction_rep": game.meta.faction_rep,
                "faction_perks_unlocked": list(game.meta.faction_perks_unlocked),
                "contracts_since_free_consumable": game.meta.contracts_since_free_consumable,
                "consumables_used": game.meta.consumables_used,
                "notoriety": game.meta.notoriety,
                "chaos_mode": game.meta.chaos_mode,
                "chaos_flags": list(game.meta.chaos_flags),
                "chaos_headlines": game.meta.chaos_headlines[-30:],
                "meltdown": game.meta.meltdown,
                "ghost_raid_cd": game.meta.ghost_raid_cd,
                "faction_war_cd": game.meta.faction_war_cd,
                "heat_scrub_cd": game.meta.heat_scrub_cd,
                "heat_scrubs_paid": game.meta.heat_scrubs_paid,
                "world_event_applied_week": game.meta.world_event_applied_week,
                "payload_drop_index": game.meta.payload_drop_index,
                "payload_drop_cd": game.meta.payload_drop_cd,
                "payload_drop_ip": game.meta.payload_drop_ip,
                "payload_drop_path": game.meta.payload_drop_path,
                "payload_drop_key": game.meta.payload_drop_key,
                "payload_drop_password": game.meta.payload_drop_password,
                "payload_drop_claimed": game.meta.payload_drop_claimed,
                "defaced_hosts": list(game.meta.defaced_hosts),
                "framed_rivals": game.meta.framed_rivals,
                "ransom_accrual": game.meta.ransom_accrual,
                "infections": game.meta.infections,
                "botnet_bank": game.meta.botnet_bank,
                "ddos_targets": game.meta.ddos_targets,
                "botnet_purges": game.meta.botnet_purges,
                "notoriety_baseline": game.meta.notoriety_baseline,
                "rival_trash_talk_unlocked": game.meta.rival_trash_talk_unlocked,
                "pending_rival_mail": game.meta.pending_rival_mail,
            },
        }

    @staticmethod
    def _recover_download_content(game: Game, local_path: str) -> str:
        """Best-effort recovery for saves that only stored download paths."""
        fname = local_path.rsplit("/", 1)[-1]
        for mission in game.missions.missions:
            target = mission.target_file
            if not target or not target.endswith(fname):
                continue
            server = game.network.get_server(mission.target_ip)
            if server and target in server.files:
                return server.files[target].read()
        for server in game.network.servers.values():
            for remote_path, remote_file in server.files.items():
                if remote_path.endswith(f"/{fname}") or remote_path == fname:
                    return remote_file.read()
        return ""

    @staticmethod
    def _apply_downloads(game: Game, raw: object, *, owner: str) -> None:
        from main import VirtualFile

        if isinstance(raw, dict):
            for path, content in raw.items():
                game.player.files[path] = VirtualFile(path, content or "", owner=owner)
            return
        if isinstance(raw, list):
            game._legacy_download_paths = list(raw)

    @staticmethod
    def _finalize_downloads(game: Game) -> None:
        from main import VirtualFile

        pending = getattr(game, "_legacy_download_paths", None)
        if not pending:
            return
        owner = game.player.username
        for path in pending:
            if path in game.player.files:
                existing = game.player.files[path].content.strip()
                if existing and existing != "restored":
                    continue
            content = SaveManager._recover_download_content(game, path)
            game.player.files[path] = VirtualFile(
                path, content or "restored\n", owner=owner,
            )
        del game._legacy_download_paths

    @staticmethod
    def _deserialize(game: Game, data: dict, *, quiet: bool = False) -> None:
        from main import MailMessage, Mission, Route, VirtualFile, NOTES_PATH
        from retention import RetentionManager, RetentionState
        from session_content import LateralManager, SessionState
        from endless_mode import EndlessManager, EndlessState
        from story_system import StoryState
        from social_board import BoardPost, SocialBoardState
        from variety_content import VarietyManager, VarietyState
        from depth_systems import MetaState

        pd = data["player"]
        daily_data = pd.pop("daily", None)
        p = game.player
        for k, v in pd.items():
            if k == "routes":
                p.routes = [Route(a, b, c) for a, b, c in v]
            elif k == "discovered_ips":
                p.discovered_ips = set(v)
            elif k == "owned_tools":
                p.owned_tools = set(v)
            elif k == "command_history":
                p.command_history = set(v)
            elif k == "tutorial_flags":
                p.tutorial_flags = set(v)
            elif k == "downloads":
                SaveManager._apply_downloads(game, v, owner=p.username)
            elif k == "notes_content":
                if NOTES_PATH in p.files:
                    p.files[NOTES_PATH].content = v
                else:
                    p.files[NOTES_PATH] = VirtualFile(NOTES_PATH, v, owner=p.username)
            elif k == "subnets_scanned":
                p.subnets_scanned = set(v)
            elif k == "privesc_hosts":
                p.privesc_hosts = set(v)
            elif hasattr(p, k):
                setattr(p, k, v)

        from main import migrate_handle_chosen
        migrate_handle_chosen(game)

        if daily_data:
            game.daily = DailyChallenge(
                daily_data["challenge_id"], daily_data["description"],
                daily_data["reward"], daily_data["flag"],
                completed=daily_data.get("completed", False),
            )
        elif pd.get("daily_done"):
            p.tutorial_flags.add(pd["daily_done"])

        game.missions.missions = []
        for md in data["missions"]:
            game.missions.missions.append(Mission(
                md["mission_id"], md["broker"], md["briefing"], md["target_ip"],
                md["target_file"], md["reward"],
                require_log_wipe=md.get("require_log_wipe", True),
                completed=md["completed"],
                rep_reward=md.get("rep_reward", 50),
                procedural=md.get("procedural", False),
                mission_type=md.get("mission_type", "exfil"),
                require_privesc=md.get("require_privesc", False),
                weekly_bounty=md.get("weekly_bounty", False),
                operation_id=md.get("operation_id", ""),
                operation_step=md.get("operation_step", 0),
                lateral_chain_id=md.get("lateral_chain_id", ""),
                hourly_event=md.get("hourly_event", False),
                reward_multiplier=md.get("reward_multiplier", 1.0),
                grade=md.get("grade", ""),
                endless_floor=md.get("endless_floor", False),
                puzzle_id=md.get("puzzle_id", ""),
                puzzle_secondary=md.get("puzzle_secondary", ""),
                social_file=md.get("social_file", ""),
                pivot_host=md.get("pivot_host", ""),
                timing_limit_ticks=md.get("timing_limit_ticks", 0),
                timing_start_tick=md.get("timing_start_tick", 0),
                modifiers=md.get("modifiers", []),
                heist_id=md.get("heist_id", ""),
                heist_step=md.get("heist_step", 0),
                story_arc=md.get("story_arc", ""),
                rival_counter=md.get("rival_counter", False),
                race_lost=md.get("race_lost", False),
            ))

        game.mail.messages = [MailMessage(**md) for md in data["mail"]]
        game.mail.trash = [MailMessage(**md) for md in data.get("mail_trash", [])]
        game.mail._counter = data.get("mail_counter", 0)
        for ip, sd in data.get("servers", {}).items():
            if ip in game.network.servers:
                game.network.servers[ip].cracked = sd.get("cracked", False)
                game.network.servers[ip].ids_alert_level = sd.get("ids", 0)
        game.achievements.unlocked = set(data.get("achievements", []))
        ast = data.get("ach_stats", {})
        game.achievements.contracts_completed = ast.get("contracts", 0)
        game.achievements.dailies_completed = ast.get("dailies", 0)
        game.achievements.bridge_completions = ast.get("bridges", 0)
        bd = data.get("blue", {})
        game.blue.ids_level = bd.get("ids_level", 1)
        game.blue.attacks_blocked = bd.get("attacks_blocked", 0)
        game.blue.defense_mode = bd.get("defense_mode", False)
        game.missions._announced = data.get("announced", False)
        rd = data.get("retention", {})
        if rd:
            game.retention = RetentionState(
                last_login=rd.get("last_login", ""),
                streak=rd.get("streak", 0),
                longest_streak=rd.get("longest_streak", 0),
                season_xp=rd.get("season_xp", 0),
                season_tier=rd.get("season_tier", 0),
                season_month=rd.get("season_month", ""),
                season_cycles=rd.get("season_cycles", 0),
                weekly_key=rd.get("weekly_key", ""),
                weekly_completed=rd.get("weekly_completed", False),
                active_operation=rd.get("active_operation", ""),
                operation_step=rd.get("operation_step", 0),
                operation_unlock_day=rd.get("operation_unlock_day", ""),
                operation_parts_done=rd.get("operation_parts_done", []),
                completed_operations=rd.get("completed_operations", []),
                operation_cooldown_until=rd.get("operation_cooldown_until", ""),
                weekly_story_week=rd.get("weekly_story_week", ""),
                rival_aggression=rd.get("rival_aggression", 0),
                last_rival=rd.get("last_rival", ""),
                rival_anger=dict(rd.get("rival_anger", {})),
                reactions_sent=rd.get("reactions_sent", []),
                bridge_id=rd.get("bridge_id", ""),
                bridge_tasks=rd.get("bridge_tasks", []),
                bridge_done=rd.get("bridge_done", []),
                bridge_claimed=rd.get("bridge_claimed", False),
                bridge_unlock_day=rd.get("bridge_unlock_day", ""),
                ghost_targets_done=set(rd.get("ghost_targets_done", [])),
            )
        sd = data.get("session", {})
        if sd:
            game.session = SessionState(
                active_chain_id=sd.get("active_chain_id", ""),
                chain_step=sd.get("chain_step", 0),
                chain_steps_done=sd.get("chain_steps_done", []),
                completed_chains=sd.get("completed_chains", []),
                unlocked_pivots=set(sd.get("unlocked_pivots", [])),
                mastery_mission_id=sd.get("mastery_mission_id", ""),
                mastery_commands=sd.get("mastery_commands", 0),
                mastery_start_money=sd.get("mastery_start_money", 0),
                mastery_shop_spent=sd.get("mastery_shop_spent", 0),
                mastery_vpn_used=sd.get("mastery_vpn_used", False),
                best_grades=sd.get("best_grades", {}),
                s_rank_total=sd.get("s_rank_total", 0),
                hourly_slot=sd.get("hourly_slot", 0),
                hourly_event_id=sd.get("hourly_event_id", ""),
                hourly_mission_id=sd.get("hourly_mission_id", ""),
                hourly_completed=sd.get("hourly_completed", False),
                hourly_completions=sd.get("hourly_completions", 0),
            )
        if game.session.active_chain_id:
            chain = LateralManager.chain_by_id(game.session.active_chain_id)
            if chain:
                LateralManager._inject_intel_files(game, chain)
        ed = data.get("endless", {})
        if ed:
            game.endless = EndlessState(
                active=ed.get("active", False),
                floor=ed.get("floor", 0),
                score=ed.get("score", 0),
                run_money=ed.get("run_money", 0),
                best_floor=ed.get("best_floor", 0),
                total_runs=ed.get("total_runs", 0),
                deaths=ed.get("deaths", 0),
                relics=ed.get("relics", []),
                floor_hosts=ed.get("floor_hosts", []),
                floor_subnet=ed.get("floor_subnet", ""),
                floor_mission_id=ed.get("floor_mission_id", ""),
                career_money=ed.get("career_money", 0),
                pending_relic_pick=ed.get("pending_relic_pick", False),
                relic_options=ed.get("relic_options", []),
                floor_modifier=ed.get("floor_modifier", ""),
                boss_floor=ed.get("boss_floor", False),
                floor_commands=ed.get("floor_commands", 0),
            )
        std = data.get("story", {})
        if std:
            game.story = StoryState(
                current_node=std.get("current_node", ""),
                flags=set(std.get("flags", [])),
                choices_made=std.get("choices_made", []),
                week_beat=std.get("week_beat", 0),
                intro_sent=std.get("intro_sent", False),
            )
        bd = data.get("board", {})
        if bd:
            game.board = SocialBoardState(
                posts=[BoardPost(**pd) for pd in bd.get("posts", [])],
                karma=bd.get("karma", 0),
                _counter=bd.get("_counter", 0),
                seeded=bd.get("seeded", False),
            )
        vd = data.get("variety", {})
        if vd:
            pp = {}
            for ip, prog in vd.get("puzzle_progress", {}).items():
                pp[ip] = {"probes": prog.get("probes", 0), "flags": set(prog.get("flags", []))}
            game.variety = VarietyState(
                puzzle_progress=pp,
                pivot_step=vd.get("pivot_step", {}),
                social_flags=set(vd.get("social_flags", [])),
                procedural_counter=vd.get("procedural_counter", 0),
                procedural_ips=vd.get("procedural_ips", []),
                hosts_puzzled=set(vd.get("hosts_puzzled", [])),
                social_completions=vd.get("social_completions", 0),
                pivot_completions=vd.get("pivot_completions", 0),
                puzzle_completions=vd.get("puzzle_completions", 0),
            )
        from llm_content import LLMState
        ld = data.get("llm", {})
        if ld:
            game.llm = LLMState(
                user_enabled=ld.get("user_enabled", True),
                cache=ld.get("cache", {}),
                struct_cache=ld.get("struct_cache", {}),
                session_calls=ld.get("session_calls", 0),
                session_struct_calls=ld.get("session_struct_calls", 0),
                total_calls=ld.get("total_calls", 0),
                total_struct_calls=ld.get("total_struct_calls", 0),
                last_error=ld.get("last_error", ""),
                world_event=ld.get("world_event", {}),
                world_event_week=ld.get("world_event_week", ""),
            )
        md = data.get("meta", {})
        legacy_world_event = "world_event_applied_week" not in md
        if md:
            tunnels = {int(k): tuple(v) for k, v in md.get("tunnels", {}).items()}
            game.meta = MetaState(
                specialization=md.get("specialization", ""),
                spec_unlock_pending=md.get("spec_unlock_pending", False),
                backdoors=set(md.get("backdoors", [])),
                forged_servers=set(md.get("forged_servers", [])),
                phished_ips=set(md.get("phished_ips", [])),
                tunnels=tunnels,
                subnet_heat=md.get("subnet_heat", {}),
                rival_race_prog=md.get("rival_race_prog", {}),
                rival_race_rival=md.get("rival_race_rival", {}),
                rival_race_warned=md.get("rival_race_warned", {}),
                weekly_heist_id=md.get("weekly_heist_id", ""),
                weekly_heist_step=md.get("weekly_heist_step", 0),
                weekly_heist_week=md.get("weekly_heist_week", ""),
                weekly_heist_done=md.get("weekly_heist_done", False),
                heist_branch=md.get("heist_branch", ""),
                heist_score=md.get("heist_score", 0),
                heists_cleared=md.get("heists_cleared", 0),
                heists_first_cleared=set(md.get("heists_first_cleared", [])),
                heist_clear_counts=md.get("heist_clear_counts", {}),
                heist_branches_cleared={
                    k: set(v) for k, v in md.get("heist_branches_cleared", {}).items()
                },
                heist_month_key=md.get("heist_month_key", ""),
                heist_rotation_key=md.get("heist_rotation_key", ""),
                inventory=md.get("inventory", {}),
                burner_commands_left=md.get("burner_commands_left", 0),
                burner_mask_ip=md.get("burner_mask_ip", ""),
                decoy_trace_immunity=md.get("decoy_trace_immunity", 0),
                faction_rep=md.get("faction_rep", {"brokers": 0, "rivals": 0, "corps": 0}),
                faction_perks_unlocked=set(md.get("faction_perks_unlocked", [])),
                contracts_since_free_consumable=md.get("contracts_since_free_consumable", 0),
                consumables_used=md.get("consumables_used", 0),
                notoriety=md.get("notoriety", 0),
                chaos_mode=md.get("chaos_mode", False),
                chaos_flags=set(md.get("chaos_flags", [])),
                chaos_headlines=list(md.get("chaos_headlines", [])),
                meltdown=dict(md.get("meltdown", {})),
                ghost_raid_cd=md.get("ghost_raid_cd", 0),
                faction_war_cd=md.get("faction_war_cd", 0),
                heat_scrub_cd=md.get("heat_scrub_cd", 0),
                heat_scrubs_paid=md.get("heat_scrubs_paid", 0),
                world_event_applied_week=md.get("world_event_applied_week", ""),
                payload_drop_index=md.get("payload_drop_index", 0),
                payload_drop_cd=md.get("payload_drop_cd", 0),
                payload_drop_ip=md.get("payload_drop_ip", ""),
                payload_drop_path=md.get("payload_drop_path", ""),
                payload_drop_key=md.get("payload_drop_key", ""),
                payload_drop_password=md.get("payload_drop_password", ""),
                payload_drop_claimed=md.get("payload_drop_claimed", False),
                defaced_hosts=set(md.get("defaced_hosts", [])),
                framed_rivals=dict(md.get("framed_rivals", {})),
                ransom_accrual=dict(md.get("ransom_accrual", {})),
                infections=md.get("infections", {}),
                botnet_bank=md.get("botnet_bank", 0),
                ddos_targets=md.get("ddos_targets", {}),
                botnet_purges=md.get("botnet_purges", 0),
                notoriety_baseline=md.get("notoriety_baseline", md.get("notoriety", 0)),
                rival_trash_talk_unlocked=md.get("rival_trash_talk_unlocked", False),
                pending_rival_mail=list(md.get("pending_rival_mail", [])),
            )
            repair_notes = SaveManager._repair_inflated_heat(
                game, legacy_world_event=legacy_world_event,
            )
            if repair_notes and not quiet:
                import sys
                for note in repair_notes:
                    print(f"  {note}", file=sys.stderr)
        from chaos_system import CareerPressureManager
        CareerPressureManager.sync_unlock_from_save(game)
        from payload_drops import PayloadDropManager
        PayloadDropManager.restore_from_save(game)
        if p.phase == "endless" and game.endless.active:
            for ip in game.endless.floor_hosts:
                if ip in game.network.servers:
                    game.network.servers[ip].endless_only = True
        SaveManager._normalize_player_state(game)
        if p.phase == "career":
            from progression import PlayerProfile
            PlayerProfile.mark_veteran()
            game.network.deploy_company_hosts_with_puzzles(game, p.reputation, p.chaos_unlocked)
            if getattr(game, "gui_mode", False):
                game.defer_career_session = True
            else:
                RetentionManager.on_career_session(game)
            from session_content import HourlyManager
            HourlyManager.refresh(game)
            from depth_systems import WeeklyHeistManager
            WeeklyHeistManager.refresh(game)
        elif p.phase == "endless" and game.endless.active and not game.endless.floor_hosts:
            EndlessManager._spawn_floor(game)

        SaveManager._finalize_downloads(game)
        game.player._game_ref = game
        game.tutorial.reconcile_stuck_lessons()


def build_company_server(spec: dict) -> Server:
    from main import Server
    s = Server(
        spec["ip"], spec["hostname"], spec["security_level"],
        subnet=spec.get("subnet", "192.168.1.0/24"),
        ssh_password=spec["ssh_password"],
        privesc_available=spec.get("privesc_available", False),
        extra_files=spec.get("extra_files", {}),
        root_only_files=spec.get("root_only_files", {}),
    )
    s.company = spec.get("company", "")
    s.story = spec.get("story", "")
    s.min_rep = spec.get("min_rep", 0)
    s.chaos_only = spec.get("chaos_only", False)
    from variety_content import COMPANY_PUZZLE_MAP
    s.puzzle_id = spec.get("puzzle_id", COMPANY_PUZZLE_MAP.get(spec["ip"], ""))
    return s
