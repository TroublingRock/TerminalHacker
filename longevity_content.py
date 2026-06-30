#!/usr/bin/env python3
"""v1.8 longevity: tool puzzles, new hosts, story arcs, season cycles, rivals, endless depth."""

from __future__ import annotations

import random
from datetime import date
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from main import Game, Mission, Server

# ---------------------------------------------------------------------------
# Tool-gated puzzles (merged into HOST_PUZZLES at import)
# ---------------------------------------------------------------------------

TOOL_PUZZLES: dict[str, dict[str, Any]] = {
    "phish_gate": {
        "name": "Spearphish gate",
        "hint": "Run phish <IP> before SSH — inbox intel unlocks crack.",
        "requires": "phish",
    },
    "tunnel_jump": {
        "name": "Tunnel jump",
        "hint": "SSH only via tunnel: tunnel 8022 <IP> 22 then connect localhost 8022.",
        "tunnel_only": True,
        "remote_port": 22,
    },
    "plant_backdoor": {
        "name": "Plant backdoor",
        "hint": "Crack shell, run plant, then exfil — persistence required.",
        "requires_plant": True,
    },
    "forge_cover": {
        "name": "Forge cover",
        "hint": "After loot run forge on shell — auditors sweep auth.log.",
        "requires_forge": True,
    },
}

# ---------------------------------------------------------------------------
# Extended company hosts — new subnets, less IP recycling
# ---------------------------------------------------------------------------

EXTENDED_COMPANY_HOSTS: list[dict[str, Any]] = [
    {"ip": "10.50.0.12", "hostname": "stream-cdn", "company": "CinderWorks Media",
     "security_level": 2, "ssh_password": "cdn_edge!", "subnet": "10.50.0.0/24",
     "story": "Media CDN edge — phish the ops team.", "min_rep": 150,
     "puzzle_id": "phish_gate",
     "extra_files": {"/home/ops/playlist_manifest.json": '{"live": true}\n'}},
    {"ip": "10.50.0.44", "hostname": "ad-bidder", "company": "CinderWorks AdTech",
     "security_level": 3, "ssh_password": "rtb_2024", "subnet": "10.50.0.0/24",
     "story": "Real-time bidder — tunnel through DMZ.", "min_rep": 150,
     "puzzle_id": "tunnel_jump",
     "extra_files": {"/home/analyst/bid_logs.csv": "impression,cpm\n"}},
    {"ip": "10.60.0.18", "hostname": "fleet-tracker", "company": "Driftline Shipping",
     "security_level": 3, "ssh_password": "ais_track", "subnet": "10.60.0.0/24",
     "story": "Maritime AIS relay — plant persistence.", "min_rep": 400,
     "puzzle_id": "plant_backdoor", "privesc_available": True,
     "extra_files": {"/home/ops/voyage_manifest.csv": "hull,lat,lon\n"}},
    {"ip": "10.60.0.77", "hostname": "port-edi", "company": "Driftline EDI",
     "security_level": 4, "ssh_password": "edi_gate!", "subnet": "10.60.0.0/24",
     "story": "Customs EDI gateway — forge logs after exfil.", "min_rep": 400,
     "puzzle_id": "forge_cover",
     "extra_files": {"/home/edi/customs_queue.xml": "<queue/>\n"}},
    {"ip": "10.70.0.21", "hostname": "defense-rfp", "company": "Garrison Mutual",
     "security_level": 4, "ssh_password": "rfp_vault", "subnet": "10.70.0.0/24",
     "story": "Defense contractor RFP vault.", "min_rep": 400, "privesc_available": True,
     "puzzle_id": "staggered_probe",
     "extra_files": {"/home/admin/rfp_draft.pdf.meta": "classification=secret\n"}},
    {"ip": "10.70.0.55", "hostname": "sat-uplink", "company": "Halcyon Aerospace",
     "security_level": 5, "ssh_password": "tle_data!", "subnet": "10.70.0.0/24",
     "story": "Satellite telemetry uplink.", "min_rep": 400,
     "puzzle_id": "port_hop",
     "extra_files": {"/home/ops/orbit_schedule.json": '{"sats": 3}\n'}},
    {"ip": "10.80.0.33", "hostname": "quant-lab", "company": "EmberGrid Research",
     "security_level": 5, "ssh_password": "qbit_lab!", "subnet": "10.80.0.0/24",
     "story": "Grid load forecasting lab.", "min_rep": 750, "privesc_available": True,
     "puzzle_id": "dual_account",
     "extra_files": {"/home/research/forecast_model.bin": "MODEL_V3\n"}},
    {"ip": "10.80.0.90", "hostname": "scada-bridge", "company": "EmberGrid SCADA",
     "security_level": 6, "ssh_password": "scada_ops!", "subnet": "10.80.0.0/24",
     "story": "CHAOS-adjacent SCADA bridge. Trace risk elevated.", "min_rep": 750,
     "chaos_only": True, "puzzle_id": "honeypot_decoy",
     "extra_files": {"/home/ops/grid_telemetry.log": "voltage_ok\n"}},
]

EXTENDED_ROUTES: list[tuple[int, str, str]] = [
    (1, "10.50.0.0/24", "192.168.1.1"),
    (2, "10.60.0.0/24", "10.0.0.1"),
    (2, "10.70.0.0/24", "10.0.0.1"),
    (3, "10.80.0.0/24", "172.16.0.8"),
]

EXTENDED_PUZZLE_MAP: dict[str, str] = {
    h["ip"]: h["puzzle_id"] for h in EXTENDED_COMPANY_HOSTS if h.get("puzzle_id")
}

# ---------------------------------------------------------------------------
# Expanded weekly bounties / hourlies / heists (monthly pool rotation)
# ---------------------------------------------------------------------------

