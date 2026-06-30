#!/usr/bin/env python3
"""Month-long retention: login streaks, 30-day season, weekly bounties, operation arcs."""

from __future__ import annotations

import random
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
# Per-operation rival + broker reactions (fire once when op completes)
# ---------------------------------------------------------------------------

OPERATION_REACTIONS: dict[str, dict[str, Any]] = {
    "op-nova": {
        "aggression": 1,
        "rival": {
            "sender": "acid_k@rival.net",
            "subject": "RE: NovaDyne — that's MY side gig",
            "body": (
                "I had a retainer on NovaDyne's DMZ.\n\n"
                "You cracked corp-dc and didn't even leave me scraps. corp-gateway logs "
                "are being scrubbed but I saw your VPN exit. I own 10.0.0.x — remember that.\n\n"
                "— acid_k"
            ),
        },
        "broker": {
            "sender": "ghost_broker@darknet",
            "subject": "NovaDyne board is panicking",
            "body": (
                "Clean work on Glass Firewall.\n\n"
                "NovaDyne CISO sent an emergency retainer to THREE rival crews. "
                "Expect heavier probes on your home IP. Upgrade firewall or stay on VPN.\n\n"
                "— ghost_broker"
            ),
        },
    },
    "op-helix": {
        "aggression": 2,
        "rival": {
            "sender": "phantom_pkt@rival.net",
            "subject": "You stole MY algo configs",
            "body": (
                "fin-trading was my score. bank-core wire keys too?\n\n"
                "Helix posted a silent bounty — no logs, no courts. Rivals don't sue. "
                "We ruin wallets. I'm first in line.\n\n"
                "— phantom_pkt"
            ),
        },
        "broker": {
            "sender": "cipher7@darknet",
            "subject": "Helix merger intel is gold",
            "body": (
                "Bull Market complete. Those wire keys change the season.\n\n"
                "Brokers are bidding on your next slot. phantom_pkt is loud — "
                "use that. Loud rivals make mistakes.\n\n"
                "— cipher7"
            ),
        },
    },
    "op-shadow": {
        "aggression": 1,
        "rival": {
            "sender": "nyx_root@rival.net",
            "subject": "Ghost runs don't impress me",
            "body": (
                "vendor-vpn with zero traces. Fine.\n\n"
                "I still fingerprinted your timing pattern. Chaos subnet scans don't hide "
                "from everyone. When you touch 203.0.113.x, I'll be waiting.\n\n"
                "— nyx_root"
            ),
        },
        "broker": {
            "sender": "nullbyte@darknet",
            "subject": "Dark Echo — you're ready for chaos",
            "body": (
                "Stealth chain complete. model_weights were a nice touch.\n\n"
                "Chaos targets pay triple. Trace chance doubles. "
                "Only take Blackout when your gear is maxed.\n\n"
                "— nullbyte"
            ),
        },
    },
    "op-treasury": {
        "aggression": 2,
        "rival": {
            "sender": "acid_k@rival.net",
            "subject": "Payroll?! Are you insane?",
            "body": (
                "vault-server payroll.csv hits EVERYONE on the board.\n\n"
                "NovaDyne lawyers will burn the subnet down. Rivals included. "
                "You made my retainer worthless and painted a target on all of us.\n\n"
                "— acid_k"
            ),
        },
        "broker": {
            "sender": "cipher7@darknet",
            "subject": "Treasury keys — leverage unlocked",
            "body": (
                "Quantum Ledger done. Payroll data is nuclear leverage.\n\n"
                "Brokers can place you on premium contracts now. "
                "Rivals will probe harder — that's the cost of relevance.\n\n"
                "— cipher7"
            ),
        },
    },
    "op-research": {
        "aggression": 1,
        "rival": {
            "sender": "zero_cool@rival.net",
            "subject": "AI weights — who told you about research-node?",
            "body": (
                "model_weights.bin isn't corporate fluff. That's a buyer's market.\n\n"
                "I had a bid in. You undercut me. I don't forget names tied to "
                "encrypted blobs.\n\n"
                "— zero_cool"
            ),
        },
        "broker": {
            "sender": "shade_runner@darknet",
            "subject": "R&D exfil — buyers lining up",
            "body": (
                "Stolen Weights closed. Ghosting the gateway afterward was professional.\n\n"
                "Keep that tradecraft. Buyers pay extra for operators who don't trip IDS.\n\n"
                "— shade_runner"
            ),
        },
    },
    "op-hr": {
        "aggression": 1,
        "rival": {
            "sender": "acid_k@rival.net",
            "subject": "terminations.csv — you have dirt on ME",
            "body": (
                "HR portal. terminations.csv. I see my handle in that file.\n\n"
                "Delete your copy or I burn your public IP to every SOC in the city. "
                "This isn't corporate games anymore.\n\n"
                "— acid_k"
            ),
        },
        "broker": {
            "sender": "ghost_broker@darknet",
            "subject": "Paper Trail — leverage secured",
            "body": (
                "HR data is blackmail currency. Sit on it.\n\n"
                "acid_k is rattled — good. Rattled rivals overextend. "
                "Your next op should be offense OR defense, not both sloppy.\n\n"
                "— ghost_broker"
            ),
        },
    },
    "op-counter": {
        "aggression": 2,
        "rival": {
            "sender": "nyx_root@rival.net",
            "subject": "You blocked me. Bad move.",
            "body": (
                "defend on. Firewall block logged. I don't fail twice.\n\n"
                "Hardline means you're playing blue-team for money now. "
                "I'll hit you when you're mid-crack on corp-dc. Multitask that.\n\n"
                "— nyx_root"
            ),
        },
        "broker": {
            "sender": "ghost_broker@darknet",
            "subject": "Hardline — brokers noticed your defense",
            "body": (
                "Blocking rivals while running offense is elite posture.\n\n"
                "I'm routing premium finance ops your way. phantom_pkt won't like it.\n\n"
                "— ghost_broker"
            ),
        },
    },
    "op-ledger": {
        "aggression": 3,
        "rival": {
            "sender": "phantom_pkt@rival.net",
            "subject": "wire_keys.env — I'm coming for your box",
            "body": (
                "Wire Trap complete. You own Helix now.\n\n"
                "I'm done with warnings. Next probe isn't training — "
                "I'm bringing power 5 against your firewall. Patch or bleed.\n\n"
                "— phantom_pkt"
            ),
        },
        "broker": {
            "sender": "packet_queen@darknet",
            "subject": "Finance sector cleared",
            "body": (
                "bank-core was the last domino. Helix is gutted.\n\n"
                "Chaos brokers are watching. Complete Blackout and you're legend tier.\n\n"
                "— packet_queen"
            ),
        },
    },
    "op-chaos": {
        "aggression": 2,
        "rival": {
            "sender": "zero_cool@rival.net",
            "subject": "Blackout complete — truce?",
            "body": (
                "chaos-c2. dark-vault. cold_wallet.dat.\n\n"
                "You survived double trace on the vault. I lost two accounts there. "
                "Respect. Truce is temporary — next season I want a rematch.\n\n"
                "— zero_cool"
            ),
        },
        "broker": {
            "sender": "nullbyte@darknet",
            "subject": "NET GOD — season legend",
            "body": (
                "Operation Blackout closed. Brokers are circulating your handle.\n\n"
                "Rivals will ease off... briefly. Finish the season track. "
                "You've earned the frame.\n\n"
                "— nullbyte"
            ),
        },
    },
}

