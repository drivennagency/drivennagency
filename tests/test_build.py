"""Tests voor scripts/build_content.py. Draaien met: python3 -m unittest discover -s tests"""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_content as bc  # noqa: E402

TITLE_KEYS = ("titel", "title")


def own_title(data, lang):
    own = data.get(lang) or {}
    return next((own[k] for k in TITLE_KEYS if own.get(k)), None)


class ContentPerTaal(unittest.TestCase):
    """Elke taal moet zijn eigen vertaling tonen, ook als de veldnamen per taal verschillen."""

    def test_blogs_gebruiken_eigen_taal(self):
        posts = {p["slug"]: p for p in bc.load_posts()}
        for f in sorted((ROOT / "content" / "blog").glob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            slug = bc._shared(data, "slug") or f.stem
            for lang in bc.ACTIVE:
                own = data.get(lang) or {}
                expected = own_title(data, lang)
                if expected:
                    self.assertEqual(posts[slug]["lang"][lang]["title"], expected, f"{f.name} [{lang}] titel")
                summary = bc._first(own, bc.BLOG_SUMMARY)
                if summary:
                    self.assertEqual(posts[slug]["lang"][lang]["summary"], summary, f"{f.name} [{lang}] samenvatting")
                body = bc._first(own, bc.BLOG_BODY)
                if body:
                    self.assertEqual(posts[slug]["lang"][lang]["body"], body, f"{f.name} [{lang}] tekst")

    def test_reserve_is_nederlands(self):
        data = {"nl": {"titel": "NL titel", "samenvatting": "NL kort", "tekst": "NL tekst", "date": "2026-01-01"},
                "en": {"title": "EN title"}}
        nl = data["nl"]
        own = data["en"]
        self.assertEqual(bc._first(own, ("titel", "title")), "EN title")
        self.assertEqual(bc._first(own, bc.BLOG_SUMMARY) or bc._first(nl, bc.BLOG_SUMMARY), "NL kort")

    def test_gegenereerde_blogpaginas_hebben_juiste_h1(self):
        for f in sorted((ROOT / "content" / "blog").glob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            slug = bc._shared(data, "slug") or f.stem
            for lang in bc.ACTIVE:
                expected = own_title(data, lang)
                if not expected:
                    continue
                page = bc.lang_dir(lang) / "blog" / f"{slug}.html"
                h1 = re.search(r"<h1[^>]*>(.*?)</h1>", page.read_text(encoding="utf-8"), re.S).group(1)
                self.assertEqual(bc.html.unescape(re.sub(r"<[^>]+>", "", h1)).strip(), expected.strip(),
                                 f"{page.relative_to(ROOT)}")


class Hulpfuncties(unittest.TestCase):
    def test_page_url(self):
        self.assertEqual(bc.page_url("nl", "index.html"), "/")
        self.assertEqual(bc.page_url("en", "index.html"), "/eng/")
        self.assertEqual(bc.page_url("de", "blog.html"), "/de/blog.html")

    def test_absolutize(self):
        out = bc.absolutize('<a href="../contact.html">x</a><img src="../assets/logo/logo-transparant-wit.png">'
                            '<a href="#top">t</a><a href="https://example.com/">e</a>'
                            '<a href="mailto:info@drivennagency.nl">m</a><a href="../index.html">h</a>', "eng/blog")
        self.assertIn('href="/eng/contact.html"', out)
        self.assertIn('src="/eng/assets/logo/logo-transparant-wit.png"', out)
        self.assertIn('href="#top"', out)
        self.assertIn('href="https://example.com/"', out)
        self.assertIn('href="mailto:info@drivennagency.nl"', out)
        self.assertIn('href="/eng/"', out, "index.html wordt de map zelf")

    def test_stylesheet_krijgt_versie(self):
        self.assertRegex(bc.absolute_url("/assets/css/style.css", ""), r"^/assets/css/style\.css\?v=[0-9a-f]{10}$")

    def test_markdown_escaped_html(self):
        out = bc.md("Tekst met <script>alert(1)</script> en **vet**")
        self.assertNotIn("<script>", out)
        self.assertIn("<strong>vet</strong>", out)

    def test_paginatitel_niet_te_lang(self):
        lang_title = "Een heel lange blogtitel die eigenlijk al bijna te lang is voor Google"
        self.assertLessEqual(len(bc.page_title(lang_title)), max(bc.TITLE_MAX, len(lang_title)))


class Idempotent(unittest.TestCase):
    def test_build_is_up_to_date(self):
        """De pagina's in de repo moeten overeenkomen met wat het script nu zou maken."""
        self.assertEqual(bc.main(["--check"]), 0)


if __name__ == "__main__":
    unittest.main()
