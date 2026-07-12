#!/usr/bin/env python3
"""Download persistence across save/load."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from main import Game, VirtualFile
from progression import SaveManager


class DownloadSaveTests(unittest.TestCase):
    def test_download_content_round_trips(self) -> None:
        game = Game()
        game.player.phase = "career"
        local = "/home/hacker/downloads/corporate_secrets.txt"
        secret = "TOP SECRET: Project Helix launch codes\n"
        game.player.files[local] = VirtualFile(local, secret, owner=game.player.username)

        data = SaveManager._serialize(game)
        self.assertEqual(data["player"]["downloads"][local], secret)

        loaded = Game()
        SaveManager._deserialize(loaded, data)
        self.assertIn(local, loaded.player.files)
        self.assertEqual(loaded.player.files[local].content, secret)

    def test_legacy_download_list_recovers_from_target_host(self) -> None:
        game = Game()
        game.player.phase = "career"
        game.network.deploy_company_hosts_with_puzzles(
            game, game.player.reputation, game.player.chaos_unlocked,
        )
        target_ip = "10.0.0.42"
        target_file = "/home/admin/corporate_secrets.txt"
        server = game.network.get_server(target_ip)
        assert server is not None
        expected = server.files[target_file].read()
        local = "/home/hacker/downloads/corporate_secrets.txt"

        legacy = {
            "player": {
                "phase": "career",
                "tutorial_step": 12,
                "tutorial_credits": 0,
                "money": 1000,
                "cpu_level": 1,
                "firewall_level": 1,
                "cracker_tier": 0,
                "vpn_licensed": False,
                "reputation": 150,
                "rank_index": 1,
                "chaos_unlocked": False,
                "routes": [],
                "discovered_ips": [],
                "owned_tools": [],
                "command_history": [],
                "tutorial_flags": [],
                "ticks": 5,
                "subnets_scanned": [],
                "privesc_hosts": [],
                "downloads": [local],
                "notes_content": "",
            },
            "missions": [{
                "mission_id": "ghost-001",
                "broker": "ghost_broker",
                "briefing": "test",
                "target_ip": target_ip,
                "target_file": target_file,
                "reward": 500,
                "completed": False,
            }],
            "mail": [],
            "servers": {target_ip: {"cracked": True, "ids": 0}},
        }

        loaded = Game()
        SaveManager._deserialize(loaded, legacy)
        self.assertEqual(loaded.player.files[local].content, expected)

    def test_save_file_preserves_downloads(self) -> None:
        game = Game()
        game.player.phase = "career"
        local = "/home/hacker/downloads/training_flag.txt"
        body = "FLAG{saved}\n"
        game.player.files[local] = VirtualFile(local, body, owner=game.player.username)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "save.json"
            path.write_text(json.dumps(SaveManager._serialize(game)))
            restored = Game()
            SaveManager._deserialize(restored, json.loads(path.read_text()))
            self.assertEqual(restored.player.files[local].content, body)


if __name__ == "__main__":
    unittest.main()