# Cross-operation reactions when specific combos are completed
CROSS_OPERATION_REACTIONS: list[dict[str, Any]] = [
    {
        "id": "cross-nova-hr",
        "requires": frozenset({"op-nova", "op-hr"}),
        "sender": "acid_k@rival.net",
        "subject": "NovaDyne AND HR — you're building a dossier on me",
        "body": (
            "corporate_secrets AND terminations.csv.\n\n"
            "You're not freelancing. You're compiling evidence. "
            "I don't know who you're selling to but I'm taking you offline first.\n\n"
            "— acid_k"
        ),
        "aggression": 2,
    },
    {
        "id": "cross-helix-ledger",
        "requires": frozenset({"op-helix", "op-ledger"}),
        "sender": "phantom_pkt@rival.net",
        "subject": "You own Helix twice over",
        "body": (
            "Bull Market AND Wire Trap. Entire finance vertical.\n\n"
            "My crew is out. I'm operating solo now. Solo means reckless. "
            "Expect me at your firewall tonight.\n\n"
            "— phantom_pkt"
        ),
        "aggression": 3,
    },
    {
        "id": "cross-shadow-chaos",
        "requires": frozenset({"op-shadow", "op-chaos"}),
        "sender": "nyx_root@rival.net",
        "subject": "Dark Echo into Blackout — you planned this",
        "body": (
            "Chaos prep then full blackout. That's a month-long campaign.\n\n"
            "You're not a script kiddie. You're competition. "
            "I'll be in the 203.0.113.x logs when you slip.\n\n"
            "— nyx_root"
        ),
        "aggression": 2,
    },
    {
        "id": "cross-all-corp",
        "requires": frozenset({"op-nova", "op-treasury", "op-research", "op-hr"}),
        "sender": "security@novadyne.corp",
        "subject": "LEGAL NOTICE — cease and desist",
        "body": (
            "This is an automated legal hold notice.\n\n"
            "Your activities against NovaDyne Corp assets have been catalogued. "
            "In-game fines may apply. (Career wallet penalties on next trace.)\n\n"
            "— NovaDyne Legal Bot [simulated]",
        ),
        "aggression": 1,
        "fine": 100,
    },
]

