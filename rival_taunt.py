#!/usr/bin/env python3
"""Player taunts — mail replies and rivals-board trash talk with consequences."""

from __future__ import annotations

import random
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from main import Game, MailMessage

from depth_systems import RIVAL_PROFILES, RivalHeatManager

RIVAL_KEYS = frozenset(RIVAL_PROFILES.keys())

NUCLEAR_WORDS = frozenset({
    "trash", "weak", "pathetic", "owned", "easy", "lame", "coward", "slow",
    "script", "kiddie", "noob", "loser", "garbage", "worthless",
})

RIVAL_TAUNT_REPLY: dict[str, dict[int, list[str]]] = {
    "acid_k": {
        1: [
            "Cute. NovaDyne logs don't forget.\n\n— acid_k",
            "Reply noted. Corp bounty boards update hourly.\n\n— acid_k",
        ],
        2: [
            "You want my attention? You got it. 10.0.0.x is mine.\n\n— acid_k",
            "Loud mouth. I'm mapping your firewall stack while we talk.\n\n— acid_k",
        ],
        3: [
            "Done playing. Your egress is getting sold to blue team.\n\n— acid_k",
            "You just moved to the top of my hit list. Sleep light.\n\n— acid_k",
        ],
    },
    "phantom_pkt": {
        1: [
            "Clock's running. I still beat you to contracts.\n\n— phantom_pkt",
            "Trash talk won't crack Helix faster.\n\n— phantom_pkt",
        ],
        2: [
            "Finance sector remembers disrespect. 172.16.0.x will eat you.\n\n— phantom_pkt",
            "I race contracts for a living. You're already behind.\n\n— phantom_pkt",
        ],
        3: [
            "You want a war on my subnet? Enjoy the IDS storm.\n\n— phantom_pkt",
            "Marked. Next contract race ends with you broke.\n\n— phantom_pkt",
        ],
    },
    "nyx_root": {
        1: [
            "Ghost talk. I see your traces anyway.\n\n— nyx_root",
            "Perimeter's quiet. Too quiet. I'm watching.\n\n— nyx_root",
        ],
        2: [
            "You post like an operator. Your logs say trainee.\n\n— nyx_root",
            "192.168.1.x isn't yours. Back off or get fingerprinted.\n\n— nyx_root",
        ],
        3: [
            "I'll ghost into your box while you type insults.\n\n— nyx_root",
            "Anger logged. Your next disconnect won't be clean.\n\n— nyx_root",
        ],
    },
    "zero_cool": {
        1: [
            "Lol. Chaos subnet loves loud idiots.\n\n— zero_cool",
            "Keep talking. Heat rises when you yap.\n\n— zero_cool",
        ],
        2: [
            "You want smoke? 203.0.113.x is burning already.\n\n— zero_cool",
            "Brave words for someone one breach from broke.\n\n— zero_cool",
        ],
        3: [
            "Nuclear take. I'm forcing a probe on your gateway NOW.\n\n— zero_cool",
            "You asked for chaos. I'm delivering.\n\n— zero_cool",
        ],
    },
}

BOARD_TAUNT_TITLES = (
    "Open season on {rival}",
    "Come get me — {rival}",
    "RE: your trash talk",
    "{rival} is soft",
)


