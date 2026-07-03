#!/usr/bin/env python3
"""Rival AI polish tests."""

from __future__ import annotations

import unittest

from depth_systems import MetaState, ModifierManager, RivalHeatManager
from main import Game, Mission
from rival_ai import RivalAIManager, RIVAL_RACE_GOAL


class RivalAITests(unittest.TestCase):
    def test_territory_weighted_pick(self) -> None:
        game = Game()
        game.player.phase = "career"
        game.player.connection = "10.0.0.42"
        game.player.has_remote_shell = True
        game.network.get_server("10.0.0.42")
        picks = [RivalAIManager.pick_rival(game) for _ in range(40)]
        self.assertGreater(picks.count("acid_k"), picks.count("phantom_pkt"))

    def test_race_progress_visible(self) -> None:
        game = Game()
        game.player.phase = "career"
        game.meta = MetaState()
        m = Mission(
            "race-1", "ghost_broker", "test", "172.16.0.20", "/home/x.txt", 400,
            modifiers=["rival_race"],
        )
        RivalAIManager.assign_race_rival(game, m)
        game.meta.rival_race_prog["race-1"] = 10
        tag = RivalAIManager.race_progress_line(game, m)
        self.assertIn("phantom_pkt", tag)
        self.assertIn("10/", tag)

    def test_race_rival_wins(self) -> None:
        game = Game()
        game.player.phase = "career"
        game.meta = MetaState()
        m = Mission(
            "race-2", "broker", "test", "10.0.0.50", "/home/x.txt", 400,
            modifiers=["rival_race"],
        )
        RivalAIManager.assign_race_rival(game, m)
        game.meta.rival_race_prog["race-2"] = RIVAL_RACE_GOAL
        RivalAIManager.on_race_tick(game, m)
        self.assertTrue(m.completed)
        self.assertNotIn("race-2", game.meta.rival_race_prog)

    def test_heat_mult_spike(self) -> None:
        game = Game()
        game.meta = MetaState()
        RivalHeatManager.spike(game, "203.0.113.0/24", 2)
        self.assertGreaterEqual(game.meta.subnet_heat["203.0.113.0/24"], 3)

    def test_career_reactions_enabled_with_heat(self) -> None:
        game = Game()
        game.player.phase = "career"
        game.player.ticks = 25
        game.meta = MetaState()
        game.meta.subnet_heat["10.0.0.0/24"] = 4
        self.assertTrue(RivalAIManager.should_react_in_career(game))


if __name__ == "__main__":
    unittest.main()
