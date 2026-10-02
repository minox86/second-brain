import subprocess
import sys
import unittest

from helpers import ROOT, run_cli

import sb_core


class CliTest(unittest.TestCase):
    def test_version(self):
        code, data, _ = run_cli("version")
        self.assertEqual(code, 0)
        self.assertEqual(data["toolkit"], sb_core.__version__)
        self.assertEqual(data["format"], 1)

    def test_unknown_command_is_usage_error(self):
        code, _, _ = run_cli("boh")
        self.assertEqual(code, 2)

    def test_entry_point_runs_as_script(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "toolkit" / "sb.py"), "version"],
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('"toolkit"', proc.stdout)


if __name__ == "__main__":
    unittest.main()