EXTENDED_WEEKLY_BOUNTIES: list[dict[str, Any]] = [
    {"id": "wb-cdn", "broker": "cipher7", "title": "CDN Edge Breach",
     "briefing": "WEEKLY: Phish then crack stream-cdn (10.50.0.12), exfil playlist_manifest.json.",
     "target_ip": "10.50.0.12", "target_file": "/home/ops/playlist_manifest.json",
     "reward": 1300, "rep_reward": 120, "min_rep": 150, "mission_type": "social"},
    {"id": "wb-adbid", "broker": "nullbyte", "title": "Ad Bidder Tunnel",
     "briefing": "WEEKLY: Tunnel into ad-bidder (10.50.0.44), exfil bid_logs.csv clean.",
     "target_ip": "10.50.0.44", "target_file": "/home/analyst/bid_logs.csv",
     "reward": 1450, "rep_reward": 125, "min_rep": 150},
    {"id": "wb-fleet", "broker": "shade_runner", "title": "Fleet Tracker Plant",
     "briefing": "WEEKLY: Crack fleet-tracker (10.60.0.18), plant backdoor, exfil voyage_manifest.csv.",
     "target_ip": "10.60.0.18", "target_file": "/home/ops/voyage_manifest.csv",
     "reward": 1800, "rep_reward": 140, "min_rep": 400, "require_privesc": False},
    {"id": "wb-edi", "broker": "packet_queen", "title": "EDI Forge Run",
     "briefing": "WEEKLY: Hit port-edi (10.60.0.77) — forge logs after exfil customs_queue.xml.",
     "target_ip": "10.60.0.77", "target_file": "/home/edi/customs_queue.xml",
     "reward": 1900, "rep_reward": 145, "min_rep": 400},
    {"id": "wb-rfp", "broker": "ghost_broker", "title": "Defense RFP Raid",
     "briefing": "WEEKLY: Privesc defense-rfp (10.70.0.21), exfil rfp_draft.pdf.meta.",
     "target_ip": "10.70.0.21", "target_file": "/home/admin/rfp_draft.pdf.meta",
     "reward": 2100, "rep_reward": 155, "min_rep": 400, "require_privesc": True, "mission_type": "root_heist"},
    {"id": "wb-sat", "broker": "cipher7", "title": "Satellite Uplink",
     "briefing": "WEEKLY: Port-hop sat-uplink (10.70.0.55), exfil orbit_schedule.json.",
     "target_ip": "10.70.0.55", "target_file": "/home/ops/orbit_schedule.json",
     "reward": 2300, "rep_reward": 165, "min_rep": 400},
    {"id": "wb-quant", "broker": "nullbyte", "title": "Quant Lab Heist",
     "briefing": "WEEKLY: Dual-account pivot on quant-lab (10.80.0.33), root exfil forecast_model.bin.",
     "target_ip": "10.80.0.33", "target_file": "/home/research/forecast_model.bin",
     "reward": 3200, "rep_reward": 190, "min_rep": 750, "require_privesc": True, "mission_type": "root_heist"},
    {"id": "wb-scada", "broker": "shade_runner", "title": "SCADA Bridge Job",
     "briefing": "WEEKLY: Avoid honeypot on scada-bridge (10.80.0.90), exfil real payload.",
     "target_ip": "10.80.0.90", "target_file": "/opt/secure/scada_bridge_payload.bin",
     "reward": 4200, "rep_reward": 220, "min_rep": 750, "mission_type": "exfil"},
]

EXTENDED_HOURLY_EVENTS: list[dict[str, Any]] = [
    {"id": "hour-cdn", "title": "FLASH: CDN Rush", "broker": "cipher7",
     "target_ip": "10.50.0.12", "target_file": "/home/ops/playlist_manifest.json",
     "multiplier": 2.1, "min_rep": 150, "mission_type": "social"},
    {"id": "hour-adbid", "title": "FLASH: RTB Snatch", "broker": "nullbyte",
     "target_ip": "10.50.0.44", "target_file": "/home/analyst/bid_logs.csv",
     "multiplier": 2.2, "min_rep": 150},
    {"id": "hour-fleet", "title": "FLASH: Fleet Manifest", "broker": "shade_runner",
     "target_ip": "10.60.0.18", "target_file": "/home/ops/voyage_manifest.csv",
     "multiplier": 2.4, "min_rep": 400},
    {"id": "hour-edi", "title": "FLASH: EDI Queue", "broker": "packet_queen",
     "target_ip": "10.60.0.77", "target_file": "/home/edi/customs_queue.xml",
     "multiplier": 2.3, "min_rep": 400},
    {"id": "hour-rfp", "title": "FLASH: RFP Leak", "broker": "ghost_broker",
     "target_ip": "10.70.0.21", "target_file": "/home/admin/rfp_draft.pdf.meta",
     "multiplier": 2.5, "min_rep": 400, "require_privesc": True, "mission_type": "root_heist"},
    {"id": "hour-sat", "title": "FLASH: TLE Grab", "broker": "cipher7",
     "target_ip": "10.70.0.55", "target_file": "/home/ops/orbit_schedule.json",
     "multiplier": 2.2, "min_rep": 400},
    {"id": "hour-quant", "title": "FLASH: Model Theft", "broker": "nullbyte",
     "target_ip": "10.80.0.33", "target_file": "/home/research/forecast_model.bin",
     "multiplier": 2.8, "min_rep": 750, "require_privesc": True, "mission_type": "root_heist"},
    {"id": "hour-scada", "title": "FLASH: Grid Telemetry", "broker": "acid_k",
     "target_ip": "10.80.0.90", "target_file": "/opt/secure/scada_bridge_payload.bin",
     "multiplier": 3.2, "min_rep": 750},
]

