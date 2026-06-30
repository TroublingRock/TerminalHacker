#!/usr/bin/env python3
"""Month-long retention: login streaks, 30-day season, weekly bounties, operation arcs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from main import Game, Mission

# ---------------------------------------------------------------------------
# Login streak — escalating cash + season XP
# ---------------------------------------------------------------------------

STREAK_MILESTONES: dict[int, tuple[int, int, str]] = {
    # day: (cash, season_xp, message)
    1: (75, 25, "Day 1 check-in — stay in the fight."),
    3: (150, 40, "3-day streak. Brokers are watching."),
    7: (400, 100, "Week one locked in. Bonus intel incoming."),
    14: (800, 175, "Two weeks straight. You're reliable."),
    21: (1200, 250, "Three-week streak — elite contractor status."),
    30: (3000, 500, "MONTH STREAK. Net God clearance unlocked in brokers' eyes."),
}

# ---------------------------------------------------------------------------
# 31 unique daily challenges — one per slot in the monthly rotation
# ---------------------------------------------------------------------------

DAILY_ROTATION: list[tuple[str, str, int, str]] = [
    ("d01", "Crack any host without VPN", 275, "no_vpn"),
    ("d02", "Disconnect leaving zero log traces", 325, "zero_trace"),
    ("d03", "Purchase any shop upgrade", 175, "buy"),
    ("d04", "Privilege escalate on a target", 375, "privesc"),
    ("d05", "Firewall blocks a rival attack", 225, "block"),
    ("d06", "Scan 3 different subnets", 200, "scan3"),
    ("d07", "Crack a host while VPN is active", 250, "vpn_crack"),
    ("d08", "Probe a host then crack it same session", 225, "probe_crack"),
    ("d09", "Download a file and wipe remote logs", 300, "exfil_wipe"),
    ("d10", "Run defend on and block an attack", 275, "defend_block"),
    ("d11", "Crack a security level 3+ host", 350, "hard_crack"),
    ("d12", "Complete any open contract", 400, "contract_done"),
    ("d13", "Earn $500 from hacks or contracts", 300, "earn500"),
    ("d14", "Use route add to reach a new subnet", 200, "new_route"),
    ("d15", "Read auth.log on a compromised host", 175, "read_auth"),
    ("d16", "Crack two different hosts today", 450, "two_cracks"),
    ("d17", "Upgrade CPU or firewall", 200, "gear_up"),
    ("d18", "Exfil from a 10.0.0.x corporate host", 350, "corp_exfil"),
    ("d19", "Survive a rival attack without breach", 250, "survive_rival"),
    ("d20", "Request a new procedural contract", 150, "request_contract"),
    ("d21", "Privesc and download a root-only file", 500, "root_exfil"),
    ("d22", "Scan the finance subnet 172.16.0.0/24", 225, "scan_finance"),
    ("d23", "Crack without buying anything today", 275, "no_shop"),
    ("d24", "Wipe both syslog and auth.log remotely", 300, "double_wipe"),
    ("d25", "Earn 50+ reputation in one session", 400, "rep_burst"),
    ("d26", "Block a rival while defense mode is on", 300, "active_defense"),
    ("d27", "Download from a host you privesc'd on", 375, "privesc_dl"),
    ("d28", "Scan chaos subnet 203.0.113.0/24", 350, "scan_chaos"),
    ("d29", "Complete a ghost-run contract (zero traces)", 450, "ghost_contract"),
    ("d30", "Earn $1000 in a single day", 600, "big_payday"),
    ("d31", "Complete your weekly bounty", 500, "weekly_bounty"),
]

DAILY_FLAGS: dict[str, str] = {
    "no_vpn": "daily_no_vpn_done",
    "zero_trace": "daily_zero_trace_done",
    "buy": "daily_buy_done",
    "privesc": "daily_privesc_done",
    "block": "daily_block_done",
    "scan3": "daily_scan3_done",
    "vpn_crack": "daily_vpn_crack_done",
    "probe_crack": "daily_probe_crack_done",
    "exfil_wipe": "daily_exfil_wipe_done",
    "defend_block": "daily_defend_block_done",
    "hard_crack": "daily_hard_crack_done",
    "contract_done": "daily_contract_done",
    "earn500": "daily_earn500_done",
    "new_route": "daily_new_route_done",
    "read_auth": "daily_read_auth_done",
    "two_cracks": "daily_two_cracks_done",
    "gear_up": "daily_gear_up_done",
    "corp_exfil": "daily_corp_exfil_done",
    "survive_rival": "daily_survive_done",
    "request_contract": "daily_request_done",
    "root_exfil": "daily_root_exfil_done",
    "scan_finance": "daily_scan_finance_done",
    "no_shop": "daily_no_shop_done",
    "double_wipe": "daily_double_wipe_done",
    "rep_burst": "daily_rep_burst_done",
    "active_defense": "daily_active_defense_done",
    "privesc_dl": "daily_privesc_dl_done",
    "scan_chaos": "daily_scan_chaos_done",
    "ghost_contract": "daily_ghost_contract_done",
    "big_payday": "daily_big_payday_done",
    "weekly_bounty": "daily_weekly_bounty_done",
}

# ---------------------------------------------------------------------------
# 30-tier season track (~120 XP/day for 30 days)
# ---------------------------------------------------------------------------

SEASON_TIERS: list[dict[str, Any]] = [
    {"xp": 80, "cash": 100, "rep": 10, "label": "Starter kit"},
    {"xp": 100, "cash": 125, "rep": 15, "label": "Recon stipend"},
    {"xp": 100, "cash": 150, "rep": 15, "label": "Tool fund"},
    {"xp": 120, "cash": 175, "rep": 20, "label": "Broker intro"},
    {"xp": 120, "cash": 200, "rep": 20, "label": "Route voucher"},
    {"xp": 130, "cash": 225, "rep": 25, "label": "VPN credit"},
    {"xp": 130, "cash": 250, "rep": 25, "label": "Firewall coupon"},
    {"xp": 140, "cash": 275, "rep": 30, "label": "Intel drop"},
    {"xp": 140, "cash": 300, "rep": 30, "label": "Mid-season bonus"},
    {"xp": 150, "cash": 350, "rep": 35, "label": "Tier 10 — Operator"},
    {"xp": 150, "cash": 375, "rep": 35, "label": "Crack bounty boost"},
    {"xp": 160, "cash": 400, "rep": 40, "label": "Stealth module"},
    {"xp": 160, "cash": 425, "rep": 40, "label": "Rival dossier"},
    {"xp": 170, "cash": 450, "rep": 45, "label": "Corporate pass"},
    {"xp": 170, "cash": 500, "rep": 45, "label": "Tier 15 — Specialist"},
    {"xp": 180, "cash": 550, "rep": 50, "label": "Finance sector tip"},
    {"xp": 180, "cash": 600, "rep": 50, "label": "IDS blueprint"},
    {"xp": 190, "cash": 650, "rep": 55, "label": "Ghost protocol"},
    {"xp": 190, "cash": 700, "rep": 55, "label": "Broker trust"},
    {"xp": 200, "cash": 750, "rep": 60, "label": "Tier 20 — Veteran"},
    {"xp": 200, "cash": 800, "rep": 65, "label": "Chaos whisper"},
    {"xp": 210, "cash": 850, "rep": 70, "label": "Darknet map"},
    {"xp": 210, "cash": 900, "rep": 75, "label": "Zero-day rumor"},
    {"xp": 220, "cash": 950, "rep": 80, "label": "Elite contract slot"},
    {"xp": 220, "cash": 1000, "rep": 85, "label": "Tier 25 — Phantom"},
    {"xp": 230, "cash": 1100, "rep": 90, "label": "Net God preview"},
    {"xp": 230, "cash": 1200, "rep": 95, "label": "Legend cache"},
    {"xp": 240, "cash": 1300, "rep": 100, "label": "Final approach"},
    {"xp": 240, "cash": 1400, "rep": 110, "label": "Penultimate tier"},
    {"xp": 250, "cash": 2500, "rep": 200, "label": "SEASON COMPLETE — Net God frame"},
]

SEASON_XP_CONTRACT = 60
SEASON_XP_DAILY = 75
SEASON_XP_WEEKLY = 200
SEASON_XP_OPERATION = 120

# ---------------------------------------------------------------------------
# Weekly bounties — rotate by ISO week
# ---------------------------------------------------------------------------

WEEKLY_BOUNTIES: list[dict[str, Any]] = [
    {
        "id": "wb-nova-gw",
        "broker": "ghost_broker",
        "title": "NovaDyne Perimeter Breach",
        "briefing": "WEEKLY: Crack corp-gateway (192.168.1.10), exfil any file, vanish clean.",
        "target_ip": "192.168.1.10",
        "target_file": "/home/admin/notes.txt",
        "reward": 900,
        "rep_reward": 90,
        "min_rep": 0,
    },
    {
        "id": "wb-vendor",
        "broker": "cipher7",
        "title": "CipherLink Compromise",
        "briefing": "WEEKLY: Hit vendor-vpn (192.168.1.30). Ghost run — zero traces, no exfil needed.",
        "target_ip": "192.168.1.30",
        "target_file": "",
        "reward": 1100,
        "rep_reward": 110,
        "min_rep": 0,
        "mission_type": "ghost",
    },
    {
        "id": "wb-hr",
        "broker": "shade_runner",
        "title": "HR Data Raid",
        "briefing": "WEEKLY: Steal terminations.csv from hr-portal (10.0.0.88), wipe logs.",
        "target_ip": "10.0.0.88",
        "target_file": "/home/admin/terminations.csv",
        "reward": 1400,
        "rep_reward": 130,
        "min_rep": 150,
    },
    {
        "id": "wb-trading",
        "broker": "packet_queen",
        "title": "Helix Algo Heist",
        "briefing": "WEEKLY: Privesc on fin-trading (172.16.0.20), exfil algo_config.yml.",
        "target_ip": "172.16.0.20",
        "target_file": "/home/admin/algo_config.yml",
        "reward": 2000,
        "rep_reward": 160,
        "min_rep": 400,
        "require_privesc": True,
        "mission_type": "root_heist",
    },
    {
        "id": "wb-research",
        "broker": "nullbyte",
        "title": "AI Model Extraction",
        "briefing": "WEEKLY: Steal model_weights.bin from research-node (192.168.1.25).",
        "target_ip": "192.168.1.25",
        "target_file": "/home/admin/model_weights.bin",
        "reward": 1250,
        "rep_reward": 115,
        "min_rep": 0,
    },
    {
        "id": "wb-vault",
        "broker": "cipher7",
        "title": "Treasury Vault Raid",
        "briefing": "WEEKLY: Privesc vault-server (10.0.0.55), exfil payroll.csv as root.",
        "target_ip": "10.0.0.55",
        "target_file": "/root/payroll.csv",
        "reward": 2200,
        "rep_reward": 175,
        "min_rep": 150,
        "require_privesc": True,
        "mission_type": "root_heist",
    },
    {
        "id": "wb-chaos-c2",
        "broker": "shade_runner",
        "title": "C2 Takedown",
        "briefing": "WEEKLY: Crack chaos-c2 (203.0.113.66), exfil rival_plans.txt, survive traces.",
        "target_ip": "203.0.113.66",
        "target_file": "/root/rival_plans.txt",
        "reward": 3500,
        "rep_reward": 200,
        "min_rep": 750,
        "require_privesc": True,
        "mission_type": "root_heist",
    },
    {
        "id": "wb-dark-vault",
        "broker": "packet_queen",
        "title": "Cold Wallet Job",
        "briefing": "WEEKLY: Hit dark-vault (203.0.113.99) — root heist on cold_wallet.dat.",
        "target_ip": "203.0.113.99",
        "target_file": "/root/cold_wallet.dat",
        "reward": 5000,
        "rep_reward": 250,
        "min_rep": 750,
        "require_privesc": True,
        "mission_type": "root_heist",
    },
]

# ---------------------------------------------------------------------------
# Weekly story mail — narrative beat each Monday (ties to bounty + season arc)
# ---------------------------------------------------------------------------

WEEKLY_STORY_MAIL: list[dict[str, str]] = [
    {
        "sender": "ghost_broker@darknet",
        "subject": "WEEK 1 INTEL — NovaDyne's perimeter is soft",
        "body": (
            "Operator,\n\n"
            "Welcome to the live board. NovaDyne Corp thought their gateway was hardened — "
            "it isn't. CipherLink left a vendor jump box wide open on the lab subnet.\n\n"
            "This week: breach the perimeter or ghost the vendor box. Brokers are grading "
            "your tradecraft, not just your loot.\n\n"
            "Rivals haven't noticed you yet. That changes soon.\n\n"
            "— ghost_broker"
        ),
    },
    {
        "sender": "cipher7@darknet",
        "subject": "WEEK 2 INTEL — Helix Capital bleeds data",
        "body": (
            "cipher7 here.\n\n"
            "Helix Capital's HFT rigs went live last quarter. Their algo configs are worth "
            "more than cash — every hedge fund on the darknet wants fin-trading (172.16.0.20).\n\n"
            "NovaDyne HR also has dirt: terminations.csv on hr-portal lists who's 'disappeared' "
            "before the merger. Steal it if you want leverage.\n\n"
            "ghost_broker says you're reliable. Prove it.\n\n"
            "— cipher7"
        ),
    },
    {
        "sender": "ghost_broker@darknet",
        "subject": "WEEK 3 INTEL — Rivals are mapping your IP",
        "body": (
            "Operator,\n\n"
            "acid_k ran a probe on your public address. Your firewall held — barely. "
            "Turn on defense mode and treat blue-team as billable work.\n\n"
            "NovaDyne R&D has prototype weights on research-node. Treasury vault-server "
            "holds payroll keys the board doesn't want leaked.\n\n"
            "Multi-day operations are live on your board. Finish what you start — "
            "phases unlock daily.\n\n"
            "— ghost_broker"
        ),
    },
    {
        "sender": "nullbyte@darknet",
        "subject": "WEEK 4 INTEL — Chaos subnet is calling",
        "body": (
            "nullbyte.\n\n"
            "You've earned whispers about 203.0.113.0/24 — the chaos edge. Rival collective "
            "C2 nodes live there. Trace chance doubles. Rewards triple.\n\n"
            "Operation Dark Echo was practice. The real prize is chaos-c2 and dark-vault. "
            "You need Ghost in the Wires clearance and maxed gear.\n\n"
            "Week 4 bounty is not for amateurs. Neither is the season finale.\n\n"
            "— nullbyte"
        ),
    },
]

WEEKLY_RIVAL_MAIL: list[dict[str, str]] = [
    {
        "sender": "acid_k@rival.net",
        "subject": "I see you on the NovaDyne board",
        "body": (
            "So the training wheels are off.\n\n"
            "I watched you hit the gateway. Cute. My crew owns half the 10.0.0.x segment — "
            "stay in your lane or I'll drain your wallet.\n\n"
            "— acid_k"
        ),
    },
    {
        "sender": "phantom_pkt@rival.net",
        "subject": "Helix is OUR mark",
        "body": (
            "Finance sector is contested territory.\n\n"
            "Fin-trading IDS is tuned for script kiddies, not me. You're not me. "
            "Back off Helix or I'll publish your public IP to every blue team in the city.\n\n"
            "— phantom_pkt"
        ),
    },
    {
        "sender": "nyx_root@rival.net",
        "subject": "Defense mode won't save you",
        "body": (
            "I saw your firewall block. Once.\n\n"
            "Rivals adapt. Your IDS is a toy. I'm mapping your box while you play hero "
            "on corporate subnets.\n\n"
            "— nyx_root"
        ),
    },
    {
        "sender": "zero_cool@rival.net",
        "subject": "Chaos is where operators go to die",
        "body": (
            "203.0.113.x isn't a playground.\n\n"
            "I lost two accounts on chaos-c2 last month. Forensics triple-tap anyone who "
            "touches the dark vault. You want Net God? Earn it.\n\n"
            "— zero_cool"
        ),
    },
]

# ---------------------------------------------------------------------------
# Multi-day operation arcs (3 parts each — next part unlocks next calendar day)
# ---------------------------------------------------------------------------

OPERATIONS: list[dict[str, Any]] = [
    {
        "id": "op-nova",
        "name": "Operation Glass Firewall",
        "broker": "ghost_broker",
        "parts": [
            {
                "step": 1,
                "briefing": "OP DAY 1: Recon NovaDyne gateway (192.168.1.10) — scan and probe it.",
                "target_ip": "192.168.1.10",
                "mission_type": "recon",
                "reward": 300,
                "rep_reward": 40,
            },
            {
                "step": 2,
                "briefing": "OP DAY 2: Crack corp-gateway, exfil notes.txt, wipe logs.",
                "target_ip": "192.168.1.10",
                "target_file": "/home/admin/notes.txt",
                "mission_type": "exfil",
                "reward": 600,
                "rep_reward": 70,
            },
            {
                "step": 3,
                "briefing": "OP DAY 3: Pivot — crack corp-dc (10.0.0.42), steal corporate_secrets.txt.",
                "target_ip": "10.0.0.42",
                "target_file": "/home/admin/corporate_secrets.txt",
                "mission_type": "exfil",
                "reward": 1200,
                "rep_reward": 120,
            },
        ],
    },
    {
        "id": "op-helix",
        "name": "Operation Bull Market",
        "broker": "cipher7",
        "parts": [
            {
                "step": 1,
                "briefing": "OP DAY 1: Scan finance subnet 172.16.0.0/24 and probe fin-trading.",
                "target_ip": "172.16.0.20",
                "mission_type": "recon",
                "reward": 350,
                "rep_reward": 45,
            },
            {
                "step": 2,
                "briefing": "OP DAY 2: Crack fin-trading, privesc, download algo_config.yml.",
                "target_ip": "172.16.0.20",
                "target_file": "/home/admin/algo_config.yml",
                "mission_type": "root_heist",
                "require_privesc": True,
                "reward": 900,
                "rep_reward": 100,
            },
            {
                "step": 3,
                "briefing": "OP DAY 3: Hit bank-core (172.16.0.33), exfil wire_keys.env as root.",
                "target_ip": "172.16.0.33",
                "target_file": "/root/wire_keys.env",
                "mission_type": "root_heist",
                "require_privesc": True,
                "reward": 1800,
                "rep_reward": 150,
            },
        ],
    },
    {
        "id": "op-shadow",
        "name": "Operation Dark Echo",
        "broker": "nullbyte",
        "parts": [
            {
                "step": 1,
                "briefing": "OP DAY 1: Ghost run on vendor-vpn — crack, zero traces, disconnect.",
                "target_ip": "192.168.1.30",
                "mission_type": "ghost",
                "reward": 500,
                "rep_reward": 60,
            },
            {
                "step": 2,
                "briefing": "OP DAY 2: Crack research-node, exfil model_weights.bin, wipe logs.",
                "target_ip": "192.168.1.25",
                "target_file": "/home/admin/model_weights.bin",
                "mission_type": "exfil",
                "reward": 800,
                "rep_reward": 90,
            },
            {
                "step": 3,
                "briefing": "OP DAY 3: Chaos prep — scan 203.0.113.0/24 (route required).",
                "target_ip": "",
                "mission_type": "scan_chaos",
                "reward": 1000,
                "rep_reward": 110,
            },
        ],
    },
    {
        "id": "op-treasury",
        "name": "Operation Quantum Ledger",
        "broker": "cipher7",
        "min_rep": 150,
        "parts": [
            {
                "step": 1,
                "briefing": "OP DAY 1: Recon vault-server (10.0.0.55) — scan DMZ and probe.",
                "target_ip": "10.0.0.55",
                "mission_type": "recon",
                "reward": 400,
                "rep_reward": 50,
            },
            {
                "step": 2,
                "briefing": "OP DAY 2: Crack vault-server, privesc to root.",
                "target_ip": "10.0.0.55",
                "mission_type": "ghost",
                "reward": 700,
                "rep_reward": 80,
            },
            {
                "step": 3,
                "briefing": "OP DAY 3: Exfil payroll.csv from vault-server as root, wipe logs.",
                "target_ip": "10.0.0.55",
                "target_file": "/root/payroll.csv",
                "mission_type": "root_heist",
                "require_privesc": True,
                "reward": 1500,
                "rep_reward": 130,
            },
        ],
    },
    {
        "id": "op-research",
        "name": "Operation Stolen Weights",
        "broker": "nullbyte",
        "min_rep": 0,
        "parts": [
            {
                "step": 1,
                "briefing": "OP DAY 1: Scan lab subnet for research-node (192.168.1.25).",
                "target_ip": "192.168.1.0/24",
                "mission_type": "scan_subnet",
                "reward": 350,
                "rep_reward": 45,
            },
            {
                "step": 2,
                "briefing": "OP DAY 2: Crack research-node, exfil model_weights.bin.",
                "target_ip": "192.168.1.25",
                "target_file": "/home/admin/model_weights.bin",
                "mission_type": "exfil",
                "reward": 850,
                "rep_reward": 95,
            },
            {
                "step": 3,
                "briefing": "OP DAY 3: Ghost run on corp-gateway to cover your tracks.",
                "target_ip": "192.168.1.10",
                "mission_type": "ghost",
                "reward": 950,
                "rep_reward": 100,
            },
        ],
    },
    {
        "id": "op-hr",
        "name": "Operation Paper Trail",
        "broker": "shade_runner",
        "min_rep": 150,
        "parts": [
            {
                "step": 1,
                "briefing": "OP DAY 1: Probe hr-portal (10.0.0.88).",
                "target_ip": "10.0.0.88",
                "mission_type": "recon",
                "reward": 380,
                "rep_reward": 48,
            },
            {
                "step": 2,
                "briefing": "OP DAY 2: Crack hr-portal, steal terminations.csv, wipe logs.",
                "target_ip": "10.0.0.88",
                "target_file": "/home/admin/terminations.csv",
                "mission_type": "exfil",
                "reward": 750,
                "rep_reward": 85,
            },
            {
                "step": 3,
                "briefing": "OP DAY 3: Clean sweep — zero traces on hr-portal after exfil.",
                "target_ip": "10.0.0.88",
                "mission_type": "ghost",
                "reward": 900,
                "rep_reward": 95,
            },
        ],
    },
    {
        "id": "op-counter",
        "name": "Operation Hardline",
        "broker": "ghost_broker",
        "min_rep": 200,
        "parts": [
            {
                "step": 1,
                "briefing": "OP DAY 1: Blue team drill — run 'defend on' and block a rival attack.",
                "target_ip": "",
                "mission_type": "defense",
                "reward": 450,
                "rep_reward": 55,
            },
            {
                "step": 2,
                "briefing": "OP DAY 2: Offense returns — ghost run on vendor-vpn (192.168.1.30).",
                "target_ip": "192.168.1.30",
                "mission_type": "ghost",
                "reward": 700,
                "rep_reward": 75,
            },
            {
                "step": 3,
                "briefing": "OP DAY 3: Crack corp-dc, exfil corporate_secrets.txt.",
                "target_ip": "10.0.0.42",
                "target_file": "/home/admin/corporate_secrets.txt",
                "mission_type": "exfil",
                "reward": 1300,
                "rep_reward": 125,
            },
        ],
    },
    {
        "id": "op-ledger",
        "name": "Operation Wire Trap",
        "broker": "packet_queen",
        "min_rep": 400,
        "parts": [
            {
                "step": 1,
                "briefing": "OP DAY 1: Scan finance subnet 172.16.0.0/24.",
                "target_ip": "172.16.0.0/24",
                "mission_type": "scan_subnet",
                "reward": 420,
                "rep_reward": 52,
            },
            {
                "step": 2,
                "briefing": "OP DAY 2: Ghost run on fin-trading — in and out silent.",
                "target_ip": "172.16.0.20",
                "mission_type": "ghost",
                "reward": 800,
                "rep_reward": 90,
            },
            {
                "step": 3,
                "briefing": "OP DAY 3: Root heist on bank-core — wire_keys.env.",
                "target_ip": "172.16.0.33",
                "target_file": "/root/wire_keys.env",
                "mission_type": "root_heist",
                "require_privesc": True,
                "reward": 2000,
                "rep_reward": 160,
            },
        ],
    },
    {
        "id": "op-chaos",
        "name": "Operation Blackout",
        "broker": "nullbyte",
        "min_rep": 750,
        "parts": [
            {
                "step": 1,
                "briefing": "OP DAY 1: Scan chaos subnet 203.0.113.0/24 — route required.",
                "target_ip": "203.0.113.0/24",
                "mission_type": "scan_subnet",
                "reward": 600,
                "rep_reward": 70,
            },
            {
                "step": 2,
                "briefing": "OP DAY 2: Crack chaos-c2, privesc, exfil rival_plans.txt.",
                "target_ip": "203.0.113.66",
                "target_file": "/root/rival_plans.txt",
                "mission_type": "root_heist",
                "require_privesc": True,
                "reward": 2500,
                "rep_reward": 180,
            },
            {
                "step": 3,
                "briefing": "OP DAY 3: Final job — dark-vault cold_wallet.dat. Double trace risk.",
                "target_ip": "203.0.113.99",
                "target_file": "/root/cold_wallet.dat",
                "mission_type": "root_heist",
                "require_privesc": True,
                "reward": 4000,
                "rep_reward": 250,
            },
        ],
    },
]

MISSION_ARCHETYPES = ("exfil", "ghost", "root_heist", "recon", "scan_chaos", "scan_subnet", "clean_sweep", "defense")


@dataclass
class RetentionState:
    last_login: str = ""
    streak: int = 0
    longest_streak: int = 0
    season_xp: int = 0
    season_tier: int = 0
    season_claimed: int = 0
    weekly_key: str = ""
    weekly_completed: bool = False
    active_operation: str = ""
    operation_step: int = 0
    operation_unlock_day: str = ""
    operation_parts_done: list[str] = field(default_factory=list)
    completed_operations: list[str] = field(default_factory=list)
    operation_cooldown_until: str = ""
    weekly_story_week: str = ""
    daily_earnings: int = 0
    daily_cracks: int = 0
    daily_rep_earned: int = 0
    daily_shop_spend: int = 0
    session_probed: set[str] = field(default_factory=set)
    session_cracked_ips: set[str] = field(default_factory=set)
    ghost_targets_done: set[str] = field(default_factory=set)


class RetentionManager:
    @staticmethod
    def today() -> str:
        return date.today().isoformat()

    @staticmethod
    def week_key() -> str:
        today = date.today()
        return f"{today.isocalendar().year}-W{today.isocalendar().week:02d}"

    @staticmethod
    def daily_slot() -> int:
        return date.today().toordinal() % len(DAILY_ROTATION)

    @staticmethod
    def make_daily_challenge():
        from progression import DailyChallenge

        cid, desc, reward, flag = DAILY_ROTATION[RetentionManager.daily_slot()]
        return DailyChallenge(cid, desc, reward, flag)

    @staticmethod
    def on_career_session(game: Game) -> None:
        from main import Mission, success, teach

        if game.player.phase != "career":
            return

        r = game.retention
        today = RetentionManager.today()
        RetentionManager._reset_daily_counters(r, today)
        RetentionManager._process_login(game, today)
        RetentionManager._refresh_weekly(game)
        RetentionManager._sync_operation_mission(game)
        RetentionManager._maybe_offer_operation(game)

        if game.daily.challenge_id != DAILY_ROTATION[RetentionManager.daily_slot()][0]:
            game.daily = RetentionManager.make_daily_challenge()

        if r.last_login == today and r.streak > 0:
            teach(
                f"Streak day {r.streak} | Season tier {r.season_tier}/{len(SEASON_TIERS)} | "
                f"'season' for rewards, 'operation' for multi-day ops."
            )

    @staticmethod
    def _reset_daily_counters(r: RetentionState, today: str) -> None:
        if r.last_login != today:
            r.daily_earnings = 0
            r.daily_cracks = 0
            r.daily_rep_earned = 0
            r.daily_shop_spend = 0
            r.session_probed = set()
            r.session_cracked_ips = set()

    @staticmethod
    def _process_login(game: Game, today: str) -> None:
        from main import success

        r = game.retention
        if r.last_login == today:
            return

        if r.last_login:
            try:
                last = date.fromisoformat(r.last_login)
                gap = (date.fromisoformat(today) - last).days
            except ValueError:
                gap = 999
            if gap == 1:
                r.streak += 1
            elif gap > 1:
                r.streak = 1
        else:
            r.streak = 1

        r.longest_streak = max(r.longest_streak, r.streak)
        r.last_login = today

        cash, xp, msg = RetentionManager._streak_reward(r.streak)
        if cash:
            game.player.earn(cash, f"{r.streak}-day streak")
        RetentionManager.add_season_xp(game, xp, "login streak")
        success(f"Login streak: {r.streak} days — {msg}")

        if r.streak >= 7:
            game.achievements.unlock("streak_7")
        if r.streak >= 30:
            game.achievements.unlock("streak_30")

        game.mail.send(
            "ghost_broker@darknet",
            f"Day {r.streak} — operator check-in",
            f"{msg}\n\nToday's challenge: {game.daily.description}\n"
            f"Reward: ${game.daily.reward} + season XP.\n\n— ghost_broker",
        )

    @staticmethod
    def _streak_reward(streak: int) -> tuple[int, int, str]:
        cash, xp, msg = 50, 25, "Back on the board."
        for day, (c, x, m) in sorted(STREAK_MILESTONES.items()):
            if streak >= day:
                cash, xp, msg = c, x, m
        return cash, xp, msg

    @staticmethod
    def add_season_xp(game: Game, amount: int, reason: str) -> None:
        from main import success
        from progression import ReputationSystem

        if game.player.phase != "career" or amount <= 0:
            return
        r = game.retention
        r.season_xp += amount
        success(f"+{amount} season XP ({reason}) — total {r.season_xp}")

        while r.season_tier < len(SEASON_TIERS):
            need = SEASON_TIERS[r.season_tier]["xp"]
            if r.season_xp < need:
                break
            r.season_xp -= need
            tier = SEASON_TIERS[r.season_tier]
            r.season_tier += 1
            game.player.earn(tier["cash"], f"season tier {r.season_tier}")
            ReputationSystem.add_rep(game, tier["rep"], f"season tier {r.season_tier}")
            game.mail.send(
                "security@terminalhacker.local",
                f"Season tier {r.season_tier} unlocked",
                f"{tier['label']}\n+${tier['cash']} +{tier['rep']} rep\n\nKeep the streak alive.",
            )
            if r.season_tier >= len(SEASON_TIERS):
                game.achievements.unlock("season_complete")
                success("SEASON COMPLETE — 30-day track finished!")

    @staticmethod
    def _refresh_weekly(game: Game) -> None:
        from main import Mission

        wk = RetentionManager.week_key()
        r = game.retention
        if r.weekly_key == wk:
            return

        r.weekly_key = wk
        r.weekly_completed = False
        RetentionManager._send_weekly_story(game)
        spec = WEEKLY_BOUNTIES[date.today().isocalendar().week % len(WEEKLY_BOUNTIES)]
        if game.player.reputation < spec.get("min_rep", 0):
            return

        mid = f"{spec['id']}-{wk}"
        if any(m.mission_id == mid for m in game.missions.missions):
            return

        m = Mission(
            mid, spec["broker"], spec["briefing"], spec["target_ip"],
            spec.get("target_file", "/home/admin/notes.txt"), spec["reward"],
            rep_reward=spec.get("rep_reward", 80),
            mission_type=spec.get("mission_type", "exfil"),
            require_privesc=spec.get("require_privesc", False),
            weekly_bounty=True,
        )
        if spec.get("mission_type") == "ghost":
            m.require_log_wipe = True
            m.target_file = ""
        game.missions.missions.insert(0, m)
        game.mail.send(
            f"{spec['broker']}@darknet",
            f"WEEKLY BOUNTY: {spec['title']}",
            f"{spec['briefing']}\n\nExpires Sunday. Bonus season XP on completion.\n\n— {spec['broker']}",
        )

    @staticmethod
    def _send_weekly_story(game: Game) -> None:
        wk = RetentionManager.week_key()
        r = game.retention
        if r.weekly_story_week == wk:
            return
        r.weekly_story_week = wk
        idx = date.today().isocalendar().week % len(WEEKLY_STORY_MAIL)
        story = WEEKLY_STORY_MAIL[idx]
        game.mail.send(story["sender"], story["subject"], story["body"])
        rival = WEEKLY_RIVAL_MAIL[idx % len(WEEKLY_RIVAL_MAIL)]
        game.mail.send(rival["sender"], rival["subject"], rival["body"])

    @staticmethod
    def current_week_story() -> dict[str, str]:
        return WEEKLY_STORY_MAIL[date.today().isocalendar().week % len(WEEKLY_STORY_MAIL)]

    @staticmethod
    def _maybe_offer_operation(game: Game) -> None:
        from main import Mission

        r = game.retention
        if r.active_operation:
            return
        if r.operation_cooldown_until and r.operation_cooldown_until > RetentionManager.today():
            return

        for op in OPERATIONS:
            if op["id"] in r.completed_operations:
                continue
            if game.player.reputation < op.get("min_rep", 0):
                continue
            if r.active_operation:
                return
            part = op["parts"][0]
            r.active_operation = op["id"]
            r.operation_step = 1
            r.operation_unlock_day = RetentionManager.today()
            RetentionManager._inject_operation_mission(game, op, part)
            game.mail.send(
                f"{op['broker']}@darknet",
                f"OPERATION: {op['name']} — Day 1",
                f"{part['briefing']}\n\nMulti-day op. Next phase unlocks tomorrow.\n\n— {op['broker']}",
            )
            return

    @staticmethod
    def _inject_operation_mission(game: Game, op: dict, part: dict) -> None:
        from main import Mission

        mid = f"{op['id']}-s{part['step']}"
        game.missions.missions = [m for m in game.missions.missions if not m.operation_id]
        if part.get("mission_type") == "defense":
            game.player.tutorial_flags.discard("op_defense_done")
        game.missions.missions.insert(
            0,
            Mission(
                mid, op["broker"], part["briefing"],
                part.get("target_ip", ""), part.get("target_file", ""),
                part.get("reward", 300), rep_reward=part.get("rep_reward", 40),
                mission_type=part.get("mission_type", "exfil"),
                require_privesc=part.get("require_privesc", False),
                operation_id=op["id"],
                operation_step=part["step"],
            ),
        )

    @staticmethod
    def _sync_operation_mission(game: Game) -> None:
        r = game.retention
        if not r.active_operation:
            return
        op = next((o for o in OPERATIONS if o["id"] == r.active_operation), None)
        if not op:
            return
        if r.operation_step > len(op["parts"]):
            r.active_operation = ""
            return
        if r.operation_unlock_day > RetentionManager.today():
            return
        if any(m.operation_id == r.active_operation and not m.completed for m in game.missions.missions):
            return
        if r.operation_step <= len(op["parts"]):
            part = op["parts"][r.operation_step - 1]
            RetentionManager._inject_operation_mission(game, op, part)

    @staticmethod
    def on_operation_step_complete(game: Game, mission: Mission) -> None:
        r = game.retention
        if not mission.operation_id:
            return

        tag = f"{mission.operation_id}:{mission.operation_step}"
        if tag not in r.operation_parts_done:
            r.operation_parts_done.append(tag)

        op = next((o for o in OPERATIONS if o["id"] == mission.operation_id), None)
        if not op:
            return

        RetentionManager.add_season_xp(game, SEASON_XP_OPERATION, f"operation step {mission.operation_step}")

        if mission.operation_step >= len(op["parts"]):
            r.active_operation = ""
            if op["id"] not in r.completed_operations:
                r.completed_operations.append(op["id"])
            game.mail.send(
                f"{mission.broker}@darknet",
                f"OPERATION COMPLETE: {op['name']}",
                "All phases done. Next operation unlocks tomorrow.\n\n— broker",
            )
            r.operation_cooldown_until = (date.today() + timedelta(days=1)).isoformat()
            RetentionManager._maybe_offer_operation(game)
            return

        r.operation_step = mission.operation_step + 1
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        r.operation_unlock_day = tomorrow
        game.mail.send(
            f"{mission.broker}@darknet",
            f"OPERATION: {op['name']} — Phase {r.operation_step} locked",
            f"Next phase unlocks tomorrow ({tomorrow}).\n"
            "Come back for the continuation.\n\n— broker",
        )

    @staticmethod
    def on_contract_complete(game: Game, mission: Mission) -> None:
        r = game.retention
        xp = SEASON_XP_CONTRACT + (40 if mission.weekly_bounty else 0)
        RetentionManager.add_season_xp(game, xp, mission.mission_id)
        if mission.weekly_bounty:
            r.weekly_completed = True
            game.player.tutorial_flags.add("daily_weekly_bounty_done")
            RetentionManager.add_season_xp(game, SEASON_XP_WEEKLY, "weekly bounty")

    @staticmethod
    def on_daily_complete(game: Game) -> None:
        RetentionManager.add_season_xp(game, SEASON_XP_DAILY, "daily challenge")
        if game.achievements.dailies_completed >= 30:
            game.achievements.unlock("daily_master")

    @staticmethod
    def on_earn(game: Game, amount: int) -> None:
        r = game.retention
        r.daily_earnings += amount
        if r.daily_earnings >= 500:
            game.player.tutorial_flags.add("daily_earn500_done")
        if r.daily_earnings >= 1000:
            game.player.tutorial_flags.add("daily_big_payday_done")

    @staticmethod
    def on_rep_gain(game: Game, amount: int) -> None:
        r = game.retention
        r.daily_rep_earned += amount
        if r.daily_rep_earned >= 50:
            game.player.tutorial_flags.add("daily_rep_burst_done")

    @staticmethod
    def on_crack(game: Game, server_ip: str, security_level: int) -> None:
        r = game.retention
        r.session_cracked_ips.add(server_ip)
        r.daily_cracks += 1
        if r.daily_cracks >= 2:
            game.player.tutorial_flags.add("daily_two_cracks_done")
        if security_level >= 3:
            game.player.tutorial_flags.add("daily_hard_crack_done")
        if r.session_probed and server_ip in r.session_probed:
            game.player.tutorial_flags.add("daily_probe_crack_done")

    @staticmethod
    def on_defense_block(game: Game) -> None:
        game.player.tutorial_flags.add("op_defense_done")
        RetentionManager._check_defense_missions(game)

    @staticmethod
    def _check_defense_missions(game: Game) -> None:
        for m in game.missions.missions:
            if m.completed or m.mission_type != "defense":
                continue
            if "op_defense_done" in game.player.tutorial_flags:
                RetentionManager._complete_mission(game, m)

    @staticmethod
    def on_scan_subnet(game: Game, cidr: str) -> None:
        p = game.player
        for m in game.missions.missions:
            if m.completed:
                continue
            if m.mission_type == "scan_subnet" and m.target_ip == cidr:
                RetentionManager._complete_mission(game, m)
            if m.mission_type == "scan_chaos" and cidr == "203.0.113.0/24":
                RetentionManager._complete_mission(game, m)

    @staticmethod
    def on_probe(game: Game, server_ip: str) -> None:
        game.retention.session_probed.add(server_ip)
        RetentionManager._check_recon_missions(game, server_ip)

    @staticmethod
    def on_ghost_complete(game: Game, server_ip: str) -> None:
        game.retention.ghost_targets_done.add(server_ip)
        game.player.tutorial_flags.add("daily_ghost_contract_done")
        RetentionManager._check_ghost_missions(game, server_ip)

    @staticmethod
    def on_disconnect_checks(game: Game, server_ip: str, clean: bool) -> None:
        RetentionManager._check_ghost_missions(game, server_ip)
        if clean:
            RetentionManager._check_recon_missions(game, server_ip)

    @staticmethod
    def _check_ghost_missions(game: Game, server_ip: str) -> None:
        for m in game.missions.missions:
            if m.completed or m.mission_type != "ghost":
                continue
            if m.target_ip == server_ip and server_ip in game.retention.ghost_targets_done:
                RetentionManager._complete_mission(game, m)

    @staticmethod
    def _check_recon_missions(game: Game, server_ip: str) -> None:
        p = game.player
        for m in game.missions.missions:
            if m.completed:
                continue
            if m.mission_type == "recon" and m.target_ip == server_ip:
                if m.target_ip in p.discovered_ips and m.target_ip in game.retention.session_probed:
                    RetentionManager._complete_mission(game, m)
            if m.mission_type == "scan_chaos" and "203.0.113.0/24" in p.subnets_scanned:
                RetentionManager._complete_mission(game, m)

    @staticmethod
    def _complete_mission(game: Game, mission: Mission) -> None:
        from main import success

        if mission.completed:
            return
        mission.completed = True
        game.player.earn(mission.reward, f"contract {mission.broker}")
        game.missions.complete_mission_hooks(game, mission)
        success(f"Contract complete: {mission.briefing[:60]}...")
        if game.mail:
            game.mail.send(
                f"{mission.broker}@darknet",
                f"Payment — ${mission.reward}",
                f"{mission.briefing}\n\nFunds transferred.",
            )

    @staticmethod
    def mission_is_satisfied(game: Game, mission: Mission) -> bool:
        from main import ip_in_subnet

        p = game.player
        mtype = getattr(mission, "mission_type", "exfil")

        if mtype == "ghost":
            return mission.target_ip in game.retention.ghost_targets_done
        if mtype == "recon":
            return (
                mission.target_ip in p.discovered_ips
                and mission.target_ip in game.retention.session_probed
            )
        if mtype == "scan_chaos":
            return "203.0.113.0/24" in p.subnets_scanned
        if mtype == "scan_subnet":
            return mission.target_ip in p.subnets_scanned
        if mtype == "defense":
            return "op_defense_done" in p.tutorial_flags

        if mtype in ("exfil", "root_heist", "clean_sweep"):
            if not mission.target_file:
                return False
            fname = mission.target_file.rsplit("/", 1)[-1]
            if f"/home/hacker/downloads/{fname}" not in p.files:
                return False
            if mtype == "root_heist" and mission.require_privesc:
                if mission.target_ip not in p.privesc_hosts and not p.remote_was_root:
                    return False
            server = game.network.get_server(mission.target_ip)
            if mission.require_log_wipe and server and server.player_left_traces(p):
                return False
            if mtype == "root_heist" and "/root/" in mission.target_file:
                return p.remote_was_root or fname in [k.rsplit("/", 1)[-1] for k in p.files if "/downloads/" in k]
            return not server or not server.player_left_traces(p)

        return False
