import tempfile
import unittest
from pathlib import Path

from scripts.check_links import app_routes, check_links, extract_links


class LinkCheckerTests(unittest.TestCase):
    def test_extract_links_from_markdown_and_jsx(self):
        text = """
        [PitWall](https://github.com/ShreyTriesToCode/PitWall)
        <a href="/predictions?target=race">Race</a>
        <Link href="/model">Model</Link>
        """
        self.assertIn("https://github.com/ShreyTriesToCode/PitWall", extract_links(text))
        self.assertIn("/predictions?target=race", extract_links(text))
        self.assertIn("/model", extract_links(text))

    def test_internal_routes_are_discovered(self):
        routes = app_routes()
        self.assertIn("/", routes)
        self.assertIn("/predictions", routes)
        self.assertIn("/api/predictions", routes)

    def test_missing_internal_route_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "frontend" / "app" / "predictions").mkdir(parents=True)
            (root / "frontend" / "app" / "predictions" / "page.jsx").write_text("export default function Page() { return null; }", encoding="utf-8")
            (root / "README.md").write_text("[bad](/missing-route)\n[good](/predictions)", encoding="utf-8")

            findings = check_links(root=root)

        self.assertEqual(len([item for item in findings if item.status == "error"]), 1)
        self.assertIn("/missing-route", findings[0].link)


if __name__ == "__main__":
    unittest.main()
