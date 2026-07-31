#!/usr/bin/env python3
"""World event heat application tests."""

from __future__ import annotations

import unittest

from llm_struct import LLMStructManager, _week_key
from main import Game


class WorldEventHeatTests(unittest.TestCase):
    def test_world_event_heat_applies_once_per_week(self) -> None:
        game = Game()
        game.player.phase = "career"
        game.player.ticks = 30
        game.missions.missions[0].completed = True
        game.llm.world_event = {"title": "Test", "heat_delta": 4}
        game.llm.world_event_week = _week_key()
        LLMStructManager.apply_world_event_login(game)
        first = game.meta.subnet_heat.get("192.168.1.0/24", 0)
        LLMStructManager.apply_world_event_login(game)
        second = game.meta.subnet_heat.get("192.168.1.0/24", 0)
        self.assertEqual(first, 4)
        self.assertEqual(second, 4)


if __name__ == "__main__":
    unittest.main()
