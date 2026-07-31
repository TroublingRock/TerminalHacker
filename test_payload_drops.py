#!/usr/bin/env python3
"""Tests for anonymous AI payload dead drops."""

from __future__ import annotations

import unittest

from depth_systems import MetaState
from main import Game
from payload_drops import PayloadDropManager, SENDER


class PayloadDropTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = Game()
        self.game.player.phase = "career"
        self.game.meta = MetaState()

    def test_spawn_sends_mail_and_creates_host(self) -> None:
        self.assertTrue(PayloadDropManager.spawn(self.game, force=True))
        drop = PayloadDropManager.active_drop(self.game)
        self.assertIsNotNone(drop)
        assert drop is not None
        self.assertTrue(drop["ip"].startswith("198.18."))
        srv = self.game.network.get_server(drop["ip"])
        self.assertIsNotNone(srv)
        self.assertIn(drop["path"], srv.files)
        self.assertTrue(any(m.sender == SENDER for m in self.game.mail.messages))

    def test_download_claims_payload_to_inventory(self) -> None:
        PayloadDropManager.spawn(self.game, force=True)
        drop = PayloadDropManager.active_drop(self.game)
        assert drop is not None
        key = drop["shop_key"]
        self.game.player.discovered_ips.add(drop["ip"])
        srv = self.game.network.get_server(drop["ip"])
        assert srv is not None
        srv.cracked = True
        self.game.player.connection = drop["ip"]
        self.game.player.has_remote_shell = True
        self.assertTrue(PayloadDropManager.try_claim_download(self.game, drop["ip"], drop["path"]))
        self.assertEqual(self.game.meta.inventory.get(key, 0), 1)
        self.assertTrue(self.game.meta.payload_drop_claimed)
        self.assertIsNone(PayloadDropManager.active_drop(self.game))

    def test_cooldown_spawns_after_tick(self) -> None:
        PayloadDropManager.spawn(self.game, force=True)
        drop = PayloadDropManager.active_drop(self.game)
        assert drop is not None
        self.game.meta.payload_drop_claimed = True
        self.game.meta.payload_drop_cd = 1
        PayloadDropManager.on_post_command(self.game)
        self.assertEqual(self.game.meta.payload_drop_cd, 0)
        PayloadDropManager.on_post_command(self.game)
        self.assertIsNotNone(PayloadDropManager.active_drop(self.game))

    def test_restore_from_save_recreates_host(self) -> None:
        PayloadDropManager.spawn(self.game, force=True)
        drop = PayloadDropManager.active_drop(self.game)
        assert drop is not None
        ip = drop["ip"]
        password = self.game.meta.payload_drop_password
        del self.game.network.servers[ip]
        PayloadDropManager.restore_from_save(self.game)
        self.assertIsNotNone(self.game.network.get_server(ip))
        self.assertEqual(self.game.meta.payload_drop_password, password)

    def test_hint_when_empty(self) -> None:
        PayloadDropManager.spawn(self.game, force=True)
        drop = PayloadDropManager.active_drop(self.game)
        assert drop is not None
        hint = PayloadDropManager.hint_when_empty(self.game, drop["shop_key"])
        self.assertIsNotNone(hint)
        self.assertIn("shard@null.dark", hint or "")


if __name__ == "__main__":
    unittest.main()
