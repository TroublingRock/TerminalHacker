#!/usr/bin/env python3
"""Mail category tab tests."""

from __future__ import annotations

import unittest

from mail_categories import (
    TAB_LABELS,
    is_completed_mail,
    is_rival_mail,
    mail_category,
    mission_id_from_mail,
    unread_count,
)
from main import Game, MailMessage, Mission


class MailCategoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.game = Game()
        self.game.player.phase = "career"

    def test_rival_mail(self) -> None:
        msg = MailMessage("m1", "acid_k@rival.net", "watching you", "body")
        self.assertTrue(is_rival_mail(msg))
        self.assertEqual(mail_category(msg, self.game), "rivals")

    def test_open_contract_is_contracts_tab(self) -> None:
        msg = MailMessage(
            "m2", "ghost_broker@darknet", "Contract offer: proc-101", "do the job",
        )
        self.game.missions.missions.append(Mission(
            "proc-101", "ghost_broker", "brief", "10.0.0.1", "/tmp/x", 500,
        ))
        self.assertEqual(mail_category(msg, self.game), "contracts")

    def test_payment_confirmed_is_completed(self) -> None:
        msg = MailMessage(
            "m3", "ghost_broker@darknet", "Payment confirmed — $500",
            "Contract fulfilled.\nFunds transferred.",
        )
        self.assertTrue(is_completed_mail(msg, self.game))
        self.assertEqual(mail_category(msg, self.game), "completed")

    def test_completed_mission_offer_moves_to_completed(self) -> None:
        msg = MailMessage(
            "m4", "ghost_broker@darknet", "Contract offer: proc-200", "old job",
        )
        self.game.missions.missions.append(Mission(
            "proc-200", "ghost_broker", "brief", "10.0.0.2", "/tmp/y", 400, completed=True,
        ))
        self.assertEqual(mail_category(msg, self.game), "completed")
        self.assertEqual(mission_id_from_mail(msg), "proc-200")

    def test_unread_count_per_category(self) -> None:
        self.game.mail.messages.clear()
        self.game.mail.send("acid_k@rival.net", "taunt", "hey")
        self.game.mail.send("ghost_broker@darknet", "Intel drop", "news")
        self.assertEqual(unread_count(self.game.mail.messages, "rivals", self.game), 1)
        self.assertEqual(unread_count(self.game.mail.messages, "contracts", self.game), 1)
        self.assertIn("contracts", TAB_LABELS)


if __name__ == "__main__":
    unittest.main()
