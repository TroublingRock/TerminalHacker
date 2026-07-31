#!/usr/bin/env python3
"""Rival race loss and handle tests."""

from __future__ import annotations

import unittest

from depth_systems import MetaState
from main import Game, Mission
from rival_ai import RIVAL_RACE_GOAL, RivalAIManager


class RivalRaceLossTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = Game()
        self.game.player.phase = "career"
        self.game.player.money = 1000
        self.game.meta = MetaState()
        self.mission = Mission(
            "race-pay", "ghost_broker",
            "test exfil", "192.168.1.10", "/home/admin/notes.txt", 500,
            modifiers=["rival_race"],
        )
        self.game.missions.missions.append(self.mission)
        RivalAIManager.assign_race_rival(self.game, self.mission)
        local = "/home/hacker/downloads/notes.txt"
        from main import VirtualFile
        self.game.player.files[local] = VirtualFile(local, "data\n", owner="hacker")
        self.game.player.exfil_sources[local] = "192.168.1.10"

    def test_lost_race_blocks_payout(self) -> None:
        self.game.meta.rival_race_prog["race-pay"] = RIVAL_RACE_GOAL
        RivalAIManager.on_race_tick(self.game, self.mission)
        self.assertTrue(self.mission.race_lost)
        before = self.game.player.money
        self.game._advance_missions()
        self.assertEqual(self.game.player.money, before)

    def test_race_resolved_before_completion_check(self) -> None:
        self.game.meta.rival_race_prog["race-pay"] = RIVAL_RACE_GOAL - 1
        self.game._advance_missions()
        self.assertTrue(self.mission.race_lost)
        self.assertEqual(self.game.player.money, 1000)


class HandleTests(unittest.TestCase):
    def test_set_handle(self) -> None:
        game = Game()
        game.cmd_handle(["ghost_ops"])
        self.assertEqual(game.player.handle, "ghost_ops")
        self.assertEqual(game.player.display_name(), "ghost_ops")

    def test_invalid_handle_rejected(self) -> None:
        game = Game()
        game.cmd_handle(["x"])
        self.assertEqual(game.player.handle, "trainee")


if __name__ == "__main__":
    unittest.main()
