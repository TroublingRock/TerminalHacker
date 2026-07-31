#!/usr/bin/env python3
"""Economy scaling tests."""

from __future__ import annotations

import unittest

from depth_systems import MetaState
from economy import EconomyManager, progression_mult
from main import Game, Mission


class EconomyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = Game()
        self.game.player.phase = "career"
        self.game.player.reputation = 100
        self.game.meta = MetaState()

    def test_easy_target_pays_less_than_hard(self) -> None:
        easy_srv = self.game.network.get_server("192.168.1.10")
        hard_srv = self.game.network.get_server("10.0.0.55")
        self.assertIsNotNone(easy_srv)
        self.assertIsNotNone(hard_srv)
        easy = Mission("e", "ghost_broker", "easy", easy_srv.ip, "/x", 400, rep_reward=20)
        hard = Mission("h", "ghost_broker", "hard", hard_srv.ip, "/x", 400, rep_reward=20)
        easy_mult = EconomyManager.payout_multiplier(self.game, easy)
        hard_mult = EconomyManager.payout_multiplier(self.game, hard)
        self.assertLess(easy_mult, hard_mult)

    def test_progression_raises_hard_target_mult(self) -> None:
        self.game.player.reputation = 900
        mission = Mission("h", "ghost_broker", "vault", "10.0.0.55", "/x", 500, rep_reward=20)
        low_rep = EconomyManager.payout_multiplier(self.game, mission)
        self.game.player.reputation = 100
        high_rep = EconomyManager.payout_multiplier(self.game, mission)
        self.assertGreater(low_rep, high_rep)

    def test_broker_fee_applied(self) -> None:
        net, fee = EconomyManager.apply_broker_fee(self.game, 500, "ghost_broker")
        self.assertEqual(fee, 40)
        self.assertEqual(net, 460)

    def test_crack_bounty_scales_down_on_easy_host(self) -> None:
        easy = EconomyManager.crack_bounty(2, 100)
        hard = EconomyManager.crack_bounty(5, 100)
        self.assertLess(easy, hard)
        self.assertLess(easy, 30)

    def test_easy_hosts_capped_progression(self) -> None:
        self.assertLess(progression_mult(1200, 2), progression_mult(1200, 5))


if __name__ == "__main__":
    unittest.main()