# Rival dossier lines shown in intel/rivals based on completed ops
RIVAL_DOSSIER: dict[str, list[tuple[frozenset[str], str]]] = {
    "acid_k": [
        (frozenset({"op-nova"}), "Hostile — lost NovaDyne retainer"),
        (frozenset({"op-hr"}), "Desperate — name in terminations.csv"),
        (frozenset({"op-treasury"}), "Furious — payroll exposure"),
    ],
    "phantom_pkt": [
        (frozenset({"op-helix"}), "Hostile — stolen algo configs"),
        (frozenset({"op-ledger"}), "Apex threat — going solo, power 5 probes"),
    ],
    "nyx_root": [
        (frozenset({"op-shadow"}), "Watching — fingerprinted your ghost pattern"),
        (frozenset({"op-counter"}), "Vengeful — you blocked a live attack"),
    ],
    "zero_cool": [
        (frozenset({"op-research"}), "Competitive — undercut on model weights"),
        (frozenset({"op-chaos"}), "Respectful truce — temporary"),
    ],
}

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

# ---------------------------------------------------------------------------
# Phase bridge — same-day side objectives while waiting for next op phase
# ---------------------------------------------------------------------------

BRIDGE_TASK_DEFS: dict[str, dict[str, Any]] = {
    "contract": {"desc": "Complete any contract (not the locked op phase)", "cash": 225, "xp": 40},
    "daily": {"desc": "Finish today's daily challenge", "cash": 175, "xp": 35},
    "earn300": {"desc": "Earn $300+ today from hacks or contracts", "cash": 200, "xp": 30},
    "block": {"desc": "Block a rival attack on your box", "cash": 250, "xp": 45},
    "defend_on": {"desc": "Run 'defend on' and survive a session", "cash": 150, "xp": 30},
    "privesc": {"desc": "Privilege escalate on any target", "cash": 275, "xp": 50},
    "ghost": {"desc": "Ghost run — crack and disconnect with zero traces", "cash": 300, "xp": 50},
    "scan": {"desc": "Scan any subnet you haven't scanned today", "cash": 175, "xp": 30},
    "gear": {"desc": "Buy a CPU or firewall upgrade", "cash": 200, "xp": 35},
    "probe": {"desc": "Probe any remote host", "cash": 125, "xp": 25},
    "request": {"desc": "Request a new procedural contract", "cash": 150, "xp": 25},
    "vpn_crack": {"desc": "Crack a host while VPN is active", "cash": 200, "xp": 35},
    "weekly": {"desc": "Make progress on the weekly bounty", "cash": 350, "xp": 55},
}

BRIDGE_BY_NEXT_TYPE: dict[str, list[str]] = {
    "exfil": ["contract", "earn300", "gear"],
    "ghost": ["ghost", "vpn_crack", "probe"],
    "root_heist": ["privesc", "gear", "contract"],
    "recon": ["scan", "probe", "request"],
    "defense": ["defend_on", "block", "gear"],
    "scan_subnet": ["scan", "request", "earn300"],
    "scan_chaos": ["scan", "gear", "earn300"],
    "clean_sweep": ["ghost", "contract", "earn300"],
}

