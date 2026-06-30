#!/usr/bin/env python3
"""Branching narrative — player choices alter brokers, rivals, and operation offers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from main import Game

# Story graph: node_id -> beat definition
STORY_NODES: dict[str, dict[str, Any]] = {
    "intro": {
        "title": "The Board Watches",
        "mail": {
            "sender": "ghost_broker@darknet",
            "subject": "STORY — Pick your lane",
            "body": (
                "Operator,\n\n"
                "The live board is watching your first moves. Brokers want operators "
                "who pick a lane and stay in it.\n\n"
                "Type 'story choose ghost' to run corporate contracts with my crew.\n"
                "Type 'story choose rivals' to play both sides — higher risk, chaos access.\n"
                "Type 'story choose solo' to stay independent.\n\n"
                "— ghost_broker"
            ),
        },
        "choices": {
            "ghost": {"flag": "story_ally_ghost", "next": "ghost_path", "label": "Trust ghost_broker"},
            "rivals": {"flag": "story_ally_rivals", "next": "rival_path", "label": "Play both sides"},
            "solo": {"flag": "story_solo", "next": "solo_path", "label": "Stay independent"},
        },
    },
    "ghost_path": {
        "title": "Corporate Ghost Lane",
        "mail": {
            "sender": "ghost_broker@darknet",
            "subject": "STORY — Corporate lane locked in",
            "body": (
                "Good. NovaDyne and Helix ops will pay well. Rivals will test you anyway — "
                "keep VPN hot and logs clean.\n\n"
                "Your next multi-day op will skew corporate.\n\n— ghost_broker"
            ),
        },
        "choices": {},
    },
    "rival_path": {
        "title": "Double Agent",
        "mail": {
            "sender": "acid_k@rival.net",
            "subject": "STORY — You have my attention",
            "body": (
                "So you want to play both sides.\n\n"
                "Fine. I'll feed you chaos intel — but cross me and I publish your home IP.\n\n"
                "— acid_k"
            ),
        },
        "choices": {},
    },
    "solo_path": {
        "title": "Lone Operator",
        "mail": {
            "sender": "cipher7@darknet",
            "subject": "STORY — Independent contractor",
            "body": (
                "No crew, no leash. Procedural contracts pay less rep but you pick your marks.\n\n"
                "— cipher7"
            ),
        },
        "choices": {},
    },
    "week_corporate": {
        "title": "Corporate Pressure",
        "requires_any": {"story_ally_ghost"},
        "mail": {
            "sender": "ghost_broker@darknet",
            "subject": "STORY — Boardroom war",
            "body": (
                "NovaDyne's board is bleeding leaks. HR vault and corp-dc are in play.\n"
                "Finish Operation Glass Firewall if you haven't — rivals want that segment.\n\n"
                "— ghost_broker"
            ),
        },
        "choices": {
            "push": {"flag": "story_push_corp", "next": "corp_escalation", "label": "Push corporate ops"},
            "lay_low": {"flag": "story_lay_low", "next": "ghost_path", "label": "Lay low this week"},
        },
    },
    "week_chaos": {
        "title": "Chaos Whisper",
        "requires_any": {"story_ally_rivals"},
        "mail": {
            "sender": "nullbyte@darknet",
            "subject": "STORY — Chaos subnet offer",
            "body": (
                "acid_k vouched for you. 203.0.113.0/24 opens early if you want it.\n\n"
                "Type 'story choose chaos' to unlock chaos targets now (trace risk x2).\n"
                "Type 'story choose refuse' to decline.\n\n— nullbyte"
            ),
        },
        "choices": {
            "chaos": {"flag": "story_chaos_unlock", "next": "chaos_committed", "label": "Enter chaos subnet"},
            "refuse": {"flag": "story_chaos_refused", "next": "rival_path", "label": "Decline for now"},
        },
    },
    "week_solo": {
        "title": "Contractor Weekly",
        "requires_any": {"story_solo"},
        "mail": {
            "sender": "cipher7@darknet",
            "subject": "STORY — Open market week",
            "body": (
                "No faction drama. Hit procedural contracts, stack grades, ignore the board politics.\n\n"
                "— cipher7"
            ),
        },
        "choices": {},
    },
    "corp_escalation": {
        "title": "Escalation",
        "mail": {
            "sender": "shade_runner@darknet",
            "subject": "STORY — Treasury target",
            "body": "Vault-server payroll is the next headline. You in?\n\n— shade_runner",
        },
        "choices": {},
    },
    "chaos_committed": {
        "title": "Chaos Bound",
        "mail": {
            "sender": "zero_cool@rival.net",
            "subject": "STORY — Welcome to the edge",
            "body": "203.0.113.x operators don't get second chances. Don't waste mine.\n\n— zero_cool",
        },
        "choices": {},
    },
}

OPERATION_PRIORITY: dict[str, list[str]] = {
    "story_ally_ghost": ["op-nova", "op-vault", "op-helix", "op-ledger", "op-counter", "op-chaos"],
    "story_ally_rivals": ["op-counter", "op-chaos", "op-nova", "op-helix", "op-vault", "op-ledger"],
    "story_solo": ["op-helix", "op-nova", "op-ledger", "op-vault", "op-counter", "op-chaos"],
    "default": ["op-nova", "op-helix", "op-vault", "op-ledger", "op-counter", "op-chaos"],
}


@dataclass
class StoryState:
    current_node: str = ""
    flags: set[str] = field(default_factory=set)
    choices_made: list[str] = field(default_factory=list)
    week_beat: int = 0
    intro_sent: bool = False


class StoryManager:
    @staticmethod
    def ensure_intro(game: Game) -> None:
        if game.player.phase != "career" or game.story.intro_sent:
            return
        game.story.intro_sent = True
        game.story.current_node = "intro"
        StoryManager._deliver_node(game, "intro")

    @staticmethod
    def send_weekly_beat(game: Game) -> None:
        if game.player.phase != "career":
            return
        game.story.week_beat += 1
        flags = game.story.flags
        if "story_ally_ghost" in flags and game.story.week_beat >= 2:
            node = "week_corporate"
        elif "story_ally_rivals" in flags and game.story.week_beat >= 2:
            node = "week_chaos"
        elif "story_solo" in flags:
            node = "week_solo"
        else:
            return
        if node not in game.story.choices_made:
            StoryManager._deliver_node(game, node)

    @staticmethod
    def _deliver_node(game: Game, node_id: str) -> None:
        node = STORY_NODES.get(node_id)
        if not node:
            return
        reqs = node.get("requires_any")
        if reqs and not reqs.intersection(game.story.flags):
            return
        mail = node.get("mail")
        if mail:
            game.mail.send(mail["sender"], mail["subject"], mail["body"])
        game.story.current_node = node_id
        from social_board import SocialBoardManager
        SocialBoardManager.on_story_beat(game, node_id, node.get("title", node_id))

    @staticmethod
    def make_choice(game: Game, choice_key: str) -> bool:
        from main import error, success

        node = STORY_NODES.get(game.story.current_node)
        if not node:
            error("No active story beat. Check Mail for the latest narrative.")
            return False
        choices = node.get("choices", {})
        if choice_key not in choices:
            keys = ", ".join(choices.keys()) or "none"
            error(f"Invalid choice '{choice_key}'. Options: {keys}")
            return False
        pick = choices[choice_key]
        flag = pick["flag"]
        game.story.flags.add(flag)
        game.story.choices_made.append(f"{game.story.current_node}:{choice_key}")
        nxt = pick.get("next", "")
        if nxt:
            StoryManager._deliver_node(game, nxt)
        success(f"Story choice: {pick['label']}")
        if len(game.story.choices_made) >= 3:
            game.achievements.unlock("story_fork")
        from social_board import SocialBoardManager
        SocialBoardManager.on_story_choice(game, choice_key, pick["label"])
        from faction_consumables import FactionRepManager
        FactionRepManager.on_story_choice(game, choice_key)
        if flag == "story_chaos_unlock":
            game.player.chaos_unlocked = True
            game.network.deploy_company_hosts_with_puzzles(game, game.player.reputation, True)
        return True

    @staticmethod
    def operation_order(game: Game) -> list[str]:
        flags = game.story.flags
        for key in ("story_ally_ghost", "story_ally_rivals", "story_solo"):
            if key in flags:
                return OPERATION_PRIORITY[key]
        return OPERATION_PRIORITY["default"]

    @staticmethod
    def narrative_addendum(game: Game) -> str:
        flags = game.story.flags
        lines: list[str] = []
        if "story_ally_ghost" in flags:
            lines.append("Brokers treat you as corporate muscle.")
        if "story_ally_rivals" in flags:
            lines.append("Rivals watch your moves — acid_k has leverage.")
        if "story_solo" in flags:
            lines.append("Independent lane — no faction backup.")
        if "story_chaos_unlock" in flags:
            lines.append("Chaos subnet clearance granted early.")
        if "story_push_corp" in flags:
            lines.append("Corporate escalation — vault targets prioritized.")
        return "\n".join(lines)

    @staticmethod
    def status_lines(game: Game) -> list[str]:
        s = game.story
        node = STORY_NODES.get(s.current_node, {})
        lines = [
            f"  Beat:    {node.get('title', s.current_node or '—')}",
            f"  Flags:   {', '.join(sorted(s.flags)) or 'none'}",
            f"  Choices: {len(s.choices_made)}",
        ]
        choices = node.get("choices", {})
        if choices:
            lines.append("  Options: story choose <" + "|".join(choices.keys()) + ">")
        return lines
