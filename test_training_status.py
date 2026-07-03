#!/usr/bin/env python3
"""Training / skip / wallet clarity tests."""

from __future__ import annotations

import unittest

from chaos_system import ChaosCareerManager
from main import Game


class TrainingStatusTests(unittest.TestCase):
    def test_lesson_shows_career_wallet_after_chaos_skip(self) -> None:
        game = Game()
        ChaosCareerManager.start(game)
        self.assertEqual(game.player.phase, "career")
        self.assertTrue(game.tutorial.skipped_training())
        self.assertIsNone(game.tutorial.current())

    def test_skip_tutorial_standard(self) -> None:
        game = Game()
        game.player.phase = "tutorial"
        game.player.tutorial_step = 3
        self.assertTrue(game.tutorial.skip_to_career(chaos=False))
        self.assertEqual(game.player.phase, "career")
        self.assertEqual(game.player.tutorial_credits, 0)

    def test_career_buy_uses_money_not_tutorial_credits(self) -> None:
        game = Game()
        game.player.phase = "career"
        game.player.money = 1000
        game.player.tutorial_credits = 500
        game.player.firewall_level = 2
        game.player._game_ref = game
        from main import Shop
        before = game.player.money
        self.assertTrue(Shop.buy(game.player, "firewall"))
        self.assertEqual(game.player.tutorial_credits, 500)
        self.assertLess(game.player.money, before)


if __name__ == "__main__":
    unittest.main()
