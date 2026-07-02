#!/usr/bin/env python3
"""Chaos / mischief mode tests."""

from __future__ import annotations

import unittest

from chaos_system import ChaosCareerManager, NotorietyManager
from main import Game


class ChaosSystemTests(unittest.TestCase):
    def test_chaos_career_skips_tutorial(self) -> None:
        game = Game()
        self.assertEqual(game.player.phase, "tutorial")
        ChaosCareerManager.start(game)
        self.assertEqual(game.player.phase, "career")
        self.assertTrue(game.meta.chaos_mode)
        self.assertGreaterEqual(game.meta.notoriety, 5)
        self.assertGreater(game.player.money, 1000)

    def test_loud_contract_pays_more_in_chaos_mode(self) -> None:
        from main import Mission

        game = Game()
        game.player.phase = "career"
        game.meta.chaos_mode = True
        ip = "192.168.1.50"
        game.network.get_server(ip).cracked = True
        game.player.discovered_ips.add(ip)
        game.player.connection = ip
        game.player.has_remote_shell = True
        game.log_remote(game.network.get_server(ip), "test", "crack attempt")
        mission = Mission(
            "t", "ghost_broker", "test", ip, "/home/trainee/training_flag.txt", 400,
            require_log_wipe=False,
        )
        mult, note = NotorietyManager.contract_style_mult(game, mission)
        self.assertGreater(mult, 1.0)
        self.assertIn("LOUD", note)

    def test_notoriety_increases(self) -> None:
        game = Game()
        game.player.phase = "career"
        before = game.meta.notoriety
        NotorietyManager.add(game, 5, "test")
        self.assertEqual(game.meta.notoriety, before + 5)


if __name__ == "__main__":
    unittest.main()
