#!/usr/bin/env python3
"""Mail trash / restore tests."""

from __future__ import annotations

import unittest

from main import Game, MailBox


class MailTrashTests(unittest.TestCase):
    def test_trash_and_restore(self) -> None:
        box = MailBox()
        msg = box.send("a@b.c", "test", "body")
        self.assertTrue(box.trash_message(msg.mail_id))
        self.assertEqual(len(box.messages), 0)
        self.assertEqual(len(box.trash), 1)
        self.assertTrue(box.restore_message(msg.mail_id))
        self.assertEqual(len(box.messages), 1)
        self.assertEqual(len(box.trash), 0)

    def test_permanent_delete(self) -> None:
        box = MailBox()
        msg = box.send("a@b.c", "gone", "body")
        box.trash_message(msg.mail_id)
        self.assertTrue(box.permanent_delete(msg.mail_id))
        self.assertEqual(len(box.trash), 0)

    def test_cmd_mail_trash(self) -> None:
        game = Game()
        before = len(game.mail.messages)
        msg = game.mail.send("trainer@local", "hello", "world")
        game.cmd_mail(["trash", msg.mail_id])
        self.assertEqual(len(game.mail.messages), before)
        self.assertTrue(any(m.mail_id == msg.mail_id for m in game.mail.trash))
        self.assertFalse(any(m.mail_id == msg.mail_id for m in game.mail.messages))


if __name__ == "__main__":
    unittest.main()
