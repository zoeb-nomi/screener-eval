#!/usr/bin/env python3
"""
Unit tests for scripts.run_screen.extract_json (formerly parse_strict_json).

extract_json must never raise — on anything it can't parse it returns None, so
callers in run_screen.py / analysis/pilot.py can retry once and then record a
parse_error instead of crashing the whole pipeline (see the bug this fixes:
gpt-5-mini's hidden reasoning tokens eating the output budget and leaving an
empty response, which used to raise json.decoder.JSONDecodeError).

Usage:
    python3 -m unittest tests/test_extract_json.py -v
    python3 -m pytest tests/test_extract_json.py -v   # if pytest is installed
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_screen import extract_json  # noqa: E402


class TestExtractJson(unittest.TestCase):
    def test_clean_json(self):
        self.assertEqual(extract_json('{"fit_score": 72, "recommendation": "advance"}'),
                          {"fit_score": 72, "recommendation": "advance"})

    def test_fenced_json_with_language_tag(self):
        text = '```json\n{"fit_score": 55, "recommendation": "hold"}\n```'
        self.assertEqual(extract_json(text), {"fit_score": 55, "recommendation": "hold"})

    def test_fenced_json_without_language_tag(self):
        text = '```\n{"fit_score": 40}\n```'
        self.assertEqual(extract_json(text), {"fit_score": 40})

    def test_leading_prose_then_json(self):
        text = 'Sure, here is my assessment:\n{"fit_score": 61, "recommendation": "advance"}'
        self.assertEqual(extract_json(text), {"fit_score": 61, "recommendation": "advance"})

    def test_leading_and_trailing_prose(self):
        text = 'Here you go:\n{"fit_score": 61}\nLet me know if you need anything else.'
        self.assertEqual(extract_json(text), {"fit_score": 61})

    def test_empty_string(self):
        self.assertIsNone(extract_json(""))

    def test_none_input(self):
        self.assertIsNone(extract_json(None))

    def test_whitespace_only(self):
        self.assertIsNone(extract_json("   \n  "))

    def test_truncated_json(self):
        # e.g. the model's output got cut off mid-object by the token budget.
        text = '{"fit_score": 61, "recommendation": "advance", "top_reasons": ["a", "b"'
        self.assertIsNone(extract_json(text))

    def test_no_braces_at_all(self):
        self.assertIsNone(extract_json("I cannot assess this résumé."))

    def test_never_raises_on_garbage(self):
        # Should return None, not raise, for arbitrary junk.
        for junk in ["{}}}}", "{{{{{", "not json { at all", "```json```", "{"]:
            with self.subTest(junk=junk):
                self.assertIsNone(extract_json(junk))


if __name__ == "__main__":
    unittest.main()
