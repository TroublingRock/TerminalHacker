#!/usr/bin/env python3
"""Smoke tests for botnet payloads."""

from __future__ import annotations

import unittest

from botnet_system import BotnetManager, PAYLOAD_MINER
from depth_systems import MetaState
from main import Game, Player


class BotnetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = Game()
        self.game.player.phase = "career"
        self.game.player.money = 5000
        self.game.meta = MetaState()
        self.game.meta.inventory["miner_payload"] = 2
        self.game.meta.inventory["ddos_payload"] = 1
        self.game.player.discovered_ips.add("192.168.1.50")
        srv = self.game.network.get_server("192.168.1.50")
        assert srv is not None
        srv.cracked = True
        self.game.player.connection = "192.168.1.50"
        self.game.player.has_remote_shell = True

    def test_infect_miner_accrues_bank(self) -> None:
        BotnetManager.cmd_infect(self.game, ["miner"])
        self.assertIn("192.168.1.50", self.game.meta.infections)
        self.assertEqual(self.game.meta.inventory["miner_payload"], 1)
        self.game.player.connection = "localhost"
        self.game.player.has_remote_shell = False
        before = self.game.meta.botnet_bank
        BotnetManager.on_tick(self.game)
        self.assertGreater(self.game.meta.botnet_bank, before)

    def test_botnet_collect(self) -> None:
        BotnetManager.cmd_infect(self.game, ["miner"])
        self.game.meta.botnet_bank = 100
        BotnetManager.cmd_botnet(self.game, ["collect"])
        self.assertEqual(self.game.meta.botnet_bank, 0)
        self.assertGreater(self.game.player.money, 5000)

    def test_ddos_lowers_effective_security(self) -> None:
        srv = self.game.network.get_server("10.0.0.99")
        if srv is None:
            self.skipTest("dmz host not in network")
        base = srv.security_level
        self.assertGreaterEqual(base, 2)
        self.game.meta.ddos_targets[srv.ip] = 5
        self.assertLess(BotnetManager.effective_security(self.game, srv), base)

    def test_tutorial_blocks_infect(self) -> None:
        self.game.player.phase = "tutorial"
        BotnetManager.cmd_infect(self.game, ["miner"])
        self.assertEqual(len(self.game.meta.infections), 0)

    def test_infect_virus(self) -> None:
        self.game.meta.inventory["virus_payload"] = 1
        BotnetManager.cmd_infect(self.game, ["virus"])
        self.assertEqual(self.game.meta.infections.get("192.168.1.50"), "virus")

    def test_infect_frame(self) -> None:
        self.game.meta.inventory["frame_payload"] = 1
        BotnetManager.cmd_infect(self.game, ["frame", "zero_cool"])
        self.assertEqual(self.game.meta.framed_rivals.get("192.168.1.50"), "zero_cool")


if __name__ == "__main__":
    unittest.main()