class RivalTauntManager:
    @staticmethod
    def _career(game: Game) -> bool:
        return game.player.phase in ("career", "endless")

    @staticmethod
    def parse_rival(name: str) -> str | None:
        raw = name.strip().lower().split("@")[0]
        if raw in RIVAL_KEYS:
            return raw
        return None

    @staticmethod
    def rival_from_mail(msg: MailMessage) -> str | None:
        return RivalTauntManager.parse_rival(msg.sender)

    @staticmethod
    def score_taunt(body: str, *, public: bool) -> int:
        text = body.lower()
        intensity = 1
        if len(body) > 50:
            intensity += 1
        if len(body) > 120:
            intensity += 1
        hits = sum(1 for w in NUCLEAR_WORDS if w in text)
        intensity += min(2, hits)
        if public:
            intensity += 1
        return min(4, intensity)

    @staticmethod
    def anger_tier(anger: int) -> int:
        if anger >= 7:
            return 3
        if anger >= 4:
            return 2
        return 1

    @staticmethod
    def _apply_consequences(game: Game, rival: str, intensity: int, *, public: bool) -> None:
        from chaos_system import NotorietyManager
        from faction_consumables import FactionRepManager

        r = game.retention
        r.last_rival = rival
        r.rival_anger[rival] = min(10, r.rival_anger.get(rival, 0) + intensity)
        r.rival_aggression = min(10, r.rival_aggression + 1 + intensity // 2)
        anger = r.rival_anger[rival]
        NotorietyManager.add(
            game, 2 + intensity + (1 if public else 0),
            f"taunted {rival}", player_action=True,
        )
        deltas = {"rivals": 2 * intensity, "corps": -intensity, "brokers": -1}
        FactionRepManager.shift(game, deltas)
        subnet = RIVAL_PROFILES[rival]["subnet"]
        RivalHeatManager.spike(game, subnet, 1 + intensity // 2)
        if anger >= 5 and random.random() < 0.35 + intensity * 0.08:
            game.threat._maybe_attack(force=anger >= 7)
        if anger >= 8 and random.random() < 0.4:
            from rival_ai import RivalAIManager
            RivalAIManager.send_breach_mail(
                game, rival, game.player.firewall_level,
                random.randint(25, 55) + anger * 5,
            )

    @staticmethod
    def _rival_response(game: Game, rival: str, player_body: str, *, public: bool) -> None:
        from chaos_system import CareerPressureManager
        from social_board import SocialBoardManager

        anger = game.retention.rival_anger.get(rival, 0)
        tier = RivalTauntManager.anger_tier(anger)
        pool = RIVAL_TAUNT_REPLY.get(rival, RIVAL_TAUNT_REPLY["acid_k"]).get(tier, [])
        body = random.choice(pool) if pool else f"Noted.\n\n— {rival}"

        from llm_content import LLMContentManager
        ctx = (
            f"Player taunted: {player_body[:200]}. "
            f"Anger {anger}/10. Public board: {public}. "
            f"Player handle: {game.player.display_name()}."
        )
        llm = LLMContentManager.enrich_rival_mail(game, rival, ctx)
        if llm:
            body = f"{llm}\n\n— {rival}"

        if public:
            SocialBoardManager._add_post(
                game, "rivals", rival,
                f"RE: {game.player.display_name()}",
                body.split("\n\n—")[0][:500],
                likes=random.randint(8, 60),
            )
        CareerPressureManager.send_or_queue_rival_mail(
            game,
            f"{rival}@rival.net",
            f"RE: your mouth — {game.player.display_name()}",
            body,
        )

    @staticmethod
    def player_taunt(
        game: Game,
        body: str,
        rival: str,
        *,
        public: bool = False,
    ) -> bool:
        from main import error, success, teach, warn

        if not RivalTauntManager._career(game):
            error("Taunts unlock in career mode.")
            return False
        from chaos_system import CareerPressureManager
        if not CareerPressureManager.can_trash_talk(game):
            error("Rivals aren't watching you yet — crack a host first.")
            teach("Complete a crack so acid_k and crew notice your handle.")
            return False
        if rival not in RIVAL_KEYS:
            error(f"Unknown rival. Pick: {', '.join(sorted(RIVAL_KEYS))}")
            return False
        body = body.strip()
        if len(body) < 5:
            error("Taunt too short — say something they'll remember.")
            return False
        if len(body) > 500:
            body = body[:500]

        intensity = RivalTauntManager.score_taunt(body, public=public)
        if public:
            from social_board import SocialBoardManager
            title = random.choice(BOARD_TAUNT_TITLES).format(rival=rival)
            SocialBoardManager._add_post(
                game, "rivals", game.player.display_name(),
                title, body, player_post=True, likes=random.randint(0, 3),
            )
            game.board.karma += 1
            success(f"Posted taunt on /rivals/ — {rival} is watching.")
        else:
            success(f"Reply sent to {rival}@rival.net (off-channel).")

        RivalTauntManager._apply_consequences(game, rival, intensity, public=public)
        RivalTauntManager._rival_response(game, rival, body, public=public)

        anger = game.retention.rival_anger.get(rival, 0)
        if anger >= 7:
            warn(f"{rival} is FURIOUS ({anger}/10) — expect probes and contract races.")
        elif anger >= 4:
            warn(f"{rival} anger {anger}/10 — subnet heat rising.")
        else:
            teach(f"{rival} anger {anger}/10. Taunt again and consequences escalate.")
        return True

    @staticmethod
    def mail_reply(game: Game, mail_id: str, body: str) -> bool:
        from main import error

        msg = game.mail.message_by_id(mail_id)
        if not msg:
            error("Message not found.")
            return False
        rival = RivalTauntManager.rival_from_mail(msg)
        if not rival:
            error("You can only reply to rival mail (sender @rival.net).")
            return False
        game.mail.mark_read(mail_id)
        return RivalTauntManager.player_taunt(game, body, rival, public=False)

    @staticmethod
    def board_taunt(game: Game, rival: str, body: str) -> bool:
        parsed = RivalTauntManager.parse_rival(rival)
        if not parsed:
            from main import error
            error(f"Unknown rival. Pick: {', '.join(sorted(RIVAL_KEYS))}")
            return False
        return RivalTauntManager.player_taunt(game, body, parsed, public=True)

    @staticmethod
    def board_reply(game: Game, post_id: str, body: str) -> bool:
        from main import error

        post = next((p for p in game.board.posts if p.post_id == post_id), None)
        if not post:
            error(f"Post '{post_id}' not found.")
            return False
        if post.board != "rivals":
            error("Reply taunts only work on /rivals/ posts.")
            return False
        rival = RivalTauntManager.parse_rival(post.author)
        if not rival:
            error(f"Can't infer rival from author '{post.author}'. Use: board taunt <rival> | <body>")
            return False
        return RivalTauntManager.player_taunt(
            game, f"RE: {post.title}\n{body}", rival, public=True,
        )

    @staticmethod
    def decay_anger_on_login(game: Game) -> None:
        if not game.retention.rival_anger:
            return
        game.retention.rival_anger = {
            k: max(0, v - 1) for k, v in game.retention.rival_anger.items() if v > 1
        }

    @staticmethod
    def status_lines(game: Game) -> list[str]:
        if not game.retention.rival_anger:
            return []
        lines = ["  Rival anger:"]
        for rival in sorted(RIVAL_KEYS):
            anger = game.retention.rival_anger.get(rival, 0)
            if anger > 0:
                bar = "#" * anger + "." * (10 - anger)
                lines.append(f"    {rival:<14} [{bar}] {anger}/10")
        return lines

    @staticmethod
    def mail_reply_hint(msg: MailMessage) -> str | None:
        if RivalTauntManager.rival_from_mail(msg):
            return f"Reply: mail reply {msg.mail_id} | your message"
        return None
