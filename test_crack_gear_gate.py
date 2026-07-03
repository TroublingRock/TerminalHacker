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

    def test_fw4_blocks_cpu1_without_cracker(self) -> None:
        game = Game()
        game.player.phase = "career"
        game.player.cpu_level = 1
        game.player.cracker_tier = 0
        srv = Server("10.60.0.77", "port-edi", 4, ssh_password="edi_gate!")
        game.network.servers[srv.ip] = srv
        self._connect(game, srv)
        game.cmd_crack([])
        joined = "\n".join(self.lines)
        self.assertIn("outpaces your gear", joined)
        self.assertFalse(srv.cracked)

    def test_fw4_allowed_with_hydra_tier(self) -> None:
        game = Game()
        game.player.phase = "career"
        game.player.cpu_level = 1
        game.player.cracker_tier = 1
        srv = Server("10.60.0.77", "port-edi", 4, ssh_password="edi_gate!")
        game.network.servers[srv.ip] = srv
        self._connect(game, srv)
        game.cmd_crack([])
        self.assertTrue(srv.cracked)

    def test_max_crack_security_formula(self) -> None:
        game = Game()
        game.player.cpu_level = 2
        game.player.cracker_tier = 2
        self.assertEqual(game.player.max_crack_security(), 6)


if __name__ == "__main__":
    unittest.main()