EXTENDED_WEEKLY_HEISTS: list[dict[str, Any]] = [
    {
        "id": "heist-dragon",
        "name": "Dragon Freight Raid",
        "broker": "shade_runner",
        "parts": [
            {"step": 1, "briefing": "HEIST P1: Recon fleet-tracker (10.60.0.18) — map shipping lanes.",
             "target_ip": "10.60.0.18", "mission_type": "recon", "reward": 380, "rep_reward": 48},
            {"step": 2, "branch": {
                "manifest": {"briefing": "HEIST P2 [MANIFEST]: Plant on fleet-tracker, exfil voyage_manifest.csv.",
                             "target_ip": "10.60.0.18", "target_file": "/home/ops/voyage_manifest.csv", "mission_type": "exfil"},
                "edi": {"briefing": "HEIST P2 [EDI]: Forge-run port-edi (10.60.0.77) — customs_queue.xml.",
                        "target_ip": "10.60.0.77", "target_file": "/home/edi/customs_queue.xml", "mission_type": "exfil"},
                "ghost": {"briefing": "HEIST P2 [GHOST]: Zero-trace on fleet-tracker — no loot.",
                          "target_ip": "10.60.0.18", "target_file": "", "mission_type": "ghost"},
            }, "reward": 1050, "rep_reward": 95},
            {"step": 3, "briefing": "HEIST P3: Finish on port-edi with clean logs.",
             "target_ip": "10.60.0.77", "target_file": "/home/edi/customs_queue.xml",
             "mission_type": "exfil", "reward": 1900, "rep_reward": 140},
        ],
    },
    {
        "id": "heist-orbit",
        "name": "Orbit Shadow Heist",
        "broker": "ghost_broker",
        "parts": [
            {"step": 1, "briefing": "HEIST P1: Scan 10.70.0.0/24 — locate sat-uplink and defense-rfp.",
             "target_ip": "10.70.0.0/24", "mission_type": "scan_subnet", "reward": 400, "rep_reward": 50},
            {"step": 2, "branch": {
                "sat": {"briefing": "HEIST P2 [SAT]: Port-hop sat-uplink, exfil orbit_schedule.json.",
                        "target_ip": "10.70.0.55", "target_file": "/home/ops/orbit_schedule.json", "mission_type": "exfil"},
                "rfp": {"briefing": "HEIST P2 [RFP]: Root heist defense-rfp classified meta.",
                        "target_ip": "10.70.0.21", "target_file": "/home/admin/rfp_draft.pdf.meta",
                        "mission_type": "root_heist", "require_privesc": True},
                "phish": {"briefing": "HEIST P2 [PHISH]: Spearphish stream-cdn path via 10.50.0.12 intel.",
                          "target_ip": "10.50.0.12", "target_file": "/home/ops/playlist_manifest.json", "mission_type": "social"},
            }, "reward": 1200, "rep_reward": 105},
            {"step": 3, "briefing": "HEIST P3: Quant-lab root exfil — finish the orbit legend.",
             "target_ip": "10.80.0.33", "target_file": "/home/research/forecast_model.bin",
             "mission_type": "root_heist", "require_privesc": True, "reward": 2400, "rep_reward": 160},
        ],
    },
]

