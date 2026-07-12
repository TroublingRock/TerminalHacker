#!/usr/bin/env python3
"""Exfil source-host tracking tests."""

from __future__ import annotations

import unittest

from main import Game, Mission, VirtualFile
from retention import RetentionManager


class ExfilSourceTests(unittest.TestCase):
    def test_same_filename_different_hosts(self) -> None:
        game = Game()
        game.player.phase = "career"
        corp_ip = "192.168.1.10"
        train_ip = "192.168.1.50"
        corp_mission = Mission(
            "corp", "ghost_broker",
            "Exfil notes from corp-gateway",
            corp_ip, "/home/admin/notes.txt", 400,
        )
        train_mission = Mission(
            "train", "nullbyte",
            "Exfil notes from training-node",
            train_ip, "/home/trainee/notes.txt", 500,
        )
        game.missions.missions = [corp_mission, train_mission]

        local = "/home/hacker/downloads/notes.txt"
        game.player.files[local] = VirtualFile(local, "corp secrets\n")
        game.player.exfil_sources[local] = corp_ip

        self.assertTrue(RetentionManager.has_target_exfil(
            game, corp_ip, "/home/admin/notes.txt",
        ))
        self.assertFalse(RetentionManager.has_target_exfil(
            game, train_ip, "/home/trainee/notes.txt",
        ))
        self.assertFalse(RetentionManager.mission_is_satisfied(game, train_mission))
        self.assertFalse(RetentionManager.mission_is_satisfied(
            game, train_mission,
        ))

    def test_missing_exfil_source_blocks_completion(self) -> None:
        game = Game()
        game.player.phase = "career"
        mission = Mission(
            "starter", "ghost_broker", "Warm-up",
            "192.168.1.10", "/home/admin/notes.txt", 400,
        )
        local = "/home/hacker/downloads/notes.txt"
        game.player.files[local] = VirtualFile(local, "legacy\n")
        self.assertFalse(RetentionManager.has_target_exfil(
            game, "192.168.1.10", "/home/admin/notes.txt",
        ))

    def test_exfil_sources_round_trip_in_save(self) -> None:
        from progression import SaveManager

        game = Game()
        game.player.phase = "career"
        local = "/home/hacker/downloads/notes.txt"
        game.player.files[local] = VirtualFile(local, "data\n")
        game.player.exfil_sources[local] = "192.168.1.10"

        data = SaveManager._serialize(game)
        self.assertEqual(
            data["player"]["exfil_sources"][local], "192.168.1.10",
        )

        loaded = Game()
        SaveManager._deserialize(loaded, data)
        self.assertEqual(loaded.player.exfil_sources.get(local), "192.168.1.10")


if __name__ == "__main__":
    unittest.main()
