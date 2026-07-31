#!/usr/bin/env python3
"""Career host visibility and reconnect shell tests."""

from __future__ import annotations

import unittest

from main import Console, Game


class CareerHostFixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.lines: list[str] = []
        Console.handler = lambda text, _tag: self.lines.append(text)

    def tearDown(self) -> None:
        Console.handler = None

    def test_mission_target_spawns_at_career_start(self) -> None:
        game = Game()
        game.player.phase = "career"
        game.player.reputation = 100
        game.network.deploy_company_hosts_with_puzzles(game, game.player.reputation, False)
        self.assertIsNotNone(game.network.get_server("10.0.0.42"))

    def test_scan_finds_contract_host_on_corp_subnet(self) -> None:
        game = Game()
        game.player.phase = "career"
        game.player.reputation = 100
        if not any(r.destination == "10.0.0.0/24" for r in game.player.routes):
            from main import Route
            game.player.routes.append(Route("10.0.0.0/24", game.player.gateway))
        game.network.deploy_company_hosts_with_puzzles(game, game.player.reputation, False)
        game.cmd_scan(["10.0.0.0/24"])
        self.assertIn("10.0.0.42", game.player.discovered_ips)

    def test_connect_restores_cracked_shell(self) -> None:
        game = Game()
        game.player.phase = "career"
        from main import Route
        game.player.routes.append(Route("10.0.0.0/24", game.player.gateway))
        game.player.discovered_ips.add("10.0.0.99")
        srv = game.network.get_server("10.0.0.99")
        assert srv is not None
        srv.cracked = True
        game.cmd_connect(["10.0.0.99", "22"])
        self.assertTrue(game.player.has_remote_shell)
        self.assertEqual(game.player.connection, "10.0.0.99")
        joined = "\n".join(self.lines)
        self.assertIn("Shell restored", joined)

    def test_ls_from_home_hints_var_log(self) -> None:
        game = Game()
        game.player.connection = "10.0.0.99"
        game.player.has_remote_shell = True
        game.player.cwd = "/home/operator"
        game.cmd_ls([])
        joined = "\n".join(self.lines)
        self.assertIn("/var/log", joined)


if __name__ == "__main__":
    unittest.main()
