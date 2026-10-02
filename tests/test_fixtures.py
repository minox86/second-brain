import unittest

from helpers import ROOT
from sb_core.validate import validate
from sb_core.wiki import Wiki

FIXTURE = ROOT / "tests" / "fixtures" / "sample-wiki"


class SampleWikiTest(unittest.TestCase):
    def test_sample_wiki_is_valid(self):
        wiki = Wiki(FIXTURE)
        self.assertEqual([i.to_dict() for i in validate(wiki)], [])
        self.assertGreaterEqual(len(wiki.pages()), 8)
        self.assertIn("conf-eng", wiki.sources)


if __name__ == "__main__":
    unittest.main()
