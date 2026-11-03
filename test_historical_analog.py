import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

# No real AI connector, configuration, or credentials are imported by these tests.
sys.modules["ai_client"] = types.SimpleNamespace(ask_json=lambda *a, **k: None)
spec = importlib.util.spec_from_file_location("historical_analog_review", Path(__file__).with_name("historical_analog.py"))
ha = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ha)


class HistoricalEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)
        self.items = [
            {"title": "Central bank raises rates", "url": "https://example.org/a", "src": "Publisher A",
             "published_at": (self.now - timedelta(hours=1)).isoformat(), "via": "news"},
            {"title": "Bond yields rise after rate announcement", "url": "https://example.net/b", "src": "Publisher B",
             "published_at": (self.now - timedelta(hours=2)).isoformat(), "via": "news"},
        ]

    def snapshot(self, items=None):
        return {"generated": self.now.isoformat(), "assets": {"rates": {"top": items or self.items}}}

    def test_news_requires_fresh_dated_safe_sources_and_deduplicates(self):
        items = self.items + [dict(self.items[0]),
            {**self.items[0], "title": "future", "published_at": (self.now + timedelta(seconds=1)).isoformat()},
            {**self.items[0], "title": "old", "published_at": (self.now - timedelta(days=4)).isoformat()},
            {**self.items[0], "title": "missing date", "published_at": None},
            {**self.items[0], "title": "unsafe URL", "url": "javascript:alert(1)"},
            {**self.items[0], "title": "social", "via": "social"},
        ]
        fresh = ha._fresh_headlines(self.snapshot(items), self.now)
        self.assertEqual(len(fresh), 2)
        self.assertTrue(all(x["url"].startswith("https://") and x["published_at"] for x in fresh))

    def test_stale_or_future_snapshot_abstains(self):
        for delta in (timedelta(hours=-2), timedelta(seconds=1)):
            doc = self.snapshot()
            doc["generated"] = (self.now + delta).isoformat()
            self.assertEqual(ha._fresh_headlines(doc, self.now), [])

    def test_curve_uses_covered_prior_points_and_reports_actual_dates(self):
        catalog = {"strategies": [{"id": "s", "name": "Strategy", "curve": [
            {"t": "2023-01-01", "v": 100}, {"t": "2023-02-01", "v": 110},
            {"t": "2023-03-01", "v": 120}, {"t": "2023-04-01", "v": 130},
            {"t": "2023-05-01", "v": 140}]}]}
        with patch.object(ha, "_load", return_value=catalog):
            reaction = ha._strategy_reactions("2023-01-15")["s"]
            self.assertEqual(reaction["start_date"], "2023-01-01")
            self.assertEqual(reaction["end_date"], "2023-04-01")
            self.assertEqual(reaction["pct"], 30)
            self.assertTrue(reaction["approximate"])
            self.assertEqual(ha._strategy_reactions("2022-12-31"), {})
            self.assertEqual(ha._strategy_reactions("2023-03-01"), {})

    def test_no_extrapolation_or_large_gap(self):
        points = ha._curve_points([{"t": "2023-01-01", "v": 100}, {"t": "2023-07-01", "v": 110}])
        self.assertIsNone(ha._at_or_before(points, datetime(2023, 3, 1).date()))
        self.assertIsNone(ha._at_or_before(points, datetime(2023, 8, 1).date()))

    def test_model_can_abstain_and_cannot_invent_sources(self):
        headlines = ha._fresh_headlines(self.snapshot(), self.now)
        events = [{"id": "rates", "date": "2023-01-15", "title": "Rate event", "summary": "Rate increase"}]
        valid = {"event_id": "rates", "similarity": .8, "evidence_ids": ["h0", "h1"], "reason": "Shared mechanism; different context."}
        with patch.object(ha, "_events", return_value=events):
            for invalid in ({**valid, "event_id": None}, {**valid, "similarity": .3},
                            {**valid, "similarity": float("nan")},
                            {**valid, "evidence_ids": ["h0", "invented"]},
                            {**valid, "evidence_ids": ["h0", "h0"]}):
                with patch.object(ha.ai_client, "ask_json", return_value=invalid):
                    self.assertIsNone(ha._pick_analog(headlines))
            with patch.object(ha.ai_client, "ask_json", return_value=valid):
                self.assertEqual(ha._pick_analog(headlines)["evidence_ids"], ["h0", "h1"])

    def test_old_cache_without_source_evidence_rejected(self):
        with patch.object(ha, "_load", return_value={"generated": datetime.now(timezone.utc).isoformat()}):
            self.assertIsNone(ha.read_latest())

    def test_analysis_persists_only_cited_evidence_and_source_timestamp(self):
        now = datetime.now(timezone.utc)
        items = [{**item, "published_at": (now - timedelta(hours=1)).isoformat()} for item in self.items]
        snapshot = {"generated": now.isoformat(), "assets": {"rates": {"top": items}}}
        event = {"id": "rates", "date": "2023-01-15", "title": "Rate event", "summary": "Rate increase"}
        match = {"event_id": "rates", "similarity": .8, "evidence_ids": ["h0", "h1"], "reason": "Shared mechanism."}
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(ha, "OUT", str(Path(directory) / "analog.json")), \
                patch.object(ha, "_load", return_value=snapshot), \
                patch.object(ha, "_events", return_value=[event]), \
                patch.object(ha, "_pick_analog", return_value=match), \
                patch.object(ha, "_strategy_reactions", return_value={"s": {"pct": 2, "approximate": True}}):
            result = ha.analyze()
            saved = json.loads(Path(ha.OUT).read_text())
            self.assertEqual(saved, result)
            self.assertEqual(saved["source_generated"], snapshot["generated"])
            self.assertEqual(len(saved["headlines"]), 2)
            self.assertTrue(all(item["url"] and item["published_at"] for item in saved["headlines"]))
            self.assertFalse(saved["similarity_is_probability"])


if __name__ == "__main__":
    unittest.main()