# 8 additional heists — 12 total, 4 active per calendar month (3-month full cycle)
MEGA_WEEKLY_HEISTS: list[dict[str, Any]] = [
    {
        "id": "heist-cipher",
        "name": "CipherLink Breach",
        "broker": "cipher7",
        "theme": "brokers",
        "modifiers": ["split_tunnel"],
        "parts": [
            {"step": 1, "briefing": "HEIST P1: Ghost vendor-vpn (192.168.1.30) — zero traces recon.",
             "target_ip": "192.168.1.30", "mission_type": "ghost", "reward": 360, "rep_reward": 46},
            {"step": 2, "branch": {
                "research": {"briefing": "HEIST P2 [LAB]: Exfil model_weights.bin from research-node.",
                               "target_ip": "192.168.1.25", "target_file": "/home/admin/model_weights.bin", "mission_type": "exfil"},
                "vpn": {"briefing": "HEIST P2 [VPN]: Pivot through vendor-vpn to corp-gateway notes.",
                          "target_ip": "192.168.1.10", "target_file": "/home/admin/notes.txt", "mission_type": "exfil"},
                "intel": {"briefing": "HEIST P2 [INTEL]: curl intel on vendor-vpn before exfil.",
                            "target_ip": "192.168.1.30", "target_file": "/home/admin/notes.txt", "mission_type": "social"},
            }, "reward": 1000, "rep_reward": 92},
            {"step": 3, "briefing": "HEIST P3: Clean sweep on research-node — finish CipherLink legend.",
             "target_ip": "192.168.1.25", "target_file": "/home/admin/model_weights.bin",
             "mission_type": "exfil", "reward": 1850, "rep_reward": 135},
        ],
    },
    {
        "id": "heist-perimeter",
        "name": "Perimeter Storm",
        "broker": "ghost_broker",
        "theme": "corps",
        "modifiers": ["deadline", "rival_race"],
        "parts": [
            {"step": 1, "briefing": "HEIST P1: Probe corp-gateway (192.168.1.10) twice — IDS baseline.",
             "target_ip": "192.168.1.10", "mission_type": "recon", "reward": 370, "rep_reward": 47},
            {"step": 2, "branch": {
                "dc": {"briefing": "HEIST P2 [DC]: Race to corp-dc corporate_secrets.txt.",
                       "target_ip": "10.0.0.42", "target_file": "/home/admin/corporate_secrets.txt", "mission_type": "exfil"},
                "hr": {"briefing": "HEIST P2 [HR]: Spearphish hr-portal terminations.csv.",
                       "target_ip": "10.0.0.88", "target_file": "/home/admin/terminations.csv", "mission_type": "social"},
                "vault": {"briefing": "HEIST P2 [VAULT]: Root vault-server payroll.csv.",
                          "target_ip": "10.0.0.55", "target_file": "/root/payroll.csv",
                          "mission_type": "root_heist", "require_privesc": True},
            }, "reward": 1150, "rep_reward": 102},
            {"step": 3, "briefing": "HEIST P3: Ghost egress from corp-dc — zero traces finale.",
             "target_ip": "10.0.0.42", "target_file": "", "mission_type": "ghost",
             "reward": 1950, "rep_reward": 142},
        ],
    },
    {
        "id": "heist-chaos",
        "name": "Blackout Protocol",
        "broker": "acid_k",
        "theme": "rivals",
        "modifiers": ["honey_net", "deadline"],
        "parts": [
            {"step": 1, "briefing": "HEIST P1: Scan chaos subnet 203.0.113.0/24 — locate C2.",
             "target_ip": "203.0.113.0/24", "mission_type": "scan_chaos", "reward": 420, "rep_reward": 52},
            {"step": 2, "branch": {
                "c2": {"briefing": "HEIST P2 [C2]: Root chaos-c2 — exfil rival_plans.txt.",
                       "target_ip": "203.0.113.66", "target_file": "/root/rival_plans.txt",
                       "mission_type": "root_heist", "require_privesc": True},
                "wallet": {"briefing": "HEIST P2 [WALLET]: Cold wallet heist dark-vault.",
                           "target_ip": "203.0.113.99", "target_file": "/root/cold_wallet.dat",
                           "mission_type": "root_heist", "require_privesc": True},
                "ghost": {"briefing": "HEIST P2 [GHOST]: Touch C2, leave zero traces — no loot.",
                          "target_ip": "203.0.113.66", "target_file": "", "mission_type": "ghost"},
            }, "reward": 1400, "rep_reward": 110},
            {"step": 3, "briefing": "HEIST P3: Exfil proof from chaos-c2 — survive double trace.",
             "target_ip": "203.0.113.66", "target_file": "/root/rival_plans.txt",
             "mission_type": "root_heist", "require_privesc": True, "reward": 2600, "rep_reward": 170},
        ],
    },
    {
        "id": "heist-media",
        "name": "Signal Hijack",
        "broker": "nullbyte",
        "theme": "brokers",
        "modifiers": ["air_gapped"],
        "parts": [
            {"step": 1, "briefing": "HEIST P1: Phish stream-cdn (10.50.0.12) — prep social lane.",
             "target_ip": "10.50.0.12", "mission_type": "social", "reward": 390, "rep_reward": 49,
             "target_file": "/home/ops/playlist_manifest.json"},
            {"step": 2, "branch": {
                "cdn": {"briefing": "HEIST P2 [CDN]: Exfil playlist_manifest.json clean.",
                        "target_ip": "10.50.0.12", "target_file": "/home/ops/playlist_manifest.json", "mission_type": "exfil"},
                "rtb": {"briefing": "HEIST P2 [RTB]: Tunnel ad-bidder (10.50.0.44), exfil bid_logs.",
                        "target_ip": "10.50.0.44", "target_file": "/home/analyst/bid_logs.csv", "mission_type": "exfil"},
                "sabotage": {"briefing": "HEIST P2 [SABOTAGE]: Ghost ad-bidder — no exfil.",
                             "target_ip": "10.50.0.44", "target_file": "", "mission_type": "ghost"},
            }, "reward": 1080, "rep_reward": 96},
            {"step": 3, "briefing": "HEIST P3: Forge-run port-edi customs queue — media blackout.",
             "target_ip": "10.60.0.77", "target_file": "/home/edi/customs_queue.xml",
             "mission_type": "exfil", "reward": 2000, "rep_reward": 145},
        ],
    },
    {
        "id": "heist-ledger",
        "name": "SWIFT Ledger Run",
        "broker": "shade_runner",
        "theme": "corps",
        "modifiers": ["no_shop", "deadline"],
        "parts": [
            {"step": 1, "briefing": "HEIST P1: Recon fin-trading (172.16.0.20) — map HFT floor.",
             "target_ip": "172.16.0.20", "mission_type": "recon", "reward": 410, "rep_reward": 51},
            {"step": 2, "branch": {
                "algo": {"briefing": "HEIST P2 [ALGO]: Exfil algo_config.yml from fin-trading.",
                         "target_ip": "172.16.0.20", "target_file": "/home/admin/algo_config.yml", "mission_type": "exfil"},
                "wire": {"briefing": "HEIST P2 [WIRE]: Root bank-core wire_keys.env.",
                         "target_ip": "172.16.0.33", "target_file": "/root/wire_keys.env",
                         "mission_type": "root_heist", "require_privesc": True},
                "frame": {"briefing": "HEIST P2 [FRAME]: Plant on fin-trading, ghost out.",
                          "target_ip": "172.16.0.20", "target_file": "", "mission_type": "ghost"},
            }, "reward": 1250, "rep_reward": 108},
            {"step": 3, "briefing": "HEIST P3: Bank-core proof-of-access — wire_keys finale.",
             "target_ip": "172.16.0.33", "target_file": "/root/wire_keys.env",
             "mission_type": "root_heist", "require_privesc": True, "reward": 2500, "rep_reward": 165},
        ],
    },
    {
        "id": "heist-grid",
        "name": "Grid Zero",
        "broker": "packet_queen",
        "theme": "corps",
        "modifiers": ["split_tunnel", "honey_net"],
        "parts": [
            {"step": 1, "briefing": "HEIST P1: Scan 10.80.0.0/24 — SCADA and quant-lab online.",
             "target_ip": "10.80.0.0/24", "mission_type": "scan_subnet", "reward": 430, "rep_reward": 53},
            {"step": 2, "branch": {
                "scada": {"briefing": "HEIST P2 [SCADA]: Honeypot dodge on scada-bridge — real payload only.",
                          "target_ip": "10.80.0.90", "target_file": "/opt/secure/scada_bridge_payload.bin", "mission_type": "exfil"},
                "quant": {"briefing": "HEIST P2 [QUANT]: Root quant-lab forecast_model.bin.",
                          "target_ip": "10.80.0.33", "target_file": "/home/research/forecast_model.bin",
                          "mission_type": "root_heist", "require_privesc": True},
                "telemetry": {"briefing": "HEIST P2 [TELEM]: Ghost scada-bridge — zero traces.",
                              "target_ip": "10.80.0.90", "target_file": "", "mission_type": "ghost"},
            }, "reward": 1350, "rep_reward": 112},
            {"step": 3, "briefing": "HEIST P3: Forge cover on quant-lab — grid legend sealed.",
             "target_ip": "10.80.0.33", "target_file": "/home/research/forecast_model.bin",
             "mission_type": "root_heist", "require_privesc": True, "reward": 2700, "rep_reward": 175},
        ],
    },
    {
        "id": "heist-syndicate",
        "name": "Syndicate Gambit",
        "broker": "phantom_pkt",
        "theme": "rivals",
        "modifiers": ["rival_race"],
        "parts": [
            {"step": 1, "briefing": "HEIST P1: Plant backdoor on fleet-tracker (10.60.0.18).",
             "target_ip": "10.60.0.18", "mission_type": "recon", "reward": 400, "rep_reward": 50},
            {"step": 2, "branch": {
                "fleet": {"briefing": "HEIST P2 [FLEET]: Exfil voyage_manifest via backdoor path.",
                          "target_ip": "10.60.0.18", "target_file": "/home/ops/voyage_manifest.csv", "mission_type": "exfil"},
                "defense": {"briefing": "HEIST P2 [DEFENSE]: Root defense-rfp classified meta.",
                            "target_ip": "10.70.0.21", "target_file": "/home/admin/rfp_draft.pdf.meta",
                            "mission_type": "root_heist", "require_privesc": True},
                "rival": {"briefing": "HEIST P2 [RIVAL]: Race acid_k to chaos-c2 intel.",
                          "target_ip": "203.0.113.66", "target_file": "/root/rival_plans.txt",
                          "mission_type": "root_heist", "require_privesc": True},
            }, "reward": 1300, "rep_reward": 115},
            {"step": 3, "briefing": "HEIST P3: Syndicate cut — dark-vault cold_wallet.dat.",
             "target_ip": "203.0.113.99", "target_file": "/root/cold_wallet.dat",
             "mission_type": "root_heist", "require_privesc": True, "reward": 2800, "rep_reward": 180},
        ],
    },
    {
        "id": "heist-vaultrun",
        "name": "Vault Circuit",
        "broker": "nyx_root",
        "theme": "rivals",
        "modifiers": ["deadline", "no_shop"],
        "parts": [
            {"step": 1, "briefing": "HEIST P1: Tunnel into ad-bidder (10.50.0.44) — map RTB path.",
             "target_ip": "10.50.0.44", "mission_type": "recon", "reward": 385, "rep_reward": 48},
            {"step": 2, "branch": {
                "payroll": {"briefing": "HEIST P2 [PAYROLL]: Root vault-server payroll.csv.",
                            "target_ip": "10.0.0.55", "target_file": "/root/payroll.csv",
                            "mission_type": "root_heist", "require_privesc": True},
                "sat": {"briefing": "HEIST P2 [SAT]: Port-hop sat-uplink orbit_schedule.json.",
                        "target_ip": "10.70.0.55", "target_file": "/home/ops/orbit_schedule.json", "mission_type": "exfil"},
                "wallet": {"briefing": "HEIST P2 [WALLET]: Cold wallet dark-vault.dat.",
                           "target_ip": "203.0.113.99", "target_file": "/root/cold_wallet.dat",
                           "mission_type": "root_heist", "require_privesc": True},
            }, "reward": 1280, "rep_reward": 110},
            {"step": 3, "briefing": "HEIST P3: Triple-vault finale — payroll + wire keys combo path.",
             "target_ip": "10.0.0.55", "target_file": "/root/payroll.csv",
             "mission_type": "root_heist", "require_privesc": True, "reward": 2650, "rep_reward": 172},
        ],
    },
]

