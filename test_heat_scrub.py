#!/usr/bin/env python3
"""Broker heat scrub tests."""

from __future__ import annotations

import unittest

from depth_systems import BrokerHeatScrub
from main import Game


class HeatScrubTests(unittest.TestCase):
    def test_cool_reduces_heat_and_charges_career_wallet(self) -> None:
        game = Game()
        game.player.phase = "career"
        game.player.money = 5000
        game.meta.subnet_heat["10.0.0.0/24"] = 7
        before_money = game.player.money
        BrokerHeatScrub.cool(game, "10.0.0.0/24")
        self.assertEqual(game.meta.subnet_heat["10.0.0.0/24"], 4)
        self.assertLess(game.player.money, before_money)
        self.assertGreater(game.meta.heat_scrub_cd, 0)
        self.assertEqual(game.meta.heat_scrubs_paid, 1)

    def test_cool_blocked_below_min_heat(self) -> None:
        game = Game()
        game.player.phase = "career"
        game.player.money = 5000
        game.meta.subnet_heat["10.0.0.0/24"] = 2
        BrokerHeatScrub.cool(game, "10.0.0.0/24")
        self.assertEqual(game.meta.subnet_heat["10.0.0.0/24"], 2)
        self.assertEqual(game.player.money, 5000)

    def test_cool_blocked_on_cooldown(self) -> None:
        game = Game()
        game.player.phase = "career"
        game.player.money = 10000
        game.meta.subnet_heat["10.0.0.0/24"] = 8
        game.meta.heat_scrub_cd = 5
        BrokerHeatScrub.cool(game, "")
        self.assertEqual(game.meta.subnet_heat["10.0.0.0/24"], 8)

    def test_escalating_cost(self) -> None:
        game = Game()
        game.player.phase = "career"
        game.meta.subnet_heat["10.0.0.0/24"] = 6
        first = BrokerHeatScrub.quote_cost(game, "10.0.0.0/24")
        game.meta.heat_scrubs_paid = 2
        third = BrokerHeatScrub.quote_cost(game, "10.0.0.0/24")
        self.assertGreater(third, first)

    def test_tutorial_blocked(self) -> None:
        game = Game()
        game.player.phase = "tutorial"
        game.player.money = 5000
        game.meta.subnet_heat["192.168.1.0/24"] = 8
        BrokerHeatScrub.cool(game, "")
        self.assertEqual(game.meta.subnet_heat["192.168.1.0/24"], 8)


if __name__ == "__main__":
    unittest.main()
