"""Run from the devsheets folder:  python3 -m unittest discover -s tests -v"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import main  # noqa: E402
from services import loader, search  # noqa: E402


class DataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cats, cls.problems = loader.load_all()

    def test_all_sheets_valid(self):
        self.assertEqual(self.problems, [])

    def test_ten_menus_in_order(self):
        self.assertEqual([c["menu"] for c in self.cats], list(range(1, 11)))

    def test_every_terminal_step_has_a_directory(self):
        for cat in self.cats:
            for e in cat["entries"]:
                for i, s in enumerate(e["steps"], 1):
                    if s["shell"] in loader.TERMINAL_SHELLS:
                        self.assertTrue(s.get("dir") or e.get("where"), f"{e['id']} step {i}")

    def test_required_search_phrases(self):
        expected = {
            "react routes": "router-setup",
            "change heading": "change-text",
            "clone repository": "git-clone",
            "ssh key": "ssh-generate",
            "npm install": "npm-install-ci",
            "vite not found": "err-vite-not-found",
            "typescript setup": "ts-new-project",
        }
        for query, entry_id in expected.items():
            ids = [e["id"] for e, _ in search.search(self.cats, query)]
            self.assertIn(entry_id, ids[:3], f"{query!r} -> {ids[:5]}")

    def test_copy_logic(self):
        entry = loader.find_by_id(self.cats, "git-clone")
        self.assertIsNotNone(main.copy_payload(entry, "")[1])          # ambiguous -> asks for a step
        self.assertEqual(main.copy_payload(entry, "1")[0], "git clone https://github.com/USERNAME/REPO.git")
        self.assertIsNotNone(main.copy_payload(entry, "99")[1])
        agent = loader.find_by_id(self.cats, "ssh-agent")
        self.assertIsNotNone(main.copy_payload(agent, "1-2")[1])        # bash + powershell mixed

    def test_bad_file_is_skipped_not_fatal(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            Path(d, "bad.json").write_text("{not json")
            Path(d, "ok.json").write_text('{"menu": 1, "menu_title": "X", "entries": ['
                                          '{"id": "a", "title": "A", "summary": "s",'
                                          ' "steps": [{"shell": "any", "code": ["ls"]}]}]}')
            cats, problems = loader.load_all(d)
            self.assertEqual(len(cats[0]["entries"]), 1)
            self.assertEqual(len(problems), 1)


if __name__ == "__main__":
    unittest.main()