# ---------------------------------------------------------------------------
# Story-exclusive contract arcs (3 missions per branch)
# ---------------------------------------------------------------------------

STORY_ARC_MISSIONS: dict[str, list[dict[str, Any]]] = {
    "ghost": [
        {"mission_id": "arc-ghost-1", "broker": "ghost_broker",
         "briefing": "ARC [GHOST 1/3]: Corporate lane — exfil corporate_secrets.txt from corp-dc (10.0.0.42).",
         "target_ip": "10.0.0.42", "target_file": "/home/admin/corporate_secrets.txt",
         "reward": 600, "rep_reward": 70, "story_arc": "ghost"},
        {"mission_id": "arc-ghost-2", "broker": "ghost_broker",
         "briefing": "ARC [GHOST 2/3]: Treasury pressure — root payroll.csv on vault-server (10.0.0.55).",
         "target_ip": "10.0.0.55", "target_file": "/root/payroll.csv",
         "reward": 900, "rep_reward": 90, "require_privesc": True, "mission_type": "root_heist", "story_arc": "ghost"},
        {"mission_id": "arc-ghost-3", "broker": "shade_runner",
         "briefing": "ARC [GHOST 3/3]: Defense RFP — privesc defense-rfp (10.70.0.21), exfil classified meta.",
         "target_ip": "10.70.0.21", "target_file": "/home/admin/rfp_draft.pdf.meta",
         "reward": 1200, "rep_reward": 110, "require_privesc": True, "mission_type": "root_heist", "story_arc": "ghost"},
    ],
    "rivals": [
        {"mission_id": "arc-rival-1", "broker": "acid_k",
         "briefing": "ARC [RIVAL 1/3]: Chaos whisper — crack chaos-c2 (203.0.113.66), map rival_plans.txt.",
         "target_ip": "203.0.113.66", "target_file": "/root/rival_plans.txt",
         "reward": 800, "rep_reward": 60, "require_privesc": True, "mission_type": "root_heist", "story_arc": "rivals"},
        {"mission_id": "arc-rival-2", "broker": "zero_cool",
         "briefing": "ARC [RIVAL 2/3]: SCADA bridge — avoid honeypot on scada-bridge (10.80.0.90).",
         "target_ip": "10.80.0.90", "target_file": "/opt/secure/scada_bridge_payload.bin",
         "reward": 1100, "rep_reward": 80, "story_arc": "rivals"},
        {"mission_id": "arc-rival-3", "broker": "phantom_pkt",
         "briefing": "ARC [RIVAL 3/3]: Cold wallet — root heist dark-vault (203.0.113.99).",
         "target_ip": "203.0.113.99", "target_file": "/root/cold_wallet.dat",
         "reward": 2000, "rep_reward": 120, "require_privesc": True, "mission_type": "root_heist", "story_arc": "rivals"},
    ],
    "solo": [
        {"mission_id": "arc-solo-1", "broker": "cipher7",
         "briefing": "ARC [SOLO 1/3]: Open market — hit ad-bidder (10.50.0.44) via tunnel, exfil bid_logs.",
         "target_ip": "10.50.0.44", "target_file": "/home/analyst/bid_logs.csv",
         "reward": 500, "rep_reward": 55, "story_arc": "solo"},
        {"mission_id": "arc-solo-2", "broker": "cipher7",
         "briefing": "ARC [SOLO 2/3]: Independent run — plant + exfil on fleet-tracker (10.60.0.18).",
         "target_ip": "10.60.0.18", "target_file": "/home/ops/voyage_manifest.csv",
         "reward": 700, "rep_reward": 65, "story_arc": "solo"},
        {"mission_id": "arc-solo-3", "broker": "cipher7",
         "briefing": "ARC [SOLO 3/3]: Satellite grab — sat-uplink (10.70.0.55) orbit_schedule.json, clean egress.",
         "target_ip": "10.70.0.55", "target_file": "/home/ops/orbit_schedule.json",
         "reward": 950, "rep_reward": 80, "story_arc": "solo"},
    ],
}

