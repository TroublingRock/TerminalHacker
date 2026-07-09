"""
Structured LLM generation — procedural missions, LFG contracts, weekly world events.

JSON output validated against real hosts, files, puzzles, and modifiers.
Budget: 3 struct calls/session vs 12 flavor calls (llm_content.py).
"""

from __future__ import annotations

import hashlib
import json
import random
import re
from datetime import date
from typing import TYPE_CHECKING, Any

from depth_systems import MODIFIERS
from variety_content import HOST_PUZZLES, PuzzleManager, VarietyMissionGenerator

if TYPE_CHECKING:
    from main import Game, Mission, Server

VALID_MODIFIERS = frozenset(MODIFIERS.keys())
VALID_MISSION_TYPES = frozenset(
    {"exfil", "ghost", "root_heist", "clean_sweep", "social", "timing", "pivot", "lfg"}
)
VALID_WORLD_KEYS = frozenset(
    {
        "title",
        "briefing",
        "heat_delta",
        "rival_aggression_delta",
        "bounty_multiplier",
        "trace_bonus",
    }
)


def _week_key() -> str:
    d = date.today()
    return f"{d.isocalendar().year}-W{d.isocalendar().week:02d}"


def _struct_cache_key(kind: str, *parts: str) -> str:
    raw = "|".join([kind] + list(parts))
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


