#!/usr/bin/env python3
"""Hint command inference tests."""

from __future__ import annotations

import unittest

from hint_system import HintManager
from main import Game


class HintSystemTests(unittest.TestCase):
    def test_tutorial_starts_with_ifconfig(self) -> None:
        game = Game()
        game.player.phase = "tutorial"
        game.player.tutorial_step = 0
        cmd, _ = HintManager.infer(game)
        self.assertEqual(cmd, "ifconfig")

    def test_tutorial_route_after_ifconfig(self) -> None:
        game = Game()
        game.player.phase = "tutorial"
        game.player.tutorial_step = 0
        game.player.command_history.add("ifconfig")
        cmd, _ = HintManager.infer(game)
        self.assertEqual(cmd, "route")

    def test_tutorial_scan_on_discovery_lesson(self) -> None:
        game = Game()
        game.player.phase = "tutorial"
        game.player.tutorial_step = 1
        cmd, _ = HintManager.infer(game)
        self.assertEqual(cmd, "scan")

    def test_tutorial_connect_when_discovered(self) -> None:
        game = Game()
        game.player.phase = "tutorial"
        game.player.tutorial_step = 2
        cmd, _ = HintManager.infer(game)
        self.assertEqual(cmd, "connect 192.168.1.50 22")

    def test_career_mission_suggests_scan(self) -> None:
        game = Game()
        game.player.phase = "career"
        mission = game.missions.missions[0]
        mission.completed = False
        mission.target_ip = "10.0.0.42"
        cmd, _ = HintManager.infer(game)
        self.assertIn("scan", cmd)

    def test_career_mission_suggests_connect_after_discovery(self) -> None:
        game = Game()
        game.player.phase = "career"
        mission = game.missions.missions[0]
        mission.completed = False
        mission.target_ip = "10.0.0.42"
        game.player.discovered_ips.add("10.0.0.42")
        cmd, _ = HintManager.infer(game)
        self.assertTrue(cmd.startswith("connect 10.0.0.42"))

    def test_career_mission_suggests_crack_with_shell_needed(self) -> None:
        game = Game()
        game.player.phase = "career"
        mission = game.missions.missions[0]
        mission.completed = False
        mission.target_ip = "10.0.0.42"
        game.player.discovered_ips.add("10.0.0.42")
        game.player.connection = "10.0.0.42"
        game.player.connected_port = 22
        game.retention.session_probed.add("10.0.0.42")
        cmd, _ = HintManager.infer(game)
        self.assertEqual(cmd, "crack")


if __name__ == "__main__":
    unittest.main()
