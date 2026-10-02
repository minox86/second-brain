import os
import unittest
from unittest import mock

from helpers import WikiCase, run_cli
from sb_core import cli
from sb_core.errors import SbError


class WikiEnvTest(WikiCase):
    def test_sb_wiki_is_used_without_flag(self):
        root = self.make_wiki()
        with mock.patch.dict(os.environ, {"SB_WIKI": str(root)}):
            code, data, _ = run_cli("version")
        self.assertEqual((code, data["wiki"]), (0, str(root.resolve())))

    def test_flag_wins_over_env(self):
        first, second = self.make_wiki(), self.make_wiki()
        with mock.patch.dict(os.environ, {"SB_WIKI": str(first)}):
            code, data, _ = run_cli("version", "--wiki", second)
        self.assertEqual(data["wiki"], str(second.resolve()))

    def test_env_is_used_by_wiki_commands(self):
        root = self.make_wiki()
        with mock.patch.dict(os.environ, {"SB_WIKI": str(root)}):
            code, data, _ = run_cli("validate")
        self.assertEqual((code, data["ok"]), (0, True))

    def test_error_payload_is_emitted(self):
        class WithPayload(SbError):
            payload = {"error": "doppione", "path": "operations/tasks/X.md"}

        with mock.patch.object(cli, "cmd_version", side_effect=WithPayload("doppione")):
            code, data, _ = run_cli("version")
        self.assertEqual((code, data), (2, {"error": "doppione", "path": "operations/tasks/X.md"}))


if __name__ == "__main__":
    unittest.main()