BRIDGE_FLAGS: dict[str, str] = {k: f"bridge_{k}_done" for k in BRIDGE_TASK_DEFS}
BRIDGE_BONUS_CASH = 350
BRIDGE_BONUS_XP = 55


@dataclass
class RetentionState:
    last_login: str = ""
    streak: int = 0
    longest_streak: int = 0
    season_xp: int = 0
    season_tier: int = 0
    season_claimed: int = 0
    season_month: str = ""
    season_cycles: int = 0
    weekly_key: str = ""
    weekly_completed: bool = False
    active_operation: str = ""
    operation_step: int = 0
    operation_unlock_day: str = ""
    operation_parts_done: list[str] = field(default_factory=list)
    completed_operations: list[str] = field(default_factory=list)
    operation_cooldown_until: str = ""
    weekly_story_week: str = ""
    rival_aggression: int = 0
    last_rival: str = ""
    reactions_sent: list[str] = field(default_factory=list)
    bridge_id: str = ""
    bridge_tasks: list[str] = field(default_factory=list)
    bridge_done: list[str] = field(default_factory=list)
    bridge_claimed: bool = False
    bridge_unlock_day: str = ""
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

        from session_content import HourlyManager
        HourlyManager.refresh(game)

        from depth_systems import RivalHeatManager, WeeklyHeistManager
        RivalHeatManager.decay_on_login(game)
        WeeklyHeistManager.refresh(game)

        from story_system import StoryManager
        StoryManager.ensure_intro(game)
        from social_board import SocialBoardManager
        SocialBoardManager.on_career_session(game)
        from longevity_content import SeasonCycleManager
        SeasonCycleManager.on_career_session(game)

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
        from longevity_content import bounty_for_week
        spec = bounty_for_week(date.today().isocalendar().week)
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
        from story_system import StoryManager
        StoryManager.send_weekly_beat(game)
        idx = date.today().isocalendar().week % len(WEEKLY_STORY_MAIL)
        story = WEEKLY_STORY_MAIL[idx]
        rival = WEEKLY_RIVAL_MAIL[idx % len(WEEKLY_RIVAL_MAIL)]
        addendum = RetentionManager._story_addendum(game)
        story_add = StoryManager.narrative_addendum(game)
        if story_add:
            addendum = f"{addendum}\n{story_add}".strip() if addendum else story_add
        rival_body = rival["body"]
        if addendum:
            rival_body += f"\n\n--- Based on your ops ---\n{addendum}"
        game.mail.send(story["sender"], story["subject"], story["body"])
        game.mail.send(rival["sender"], rival["subject"], rival_body)

    @staticmethod
    def _story_addendum(game: Game) -> str:
        done = set(game.retention.completed_operations)
        if not done:
            return ""
        lines: list[str] = []
        if "op-nova" in done:
            lines.append("acid_k is still furious about NovaDyne.")
        if "op-helix" in done or "op-ledger" in done:
            lines.append("phantom_pkt has marked you in finance sector.")
        if "op-counter" in done:
            lines.append("nyx_root is probing your firewall on off-hours.")
        if "op-chaos" in done:
            lines.append("zero_cool issued a temporary truce — don't test it.")
        if len(done) >= 5:
            lines.append(f"Brokers rate you tier-{min(10, len(done))} threat. {len(done)} ops cleared.")
        return "\n".join(lines)

    @staticmethod
    def _send_operation_reactions(game: Game, op_id: str) -> None:
        r = game.retention
        if op_id in r.reactions_sent:
            return
        r.reactions_sent.append(op_id)

        reaction = OPERATION_REACTIONS.get(op_id)
        if reaction:
            rival = reaction.get("rival")
            broker = reaction.get("broker")
            if broker:
                game.mail.send(broker["sender"], broker["subject"], broker["body"])
            if rival:
                game.mail.send(rival["sender"], rival["subject"], rival["body"])
                r.last_rival = rival["sender"].split("@")[0]
            r.rival_aggression += reaction.get("aggression", 1)
            if r.rival_aggression >= 5:
                game.achievements.unlock("rival_magnet")

        RetentionManager._check_cross_reactions(game)

    @staticmethod
    def _check_cross_reactions(game: Game) -> None:
        from main import warn

        done = frozenset(game.retention.completed_operations)
        r = game.retention
        for cross in CROSS_OPERATION_REACTIONS:
            cid = cross["id"]
            if cid in r.reactions_sent:
                continue
            if not cross["requires"].issubset(done):
                continue
            r.reactions_sent.append(cid)
            game.mail.send(cross["sender"], cross["subject"], cross["body"])
            r.rival_aggression += cross.get("aggression", 1)
            if "@" in cross["sender"]:
                r.last_rival = cross["sender"].split("@")[0]
            fine = cross.get("fine", 0)
            if fine:
                game.player.penalize(fine, "Corporate legal hold (simulated)")
                warn(f"NovaDyne legal bot fined you ${fine} for accumulated corporate ops.")

    @staticmethod
    def rival_threat_bonus(game: Game) -> float:
        return min(0.12, game.retention.rival_aggression * 0.022)

    @staticmethod
    def pick_rival_attacker(game: Game) -> str:
        r = game.retention
        if r.last_rival and random.random() < 0.6:
            return r.last_rival
        return random.choice(["zero_cool", "acid_k", "phantom_pkt", "nyx_root"])

    @staticmethod
    def rival_attack_power(game: Game, base: int) -> int:
        return min(6, base + game.retention.rival_aggression // 3)

    @staticmethod
    def rival_dossier_lines(game: Game) -> list[str]:
        done = set(game.retention.completed_operations)
        r = game.retention
        lines = [f"Threat level: {r.rival_aggression}/10", f"Primary rival: {r.last_rival or 'none'}"]
        for rival, entries in RIVAL_DOSSIER.items():
            status = "Unknown"
            for required, desc in entries:
                if required.issubset(done):
                    status = desc
            lines.append(f"  {rival}: {status}")
        if len(done) >= 3:
            lines.append(f"  Corps hit: {len(done)} operations — rivals coordinating.")
        return lines

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

        for op in RetentionManager._operation_offer_order(game):
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
    def _operation_offer_order(game: Game) -> list[dict]:
        from story_system import StoryManager
        order = StoryManager.operation_order(game)
        by_id = {op["id"]: op for op in OPERATIONS}
        return [by_id[oid] for oid in order if oid in by_id]

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
            RetentionManager._send_operation_reactions(game, op["id"])
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
        RetentionManager.activate_phase_bridge(game, op, mission.operation_step)
        bridge_txt = RetentionManager.bridge_summary(game)
        game.mail.send(
            f"{mission.broker}@darknet",
            f"OPERATION: {op['name']} — Phase {r.operation_step} locked",
            f"Next phase unlocks tomorrow ({tomorrow}).\n\n"
            f"TONIGHT — optional prep objectives (bonus rewards):\n{bridge_txt}\n"
            "Type 'bridge' in terminal. Dailies, weekly bounty, and contracts still active.\n\n"
            "— broker",
        )

    @staticmethod
    def activate_phase_bridge(game: Game, op: dict, completed_step: int) -> None:
        from main import teach

        if completed_step >= len(op["parts"]):
            return
        next_part = op["parts"][completed_step]
        mtype = next_part.get("mission_type", "exfil")
        tasks = BRIDGE_BY_NEXT_TYPE.get(mtype, ["contract", "earn300", "probe"])[:3]
        r = game.retention
        r.bridge_id = f"{op['id']}:{completed_step}"
        r.bridge_tasks = tasks
        r.bridge_done = []
        r.bridge_claimed = False
        r.bridge_unlock_day = r.operation_unlock_day
        for tid in tasks:
            game.player.tutorial_flags.discard(BRIDGE_FLAGS[tid])
        teach(
            f"Op phase complete — prep objectives active until tomorrow. "
            f"Type 'bridge' for same-day side missions (+${BRIDGE_BONUS_CASH} bonus if all 3 done)."
        )

    @staticmethod
    def bridge_active(game: Game) -> bool:
        r = game.retention
        if not r.bridge_id or r.bridge_claimed:
            return False
        if r.bridge_unlock_day and r.bridge_unlock_day <= RetentionManager.today():
            return False
        return True

    @staticmethod
    def bridge_summary(game: Game) -> str:
        r = game.retention
        if not RetentionManager.bridge_active(game):
            return "  (no active prep objectives)"
        lines = []
        for tid in r.bridge_tasks:
            mark = "[x]" if tid in r.bridge_done else "[ ]"
            desc = BRIDGE_TASK_DEFS[tid]["desc"]
            cash = BRIDGE_TASK_DEFS[tid]["cash"]
            lines.append(f"  {mark} {desc} (+${cash})")
        done = len(r.bridge_done)
        total = len(r.bridge_tasks)
        lines.append(f"  Bonus if all done: +${BRIDGE_BONUS_CASH} + {BRIDGE_BONUS_XP} season XP ({done}/{total})")
        return "\n".join(lines)

    @staticmethod
    def bridge_mark(game: Game, task_id: str) -> None:
        if not RetentionManager.bridge_active(game):
            return
        r = game.retention
        if task_id not in r.bridge_tasks or task_id in r.bridge_done:
            return
        r.bridge_done.append(task_id)
        spec = BRIDGE_TASK_DEFS[task_id]
        game.player.earn(spec["cash"], f"prep: {task_id}")
        RetentionManager.add_season_xp(game, spec["xp"], f"prep {task_id}")
        from main import success
        success(f"Prep objective done: {spec['desc']}")
        RetentionManager._try_bridge_bonus(game)

    @staticmethod
    def _try_bridge_bonus(game: Game) -> None:
        from main import success

        r = game.retention
        if not RetentionManager.bridge_active(game) or r.bridge_claimed:
            return
        if len(r.bridge_done) < len(r.bridge_tasks):
            return
        r.bridge_claimed = True
        game.player.earn(BRIDGE_BONUS_CASH, "phase prep complete")
        RetentionManager.add_season_xp(game, BRIDGE_BONUS_XP, "phase prep bonus")
        success(f"ALL PREP OBJECTIVES DONE — +${BRIDGE_BONUS_CASH} bonus!")
        game.achievements.bridge_completions = getattr(game.achievements, "bridge_completions", 0) + 1
        if game.achievements.bridge_completions >= 5:
            game.achievements.unlock("prep_master")
        game.mail.send(
            "ghost_broker@darknet",
            "Prep work on point",
            "You cleared tonight's side objectives before the next op phase. "
            "That's how operators stay ahead of rivals.\n\n— ghost_broker",
        )

    @staticmethod
    def check_bridge_triggers(game: Game) -> None:
        if not RetentionManager.bridge_active(game):
            return
        p = game.player
        r = game.retention
        if "earn300" in r.bridge_tasks and r.daily_earnings >= 300:
            RetentionManager.bridge_mark(game, "earn300")
        if "daily" in r.bridge_tasks and game.daily.completed:
            RetentionManager.bridge_mark(game, "daily")
        if "defend_on" in r.bridge_tasks and game.blue.defense_mode:
            RetentionManager.bridge_mark(game, "defend_on")
        if "weekly" in r.bridge_tasks and r.weekly_completed:
            RetentionManager.bridge_mark(game, "weekly")

    @staticmethod
    def on_bridge_event(game: Game, task_id: str) -> None:
        if task_id in BRIDGE_TASK_DEFS:
            p = game.player
            p.tutorial_flags.add(BRIDGE_FLAGS[task_id])
            RetentionManager.bridge_mark(game, task_id)

    @staticmethod
    def on_contract_complete(game: Game, mission: Mission) -> None:
        r = game.retention
        xp = SEASON_XP_CONTRACT + (40 if mission.weekly_bounty else 0)
        RetentionManager.add_season_xp(game, xp, mission.mission_id)
        if mission.weekly_bounty:
            r.weekly_completed = True
            game.player.tutorial_flags.add("daily_weekly_bounty_done")
            RetentionManager.add_season_xp(game, SEASON_XP_WEEKLY, "weekly bounty")
            RetentionManager.on_bridge_event(game, "weekly")
        if not mission.operation_id:
            RetentionManager.on_bridge_event(game, "contract")

    @staticmethod
    def on_daily_complete(game: Game) -> None:
        RetentionManager.add_season_xp(game, SEASON_XP_DAILY, "daily challenge")
        RetentionManager.on_bridge_event(game, "daily")
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
        RetentionManager.check_bridge_triggers(game)

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
        RetentionManager.on_bridge_event(game, "block")

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
        RetentionManager.on_bridge_event(game, "probe")
        RetentionManager._check_recon_missions(game, server_ip)

    @staticmethod
    def on_ghost_complete(game: Game, server_ip: str) -> None:
        game.retention.ghost_targets_done.add(server_ip)
        game.player.tutorial_flags.add("daily_ghost_contract_done")
        RetentionManager.on_bridge_event(game, "ghost")
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
        if mtype == "lateral":
            from session_content import LateralManager
            return LateralManager.is_chain_satisfied(game, mission)
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

        from depth_systems import ModifierManager, ToolManager

        if ModifierManager.requires_vpn(mission) and not p.vpn_active:
            return False

        def logs_ok(server, require_wipe: bool) -> bool:
            if not require_wipe:
                return True
            if not server:
                return True
            from longevity_content import ToolPuzzleManager
            if not ToolPuzzleManager.mission_extra_checks(game, server, mission):
                return False
            return ToolManager.logs_clean_enough(game, server, p)

        if getattr(mission, "heist_id", "") and mtype in (
            "exfil", "root_heist", "ghost", "social", "recon", "scan_subnet",
        ):
            if mtype == "ghost":
                return mission.target_ip in game.retention.ghost_targets_done
            if mtype == "recon":
                return (
                    mission.target_ip in p.discovered_ips
                    and mission.target_ip in game.retention.session_probed
                )
            if mtype == "scan_subnet":
                return mission.target_ip in p.subnets_scanned
            if mtype == "social":
                if not mission.target_file:
                    return False
                fname = mission.target_file.rsplit("/", 1)[-1]
                if f"/home/hacker/downloads/{fname}" not in p.files:
                    return False
                return logs_ok(game.network.get_server(mission.target_ip), mission.require_log_wipe)
            if not mission.target_file:
                return mtype == "ghost"
            fname = mission.target_file.rsplit("/", 1)[-1]
            if f"/home/hacker/downloads/{fname}" not in p.files:
                return False
            server = game.network.get_server(mission.target_ip)
            if mtype == "root_heist" and mission.require_privesc:
                if mission.target_ip not in p.privesc_hosts and not p.remote_was_root:
                    return False
            return logs_ok(server, mission.require_log_wipe)

        if mtype == "social":
            server = game.network.get_server(mission.target_ip)
            if not mission.target_file:
                return False
            fname = mission.target_file.rsplit("/", 1)[-1]
            if f"/home/hacker/downloads/{fname}" not in p.files:
                return False
            pid = getattr(server, "puzzle_id", "") if server else ""
            if pid == "http_intel":
                if f"curl_{mission.target_ip}_http_intel_read" not in game.variety.social_flags:
                    if mission.target_ip not in game.meta.phished_ips:
                        return False
            elif pid == "spearphish_read":
                if f"spear_{mission.target_ip}" not in game.variety.social_flags:
                    if mission.target_ip not in game.meta.phished_ips:
                        return False
            return logs_ok(server, mission.require_log_wipe)

        if mtype == "timing":
            from variety_content import VarietyManager
            if VarietyManager.timing_expired(game, mission):
                return False
            if not mission.target_file:
                return False
            fname = mission.target_file.rsplit("/", 1)[-1]
            if f"/home/hacker/downloads/{fname}" not in p.files:
                return False
            server = game.network.get_server(mission.target_ip)
            return logs_ok(server, mission.require_log_wipe)

        if mtype == "pivot":
            step = game.variety.pivot_step.get(mission.mission_id, 0)
            if step < 2:
                return False
            if not mission.target_file:
                return False
            fname = mission.target_file.rsplit("/", 1)[-1]
            if f"/home/hacker/downloads/{fname}" not in p.files:
                return False
            jump = game.network.get_server(mission.pivot_host)
            target = game.network.get_server(mission.target_ip)
            if jump and not logs_ok(jump, True):
                return False
            if target and not logs_ok(target, True):
                return False
            return True

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
            return logs_ok(server, mission.require_log_wipe)

        return False
