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

    def test_handle_persists_in_save(self) -> None:
        import json
        import tempfile
        from pathlib import Path
        from progression import SaveManager

        game = Game()
        game.player.phase = "career"
        self.assertTrue(game.apply_handle("ghost_ops"))

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "save.json"
            data = SaveManager._serialize(game)
            path.write_text(json.dumps(data))
            loaded = json.loads(path.read_text())
            self.assertEqual(loaded["player"]["handle"], "ghost_ops")
            self.assertIn("handle_chosen", loaded["player"]["tutorial_flags"])

            game2 = Game()
            SaveManager._deserialize(game2, loaded)
            self.assertEqual(game2.player.handle, "ghost_ops")
            self.assertEqual(game2.player.display_name(), "ghost_ops")

    def test_needs_handle_setup_until_chosen(self) -> None:
        from main import HANDLE_CHOSEN_FLAG, needs_handle_setup

        game = Game()
        self.assertFalse(needs_handle_setup(game))
        game.player.phase = "career"
        self.assertTrue(needs_handle_setup(game))
        game.apply_handle("cipher7")
        self.assertFalse(needs_handle_setup(game))
        self.assertIn(HANDLE_CHOSEN_FLAG, game.player.tutorial_flags)

    def test_migrate_handle_chosen_from_save(self) -> None:
        from main import migrate_handle_chosen, needs_handle_setup

        game = Game()
        game.player.phase = "career"
        game.player.handle = "legacy_ops"
        migrate_handle_chosen(game)
        self.assertFalse(needs_handle_setup(game))

    def test_repair_premature_career(self) -> None:
        from main import repair_invalid_career_state

        game = Game()
        game.player.phase = "career"
        game.player.tutorial_step = 0
        game.player.handle = "ghost_ops"
        game.player.tutorial_flags.add("handle_chosen")
        repair_invalid_career_state(game)
        self.assertEqual(game.player.phase, "tutorial")
        self.assertEqual(game.player.handle, "trainee")
        self.assertNotIn("handle_chosen", game.player.tutorial_flags)

    def test_skip_to_career_marks_training_done(self) -> None:
        from main import TUTORIAL_CURRICULUM

        game = Game()
        game.player.phase = "tutorial"
        game.player.tutorial_step = 2
        self.assertTrue(game.tutorial.skip_to_career(chaos=False))
        self.assertEqual(game.player.phase, "career")
        self.assertEqual(game.player.tutorial_step, len(TUTORIAL_CURRICULUM))


if __name__ == "__main__":
    unittest.main()
