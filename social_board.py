#!/usr/bin/env python3
"""Social boards — darknet forums with NPC threads and player posts."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from main import Game

BOARD_NAMES = ("intel", "rivals", "flex", "lfg")

SEED_POSTS: list[dict[str, Any]] = [
    {
        "board": "intel", "author": "ghost_broker",
        "title": "NovaDyne perimeter still soft",
        "body": "Gateway FW is L3. Vendor jump box on .30 is the real entry. VPN recommended.",
        "likes": 42,
    },
    {
        "board": "intel", "author": "cipher7",
        "title": "Helix algo configs fetching 2x",
        "body": "fin-trading pays better than corp exfil this week. Root heist only.",
        "likes": 28,
    },
    {
        "board": "rivals", "author": "acid_k",
        "title": "Newbies on the board",
        "body": "Training grads think they're operators. Cute. Touch 10.0.0.x and I'll bill you.",
        "likes": 91,
    },
    {
        "board": "rivals", "author": "phantom_pkt",
        "title": "Finance sector claimed",
        "body": "172.16.0.x is contested. Helix IDS got an upgrade — adjust your wordlists.",
        "likes": 55,
    },
    {
        "board": "lfg", "author": "shade_runner",
        "title": "LFG vault crew — need ghost runner",
        "body": "HR pivot chain tonight. Need someone who wipes logs. DM via board post.",
        "likes": 12,
    },
    {
        "board": "flex", "author": "nullbyte",
        "title": "S-rank on chaos-c2",
        "body": "15 commands, zero traces, no shop buys. Beat that.",
        "likes": 120,
    },
]

NPC_REPLY_TEMPLATES: dict[str, list[str]] = {
    "ghost_broker": [
        "Clean run. Brokers are watching.",
        "Payment posted. Keep the board quiet.",
    ],
    "acid_k": [
        "Lucky crack. Won't happen twice.",
        "I saw that trace. Fix your tradecraft.",
    ],
    "cipher7": [
        "Solid exfil. Procedural crew wants you.",
        "Grade matters — S-rank gets priority contracts.",
    ],
    "phantom_pkt": [
        "Finance sector noticed.",
        "Stay out of Helix unless you're ready.",
    ],
}


@dataclass
class BoardPost:
    post_id: str
    board: str
    author: str
    title: str
    body: str
    timestamp: str = ""
    likes: int = 0
    player_post: bool = False
    upvoted: bool = False

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = time.strftime("%Y-%m-%d %H:%M")


@dataclass
class SocialBoardState:
    posts: list[BoardPost] = field(default_factory=list)
    karma: int = 0
    _counter: int = 0
    seeded: bool = False


class SocialBoardManager:
    @staticmethod
    def _next_id(state: SocialBoardState) -> str:
        state._counter += 1
        return f"post-{state._counter:04d}"

    @staticmethod
    def seed_if_needed(game: Game) -> None:
        if game.board.seeded or game.player.phase not in ("career", "endless"):
            return
        game.board.seeded = True
        for spec in SEED_POSTS:
            SocialBoardManager._add_post(
                game, spec["board"], spec["author"], spec["title"], spec["body"],
                likes=spec.get("likes", 0),
            )

    @staticmethod
    def _add_post(
        game: Game, board: str, author: str, title: str, body: str,
        *, likes: int = 0, player_post: bool = False,
    ) -> BoardPost:
        post = BoardPost(
            SocialBoardManager._next_id(game.board),
            board, author, title, body, likes=likes, player_post=player_post,
        )
        game.board.posts.insert(0, post)
        return post

    @staticmethod
    def on_career_session(game: Game) -> None:
        SocialBoardManager.seed_if_needed(game)

    @staticmethod
    def on_contract_complete(game: Game, mission: Any) -> None:
        if game.player.phase not in ("career", "endless"):
            return
        grade = getattr(mission, "grade", "") or "B"
        title = f"Cleared {mission.broker} contract"
        body = f"{mission.briefing}\n\nGrade: {grade}"
        SocialBoardManager._add_post(game, "flex", game.player.username, title, body, player_post=True)
        game.board.karma += 5 + {"S": 15, "A": 10, "B": 5, "C": 2}.get(grade, 5)
        SocialBoardManager._npc_reply(game, mission.broker)

    @staticmethod
    def on_story_choice(game: Game, choice_key: str, label: str) -> None:
        SocialBoardManager._add_post(
            game, "intel", game.player.username,
            f"Story choice: {label}",
            f"Picked '{choice_key}' on the narrative track.",
            player_post=True,
        )
        if choice_key == "rivals":
            SocialBoardManager._add_post(
                game, "rivals", "acid_k",
                "RE: new double agent",
                "Bold move posting that publicly. Don't embarrass me.",
                likes=33,
            )

    @staticmethod
    def on_story_beat(game: Game, node_id: str, title: str) -> None:
        SocialBoardManager._add_post(
            game, "intel", "ghost_broker",
            f"STORY: {title}",
            f"Narrative beat '{node_id}' is live. Check Mail for choices.",
            likes=8,
        )

    @staticmethod
    def on_endless_start(game: Game) -> None:
        SocialBoardManager._add_post(
            game, "lfg", game.player.username,
            "Dropping into endless abyss",
            "Roguelike run started. Who's beating floor 10?",
            player_post=True,
        )

    @staticmethod
    def on_endless_end(game: Game, reason: str) -> None:
        e = game.endless
        SocialBoardManager._add_post(
            game, "flex", game.player.username,
            f"Endless run ended — floor {e.best_floor}",
            f"Reason: {reason}. Score {e.score}.",
            player_post=True,
        )
        game.board.karma += e.floor * 2

    @staticmethod
    def _npc_reply(game: Game, broker: str) -> None:
        import random
        templates = NPC_REPLY_TEMPLATES.get(broker, NPC_REPLY_TEMPLATES.get("cipher7", []))
        if not templates:
            return
        body = random.choice(templates)
        board = "rivals" if broker in ("acid_k", "phantom_pkt", "nyx_root", "zero_cool") else "intel"
        author = broker if "@" not in broker else broker.split("@")[0]
        if broker.endswith("_broker") or broker in ("ghost_broker", "cipher7", "shade_runner", "packet_queen", "nullbyte"):
            author = broker
        SocialBoardManager._add_post(
            game, board, author,
            f"RE: your contract",
            body,
            likes=random.randint(3, 40),
        )

    @staticmethod
    def player_post(game: Game, board: str, title: str, body: str) -> bool:
        from main import error, success

        if board not in BOARD_NAMES:
            error(f"Unknown board '{board}'. Try: {', '.join(BOARD_NAMES)}")
            return False
        if game.player.phase not in ("career", "endless"):
            error("Board unlocks in career mode.")
            return False
        if len(title) < 3 or len(body) < 5:
            error("Title and body too short.")
            return False
        SocialBoardManager._add_post(
            game, board, game.player.username, title[:80], body[:500], player_post=True,
        )
        game.board.karma += 3
        from faction_consumables import FactionRepManager
        FactionRepManager.on_board_post(game, board)
        success(f"Posted to /{board}/")
        if game.board.karma >= 100:
            game.achievements.unlock("board_karma_100")
        return True

    @staticmethod
    def upvote(game: Game, post_id: str) -> bool:
        from main import error, success

        for p in game.board.posts:
            if p.post_id != post_id:
                continue
            if p.upvoted:
                error("Already upvoted.")
                return False
            p.upvoted = True
            p.likes += 1
            if p.player_post:
                game.board.karma += 2
            success(f"Upvoted [{p.board}] {p.title}")
            return True
        error(f"Post '{post_id}' not found.")
        return False

    @staticmethod
    def list_posts(game: Game, board: str | None = None, limit: int = 12) -> list[BoardPost]:
        posts = game.board.posts
        if board:
            posts = [p for p in posts if p.board == board]
        return posts[:limit]

    @staticmethod
    def format_post(p: BoardPost) -> str:
        tag = "[YOU]" if p.player_post else ""
        return f"[{p.post_id}] /{p.board}/ {tag} {p.author}: {p.title} (+{p.likes})"
