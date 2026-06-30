#!/usr/bin/env python3
"""Gameplay variety: per-host puzzles, new mission types, procedural hosts."""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from main import Game, Mission, Server

# ---------------------------------------------------------------------------
# Per-host puzzle definitions (applied to company + procedural hosts)
# ---------------------------------------------------------------------------

HOST_PUZZLES: dict[str, dict[str, Any]] = {
    "staggered_probe": {
        "name": "IDS fingerprint",
        "hint": "Probe twice before brute-force — IDS needs a baseline scan.",
        "probes_required": 2,
    },
    "http_intel": {
        "name": "HTTP intel leak",
        "hint": "Public web folder leaks creds. curl http://IP/path before SSH crack.",
        "web_path": "/security_notice.txt",
        "web_body": (
            "IT NOTICE: SSH password rotation deferred.\n"
            "Temporary access token for audits: {password}\n"
        ),
        "flag": "http_intel_read",
    },
    "spearphish_read": {
        "name": "Spearphish intel",
        "hint": "Read the helpdesk ticket on the host before cracking — social engineering.",
        "file": "/home/{user}/helpdesk_ticket.txt",
        "file_body": (
            "Ticket #4421 — CEO password reset approved.\n"
            "Temporary passphrase for vault sync: {password}\n"
        ),
        "flag": "spearphish_read",
    },
    "port_hop": {
        "name": "Port hop",
        "hint": "HTTP banner lists alternate SSH port. curl http://IP/ then connect to port 2222.",
        "web_path": "/banner.txt",
        "web_body": "Legacy admin SSH moved to port 2222 during migration.\n",
        "alt_ssh_port": 2222,
        "flag": "port_hop_seen",
    },
    "honeypot_decoy": {
        "name": "Honeypot decoy",
        "hint": "Decoy file in /tmp is a trap. Exfil the real payload in /opt/secure/.",
        "decoy": "/tmp/decoy_secrets.txt",
        "decoy_body": "HONEYPOT — downloading this triggers IDS.\n",
        "real_file": "/opt/secure/{company_slug}_payload.bin",
        "real_body": "AUTHENTIC_PAYLOAD\n",
    },
    "dual_account": {
        "name": "Dual account pivot",
        "hint": "Low-priv user first. Read /home/{user}/jump_creds.txt for admin password.",
        "jump_file": "/home/{user}/jump_creds.txt",
        "jump_body": "admin account password (rotate weekly): {admin_password}\n",
        "admin_user": "admin",
        "admin_password": "admin_{rand}",
        "flag": "dual_account_ready",
    },
}

from longevity_content import TOOL_PUZZLES, EXTENDED_PUZZLE_MAP  # noqa: E402

HOST_PUZZLES.update(TOOL_PUZZLES)

# Fixed puzzle assignments for canonical company hosts
COMPANY_PUZZLE_MAP: dict[str, str] = {
    "192.168.1.10": "staggered_probe",
    "192.168.1.30": "http_intel",
    "10.0.0.88": "spearphish_read",
    "192.168.1.25": "honeypot_decoy",
    "172.16.0.20": "port_hop",
    "10.0.0.42": "dual_account",
}
COMPANY_PUZZLE_MAP.update(EXTENDED_PUZZLE_MAP)

# ---------------------------------------------------------------------------
# Procedural host generation — non-reskin paths and identities
# ---------------------------------------------------------------------------

PROC_COMPANIES = [
    "Axiom Logistics", "BrightMatter Health", "CinderWorks Media", "Driftline Shipping",
    "EmberGrid Power", "Frostbyte Retail", "Garrison Mutual", "Halcyon Aerospace",
]

PROC_HOST_PREFIX = [
    "edge", "bastion", "relay", "archive", "ledger", "beacon", "cache", "shard",
    "vault", "relay", "mesh", "node",
]