# ---------------------------------------------------------------------------
# Endless floor modifiers & bosses
# ---------------------------------------------------------------------------

FLOOR_MODIFIERS: dict[str, dict[str, Any]] = {
    "air_gapped": {"label": "Air-gapped", "desc": "No curl on floor contract."},
    "trace_storm": {"label": "Trace storm", "desc": "+12% disconnect trace chance."},
    "rival_hunt": {"label": "Rival hunt", "desc": "Rival probe every 3 commands."},
    "speed_run": {"label": "Speed run", "desc": "12-command window on floor."},
    "tool_lock": {"label": "Tool lock", "desc": "Requires floor puzzle tool step."},
}

ENDLESS_ARCHETYPES = ("exfil", "ghost", "root_heist", "social", "timing", "tunnel")

BOSS_PUZZLES = ("phish_gate", "tunnel_jump", "plant_backdoor", "forge_cover")


def all_weekly_bounties() -> list[dict[str, Any]]:
    from retention import WEEKLY_BOUNTIES
    return WEEKLY_BOUNTIES + EXTENDED_WEEKLY_BOUNTIES


def all_hourly_events() -> list[dict[str, Any]]:
    from session_content import HOURLY_EVENTS
    return HOURLY_EVENTS + EXTENDED_HOURLY_EVENTS


def all_weekly_heists() -> list[dict[str, Any]]:
    from depth_systems import WEEKLY_HEISTS
    return WEEKLY_HEISTS + EXTENDED_WEEKLY_HEISTS + MEGA_WEEKLY_HEISTS


HEISTS_PER_MONTH = 4
MONTHLY_CYCLE_MONTHS = 3  # 12 heists / 4 per month


def heist_for_week(week: int) -> dict[str, Any]:
    """Legacy helper — prefer HeistRotationManager.current_heist()."""
    return HeistRotationManager.current_heist()


def heist_branch_choices(heist: dict[str, Any]) -> str:
    part = heist["parts"][1]
    opts = part.get("branch", {})
    return "  heist choose " + "|".join(opts.keys())