def _parse_json_object(text: str) -> dict[str, Any] | None:
    text = (text or "").strip()
    if not text:
        return None
    try:
        obj = json.loads(text)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            obj = json.loads(m.group(0))
            return obj if isinstance(obj, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def validate_mission_spec(
    spec: dict[str, Any],
    server: Server,
    mission_type: str,
) -> tuple[bool, str]:
    if not isinstance(spec, dict):
        return False, "not a dict"

    mt = str(spec.get("mission_type", mission_type)).lower()
    if mt not in VALID_MISSION_TYPES:
        return False, f"unknown mission_type: {mt}"

    tip = str(spec.get("target_ip", "")).strip()
    if tip and tip != server.ip:
        return False, f"target_ip {tip} != host {server.ip}"

    tf = str(spec.get("target_file", "")).strip()
    if mt == "ghost":
        if tf:
            return False, "ghost must not have target_file"
    elif tf and tf not in server.files:
        return False, f"target_file missing on host: {tf}"

    pp = str(spec.get("puzzle_primary", "")).strip()
    ps = str(spec.get("puzzle_secondary", "")).strip()
    if pp not in HOST_PUZZLES:
        return False, f"unknown puzzle_primary: {pp}"
    if ps not in HOST_PUZZLES:
        return False, f"unknown puzzle_secondary: {ps}"
    if pp == ps:
        return False, "puzzle_primary and puzzle_secondary must differ"

    mods = spec.get("modifiers", [])
    if not isinstance(mods, list):
        return False, "modifiers must be a list"
    for mod in mods:
        if str(mod) not in VALID_MODIFIERS:
            return False, f"unknown modifier: {mod}"

    if bool(spec.get("require_privesc")) and not server.privesc_available:
        return False, "require_privesc on host without privesc"

    return True, "ok"


def validate_world_event(spec: dict[str, Any]) -> tuple[bool, str]:
    if not isinstance(spec, dict):
        return False, "not a dict"
    for k in spec:
        if k not in VALID_WORLD_KEYS:
            return False, f"unknown key: {k}"
    if "title" not in spec or not str(spec["title"]).strip():
        return False, "missing title"
    try:
        hd = int(spec.get("heat_delta", 0))
        if not -30 <= hd <= 30:
            return False, "heat_delta out of range"
    except (TypeError, ValueError):
        return False, "heat_delta invalid"
    try:
        ra = int(spec.get("rival_aggression_delta", 0))
        if not -5 <= ra <= 5:
            return False, "rival_aggression_delta out of range"
    except (TypeError, ValueError):
        return False, "rival_aggression_delta invalid"
    try:
        bm = float(spec.get("bounty_multiplier", 1.0))
        if not 0.5 <= bm <= 2.0:
            return False, "bounty_multiplier out of range"
    except (TypeError, ValueError):
        return False, "bounty_multiplier invalid"
    try:
        tb = int(spec.get("trace_bonus", 0))
        if not -5 <= tb <= 10:
            return False, "trace_bonus out of range"
    except (TypeError, ValueError):
        return False, "trace_bonus invalid"
    return True, "ok"


class LLMStructManager:
    @staticmethod
    def can_struct_call(game: Game) -> bool:
        from llm_content import LLMClient, LLMConfig, LLMContentManager

        cfg = LLMConfig.load()
        if not game.llm.user_enabled or not cfg.enabled:
            return False
        if not LLMClient.available(cfg):
            return False
        LLMContentManager.reset_session_if_new_day(game)
        return game.llm.session_struct_calls < cfg.max_struct_calls_per_session

    @staticmethod
    def _struct_call(
        game: Game,
        cache_key: str,
        system: str,
        user: str,
        temperature: float = 0.55,
    ) -> dict[str, Any] | None:
        from llm_content import LLMContentManager

        st = game.llm
        if cache_key in st.struct_cache:
            cached = st.struct_cache[cache_key]
            if isinstance(cached, dict):
                return cached

        if not LLMStructManager.can_struct_call(game):
            return None

        raw = LLMContentManager.api_call(game, system, user, temperature, json_mode=True)
        if not raw:
            return None

        obj = _parse_json_object(raw)
        if not obj:
            st.last_error = "struct: invalid JSON"
            return None

        st.struct_cache[cache_key] = obj
        st.session_struct_calls += 1
        st.total_struct_calls += 1
        st.last_error = ""
        return obj

    @staticmethod
    def _apply_composite_puzzles(game: Game, server: Server, primary: str, secondary: str) -> None:
        server.puzzle_id = primary
        server.puzzle_secondary = secondary
        server.puzzle_ids = [primary, secondary]
        PuzzleManager.apply_to_server(game, server, primary)
        PuzzleManager.apply_to_server(game, server, secondary)
        game.variety.hosts_puzzled.add(server.ip)

    @staticmethod
    def _build_mission_from_spec(
        game: Game,
        server: Server,
        spec: dict[str, Any],
        mid: str,
        broker: str,
        default_type: str,
        source_tag: str,
    ) -> Mission:
        from main import Mission

        mt = str(spec.get("mission_type", default_type)).lower()
        if mt == "lfg":
            mt = "exfil"
        tf = str(spec.get("target_file", "")).strip()
        pp = str(spec["puzzle_primary"])
        ps = str(spec["puzzle_secondary"])
        mods_out = [str(m) for m in spec.get("modifiers", []) if str(m) in VALID_MODIFIERS][:2]

        LLMStructManager._apply_composite_puzzles(game, server, pp, ps)

        if not tf and mt != "ghost":
            tf = VarietyMissionGenerator._pick_loot_file(server)

        from economy import EconomyManager
        reward, rep = EconomyManager.build_classic_reward(server.security_level, mt)
        if mods_out:
            reward = int(reward * (1.0 + 0.12 * len(mods_out)))
        reward += int(spec.get("payout_bonus", 0))

        briefing = str(spec.get("briefing", "")).strip()
        if not briefing:
            company = getattr(server, "company", "Unknown")
            hint = PuzzleManager.puzzle_hint(server)
            extra = f" Puzzles: {hint}" if hint else ""
            briefing = f"[{company}] {mt} on {server.hostname} ({server.ip}).{extra}"
        if mods_out:
            tags = ", ".join(MODIFIERS[m]["label"] for m in mods_out)
            briefing += f" [MODS: {tags}]"

        mission = Mission(
            mid,
            broker,
            briefing[:500],
            server.ip,
            tf,
            reward,
            rep_reward=rep,
            procedural=True,
            mission_type=mt,
            require_privesc=bool(spec.get("require_privesc")) or mt == "root_heist",
            puzzle_id=pp,
            puzzle_secondary=ps,
            modifiers=mods_out,
        )
        if mt == "timing":
            mission.timing_limit_ticks = random.randint(14, 24)
            mission.timing_start_tick = game.player.ticks
        if "deadline" in mods_out and not mission.timing_limit_ticks:
            mission.timing_limit_ticks = random.randint(14, 24)
            mission.timing_start_tick = game.player.ticks
        if "rival_race" in mods_out:
            from rival_ai import RivalAIManager
            RivalAIManager.assign_race_rival(game, mission)
        mission.llm_source = source_tag  # type: ignore[attr-defined]
        return mission

    @staticmethod
    def try_structured_procedural(
        game: Game,
        server: Server,
        seed: int,
    ) -> Mission | None:
        from progression import BROKERS

        if not LLMStructManager.can_struct_call(game):
            return None

        puzzles = sorted(HOST_PUZZLES.keys())
        mods = sorted(VALID_MODIFIERS)
        files = list(server.files.keys())[:12]
        mtype = random.choice(["exfil", "ghost", "root_heist", "timing", "social"])
        cache_key = _struct_cache_key("proc", server.ip, mtype, str(seed))

        system = (
            "You design Terminal Hacker procedural missions. "
            "Reply with ONLY one JSON object, no markdown. Keys:\n"
            "mission_type (exfil|ghost|root_heist|timing|social),\n"
            "target_ip (must equal host IP),\n"
            "target_file (empty string for ghost; else from file list),\n"
            "puzzle_primary, puzzle_secondary (two DIFFERENT ids from puzzle list),\n"
            "modifiers (array, subset of modifier list, max 2),\n"
            "require_privesc (boolean),\n"
            "briefing (string, 2 sentences max)."
        )
        user = (
            f"Host IP: {server.ip}\n"
            f"Hostname: {server.hostname}\n"
            f"Sector: {getattr(server, 'story', '')[:40]}\n"
            f"Suggested type: {mtype}\n"
            f"Difficulty: {server.security_level}\n"
            f"Files on host: {files}\n"
            f"privesc_available: {server.privesc_available}\n"
            f"Puzzle ids: {puzzles}\n"
            f"Modifiers: {mods}\n"
            f"Seed: {seed}"
        )

        spec = LLMStructManager._struct_call(game, cache_key, system, user)
        if not spec:
            return None

        ok, err = validate_mission_spec(spec, server, mtype)
        if not ok:
            game.llm.last_error = f"mission validation: {err}"
            return None

        mid = f"llm-proc-{seed}-{random.randint(1000, 9999)}"
        return LLMStructManager._build_mission_from_spec(
            game, server, spec, mid, random.choice(BROKERS), mtype, "llm_struct",
        )

    @staticmethod
    def spawn_lfg_contract(game: Game, title: str, body: str) -> Mission | None:
        from progression import BROKERS
        from variety_content import ProceduralHostGenerator

        if not LLMStructManager.can_struct_call(game):
            return None

        server = ProceduralHostGenerator.spawn(game)
        if not server:
            return None

        puzzles = sorted(HOST_PUZZLES.keys())
        mods = sorted(VALID_MODIFIERS)
        cache_key = _struct_cache_key("lfg", title[:40], body[:80], server.ip)

        system = (
            "Player posted LFG on a hacker job board. Design ONE contract JSON. "
            "Match their intent when possible. ONLY JSON, keys:\n"
            "mission_type (exfil|ghost|root_heist|timing|social),\n"
            "target_ip (must equal host IP),\n"
            "target_file (empty for ghost),\n"
            "puzzle_primary, puzzle_secondary (different, from list),\n"
            "modifiers (max 2),\n"
            "require_privesc (boolean),\n"
            "briefing (2 sentences),\n"
            "payout_bonus (0-500 int, optional)."
        )
        user = (
            f"Player title: {title}\n"
            f"Player body: {body}\n"
            f"Host IP: {server.ip}\n"
            f"Hostname: {server.hostname}\n"
            f"Files: {list(server.files.keys())[:12]}\n"
            f"privesc: {server.privesc_available}\n"
            f"Puzzles: {puzzles}\n"
            f"Modifiers: {mods}"
        )

        spec = LLMStructManager._struct_call(game, cache_key, system, user, temperature=0.65)
        if not spec:
            return None

        ok, err = validate_mission_spec(spec, server, "lfg")
        if not ok:
            game.llm.last_error = f"LFG validation: {err}"
            return None

        mid = f"lfg-{abs(hash(title + body)) % 100000}"
        return LLMStructManager._build_mission_from_spec(
            game, server, spec, mid, random.choice(BROKERS), "exfil", "lfg",
        )

    @staticmethod
    def refresh_world_event(game: Game, force: bool = False) -> dict[str, Any] | None:
        wk = _week_key()
        st = game.llm
        if not force and st.world_event_week == wk and st.world_event:
            return st.world_event

        if not LLMStructManager.can_struct_call(game) and not st.world_event:
            return st.world_event or None

        cache_key = _struct_cache_key("world", wk)
        if cache_key in st.struct_cache and not force:
            ev = st.struct_cache[cache_key]
            if isinstance(ev, dict):
                st.world_event = ev
                st.world_event_week = wk
                return ev

        system = (
            "Weekly world event for hacker MMO Terminal Hacker. "
            "ONLY JSON keys: title, briefing (2-3 sentences), "
            "heat_delta (-20 to 20 int), rival_aggression_delta (-3 to 3 int), "
            "bounty_multiplier (0.8 to 1.5 float), trace_bonus (-3 to 5 int)."
        )
        user = f"Week: {wk}. Invent one coherent global event (corp crackdown, data leak, rival war, etc.)."

        spec = LLMStructManager._struct_call(game, cache_key, system, user, temperature=0.7)
        if not spec:
            return st.world_event or None

        ok, err = validate_world_event(spec)
        if not ok:
            game.llm.last_error = f"world event validation: {err}"
            return st.world_event or None

        st.world_event = spec
        st.world_event_week = wk
        return spec

    @staticmethod
    def apply_world_event_login(game: Game) -> list[str]:
        ev = LLMStructManager.refresh_world_event(game)
        lines: list[str] = []
        if not ev:
            return lines
        wk = _week_key()
        applied = game.meta.world_event_applied_week
        if applied == wk:
            return lines
        game.meta.world_event_applied_week = wk

        hd = int(ev.get("heat_delta", 0))
        if hd:
            from chaos_system import CareerPressureManager
            if CareerPressureManager.rookie_grace(game) and hd > 0:
                hd = min(hd, 2)
            if game.meta.subnet_heat:
                hottest = max(game.meta.subnet_heat, key=game.meta.subnet_heat.get)
                game.meta.subnet_heat[hottest] = max(0, min(10, game.meta.subnet_heat[hottest] + hd))
            else:
                game.meta.subnet_heat["192.168.1.0/24"] = max(0, min(10, hd))

        ra = int(ev.get("rival_aggression_delta", 0))
        if ra:
            game.retention.rival_aggression = max(0, min(10, game.retention.rival_aggression + ra))

        lines.append(f"[WORLD EVENT] {ev.get('title', 'Unknown')}")
        if ev.get("briefing"):
            lines.append(str(ev["briefing"])[:300])
        bm = float(ev.get("bounty_multiplier", 1.0))
        if bm != 1.0:
            lines.append(f"  Bounty multiplier this week: {bm:.2f}x")
        tb = int(ev.get("trace_bonus", 0))
        if tb:
            lines.append(f"  Trace pressure: {'+' if tb > 0 else ''}{tb}")
        return lines

    @staticmethod
    def world_event_bounty_mult(game: Game) -> float:
        ev = game.llm.world_event or {}
        try:
            return float(ev.get("bounty_multiplier", 1.0))
        except (TypeError, ValueError):
            return 1.0

    @staticmethod
    def world_event_trace_bonus(game: Game) -> float:
        ev = game.llm.world_event or {}
        try:
            return int(ev.get("trace_bonus", 0)) * 0.02
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def status_lines(game: Game) -> list[str]:
        cfg_lines: list[str] = []
        ev = game.llm.world_event or {}
        if ev:
            cfg_lines.append(f"  World event: {ev.get('title', '?')} (week {game.llm.world_event_week})")
        cfg_lines.append(
            f"  Struct calls: {game.llm.session_struct_calls} this session / "
            f"{game.llm.total_struct_calls} total (max {game.llm.session_struct_calls} + flavor 12)"
        )
        cfg_lines.append(f"  Struct cache: {len(game.llm.struct_cache)} JSON blobs")
        return cfg_lines

    @staticmethod
    def test_struct(game: Game) -> bool:
        from main import error, success

        spec = LLMStructManager._struct_call(
            game,
            _struct_cache_key("test", "ping"),
            "Reply ONLY JSON: {\"ok\": true, \"message\": \"struct layer alive\"}",
            "ping",
            temperature=0.2,
        )
        if spec and spec.get("ok"):
            success(f"Struct LLM OK: {spec.get('message', 'ok')}")
            return True
        error(f"Struct LLM failed: {game.llm.last_error or 'unknown'}")
        return False
