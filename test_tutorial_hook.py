#!/usr/bin/env python3
"""Tutorial curriculum compression tests."""

from __future__ import annotations

import unittest

from main import Game, TUTORIAL_CURRICULUM, TutorialManager


class TutorialHookTests(unittest.TestCase):
    def test_curriculum_twelve_lessons(self) -> None:
        self.assertEqual(len(TUTORIAL_CURRICULUM), 12)
        self.assertEqual(TutorialManager.DEFENSE_LESSON, 11)

    def test_lesson_zero_needs_ifconfig_and_route(self) -> None:
        game = Game()
        game.player.phase = "tutorial"
        game.player.tutorial_step = 0
        game.player.command_history.add("ifconfig")
        game.tutorial.check_advance()
        self.assertEqual(game.player.tutorial_step, 0)
        game.player.command_history.add("route")
        game.tutorial.check_advance()
        self.assertEqual(game.player.tutorial_step, 1)

    def test_opening_hook_once(self) -> None:
        game = Game()
        game.player.phase = "tutorial"
        before = len(game.mail.messages)
        game.tutorial.send_opening_hook()
        self.assertEqual(len(game.mail.messages), before + 2)
        self.assertIn("opening_hook_sent", game.player.tutorial_flags)
        game.tutorial.send_opening_hook()
        self.assertEqual(len(game.mail.messages), before + 2)

    def test_curriculum_migration(self) -> None:
        game = Game()
        game.player.phase = "tutorial"
        game.player.tutorial_step = 5
        game.player.tutorial_flags.discard("tutorial_v2")
        game.tutorial.migrate_curriculum_step_for()
        self.assertEqual(game.player.tutorial_step, 4)

    def test_curriculum_migration_keeps_v2_lesson_one(self) -> None:
        game = Game()
        game.player.phase = "tutorial"
        game.player.tutorial_step = 1
        game.player.tutorial_flags.discard("tutorial_v2")
        game.player.command_history.add("ifconfig")
        game.player.command_history.add("route")
        game.tutorial.migrate_curriculum_step_for()
        self.assertEqual(game.player.tutorial_step, 1)

    def test_sync_repairs_reset_tutorial_step(self) -> None:
        game = Game()
        game.player.phase = "tutorial"
        game.player.tutorial_step = 0
        game.player.tutorial_flags.add("tutorial_v2")
        game.player.command_history.add("ifconfig")
        game.player.command_history.add("route")
        game.tutorial.sync_tutorial_step_from_progress()
        self.assertEqual(game.player.tutorial_step, 1)


if __name__ == "__main__":
    unittest.main()