class HeistRotationManager:
    @staticmethod
    def month_key() -> str:
        return date.today().strftime("%Y-%m")

    @staticmethod
    def week_slot_in_month() -> int:
        return min(3, (date.today().day - 1) // 7)

    @staticmethod
    def monthly_pool(ym: str | None = None) -> list[dict[str, Any]]:
        pool = all_weekly_heists()
        ym = ym or HeistRotationManager.month_key()
        month = int(ym.split("-")[1])
        offset = ((month - 1) % MONTHLY_CYCLE_MONTHS) * HEISTS_PER_MONTH
        return [pool[(offset + i) % len(pool)] for i in range(HEISTS_PER_MONTH)]

    @staticmethod
    def rotation_key() -> str:
        from retention import RetentionManager
        wk = RetentionManager.week_key()
        return f"{wk}|{HeistRotationManager.month_key()}|s{HeistRotationManager.week_slot_in_month()}"

    @staticmethod
    def current_heist(ym: str | None = None) -> dict[str, Any]:
        monthly = HeistRotationManager.monthly_pool(ym)
        slot = HeistRotationManager.week_slot_in_month()
        return monthly[slot % len(monthly)]

    @staticmethod
    def pool_status_lines(game: Game) -> list[str]:
        ym = HeistRotationManager.month_key()
        monthly = HeistRotationManager.monthly_pool(ym)
        slot = HeistRotationManager.week_slot_in_month()
        lines = [
            f"  Month pool ({ym}) — 4 of {len(all_weekly_heists())} heists active:",
        ]
        for i, h in enumerate(monthly):
            mark = ">" if i == slot else " "
            cleared = "✓" if h["id"] in game.meta.heists_first_cleared else " "
            lines.append(f"    {mark} W{i + 1}: {h['name']} [{cleared}]")
        month = int(ym.split("-")[1])
        months_until_repeat = MONTHLY_CYCLE_MONTHS - ((month - 1) % MONTHLY_CYCLE_MONTHS)
        lines.append(f"  Full pool repeats every {MONTHLY_CYCLE_MONTHS} months ({months_until_repeat} mo until rotation reset)")
        branches = sum(len(v) for v in game.meta.heist_branches_cleared.values())
        lines.append(f"  First clears: {len(game.meta.heists_first_cleared)}/{len(all_weekly_heists())} | Branches mastered: {branches}")
        return lines


class HeistRewardManager:
    FIRST_CLEAR_FACTION = 12
    BRANCH_CASH = 250
    BRANCH_REP = 30

    @staticmethod
    def completion_bonus(game: Game, heist_id: str) -> tuple[int, str]:
        base_score = game.meta.heist_score
        base_bonus = 500 + base_score
        clears = game.meta.heist_clear_counts.get(heist_id, 0)
        mult = max(0.45, 1.0 - 0.12 * clears)
        bonus = int(base_bonus * mult)
        tag = "first clear!" if heist_id not in game.meta.heists_first_cleared else f"repeat x{clears + 1} ({int(mult * 100)}%)"
        return bonus, tag

    @staticmethod
    def on_complete(game: Game, heist_id: str, branch: str) -> tuple[int, str]:
        from main import success
        from faction_consumables import ConsumableManager, CONSUMABLES, FactionRepManager
        from progression import ReputationSystem

        heist = next((h for h in all_weekly_heists() if h["id"] == heist_id), None)
        theme = heist.get("theme", "brokers") if heist else "brokers"

        bonus, tag = HeistRewardManager.completion_bonus(game, heist_id)
        game.player.earn(bonus, f"weekly heist bonus ({tag})")

        first = heist_id not in game.meta.heists_first_cleared
        if first:
            game.meta.heists_first_cleared.add(heist_id)
            key = random.choice(list(CONSUMABLES.keys()))
            ConsumableManager.add_to_inventory(game, key, 1)
            FactionRepManager.shift(game, {theme: HeistRewardManager.FIRST_CLEAR_FACTION})
            success(f"FIRST CLEAR — free {CONSUMABLES[key]['name']} + {theme} faction rep")

        if branch:
            branches = game.meta.heist_branches_cleared.setdefault(heist_id, set())
            if branch not in branches:
                branches.add(branch)
                game.player.earn(HeistRewardManager.BRANCH_CASH, f"new branch [{branch}]")
                ReputationSystem.add_rep(game, HeistRewardManager.BRANCH_REP, f"heist branch {branch}")
                success(f"BRANCH MASTERY [{branch}] — +${HeistRewardManager.BRANCH_CASH} +{HeistRewardManager.BRANCH_REP} rep")

        game.meta.heist_clear_counts[heist_id] = game.meta.heist_clear_counts.get(heist_id, 0) + 1

        total_first = len(game.meta.heists_first_cleared)
        if total_first >= len(all_weekly_heists()):
            game.achievements.unlock("heist_legend")
        if game.meta.heists_cleared >= 12:
            game.achievements.unlock("heist_master")
        return bonus, tag


def bounty_for_week(week: int) -> dict[str, Any]:
    pool = all_weekly_bounties()
    return pool[week % len(pool)]


def hourly_for_slot(slot: int) -> dict[str, Any]:
    pool = all_hourly_events()
    return pool[slot % len(pool)]


class SeasonCycleManager:
    @staticmethod
    def month_key() -> str:
        return date.today().strftime("%Y-%m")

    @staticmethod
    def on_career_session(game: Game) -> None:
        from main import success
        from retention import SEASON_TIERS

        r = game.retention
        mk = SeasonCycleManager.month_key()
        if r.season_month == mk:
            return
        prev = r.season_month
        r.season_month = mk
        if not prev:
            return
        bonus = 200 + r.season_tier * 50
        if r.season_tier >= len(SEASON_TIERS):
            bonus += 500
            game.achievements.unlock("season_complete")
        r.season_xp = 0
        r.season_tier = 0
        r.season_cycles += 1
        if r.season_cycles >= 3:
            game.achievements.unlock("season_veteran")
        game.player.earn(bonus, f"new season {mk}")
        success(f"NEW SEASON {mk} — track reset. Carryover bonus ${bonus}.")
        game.mail.send(
            "ghost_broker@darknet",
            f"Season rollover — {mk}",
            f"New monthly season live. Expanded bounty/heist pools active.\n"
            f"Bonus: ${bonus}\n\n— ghost_broker",
        )


class StoryArcManager:
    @staticmethod
    def deliver_arc(game: Game, choice_key: str) -> None:
        from main import Mission

        specs = STORY_ARC_MISSIONS.get(choice_key, [])
        if not specs:
            return
        if f"arc_{choice_key}_started" in game.story.flags:
            return
        game.story.flags.add(f"arc_{choice_key}_started")
        spec = specs[0]
        if any(m.mission_id == spec["mission_id"] for m in game.missions.missions):
            return
        game.missions.missions.insert(
            0,
            Mission(
                spec["mission_id"], spec["broker"], spec["briefing"],
                spec["target_ip"], spec.get("target_file", ""),
                spec["reward"], rep_reward=spec.get("rep_reward", 50),
                mission_type=spec.get("mission_type", "exfil"),
                require_privesc=spec.get("require_privesc", False),
                story_arc=spec.get("story_arc", choice_key),
            ),
        )
        game.mail.send(
            f"{spec['broker']}@darknet",
            f"STORY ARC — {choice_key.upper()} lane",
            f"{spec['briefing']}\n\nExclusive 3-part arc. Complete to unlock parts 2–3.\n\n— {spec['broker']}",
        )

    @staticmethod
    def on_arc_mission_complete(game: Game, mission: Mission) -> None:
        arc = getattr(mission, "story_arc", "")
        if not arc or arc not in STORY_ARC_MISSIONS:
            return
        specs = STORY_ARC_MISSIONS[arc]
        for i, spec in enumerate(specs):
            if spec["mission_id"] != mission.mission_id:
                continue
            if i + 1 >= len(specs):
                game.story.flags.add(f"arc_{arc}_complete")
                game.achievements.unlock(f"arc_{arc}")
                return
            nxt = specs[i + 1]
            if any(m.mission_id == nxt["mission_id"] for m in game.missions.missions):
                return
            from main import Mission
            game.missions.missions.insert(
                0,
                Mission(
                    nxt["mission_id"], nxt["broker"], nxt["briefing"],
                    nxt["target_ip"], nxt.get("target_file", ""),
                    nxt["reward"], rep_reward=nxt.get("rep_reward", 50),
                    mission_type=nxt.get("mission_type", "exfil"),
                    require_privesc=nxt.get("require_privesc", False),
                    story_arc=arc,
                ),
            )
            game.mail.send(
                f"{nxt['broker']}@darknet",
                f"STORY ARC — part {i + 2}/3",
                f"{nxt['briefing']}\n\n— {nxt['broker']}",
            )
            return


class RivalCounterManager:
    RIVAL_BROKERS = ("acid_k", "phantom_pkt", "nyx_root", "zero_cool")

    @staticmethod
    def maybe_spawn(game: Game, trigger_ip: str) -> None:
        from main import Mission

        if game.player.phase not in ("career", "endless"):
            return
        server = game.network.get_server(trigger_ip)
        if not server or not getattr(server, "procedural", False):
            return
        if random.random() > 0.35:
            return
        if any(getattr(m, "rival_counter", False) and not m.completed for m in game.missions.missions):
            return
        rival = random.choice(RivalCounterManager.RIVAL_BROKERS)
        mid = f"rival-{rival}-{trigger_ip.replace('.', '-')}"
        if any(m.mission_id == mid for m in game.missions.missions):
            return
        loot = next(
            (p for p in server.files if "/home/" in p or "/opt/" in p),
            f"/home/{server.ssh_user}/notes.txt",
        )
        briefing = (
            f"RIVAL COUNTER [{rival}]: Race you on {server.hostname} ({trigger_ip}) — "
            f"exfil before they patch. Mod: rival-race."
        )
        m = Mission(
            mid, rival, briefing, trigger_ip, loot, 400 + server.security_level * 80,
            rep_reward=45, rival_counter=True, procedural=True,
            modifiers=["rival_race"],
        )
        game.missions.missions.insert(0, m)
        game.meta.rival_race_prog[mid] = 0
        game.mail.send(
            f"{rival}@rival.net",
            f"COUNTER-OP on {trigger_ip}",
            f"I saw your scan on {server.hostname}. Beat me to the loot or eat trace.\n\n— {rival}",
        )

    @staticmethod
    def on_procedural_spawn(game: Game, ip: str) -> None:
        RivalCounterManager.maybe_spawn(game, ip)

    @staticmethod
    def on_contract_complete(game: Game, mission: Any) -> None:
        if getattr(mission, "procedural", False):
            RivalCounterManager.maybe_spawn(game, mission.target_ip)


class ToolPuzzleManager:
    """Checks for tool-gated puzzles — wired from variety_content.PuzzleManager."""

    @staticmethod
    def can_crack_extra(game: Game, server: Server, pid: str) -> str | None:
        if pid == "phish_gate":
            if server.ip not in game.meta.phished_ips:
                return f"Run phish {server.ip} before cracking this host."
        if pid == "tunnel_jump":
            from depth_systems import ToolManager
            rip, rport = ToolManager.resolve_connect(game, "localhost", game.player.connected_port or 0)
            if rip != server.ip or game.player.connected_port is None:
                return f"SSH only via tunnel: tunnel 8022 {server.ip} 22 then connect localhost 8022."
        return None

    @staticmethod
    def mission_extra_checks(game: Game, server: Server | None, mission: Any) -> bool:
        if not server:
            return True
        pid = getattr(server, "puzzle_id", "")
        if pid == "plant_backdoor" and getattr(mission, "require_log_wipe", True):
            if server.ip not in game.meta.backdoors:
                return False
        if pid == "forge_cover" and getattr(mission, "require_log_wipe", True):
            if server.ip not in game.meta.forged_servers:
                from faction_consumables import ConsumableManager
                if not ConsumableManager.logs_clean_enough(game):
                    return False
        return True

    @staticmethod
    def apply_tunnel_puzzle(server: Server) -> None:
        from main import NetworkService
        server.services = [svc for svc in server.services if svc.port != 22]
        if not server.service_on_port(8022):
            server.services.append(NetworkService(8022, "ssh", "OpenSSH_8.9p1 tunneled"))


class ExtendedHostManager:
    @staticmethod
    def deploy(game: Game, reputation: int, chaos: bool) -> None:
        from progression import build_company_server
        from variety_content import PuzzleManager

        for spec in EXTENDED_COMPANY_HOSTS:
            if spec["ip"] in game.network.servers:
                continue
            if spec.get("chaos_only") and not chaos:
                continue
            if reputation < spec.get("min_rep", 0):
                continue
            s = build_company_server(spec)
            pid = spec.get("puzzle_id", "")
            if pid:
                s.puzzle_id = pid
                PuzzleManager.apply_to_server(game, s, pid)
                if pid == "tunnel_jump":
                    ToolPuzzleManager.apply_tunnel_puzzle(s)
                if pid == "honeypot_decoy":
                    PuzzleManager.apply_to_server(game, s, pid)
            game.network.servers[spec["ip"]] = s

    @staticmethod
    def apply_rank_routes(game: Game) -> None:
        from main import Route
        for min_rank, cidr, gw in EXTENDED_ROUTES:
            if game.player.rank_index < min_rank:
                continue
            if not any(r.destination == cidr for r in game.player.routes):
                game.player.routes.append(Route(cidr, gw))
