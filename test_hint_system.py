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

    def test_hint_on_connected_host_suggests_log_wipe(self) -> None:
        game = Game()
        game.player.phase = "career"
        game.network.deploy_company_hosts_with_puzzles(
            game, game.player.reputation, game.player.chaos_unlocked,
        )
        ip = "10.0.0.55"
        for mission in game.missions.missions:
            mission.completed = True
        from main import Mission
        game.missions.missions.insert(
            0,
            Mission(
                "vault-test", "ghost_broker",
                "Exfil payroll.csv from vault-server, wipe logs.",
                ip, "/root/payroll.csv", 500, require_privesc=True,
            ),
        )
        game.missions.missions.insert(
            0,
            Mission(
                "other", "ghost_broker", "Other target", "10.0.0.42",
                "/home/admin/corporate_secrets.txt", 400,
            ),
        )
        game.player.discovered_ips.add(ip)
        if not any(r.destination == "10.0.0.0/24" for r in game.player.routes):
            from main import Route
            game.player.routes.append(Route("10.0.0.0/24", "192.168.1.1"))
        game.player.connection = ip
        game.player.has_remote_shell = True
        game.player.privesc_hosts.add(ip)
        game.player.cwd = "/root"
        server = game.network.get_server(ip)
        assert server is not None
        server.cracked = True
        server.write_auth(f"Accepted password for admin from {game.player.public_ip}")
        game.player.files["/home/hacker/downloads/payroll.csv"] = __import__(
            "main", fromlist=["VirtualFile"]
        ).VirtualFile("/home/hacker/downloads/payroll.csv", "ceo,2.1M\n")
        cmd, why = HintManager.infer(game)
        self.assertIn("rm /var/log", cmd)
        self.assertIn("10.0.0.55", why)


if __name__ == "__main__":
    unittest.main()