PROC_FILE_TEMPLATES: list[tuple[str, str, str]] = [
    ("/opt/exports/{slug}_manifest_{n}.json", "manifest", '{{"batch": {n}, "sector": "{sector}"}}\n'),
    ("/var/backups/{slug}/snapshot_{n}.tar.meta", "backup_meta", "snapshot_id={n}\nencrypted=1\n"),
    ("/srv/ingest/{slug}_stream_{n}.log", "stream_log", "ingest_ok seq={n}\n"),
    ("/data/lake/{sector}/{slug}_{n}.parquet.meta", "data_lake", "rows={n}\nclassification=internal\n"),
    ("/etc/secrets/{slug}_token_{n}.env", "env_token", "API_TOKEN=sk-{n}-{slug}\n"),
    ("/home/{user}/drafts/{slug}_memo_{n}.md", "memo", "# Internal memo {n}\n"),
    ("/root/audit/{slug}_findings_{n}.pdf.meta", "audit", "finding_id=F-{n}\nseverity=high\n"),
]

PROC_WEB_TEMPLATES: list[tuple[str, str]] = [
    ("/robots.txt", "User-agent: *\nDisallow: /internal/\n"),
    ("/internal/status.html", "<html><body>MAINTENANCE WINDOW ACTIVE</body></html>\n"),
    ("/.well-known/security.txt", "Contact: security@{slug}.corp\n"),
]

PROC_SECTORS = ["finance", "health", "media", "logistics", "energy", "defense"]


@dataclass
class VarietyState:
    puzzle_progress: dict[str, dict[str, Any]] = field(default_factory=dict)
    pivot_step: dict[str, int] = field(default_factory=dict)
    social_flags: set[str] = field(default_factory=set)
    procedural_counter: int = 0
    procedural_ips: list[str] = field(default_factory=list)
    hosts_puzzled: set[str] = field(default_factory=set)
    social_completions: int = 0
    pivot_completions: int = 0
    puzzle_completions: int = 0


