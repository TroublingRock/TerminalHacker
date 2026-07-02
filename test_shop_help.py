#!/usr/bin/env python3
"""Shop and defense help text tests."""

from __future__ import annotations

import unittest

from main import Game, SHOP_CATALOG, defense_firewall_help


class ShopHelpTests(unittest.TestCase):
    def test_all_shop_items_have_detail(self) -> None:
        for item in SHOP_CATALOG:
            self.assertTrue(item.detail, msg=item.key)

    def test_defense_help_mentions_firewall_always_on(self) -> None:
        game = Game()
        game.player.phase = "career"
        text = "\n".join(defense_firewall_help(game))
        self.assertIn("ALWAYS ON", text)
        self.assertIn("Defense off", text)


if __name__ == "__main__":
    unittest.main()
