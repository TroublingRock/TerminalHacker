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
     "story": "Domain controller. Board secrets.", "min_rep": 150, "privesc_available": True,
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
            game.network.deploy_company_hosts(p.reputation, p.chaos_unlocked)
            if p.rank_index >= 3:
                p.chaos_unlocked = True
            game.mail.send(
                "ghost_broker@darknet", f"Clearance: {rank.name}",
                f"New subnets are live. Check scan targets.\n— ghost_broker",
            )
            if p.rank_index >= 3:
                game.achievements.unlock("rank_ghost")

    @staticmethod
    def chaos_available(player: Player) -> bool:
        return player.chaos_unlocked or (
            player.reputation >= CHAOS_REP
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
        from main import Mission, VirtualFile

        if game.player.phase != "career":
            return None
        if sum(1 for m in game.missions.missions if not m.completed) >= 5:
            return None
        candidates = [
            s for s in game.network.servers.values()
            if not getattr(s, "chaos_only", False)
            and game.player.reputation >= getattr(s, "min_rep", 0)
            and game.player.has_route_to(s.ip)
        ]
        if not candidates:
            return None
        server = random.choice(candidates)
        archetype = random.choice(["exfil", "exfil", "ghost", "root_heist", "clean_sweep"])
        user = server.ssh_user
        tpl_path, tpl_body = random.choice(FILE_TEMPLATES)
        n = random.randint(1, 99)
        rel = tpl_path.format(user=user, n=n)
        if archetype == "ghost":
            rel = ""
        elif archetype == "root_heist":
            rel = f"/root/secret_{n}.txt"
            if rel not in server.files:
                server.files[rel] = VirtualFile(rel, tpl_body.format(n=n), owner="root", mode="rw-------", requires_root=True)
        elif rel not in server.files:
            server.files[rel] = VirtualFile(rel, tpl_body.format(n=n))
        reward = 320 + server.security_level * 100 + random.randint(0, 180)
        rep = 35 + server.security_level * 12
        company = getattr(server, "company", "Unknown")
        if archetype == "ghost":
            briefing = f"[{company}] Ghost run on {server.hostname} ({server.ip}) — crack, leave zero traces."
            reward += 200
        elif archetype == "root_heist":
            fname = rel.rsplit("/", 1)[-1]
            briefing = f"[{company}] Root heist on {server.hostname} — privesc, exfil {fname}, wipe logs."
            reward += 300
            rep += 30
        elif archetype == "clean_sweep":
            briefing = f"[{company}] Clean sweep on {server.hostname} — crack, wipe ALL logs, exfil {rel.rsplit('/', 1)[-1]}."
            reward += 150
        else:
            fname = rel.rsplit("/", 1)[-1]
            briefing = f"[{company}] Hit {server.hostname} ({server.ip}), exfil {fname}, wipe logs."
        return Mission(
            cls.next_id(), random.choice(BROKERS), briefing,
            server.ip, rel, reward, rep_reward=rep, procedural=True,
            mission_type=archetype,
            require_privesc=archetype == "root_heist",
        )


class SaveManager:
    AUTOSAVE_EVERY = 5

    @staticmethod
    def save(game: Game, *, quiet: bool = False) -> bool:
        from main import error, success
        try:
            SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)
            SAVE_PATH.write_text(json.dumps(SaveManager._serialize(game), indent=2))
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
        from main import error, success
        if not SAVE_PATH.exists():
            if not quiet:
                error("No save file found.")
            return False
        try:
            SaveManager._deserialize(game, json.loads(SAVE_PATH.read_text()))
            if not quiet:
                success(f"Loaded from {SAVE_PATH}")
            return True
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            if not quiet:
                error(f"Load failed: {exc}")
            return False

    @staticmethod
    def _serialize(game: Game) -> dict:
        p = game.player
        return {
            "player": {
                "phase": p.phase, "tutorial_step": p.tutorial_step,
                "tutorial_credits": p.tutorial_credits, "money": p.money,
                "cpu_level": p.cpu_level, "firewall_level": p.firewall_level,
                "cracker_tier": p.cracker_tier, "vpn_licensed": p.vpn_licensed,
                "reputation": p.reputation, "rank_index": p.rank_index,
                "chaos_unlocked": p.chaos_unlocked,
                "routes": [(r.destination, r.gateway, r.iface) for r in p.routes],
                "discovered_ips": list(p.discovered_ips),
                "owned_tools": list(p.owned_tools),
                "command_history": list(p.command_history),
                "tutorial_flags": list(p.tutorial_flags),
                "ticks": p.ticks,
                "subnets_scanned": list(p.subnets_scanned),
                "privesc_hosts": list(p.privesc_hosts),
                "downloads": [k for k in p.files if "/downloads/" in k],
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
                 "grade": getattr(m, "grade", "")}
                for m in game.missions.missions
            ],
            "mail": [{"mail_id": m.mail_id, "sender": m.sender, "subject": m.subject,
                      "body": m.body, "read": m.read, "timestamp": m.timestamp}
                     for m in game.mail.messages],
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
        }

    @staticmethod
    def _deserialize(game: Game, data: dict) -> None:
        from main import MailMessage, Mission, Route, VirtualFile
        from retention import RetentionManager, RetentionState
        from session_content import LateralManager, SessionState

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
                for path in v:
                    if path not in p.files:
                        p.files[path] = VirtualFile(path, "restored\n")
            elif k == "subnets_scanned":
                p.subnets_scanned = set(v)
            elif k == "privesc_hosts":
                p.privesc_hosts = set(v)
            elif hasattr(p, k):
                setattr(p, k, v)

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
            ))

        game.mail.messages = [MailMessage(**md) for md in data["mail"]]
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
        if p.phase == "career":
            game.network.deploy_company_hosts(p.reputation, p.chaos_unlocked)
            RetentionManager.on_career_session(game)
            from session_content import HourlyManager
            HourlyManager.refresh(game)


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
    return s
