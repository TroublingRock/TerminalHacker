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
        self.assertGreaterEqual(game.meta.notoriety, 4)
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
        game.player.ticks = 25
        before = game.meta.notoriety
        NotorietyManager.add(game, 5, "test", player_action=True)
        self.assertEqual(game.meta.notoriety, before + 5)
        self.assertTrue(game.meta.chaos_headlines)

    def test_ghost_raid_spawns_mission(self) -> None:
        from chaos_system import GhostRaidManager

        game = Game()
        game.player.phase = "career"
        game.meta.chaos_mode = True
        GhostRaidManager.launch(game)
        self.assertTrue(any("ghost" in m.mission_id for m in game.missions.missions))

    def test_teach_suppressed_in_chaos_mode(self) -> None:
        from main import set_teach_suppress_chaos, _teach_suppressed, teach

        game = Game()
        game.meta.chaos_mode = True
        set_teach_suppress_chaos(True)
        self.assertTrue(_teach_suppressed())
        set_teach_suppress_chaos(False)

    def test_deface_adds_notoriety(self) -> None:
        from botnet_system import BotnetManager, PAYLOAD_DEFACE
        from depth_systems import MetaState

        game = Game()
        game.player.phase = "career"
        game.meta = MetaState()
        game.meta.chaos_mode = True
        game.meta.inventory["deface_payload"] = 1
        ip = "192.168.1.50"
        game.player.discovered_ips.add(ip)
        srv = game.network.get_server(ip)
        assert srv is not None
        srv.cracked = True
        game.player.connection = ip
        game.player.has_remote_shell = True
        BotnetManager.cmd_infect(game, ["deface"])
        self.assertIn(ip, game.meta.defaced_hosts)
        self.assertEqual(game.meta.infections.get(ip), PAYLOAD_DEFACE)
        self.assertGreater(game.meta.notoriety, 0)

    def test_botnet_map_lines(self) -> None:
        from botnet_system import BotnetMapRenderer, PAYLOAD_MINER
        from depth_systems import MetaState

        game = Game()
        game.player.phase = "career"
        game.meta = MetaState()
        game.meta.infections["192.168.1.50"] = PAYLOAD_MINER
        game.player.discovered_ips.add("192.168.1.50")
        lines = BotnetMapRenderer.map_lines(game)
        self.assertTrue(any("BOTNET MAP" in ln for ln in lines))
        self.assertTrue(any("192.168.1.50" in ln for ln in lines))

    def test_veteran_profile(self) -> None:
        from progression import PROFILE_PATH, PlayerProfile
        import json

        backup = PROFILE_PATH.read_text() if PROFILE_PATH.exists() else None
        try:
            if PROFILE_PATH.exists():
                PROFILE_PATH.unlink()
            self.assertFalse(PlayerProfile.is_veteran())
            PlayerProfile.mark_veteran()
            self.assertTrue(PlayerProfile.is_veteran())
        finally:
            if backup is not None:
                PROFILE_PATH.write_text(backup)
            elif PROFILE_PATH.exists():
                PROFILE_PATH.unlink()

    def test_rookie_grace_blocks_heat_lockdown(self) -> None:
        from chaos_system import CareerPressureManager, ChaosEventManager

        game = Game()
        game.player.phase = "career"
        game.player.ticks = 2
        game.meta.subnet_heat["192.168.1.0/24"] = 8
        before = game.meta.notoriety
        ChaosEventManager.on_post_command(game)
        self.assertTrue(CareerPressureManager.rookie_grace(game))
        self.assertEqual(game.meta.notoriety, before)
        self.assertFalse(any("lockdown" in f for f in game.meta.chaos_flags))


if __name__ == "__main__":
    unittest.main()
