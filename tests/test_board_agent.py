import plistlib
import sys
import unittest
from pathlib import Path

from helpers import ROOT, WikiCase
from sb_core import board_agent


class AgentTest(WikiCase):
    def test_plist_runs_the_board_for_this_wiki(self):
        root = self.make_wiki({})
        plist = board_agent.agent_plist(root, python="/usr/bin/python3", path_env="/opt/homebrew/bin:/usr/bin")
        resolved = str(Path(root).resolve())
        self.assertEqual(plist["ProgramArguments"],
                         ["/usr/bin/python3", str(ROOT / "toolkit" / "sb.py"), "board", "--no-open", "--wiki", resolved])
        self.assertEqual((plist["RunAtLoad"], plist["KeepAlive"]), (True, {"SuccessfulExit": False}))
        self.assertEqual(plist["EnvironmentVariables"], {"PATH": "/opt/homebrew/bin:/usr/bin"})
        self.assertEqual(plist["StandardErrorPath"], resolved + "/.sb/board.log")
        self.assertTrue(plist["Label"].startswith("com.second-brain.board."))
        plistlib.dumps(plist)  # serializzabile

    def test_label_is_stable_and_per_wiki(self):
        a, b = self.make_wiki({}), self.make_wiki({})
        self.assertEqual(board_agent.label_of(a), board_agent.label_of(a))
        self.assertNotEqual(board_agent.label_of(a), board_agent.label_of(b))

    @unittest.skipUnless(sys.platform == "darwin", "solo macOS")
    def test_uninstall_without_agent_is_harmless(self):
        root = self.make_wiki({})
        calls = []
        result = board_agent.uninstall(root, launchctl=lambda *a: calls.append(a))
        self.assertFalse(result["uninstalled"])
        self.assertEqual(calls[0][0], "bootout")


if __name__ == "__main__":
    unittest.main()