class PuzzleManager:
    @staticmethod
    def _key(server: Server) -> str:
        return server.ip

    @staticmethod
    def progress(game: Game, server: Server) -> dict[str, Any]:
        k = PuzzleManager._key(server)
        if k not in game.variety.puzzle_progress:
            game.variety.puzzle_progress[k] = {"probes": 0, "flags": set()}
        prog = game.variety.puzzle_progress[k]
        if isinstance(prog.get("flags"), list):
            prog["flags"] = set(prog["flags"])
        return prog

    @staticmethod
    def apply_to_server(game: Game, server: Server, puzzle_id: str | None = None) -> None:
        from main import VirtualFile

        pid = puzzle_id or getattr(server, "puzzle_id", "") or COMPANY_PUZZLE_MAP.get(server.ip, "")
        if not pid or pid not in HOST_PUZZLES:
            return
        if server.ip in game.variety.hosts_puzzled:
            return
        server.puzzle_id = pid
        game.variety.hosts_puzzled.add(server.ip)
        spec = HOST_PUZZLES[pid]
        user = server.ssh_user
        pw = server.ssh_password

        if pid == "http_intel":
            path = spec["web_path"]
            body = spec["web_body"].format(password=pw)
            if not hasattr(server, "web_files"):
                server.web_files = {}
            server.web_files[path] = body
        elif pid == "spearphish_read":
            path = spec["file"].format(user=user)
            body = spec["file_body"].format(password=pw)
            server.files[path] = VirtualFile(path, body, owner=user)
        elif pid == "port_hop":
            if not hasattr(server, "web_files"):
                server.web_files = {}
            server.web_files[spec["web_path"]] = spec["web_body"]
            alt = spec["alt_ssh_port"]
            from main import NetworkService
            if not server.service_on_port(alt):
                server.services.append(NetworkService(alt, "ssh", "OpenSSH_8.9p1 legacy"))
        elif pid == "honeypot_decoy":
            slug = server.hostname.replace("-", "_")
            decoy = spec["decoy"]
            server.files[decoy] = VirtualFile(decoy, spec["decoy_body"])
            real = spec["real_file"].format(company_slug=slug)
            server.files[real] = VirtualFile(
                real, spec["real_body"].format(n=random.randint(10, 99)),
            )
            server.honeypot_real_file = real  # type: ignore[attr-defined]
        elif pid == "dual_account":
            path = spec["jump_file"].format(user=user)
            admin_pw = spec["admin_password"].replace("{rand}", str(random.randint(100, 999)))
            server.files[path] = VirtualFile(path, spec["jump_body"].format(admin_password=admin_pw), owner=user)
            server.admin_ssh_user = spec["admin_user"]  # type: ignore[attr-defined]
            server.admin_ssh_password = admin_pw  # type: ignore[attr-defined]
        elif pid == "tunnel_jump":
            from longevity_content import ToolPuzzleManager
            ToolPuzzleManager.apply_tunnel_puzzle(server)

    @staticmethod
    def on_probe(game: Game, server: Server) -> None:
        if not getattr(server, "puzzle_id", ""):
            return
        if server.puzzle_id == "staggered_probe":
            prog = PuzzleManager.progress(game, server)
            prog["probes"] = prog.get("probes", 0) + 1

    @staticmethod
    def on_curl(game: Game, server: Server, path: str, body: str) -> None:
        pid = getattr(server, "puzzle_id", "")
        if not pid:
            return
        prog = PuzzleManager.progress(game, server)
        flags = prog.setdefault("flags", set())
        if pid in ("http_intel", "port_hop"):
            spec = HOST_PUZZLES[pid]
            if path.rstrip("/") == spec["web_path"].rstrip("/"):
                flags.add(spec["flag"])
                game.variety.social_flags.add(f"curl_{server.ip}_{spec['flag']}")
                from main import teach
                teach(HOST_PUZZLES[pid]["hint"])

    @staticmethod
    def on_cat(game: Game, server: Server, path: str) -> None:
        pid = getattr(server, "puzzle_id", "")
        if pid == "spearphish_read":
            spec = HOST_PUZZLES[pid]
            expected = spec["file"].format(user=server.ssh_user)
            if path == expected:
                PuzzleManager.progress(game, server)["flags"].add(spec["flag"])
                game.variety.social_flags.add(f"spear_{server.ip}")
        if pid == "dual_account":
            spec = HOST_PUZZLES[pid]
            expected = spec["jump_file"].format(user=server.ssh_user)
            if path == expected:
                PuzzleManager.progress(game, server)["flags"].add(spec["flag"])

    @staticmethod
    def can_crack(game: Game, server: Server) -> str | None:
        pid = getattr(server, "puzzle_id", "")
        if not pid:
            return None
        prog = PuzzleManager.progress(game, server)
        flags = prog.get("flags", set())

        if pid == "staggered_probe":
            need = HOST_PUZZLES[pid]["probes_required"]
            if prog.get("probes", 0) < need:
                return f"IDS needs {need} probes before brute-force ({prog.get('probes', 0)}/{need})."
        if pid == "http_intel" and HOST_PUZZLES[pid]["flag"] not in flags:
            return f"curl http://{server.ip}{HOST_PUZZLES[pid]['web_path']} for password intel first."
        if pid == "spearphish_read" and HOST_PUZZLES[pid]["flag"] not in flags:
            fpath = HOST_PUZZLES[pid]["file"].format(user=server.ssh_user)
            return f"Social step: read {fpath} before cracking."
        if pid == "port_hop":
            if game.player.connected_port != HOST_PUZZLES[pid]["alt_ssh_port"]:
                if HOST_PUZZLES[pid]["flag"] not in flags:
                    return f"curl http://{server.ip}{HOST_PUZZLES[pid]['web_path']} then connect port {HOST_PUZZLES[pid]['alt_ssh_port']}."
                return f"Connect to SSH on port {HOST_PUZZLES[pid]['alt_ssh_port']}, not {game.player.connected_port}."
        if pid == "dual_account" and HOST_PUZZLES[pid]["flag"] not in flags:
            return "Read jump_creds.txt on low-priv shell before admin crack."
        from longevity_content import ToolPuzzleManager
        extra = ToolPuzzleManager.can_crack_extra(game, server, pid)
        if extra:
            return extra
        return None

    @staticmethod
    def exfil_target(server: Server, default: str) -> str:
        if getattr(server, "puzzle_id", "") == "honeypot_decoy":
            return getattr(server, "honeypot_real_file", default)
        return default

    @staticmethod
    def puzzle_hint(server: Server) -> str:
        pid = getattr(server, "puzzle_id", "")
        if pid and pid in HOST_PUZZLES:
            return HOST_PUZZLES[pid]["hint"]
        return ""


