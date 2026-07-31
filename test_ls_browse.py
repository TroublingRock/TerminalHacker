#!/usr/bin/env python3
"""Remote filesystem listing tests."""

from __future__ import annotations

import unittest

from main import Console, Game


class LsBrowseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.lines: list[str] = []
        Console.handler = lambda text, _tag: self.lines.append(text)

    def tearDown(self) -> None:
        Console.handler = None

    def _remote_shell_on_training(self, game: Game) -> None:
        game.player.connection = "192.168.1.50"
        game.player.has_remote_shell = True
        game.player.cwd = "/home/trainee"

    def test_ls_root_shows_top_level_dirs(self) -> None:
        game = Game()
        self._remote_shell_on_training(game)
        game.cmd_ls(["/"])
        joined = "\n".join(self.lines)
        self.assertIn("/var/", joined)
        self.assertIn("/home/", joined)
        self.assertIn("/etc/", joined)

    def test_ls_var_shows_log_dir(self) -> None:
        game = Game()
        self._remote_shell_on_training(game)
        game.cmd_ls(["/var"])
        joined = "\n".join(self.lines)
        self.assertIn("/var/log/", joined)

    def test_ls_var_log_shows_log_files(self) -> None:
        game = Game()
        self._remote_shell_on_training(game)
        game.cmd_ls(["/var/log"])
        joined = "\n".join(self.lines)
        self.assertIn("/var/log/auth.log", joined)
        self.assertIn("/var/log/syslog", joined)

    def test_ls_from_root_nudges_var_log(self) -> None:
        game = Game()
        self._remote_shell_on_training(game)
        game.player.cwd = "/root"
        game.cmd_ls([])
        joined = "\n".join(self.lines)
        self.assertIn("/var/log", joined)


if __name__ == "__main__":
    unittest.main()
