#!/usr/bin/env python3
"""Interactive rival taunt tests."""

from __future__ import annotations

import unittest

from depth_systems import MetaState
from main import Game, MailMessage
from rival_taunt import RivalTauntManager


class RivalTauntTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = Game()
        self.game.player.phase = "career"
        self.game.meta = MetaState()
        self.game.meta.rival_trash_talk_unlocked = True

    def test_mail_reply_raises_anger(self) -> None:
        msg = self.game.mail.send("acid_k@rival.net", "test", "body")
        before = self.game.retention.rival_aggression
        self.assertTrue(RivalTauntManager.mail_reply(self.game, msg.mail_id, "you're slow and weak"))
        self.assertGreater(self.game.retention.rival_aggression, before)
        self.assertGreater(self.game.retention.rival_anger.get("acid_k", 0), 0)

    def test_board_taunt_posts_to_rivals(self) -> None:
        from social_board import SocialBoardManager
        SocialBoardManager.seed_if_needed(self.game)
        self.assertTrue(
            RivalTauntManager.board_taunt(self.game, "phantom_pkt", "finance sector is mine now"),
        )
        self.assertTrue(any(p.board == "rivals" and p.player_post for p in self.game.board.posts))

    def test_broker_mail_cannot_reply(self) -> None:
        msg = self.game.mail.send("ghost_broker@darknet", "job", "do work")
        self.assertFalse(RivalTauntManager.mail_reply(self.game, msg.mail_id, "nah"))

    def test_anger_scales_with_nuclear_words(self) -> None:
        mild = RivalTauntManager.score_taunt("nice try", public=False)
        hot = RivalTauntManager.score_taunt("you're trash and pathetic", public=True)
        self.assertLess(mild, hot)

    def test_decay_on_login(self) -> None:
        self.game.retention.rival_anger = {"acid_k": 5, "zero_cool": 1}
        RivalTauntManager.decay_anger_on_login(self.game)
        self.assertEqual(self.game.retention.rival_anger.get("acid_k"), 4)
        self.assertNotIn("zero_cool", self.game.retention.rival_anger)


if __name__ == "__main__":
    unittest.main()