class ProceduralHostGenerator:
    @staticmethod
    def spawn(game: Game) -> Server | None:
        from main import Route, Server, VirtualFile

        if game.player.phase not in ("career", "endless"):
            return None
        n = game.variety.procedural_counter + 1
        octet2 = 110 + (n % 40)
        host_octet = 10 + (n * 7) % 240
        ip = f"10.{octet2}.{host_octet}"
        if ip in game.network.servers:
            game.variety.procedural_counter = n
            return game.network.servers[ip]

        company = random.choice(PROC_COMPANIES)
        slug = company.split()[0].lower()
        prefix = random.choice(PROC_HOST_PREFIX)
        hostname = f"{prefix}-{slug}-{n % 1000}"
        sector = random.choice(PROC_SECTORS)
        cidr = f"10.{octet2}.0/24"
        gw = "192.168.1.1" if octet2 < 128 else "10.0.0.1"
        if not any(r.destination == cidr for r in game.player.routes):
            game.player.routes.append(Route(cidr, gw))

        sec = 2 + min(4, n // 3)
        password = f"{slug}{random.randint(10, 99)}!"
        user = random.choice(["ops", "svc", "deploy", "analyst"])
        tpl_path, kind, tpl_body = random.choice(PROC_FILE_TEMPLATES)
        rel = tpl_path.format(slug=slug, n=n, sector=sector, user=user)
        body = tpl_body.format(slug=slug, n=n, sector=sector, user=user)

        extra: dict[str, str] = {rel: body}
        privesc = kind in ("audit", "env_token") and random.random() < 0.5
        root_only: dict[str, str] = {}
        if privesc and kind != "audit":
            rpath = f"/root/{slug}_vault_{n}.key"
            root_only[rpath] = f"VAULT_KEY_{n}\n"

        server = Server(
            ip, hostname, sec, subnet=cidr,
            ssh_user=user, ssh_password=password,
            privesc_available=privesc,
            extra_files=extra, root_only_files=root_only,
        )
        server.company = company
        server.story = f"Procedural {sector} segment — unique layout #{n}"
        server.min_rep = max(0, game.player.reputation - 100)
        server.procedural = True  # type: ignore[attr-defined]

        if not hasattr(server, "web_files"):
            server.web_files = {}
        for wpath, wbody in random.sample(PROC_WEB_TEMPLATES, k=min(2, len(PROC_WEB_TEMPLATES))):
            server.web_files[wpath] = wbody.format(slug=slug)

        puzzle = random.choice(list(HOST_PUZZLES.keys()))
        server.puzzle_id = puzzle
        PuzzleManager.apply_to_server(game, server, puzzle)

        from longevity_content import RivalCounterManager
        RivalCounterManager.on_procedural_spawn(game, ip)

        from llm_content import LLMContentManager
        LLMContentManager.enrich_host_story(game, server)

        game.network.servers[ip] = server
        game.variety.procedural_counter = n
        game.variety.procedural_ips.append(ip)
        game.player.discovered_ips.add(ip)
        return server


class VarietyMissionGenerator:
    @staticmethod
    def generate(game: Game) -> Mission | None:
        from main import Mission, VirtualFile
        from progression import BROKERS

        if game.player.phase != "career":
            return None
        if sum(1 for m in game.missions.missions if not m.completed) >= 6:
            return None

        use_proc = random.random() < 0.45
        server = ProceduralHostGenerator.spawn(game) if use_proc else None
        if not server:
            candidates = [
                s for s in game.network.servers.values()
                if not getattr(s, "chaos_only", False)
                and not getattr(s, "endless_only", False)
                and game.player.reputation >= getattr(s, "min_rep", 0)
                and game.player.has_route_to(s.ip)
            ]
            if not candidates:
                return None
            server = random.choice(candidates)
            PuzzleManager.apply_to_server(game, server)

        archetypes = ["exfil", "ghost", "root_heist", "clean_sweep", "social", "timing", "pivot"]
        weights = [2, 2, 2, 1, 2, 2, 2]
        mtype = random.choices(archetypes, weights=weights)[0]
        company = getattr(server, "company", "Unknown")
        mid = f"proc-{game.variety.procedural_counter}-{random.randint(1000, 9999)}"

        if mtype == "social":
            return VarietyMissionGenerator._finish(
                game, VarietyMissionGenerator._social(game, server, company, mid, random.choice(BROKERS)))
        if mtype == "timing":
            return VarietyMissionGenerator._finish(
                game, VarietyMissionGenerator._timing(game, server, company, mid, random.choice(BROKERS)))
        if mtype == "pivot":
            return VarietyMissionGenerator._finish(
                game, VarietyMissionGenerator._pivot(game, server, company, mid, random.choice(BROKERS)))
        return VarietyMissionGenerator._finish(
            game,
            VarietyMissionGenerator._classic(game, server, company, mid, random.choice(BROKERS), mtype),
        )

    @staticmethod
    def _finish(game: Game, mission: "Mission") -> "Mission":
        from depth_systems import ModifierManager
        ModifierManager.apply_to_mission(mission, game)
        server = game.network.get_server(mission.target_ip)
        from llm_content import LLMContentManager
        LLMContentManager.enrich_briefing(game, mission, server)
        return mission

    @staticmethod
    def _pick_loot_file(server: Server) -> str:
        candidates = [
            p for p in server.files
            if "/home/" in p or "/opt/" in p or "/data/" in p or "/srv/" in p
        ]
        candidates = [p for p in candidates if "log" not in p and p not in ("/etc/hostname", "/etc/passwd")]
        if candidates:
            return PuzzleManager.exfil_target(server, random.choice(candidates))
        return PuzzleManager.exfil_target(server, f"/home/{server.ssh_user}/notes.txt")

    @staticmethod
    def _classic(game: Game, server: Server, company: str, mid: str, broker: str, mtype: str) -> "Mission":
        from main import Mission
        rel = VarietyMissionGenerator._pick_loot_file(server)
        reward = 320 + server.security_level * 100 + random.randint(0, 180)
        rep = 35 + server.security_level * 12
        hint = PuzzleManager.puzzle_hint(server)
        extra = f" Puzzle: {hint}" if hint else ""

        if mtype == "ghost":
            briefing = f"[{company}] Ghost {server.hostname} ({server.ip}) — zero traces.{extra}"
            rel = ""
            reward += 200
        elif mtype == "root_heist":
            root_files = [p for p in server.files if p.startswith("/root/")]
            rel = root_files[0] if root_files else f"/root/secret_{mid}.txt"
            briefing = f"[{company}] Root heist {server.hostname} — privesc, exfil, wipe.{extra}"
            reward += 300
            rep += 30
        elif mtype == "clean_sweep":
            fname = rel.rsplit("/", 1)[-1]
            briefing = f"[{company}] Clean sweep {server.hostname} — wipe ALL logs, exfil {fname}.{extra}"
            reward += 150
        else:
            fname = rel.rsplit("/", 1)[-1]
            briefing = f"[{company}] Exfil {fname} from {server.hostname} ({server.ip}), wipe logs.{extra}"
        return Mission(
            mid, broker, briefing, server.ip, rel, reward, rep_reward=rep,
            procedural=True, mission_type=mtype,
            require_privesc=mtype == "root_heist",
            puzzle_id=getattr(server, "puzzle_id", ""),
        )

    @staticmethod
    def _social(game: Game, server: Server, company: str, mid: str, broker: str) -> "Mission":
        from main import Mission
        PuzzleManager.apply_to_server(game, server, server.puzzle_id or "spearphish_read")
        spec = HOST_PUZZLES.get(server.puzzle_id, HOST_PUZZLES["spearphish_read"])
        if server.puzzle_id == "http_intel":
            social_file = spec["web_path"]
            briefing = (
                f"[{company}] SOCIAL: curl http://{server.ip}{social_file}, "
                f"then crack {server.hostname} and exfil payload — no traces."
            )
        else:
            social_file = spec.get("file", "/home/{user}/helpdesk_ticket.txt").format(user=server.ssh_user)
            briefing = (
                f"[{company}] SOCIAL: read {social_file} on {server.hostname}, "
                f"crack with intel, exfil real payload, wipe logs."
            )
        rel = VarietyMissionGenerator._pick_loot_file(server)
        reward = 450 + server.security_level * 80
        return Mission(
            mid, broker, briefing, server.ip, rel, reward, rep_reward=55,
            procedural=True, mission_type="social",
            social_file=social_file, puzzle_id=getattr(server, "puzzle_id", ""),
        )

    @staticmethod
    def _timing(game: Game, server: Server, company: str, mid: str, broker: str) -> "Mission":
        from main import Mission
        limit = random.randint(12, 22)
        rel = VarietyMissionGenerator._pick_loot_file(server)
        fname = rel.rsplit("/", 1)[-1]
        briefing = (
            f"[{company}] TIMING: Maintenance window — complete within {limit} commands. "
            f"Crack {server.hostname}, exfil {fname}, wipe logs."
        )
        reward = 500 + server.security_level * 90
        return Mission(
            mid, broker, briefing, server.ip, rel, reward, rep_reward=60,
            procedural=True, mission_type="timing",
            timing_limit_ticks=limit, timing_start_tick=game.player.ticks,
            puzzle_id=getattr(server, "puzzle_id", ""),
        )

    @staticmethod
    def _pivot(game: Game, server: Server, company: str, mid: str, broker: str) -> "Mission":
        from main import Mission
        jump = ProceduralHostGenerator.spawn(game)
        if not jump or jump.ip == server.ip:
            jump_ip = server.ip
            loot_ip = server.ip
            rel = VarietyMissionGenerator._pick_loot_file(server)
        else:
            jump_ip = server.ip
            loot_ip = jump.ip
            rel = VarietyMissionGenerator._pick_loot_file(jump)
        game.variety.pivot_step[mid] = 0
        briefing = (
            f"[{company}] PIVOT: Crack jump box {server.hostname} ({jump_ip}), "
            f"read pivot creds, breach {jump.hostname if jump else 'target'} ({loot_ip}), "
            f"exfil {rel.rsplit('/', 1)[-1]}, wipe both hosts."
        )
        reward = 650 + server.security_level * 100
        return Mission(
            mid, broker, briefing, loot_ip, rel, reward, rep_reward=75,
            procedural=True, mission_type="pivot",
            pivot_host=jump_ip, puzzle_id=getattr(server, "puzzle_id", ""),
        )


class VarietyManager:
    @staticmethod
    def deploy_puzzles(game: Game) -> None:
        for ip, server in game.network.servers.items():
            if ip in COMPANY_PUZZLE_MAP:
                PuzzleManager.apply_to_server(game, server, COMPANY_PUZZLE_MAP[ip])

    @staticmethod
    def on_pivot_crack(game: Game, ip: str) -> None:
        for m in game.missions.missions:
            if m.completed or m.mission_type != "pivot":
                continue
            step = game.variety.pivot_step.get(m.mission_id, 0)
            if step == 0 and ip == m.pivot_host:
                from main import VirtualFile, success

                jump = game.network.get_server(ip)
                if not jump:
                    return
                cred_path = f"/home/{jump.ssh_user}/pivot_bridge.txt"
                if cred_path not in jump.files:
                    target = game.network.get_server(m.target_ip)
                    hint_pw = target.ssh_password if target else "pivot!"
                    jump.files[cred_path] = VirtualFile(
                        cred_path,
                        f"pivot to {m.target_ip}\nssh_password={hint_pw}\n",
                        owner=jump.ssh_user,
                    )
                game.variety.pivot_step[m.mission_id] = 1
                success(f"Pivot step 1: jump box {ip} owned — read {cred_path}")
            elif step == 1 and ip == m.target_ip:
                game.variety.pivot_step[m.mission_id] = 2

    @staticmethod
    def timing_expired(game: Game, mission: Mission) -> bool:
        if mission.mission_type != "timing" or not mission.timing_limit_ticks:
            return False
        elapsed = game.player.ticks - mission.timing_start_tick
        return elapsed > mission.timing_limit_ticks

    @staticmethod
    def fetch_http(game: Game, ip: str, path: str) -> str | None:
        server = game.network.get_server(ip)
        if not server:
            return None
        web = getattr(server, "web_files", {}) or {}
        norm = path if path.startswith("/") else f"/{path}"
        for wpath, body in web.items():
            if wpath.rstrip("/") == norm.rstrip("/"):
                return body
        return None
