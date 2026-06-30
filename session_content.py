#!/usr/bin/env python3
"""Session depth: lateral chains, mastery grades, hourly flash events."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from main import Game, Mission

# ---------------------------------------------------------------------------
# Lateral movement chains
# ---------------------------------------------------------------------------

LATERAL_CHAINS: list[dict[str, Any]] = [
    {
        "id": "chain-vendor-dc",
        "name": "Pivot: Vendor → Domain Controller",
        "broker": "ghost_broker",
        "min_rep": 150,
        "reward": 1800,
        "rep_reward": 140,
        "briefing": "LATERAL: Compromise vendor-vpn, steal pivot intel, hit corp-dc, exfil secrets.",
        "steps": [
            {"type": "crack", "ip": "192.168.1.30", "label": "Own vendor-vpn jump box"},
            {"type": "read_intel", "ip": "192.168.1.30", "file": "/home/admin/pivot_notes.txt",
             "unlock_ip": "10.0.0.42", "label": "Read pivot notes on vendor-vpn"},
            {"type": "crack", "ip": "10.0.0.42", "needs_pivot": True,
             "label": "Pivot — crack corp-dc with stolen intel"},
            {"type": "exfil", "ip": "10.0.0.42", "file": "/home/admin/corporate_secrets.txt",
             "wipe": True, "label": "Exfil corporate_secrets.txt, leave zero traces"},
        ],
        "intel_files": {
            "192.168.1.30": {
                "/home/admin/pivot_notes.txt": (
                    "Internal pivot intel — CONFIDENTIAL\n\n"
                    "corp-dc (10.0.0.42) reuses legacy password from migration.\n"
                    "Password hint: corp42!\n"
                    "Route: 10.0.0.0/24 via 192.168.1.1\n"
                ),
            },
        },
    },
    {
        "id": "chain-gw-research",
        "name": "Pivot: Gateway → R&D Vault",
        "broker": "cipher7",
        "min_rep": 0,
        "reward": 1400,
        "rep_reward": 110,
        "briefing": "LATERAL: Breach corp-gateway, grab VPN config, pivot to research-node.",
        "steps": [
            {"type": "crack", "ip": "192.168.1.10", "label": "Crack corp-gateway"},
            {"type": "read_intel", "ip": "192.168.1.10", "file": "/home/admin/vpn_routes.txt",
             "unlock_ip": "192.168.1.25", "label": "Steal VPN route table from gateway"},
            {"type": "crack", "ip": "192.168.1.25", "needs_pivot": True,
             "label": "Pivot to research-node"},
            {"type": "exfil", "ip": "192.168.1.25", "file": "/home/admin/model_weights.bin",
             "wipe": True, "label": "Exfil model_weights.bin clean"},
        ],
        "intel_files": {
            "192.168.1.10": {
                "/home/admin/vpn_routes.txt": (
                    "VPN peer routes\nresearch-node: 192.168.1.25\n"
                    "SSH creds shared with lab segment (check auth.log...)\n",
                ),
            },
        },
    },
    {
        "id": "chain-hr-vault",
        "name": "Pivot: HR → Treasury Vault",
        "broker": "shade_runner",
        "min_rep": 150,
        "reward": 2200,
        "rep_reward": 160,
        "briefing": "LATERAL: HR portal leaks vault creds. Privesc on treasury, steal payroll.",
        "steps": [
            {"type": "crack", "ip": "10.0.0.88", "label": "Crack hr-portal"},
            {"type": "read_intel", "ip": "10.0.0.88", "file": "/home/admin/vault_hint.txt",
             "unlock_ip": "10.0.0.55", "label": "Find vault access notes in HR data"},
            {"type": "crack", "ip": "10.0.0.55", "needs_pivot": True,
             "label": "Pivot to vault-server"},
            {"type": "privesc", "ip": "10.0.0.55", "label": "Privesc on vault-server"},
            {"type": "exfil", "ip": "10.0.0.55", "file": "/root/payroll.csv",
             "wipe": True, "label": "Exfil payroll.csv as root"},
        ],
        "intel_files": {
            "10.0.0.88": {
                "/home/admin/vault_hint.txt": (
                    "IT ticket #8842: vault-server shared admin password rotated Q3.\n"
                    "Hint: qu4ntum_vault\n",
                ),
            },
        },
    },
    {
        "id": "chain-fin-wire",
        "name": "Pivot: Trading → Bank Core",
        "broker": "packet_queen",
        "min_rep": 400,
        "reward": 2800,
        "rep_reward": 190,
        "briefing": "LATERAL: fin-trading → steal SWIFT bridge creds → bank-core wire keys.",
        "steps": [
            {"type": "crack", "ip": "172.16.0.20", "label": "Crack fin-trading"},
            {"type": "read_intel", "ip": "172.16.0.20", "file": "/home/admin/bridge_hosts.txt",
             "unlock_ip": "172.16.0.33", "label": "Parse bridge hosts for bank-core pivot"},
            {"type": "crack", "ip": "172.16.0.33", "needs_pivot": True,
             "label": "Pivot to bank-core"},
            {"type": "privesc", "ip": "172.16.0.33", "label": "Privesc on bank-core"},
            {"type": "exfil", "ip": "172.16.0.33", "file": "/root/wire_keys.env",
             "wipe": True, "label": "Exfil wire_keys.env"},
        ],
        "intel_files": {
            "172.16.0.20": {
                "/home/admin/bridge_hosts.txt": (
                    "bank-core internal bridge: 172.16.0.33\n"
                    "Cross-segment auth via shared swift_key password.\n",
                ),
            },
        },
    },
    {
        "id": "chain-ghost-chaos",
        "name": "Pivot: Ghost Lane → Chaos Edge",
        "broker": "nullbyte",
        "min_rep": 750,
        "reward": 4500,
        "rep_reward": 280,
        "briefing": "LATERAL: Ghost vendor-vpn, raid research, scan chaos subnet for C2.",
        "steps": [
            {"type": "ghost", "ip": "192.168.1.30", "label": "Ghost-run vendor-vpn (zero traces)"},
            {"type": "crack", "ip": "192.168.1.25", "label": "Hit research-node"},
            {"type": "exfil", "ip": "192.168.1.25", "file": "/home/admin/model_weights.bin",
             "wipe": True, "label": "Exfil model weights clean"},
            {"type": "scan", "cidr": "203.0.113.0/24", "label": "Scan chaos subnet 203.0.113.0/24"},
        ],
        "intel_files": {},
    },
]

# ---------------------------------------------------------------------------
# Hourly flash events (rotate each real-world hour)
# ---------------------------------------------------------------------------

HOURLY_EVENTS: list[dict[str, Any]] = [
    {
        "id": "hour-gw", "title": "FLASH: Gateway Double Pay",
        "broker": "ghost_broker", "target_ip": "192.168.1.10",
        "target_file": "/home/admin/notes.txt", "multiplier": 2.0, "min_rep": 0,
    },
    {
        "id": "hour-vendor", "title": "FLASH: Vendor Ghost Bonus",
        "broker": "cipher7", "target_ip": "192.168.1.30",
        "target_file": "", "multiplier": 2.2, "min_rep": 0, "mission_type": "ghost",
    },
    {
        "id": "hour-hr", "title": "FLASH: HR Data Rush",
        "broker": "shade_runner", "target_ip": "10.0.0.88",
        "target_file": "/home/admin/terminations.csv", "multiplier": 2.0, "min_rep": 150,
    },
    {
        "id": "hour-research", "title": "FLASH: AI Weights Heist",
        "broker": "nullbyte", "target_ip": "192.168.1.25",
        "target_file": "/home/admin/model_weights.bin", "multiplier": 2.5, "min_rep": 0,
    },
    {
        "id": "hour-vault", "title": "FLASH: Vault Payroll",
        "broker": "packet_queen", "target_ip": "10.0.0.55",
        "target_file": "/root/payroll.csv", "multiplier": 2.0, "min_rep": 150,
        "require_privesc": True, "mission_type": "root_heist",
    },
    {
        "id": "hour-trading", "title": "FLASH: Algo Snatch",
        "broker": "cipher7", "target_ip": "172.16.0.20",
        "target_file": "/home/admin/algo_config.yml", "multiplier": 2.3, "min_rep": 400,
        "require_privesc": True, "mission_type": "root_heist",
    },
    {
        "id": "hour-chaos", "title": "FLASH: Chaos C2 Takedown",
        "broker": "shade_runner", "target_ip": "203.0.113.66",
        "target_file": "/root/rival_plans.txt", "multiplier": 3.0, "min_rep": 750,
        "require_privesc": True, "mission_type": "root_heist",
    },
    {
        "id": "hour-dc", "title": "FLASH: Board Secrets",
        "broker": "ghost_broker", "target_ip": "10.0.0.42",
        "target_file": "/home/admin/corporate_secrets.txt", "multiplier": 2.0, "min_rep": 150,
    },
]

GRADE_MULTIPLIERS = {"S": 1.5, "A": 1.25, "B": 1.0, "C": 0.85}
GRADE_REP_BONUS = {"S": 40, "A": 20, "B": 0, "C": 0}


@dataclass
class SessionState:
    # Lateral
    active_chain_id: str = ""
    chain_step: int = 0
    chain_steps_done: list[str] = field(default_factory=list)
    completed_chains: list[str] = field(default_factory=list)
    unlocked_pivots: set[str] = field(default_factory=set)
    # Mastery
    mastery_mission_id: str = ""
    mastery_commands: int = 0
    mastery_start_money: int = 0
    mastery_shop_spent: int = 0
    mastery_vpn_used: bool = False
    best_grades: dict[str, str] = field(default_factory=dict)
    s_rank_total: int = 0
    # Hourly
    hourly_slot: int = 0
    hourly_event_id: str = ""
    hourly_mission_id: str = ""
    hourly_completed: bool = False
    hourly_completions: int = 0


class LateralManager:
    @staticmethod
    def chain_by_id(chain_id: str) -> dict | None:
        return next((c for c in LATERAL_CHAINS if c["id"] == chain_id), None)

    @staticmethod
    def available_chains(game: Game) -> list[dict]:
        s = game.session
        return [
            c for c in LATERAL_CHAINS
            if c["id"] not in s.completed_chains
            and game.player.reputation >= c.get("min_rep", 0)
            and game.player.has_route_to(
                next((st["ip"] for st in c["steps"] if st.get("ip")), "192.168.1.10")
            )
        ]

    @staticmethod
    def start_chain(game: Game, chain_id: str) -> bool:
        from main import Mission, error, success, teach

        chain = LateralManager.chain_by_id(chain_id)
        if not chain:
            error(f"Unknown chain '{chain_id}'.")
            return False
        if chain_id in game.session.completed_chains:
            error("Chain already completed.")
            return False
        if game.session.active_chain_id:
            error("Finish the active lateral chain first.")
            return False
        if game.player.reputation < chain.get("min_rep", 0):
            error(f"Need {chain['min_rep']} rep for this chain.")
            return False

        LateralManager._inject_intel_files(game, chain)
        game.session.active_chain_id = chain_id
        game.session.chain_step = 0
        game.session.chain_steps_done = []

        mid = f"lateral-{chain_id}"
        if not any(m.mission_id == mid for m in game.missions.missions):
            step = chain["steps"][0]
            game.missions.missions.insert(
                0,
                Mission(
                    mid, chain["broker"], f"[LATERAL 1/{len(chain['steps'])}] {step['label']}",
                    step.get("ip", ""), step.get("file", ""),
                    chain["reward"], rep_reward=chain["rep_reward"],
                    mission_type="lateral", lateral_chain_id=chain_id,
                ),
            )
        success(f"Lateral chain started: {chain['name']}")
        teach("Pivot through hosts — read intel files for credentials to the next hop.")
        game.mail.send(
            f"{chain['broker']}@darknet",
            f"LATERAL CHAIN: {chain['name']}",
            f"{chain['briefing']}\n\nStep 1: {chain['steps'][0]['label']}\n\n— {chain['broker']}",
        )
        return True

    @staticmethod
    def _inject_intel_files(game: Game, chain: dict) -> None:
        from main import VirtualFile

        for ip, files in chain.get("intel_files", {}).items():
            server = game.network.get_server(ip)
            if not server:
                continue
            for path, body in files.items():
                if path not in server.files:
                    server.files[path] = VirtualFile(path, body)

    @staticmethod
    def active_step(game: Game) -> dict | None:
        chain = LateralManager.chain_by_id(game.session.active_chain_id)
        if not chain:
            return None
        idx = game.session.chain_step
        if idx >= len(chain["steps"]):
            return None
        return chain["steps"][idx]

    @staticmethod
    def pivot_blocked(game: Game, ip: str) -> str | None:
        """Return error message if lateral chain blocks cracking this IP."""
        step = LateralManager.active_step(game)
        if not step or step["type"] != "crack" or step.get("ip") != ip:
            return None
        unlock = step.get("unlock_ip")
        if step.get("needs_pivot") or unlock:
            pivot = unlock or ip
            if pivot not in game.session.unlocked_pivots:
                if f"pivot_unlock_{pivot}" not in game.player.tutorial_flags:
                    return f"Need pivot intel before cracking {ip}. Read intel on prior host."
        return None

    @staticmethod
    def on_crack(game: Game, ip: str) -> None:
        step = LateralManager.active_step(game)
        if not step or step["type"] != "crack" or step.get("ip") != ip:
            return
        LateralManager._advance(game, step)

    @staticmethod
    def on_ghost(game: Game, ip: str) -> None:
        step = LateralManager.active_step(game)
        if not step or step["type"] != "ghost" or step.get("ip") != ip:
            return
        if ip not in game.retention.ghost_targets_done:
            return
        LateralManager._advance(game, step)

    @staticmethod
    def on_read_intel(game: Game, path: str) -> None:
        step = LateralManager.active_step(game)
        if not step or step["type"] != "read_intel":
            return
        server = game.remote_server() if hasattr(game, "remote_server") else None
        if not server or server.ip != step.get("ip"):
            return
        if path != step.get("file"):
            return
        unlock = step.get("unlock_ip")
        if unlock:
            game.session.unlocked_pivots.add(unlock)
            game.player.tutorial_flags.add(f"pivot_unlock_{unlock}")
            from main import teach
            teach(f"Pivot intel acquired — {unlock} is reachable. Password hints in file.")
        LateralManager._advance(game, step)

    @staticmethod
    def on_privesc(game: Game, ip: str) -> None:
        step = LateralManager.active_step(game)
        if not step or step["type"] != "privesc" or step.get("ip") != ip:
            return
        LateralManager._advance(game, step)

    @staticmethod
    def on_scan(game: Game, cidr: str) -> None:
        step = LateralManager.active_step(game)
        if not step or step["type"] != "scan" or step.get("cidr") != cidr:
            return
        LateralManager._advance(game, step)

    @staticmethod
    def on_exfil_step(game: Game, ip: str, path: str) -> None:
        step = LateralManager.active_step(game)
        if not step or step["type"] != "exfil":
            return
        if step.get("ip") != ip or step.get("file") != path:
            return
        server = game.network.get_server(ip)
        if step.get("wipe") and server and server.player_left_traces(game.player):
            return
        LateralManager._advance(game, step)

    @staticmethod
    def _advance(game: Game, step: dict) -> None:
        from main import success

        chain = LateralManager.chain_by_id(game.session.active_chain_id)
        if not chain:
            return
        tag = f"{chain['id']}:{game.session.chain_step}"
        if tag in game.session.chain_steps_done:
            return
        game.session.chain_steps_done.append(tag)
        game.session.chain_step += 1
        success(f"Lateral step complete: {step['label']}")

        if game.session.chain_step >= len(chain["steps"]):
            LateralManager._complete_chain(game, chain)
            return

        nxt = chain["steps"][game.session.chain_step]
        for m in game.missions.missions:
            if m.lateral_chain_id == chain["id"]:
                m.briefing = f"[LATERAL {game.session.chain_step + 1}/{len(chain['steps'])}] {nxt['label']}"
                m.target_ip = nxt.get("ip", "")
                m.target_file = nxt.get("file", "")
                break

    @staticmethod
    def _complete_chain(game: Game, chain: dict) -> None:
        from main import success

        cid = chain["id"]
        game.session.completed_chains.append(cid)
        game.session.active_chain_id = ""
        if len(game.session.completed_chains) >= 5:
            game.achievements.unlock("chain_master")
        success(f"LATERAL CHAIN COMPLETE: {chain['name']}")
        game.mail.send(
            f"{chain['broker']}@darknet",
            f"Chain cleared — {chain['name']}",
            f"Full pivot path executed. Payment incoming.\n\n— {chain['broker']}",
        )

    @staticmethod
    def is_chain_satisfied(game: Game, mission: Mission) -> bool:
        if not mission.lateral_chain_id:
            return False
        return mission.lateral_chain_id in game.session.completed_chains


class MasteryGrader:
    @staticmethod
    def begin(game: Game, mission_id: str) -> None:
        s = game.session
        if s.mastery_mission_id == mission_id:
            return
        s.mastery_mission_id = mission_id
        s.mastery_commands = 0
        s.mastery_start_money = game.player.money
        s.mastery_shop_spent = 0
        s.mastery_vpn_used = game.player.vpn_active

    @staticmethod
    def on_command(game: Game) -> None:
        if game.session.mastery_mission_id:
            game.session.mastery_commands += 1
        if game.player.vpn_active:
            game.session.mastery_vpn_used = True

    @staticmethod
    def on_shop_spend(game: Game, amount: int) -> None:
        if game.session.mastery_mission_id:
            game.session.mastery_shop_spent += amount

    @staticmethod
    def grade(game: Game, mission: Mission) -> tuple[str, float, str]:
        p = game.player
        s = game.session
        server = game.network.get_server(mission.target_ip) if mission.target_ip else None

        score = 100
        notes: list[str] = []

        if server and server.player_left_traces(p):
            score -= 35
            notes.append("log traces (-35)")
        elif mission.require_log_wipe and server:
            notes.append("clean logs (+)")

        if s.mastery_commands <= 15:
            notes.append("fast run (+)")
        elif s.mastery_commands <= 25:
            score -= 10
            notes.append(f"{s.mastery_commands} commands (-10)")
        else:
            score -= 25
            notes.append(f"{s.mastery_commands} commands (-25)")

        if s.mastery_shop_spent > 0:
            score -= 10
            notes.append("shop buys during contract (-10)")

        if s.mastery_vpn_used or p.vpn_active:
            notes.append("VPN used (+)")
        elif mission.require_log_wipe:
            score -= 5
            notes.append("no VPN (-5)")

        if score >= 90:
            grade = "S"
        elif score >= 75:
            grade = "A"
        elif score >= 60:
            grade = "B"
        else:
            grade = "C"

        prev = s.best_grades.get(mission.mission_id)
        if not prev or "SABCD".index(grade) < "SABCD".index(prev):
            s.best_grades[mission.mission_id] = grade
        if grade == "S":
            s.s_rank_total += 1
            if s.s_rank_total >= 10:
                game.achievements.unlock("grade_s_master")

        mult = GRADE_MULTIPLIERS[grade]
        summary = f"Grade {grade} ({score}/100): " + ", ".join(notes)
        s.mastery_mission_id = ""
        return grade, mult, summary

    @staticmethod
    def rep_bonus(grade: str) -> int:
        return GRADE_REP_BONUS.get(grade, 0)


class HourlyManager:
    @staticmethod
    def current_slot() -> int:
        return int(time.time() // 3600)

    @staticmethod
    def refresh(game: Game) -> None:
        from main import Mission

        if game.player.phase != "career":
            return
        slot = HourlyManager.current_slot()
        s = game.session
        if s.hourly_slot == slot:
            return

        s.hourly_slot = slot
        s.hourly_completed = False
        # Remove expired hourly missions
        game.missions.missions = [m for m in game.missions.missions if not m.hourly_event]

        spec = HOURLY_EVENTS[slot % len(HOURLY_EVENTS)]
        if game.player.reputation < spec.get("min_rep", 0):
            return

        base = 500
        mid = f"{spec['id']}-{slot}"
        mtype = spec.get("mission_type", "exfil")
        m = Mission(
            mid, spec["broker"],
            f"HOURLY FLASH ({spec['multiplier']}x): {spec['title']} — expires top of next hour",
            spec["target_ip"], spec.get("target_file", "/home/admin/notes.txt"),
            base, rep_reward=int(60 * spec["multiplier"]),
            mission_type=mtype,
            require_privesc=spec.get("require_privesc", False),
            hourly_event=True,
            reward_multiplier=spec["multiplier"],
        )
        if mtype == "ghost":
            m.target_file = ""
        game.missions.missions.insert(0, m)
        s.hourly_mission_id = mid
        game.mail.send(
            f"{spec['broker']}@darknet",
            f"⚡ HOURLY FLASH: {spec['title']}",
            f"Target: {spec['target_ip']}\n"
            f"Pay multiplier: {spec['multiplier']}x\n"
            "Expires at the top of the next hour.\n\n"
            f"— {spec['broker']}",
        )

    @staticmethod
    def on_complete(game: Game, mission: Mission) -> None:
        if not mission.hourly_event:
            return
        game.session.hourly_completed = True
        game.session.hourly_completions += 1
        if game.session.hourly_completions >= 10:
            game.achievements.unlock("hourly_hunter")
        from retention import RetentionManager
        RetentionManager.add_season_xp(game, 100, "hourly flash event")

    @staticmethod
    def time_remaining() -> str:
        secs = 3600 - (int(time.time()) % 3600)
        return f"{secs // 60}m {secs % 60}s"
