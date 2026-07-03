#!/usr/bin/env python3
"""Offensive gear vs remote firewall tests."""

from __future__ import annotations

import unittest

from main import Console, Game, Server


class CrackGearGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.lines: list[str] = []
        Console.handler = lambda text, _tag: self.lines.append(text)

    def tearDown(self) -> None:
        Console.handler = None

    def _connect(self, game: Game, server: Server) -> None:
        game.player.connection = server.ip
        game.player.connected_port = 22
        game.player.discovered_ips.add(server.ip)

    def test_offensive_power_formula(self) -> None:
        game = Game()
        p = game.player
        p.cpu_level = 2
        p.cracker_tier = 2
        self.assertEqual(p.offensive_power(), 6)

    def test_fw4_blocks_cpu1_with_hydra(self) -> None:
        game = Game()
        game.player.phase = "career"
        game.player.cpu_level = 1
        game.player.cracker_tier = 1
        self.assertEqual(game.player.offensive_power(), 3)
        srv = Server("10.60.0.77", "port-edi", 4, ssh_password="edi_gate!")
        game.network.servers[srv.ip] = srv
        self._connect(game, srv)
        game.cmd_crack([])
        self.assertIn("offensive power", "\n".join(self.lines).lower())
        self.assertFalse(srv.cracked)

    def test_fw4_requires_cpu2_hydra(self) -> None:
        game = Game()
        game.player.phase = "career"
        game.player.cpu_level = 2
        game.player.cracker_tier = 1
        self.assertEqual(game.player.offensive_power(), 4)
        srv = Server("10.60.0.77", "port-edi", 4, ssh_password="edi_gate!")
        game.network.servers[srv.ip] = srv
        self._connect(game, srv)
        game.cmd_crack([])
        self.assertTrue(srv.cracked)

    def test_fw5_requires_more_than_cpu2_hydra(self) -> None:
        game = Game()
        game.player.phase = "career"
        game.player.cpu_level = 2
        game.player.cracker_tier = 1
        srv = Server("10.0.0.55", "vault-server", 5, ssh_password="vault!")
        game.network.servers[srv.ip] = srv
        self._connect(game, srv)
        game.cmd_crack([])
        self.assertFalse(srv.cracked)

    def test_fw5_allowed_cpu3_hydra(self) -> None:
        game = Game()
        game.player.phase = "career"
        game.player.cpu_level = 3
        game.player.cracker_tier = 1
        self.assertEqual(game.player.offensive_power(), 5)
        srv = Server("10.0.0.55", "vault-server", 5, ssh_password="vault!")
        game.network.servers[srv.ip] = srv
        self._connect(game, srv)
        game.cmd_crack([])
        self.assertTrue(srv.cracked)


if __name__ == "__main__":
    unittest.main()
