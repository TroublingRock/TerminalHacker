#!/usr/bin/env python3
"""Optional LLM layer — OpenAI / Groq for dynamic briefings, board posts, rival banter.

Keys are NEVER stored in the repo. Configure via:
  ~/.terminalhacker/llm.json   (copy from llm.json.example)
  or env: OPENAI_API_KEY, GROQ_API_KEY, LLM_PROVIDER=groq|openai
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from main import Game, Mission, Server

CONFIG_PATH = Path.home() / ".terminalhacker" / "llm.json"

PROVIDERS: dict[str, dict[str, str]] = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1/chat/completions",
        "default_model": "llama-3.3-70b-versatile",
        "env_key": "GROQ_API_KEY",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1/chat/completions",
        "default_model": "gpt-4o-mini",
        "env_key": "OPENAI_API_KEY",
    },
}

SYSTEM_PROMPT = (
    "You write in-universe copy for TerminalHacker, a cyberpunk terminal hacking game. "
    "Tone: terse, noir, darknet broker slang. No markdown. No emojis. "
    "Stay under the character limit. Reference only hosts, tools, and mechanics given in context. "
    "Never invent IP addresses not in context. Output plain text only."
)


@dataclass
class LLMState:
    user_enabled: bool = True
    cache: dict[str, str] = field(default_factory=dict)
    struct_cache: dict[str, dict[str, Any]] = field(default_factory=dict)
    session_calls: int = 0
    session_struct_calls: int = 0
    total_calls: int = 0
    total_struct_calls: int = 0
    last_error: str = ""
    world_event: dict[str, Any] = field(default_factory=dict)
    world_event_week: str = ""


@dataclass
class LLMConfig:
    provider: str = "openai"
    api_key: str = ""
    model: str = ""
    enabled: bool = True
    max_calls_per_session: int = 12
    max_struct_calls_per_session: int = 3
    timeout_sec: int = 20

    @staticmethod
    def load() -> LLMConfig:
        data: dict[str, Any] = {}
        if CONFIG_PATH.exists():
            try:
                data = json.loads(CONFIG_PATH.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        provider = (
            os.environ.get("LLM_PROVIDER")
            or data.get("provider")
            or ("openai" if os.environ.get("OPENAI_API_KEY") else "groq")
        ).lower()
        if provider not in PROVIDERS:
            provider = "openai"
        prof = PROVIDERS[provider]
        api_key = (
            data.get("api_key")
            or os.environ.get(prof["env_key"], "")
            or os.environ.get("OPENAI_API_KEY", "")
            or os.environ.get("GROQ_API_KEY", "")
        )
        model = data.get("model") or os.environ.get("LLM_MODEL", prof["default_model"])
        return LLMConfig(
            provider=provider,
            api_key=api_key.strip(),
            model=model,
            enabled=bool(data.get("enabled", True)),
            max_calls_per_session=int(data.get("max_calls_per_session", 12)),
            max_struct_calls_per_session=int(data.get("max_struct_calls_per_session", 3)),
            timeout_sec=int(data.get("timeout_sec", 20)),
        )


class LLMClient:
    @staticmethod
    def available(cfg: LLMConfig | None = None) -> bool:
        c = cfg or LLMConfig.load()
        return bool(c.enabled and c.api_key and c.provider in PROVIDERS)

    @staticmethod
    def chat(
        user_prompt: str,
        *,
        max_tokens: int = 180,
        system: str | None = None,
        temperature: float = 0.85,
        json_mode: bool = False,
    ) -> str:
        cfg = LLMConfig.load()
        if not LLMClient.available(cfg):
            raise RuntimeError("LLM not configured — set OPENAI_API_KEY or GROQ_API_KEY")
        url = PROVIDERS[cfg.provider]["base_url"]
        payload: dict[str, Any] = {
            "model": cfg.model,
            "messages": [
                {"role": "system", "content": system or SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if json_mode and cfg.provider == "openai":
            payload["response_format"] = {"type": "json_object"}
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {cfg.api_key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=cfg.timeout_sec) as resp:
                body = json.loads(resp.read().decode())
            return body["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as exc:
            err = exc.read().decode(errors="replace")[:200]
            raise RuntimeError(f"LLM HTTP {exc.code}: {err}") from exc
        except Exception as exc:
            raise RuntimeError(str(exc)) from exc

    @staticmethod
    def sanitize(text: str, limit: int = 480) -> str:
        text = re.sub(r"\s+", " ", text).strip()
        text = text.replace("```", "").strip('"').strip("'")
        if len(text) > limit:
            text = text[: limit - 3].rstrip() + "..."
        return text


class LLMContentManager:
    @staticmethod
    def is_available() -> bool:
        return LLMClient.available()

    @staticmethod
    def reset_session_if_new_day(game: Game) -> None:
        from retention import RetentionManager

        today = RetentionManager.today()
        if getattr(game.llm, "_session_day", "") != today:
            game.llm.session_calls = 0
            game.llm.session_struct_calls = 0
            game.llm._session_day = today  # type: ignore[attr-defined]

    @staticmethod
    def can_call(game: Game) -> bool:
        cfg = LLMConfig.load()
        if not game.llm.user_enabled or not cfg.enabled:
            return False
        if not LLMClient.available(cfg):
            return False
        LLMContentManager.reset_session_if_new_day(game)
        return game.llm.session_calls < cfg.max_calls_per_session

    @staticmethod
    def api_call(
        game: Game,
        system: str,
        user: str,
        temperature: float = 0.7,
        *,
        json_mode: bool = False,
        max_tokens: int = 400,
    ) -> str | None:
        if not LLMClient.available():
            return None
        try:
            return LLMClient.chat(
                user,
                system=system,
                temperature=temperature,
                json_mode=json_mode,
                max_tokens=max_tokens,
            )
        except Exception as exc:
            game.llm.last_error = str(exc)[:200]
            return None

    @staticmethod
    def _cache_key(kind: str, seed: str) -> str:
        return f"{kind}:{seed}"

    @staticmethod
    def generate(game: Game, kind: str, seed: str, prompt: str, *, limit: int = 480) -> str | None:
        key = LLMContentManager._cache_key(kind, seed)
        if key in game.llm.cache:
            return game.llm.cache[key]
        if not LLMContentManager.can_call(game):
            return None
        try:
            raw = LLMClient.chat(prompt, max_tokens=min(220, limit // 2))
            text = LLMClient.sanitize(raw, limit)
            if len(text) < 20:
                return None
            game.llm.cache[key] = text
            game.llm.session_calls += 1
            game.llm.total_calls += 1
            game.llm.last_error = ""
            return text
        except Exception as exc:
            game.llm.last_error = str(exc)[:200]
            return None

    @staticmethod
    def enrich_briefing(game: Game, mission: Mission, server: Server | None = None) -> None:
        if not LLMContentManager.can_call(game):
            return
        host = server or game.network.get_server(mission.target_ip)
        puzzle = getattr(host, "puzzle_id", "") if host else ""
        mods = ",".join(getattr(mission, "modifiers", []))
        seed = f"{mission.mission_id}:{mission.briefing[:40]}"
        prompt = (
            f"Rewrite this contract briefing (1-2 sentences, keep facts):\n"
            f"ORIGINAL: {mission.briefing}\n"
            f"Broker: {mission.broker} | Type: {mission.mission_type} | "
            f"Target: {mission.target_ip} | Loot: {mission.target_file or 'ghost'} | "
            f"Puzzle: {puzzle or 'none'} | Mods: {mods or 'none'}\n"
            f"Add one concrete tradecraft detail (VPN, phish, tunnel, plant, forge, or log wipe)."
        )
        enriched = LLMContentManager.generate(game, "briefing", seed, prompt, limit=420)
        if enriched:
            mission.briefing = enriched

    @staticmethod
    def enrich_host_story(game: Game, server: Server) -> None:
        if not LLMContentManager.can_call(game):
            return
        seed = f"host:{server.ip}"
        prompt = (
            f"One sentence host lore for a hackable server.\n"
            f"Company: {getattr(server, 'company', 'Unknown')} | "
            f"Hostname: {server.hostname} | IP: {server.ip} | "
            f"Puzzle: {getattr(server, 'puzzle_id', 'none')} | "
            f"Sector flavor: {getattr(server, 'story', '')[:80]}"
        )
        lore = LLMContentManager.generate(game, "host_lore", seed, prompt, limit=160)
        if lore:
            server.story = lore

    @staticmethod
    def enrich_board_reply(game: Game, broker: str, mission_briefing: str) -> str | None:
        seed = f"board:{broker}:{mission_briefing[:30]}"
        prompt = (
            f"Darknet forum reply from {broker} to an operator who just posted a contract flex.\n"
            f"Contract: {mission_briefing[:200]}\n"
            f"2-3 sentences. Cocky or approving. Mention one tradecraft tip."
        )
        return LLMContentManager.generate(game, "board", seed, prompt, limit=320)

    @staticmethod
    def enrich_rival_mail(game: Game, rival: str, context: str) -> str | None:
        seed = f"rival:{rival}:{context[:30]}"
        prompt = (
            f"Rival hacker {rival} sends a threatening email to the player.\n"
            f"Context: {context[:220]}\n"
            f"3-4 short lines. Mention subnet heat or a specific IP from context."
        )
        return LLMContentManager.generate(game, "rival_mail", seed, prompt, limit=380)

    @staticmethod
    def enrich_weekly_flavor(game: Game, title: str, template_body: str) -> str | None:
        seed = f"weekly:{title}"
        prompt = (
            f"Weekly intel mail for operator.\nTitle: {title}\n"
            f"Template: {template_body[:300]}\n"
            f"Expand to 4-5 lines with one new rumor about corps, rivals, or brokers."
        )
        return LLMContentManager.generate(game, "weekly", seed, prompt, limit=450)

    @staticmethod
    def maybe_rival_taunt(game: Game) -> None:
        if game.player.phase not in ("career", "endless"):
            return
        if not LLMContentManager.can_call(game):
            return
        if game.retention.rival_aggression < 2:
            return
        rival = game.retention.last_rival or "acid_k"
        hottest = max(game.meta.subnet_heat.items(), key=lambda x: x[1], default=("", 0))
        context = f"Heat on {hottest[0]} at {hottest[1]}/10. Player rep {game.player.reputation}."
        body = LLMContentManager.enrich_rival_mail(game, rival, context)
        if body:
            game.mail.send(f"{rival}@rival.net", "RE: your subnet noise", body)

    @staticmethod
    def status_lines(game: Game) -> list[str]:
        cfg = LLMConfig.load()
        lines = [
            "  LLM dynamic content (OpenAI / Groq):",
            f"  Config file: {CONFIG_PATH}",
            f"  Provider:    {cfg.provider} ({cfg.model})" if cfg.api_key else "  Provider:    not configured",
            f"  API key:     {'set' if cfg.api_key else 'missing — see llm.json.example'}",
            f"  Game toggle: {'on' if game.llm.user_enabled else 'off'}",
            f"  Flavor:      {game.llm.session_calls}/{cfg.max_calls_per_session} this session "
            f"({game.llm.total_calls} total)",
            f"  Structural:  {game.llm.session_struct_calls}/{cfg.max_struct_calls_per_session} this session "
            f"({game.llm.total_struct_calls} total)",
            f"  Text cache:  {len(game.llm.cache)} | JSON cache: {len(game.llm.struct_cache)}",
        ]
        if game.llm.last_error:
            lines.append(f"  Last error:  {game.llm.last_error}")
        if LLMClient.available(cfg):
            lines.append(
                "  Hooks: flavor text + structured missions, LFG contracts, weekly world events"
            )
            from llm_struct import LLMStructManager
            lines.extend(LLMStructManager.status_lines(game))
        else:
            lines.append("  Set OPENAI_API_KEY (recommended) or GROQ_API_KEY in ~/.terminalhacker/llm.json")
        return lines

    @staticmethod
    def test_generation(game: Game) -> bool:
        from main import error, success

        if not LLMClient.available():
            error("No API key. Copy llm.json.example → ~/.terminalhacker/llm.json")
            return False
        ok_flavor = False
        sample = LLMContentManager.generate(
            game,
            "test",
            "ping",
            "One sentence darknet broker offers a contract on corp-gateway 192.168.1.10.",
            limit=200,
        )
        if sample:
            success(f"Flavor LLM OK: {sample}")
            ok_flavor = True
        else:
            error(f"Flavor LLM failed: {game.llm.last_error or 'unknown'}")
        from llm_struct import LLMStructManager
        ok_struct = LLMStructManager.test_struct(game)
        return ok_flavor or ok_struct
