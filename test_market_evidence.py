"""Deterministic evidence/selection tests; no network or credentials required."""
import importlib
import unittest
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

from market_evidence import event_reactions, history_adjustment, price_metrics, base_score


def prices(start, count, step=1.0, skip=()):
    rows = []
    day = start
    while len(rows) < count:
        if day.weekday() < 5 and day not in skip:
            stamp = datetime.combine(day, datetime.min.time(), timezone.utc).timestamp()
            rows.append((stamp, 100 + step * len(rows)))
        day += timedelta(days=1)
    return rows


def event(day, identifier="event", theme="rate_cuts"):
    return {"id": identifier, "date": day, "title": "Historical event",
            "theme": theme, "source_url": "https://www.federalreserve.gov/example"}


def example(day, excess, identifier="event", theme="rate_cuts"):
    end = (date.fromisoformat(day) + timedelta(days=28)).isoformat()
    return {**event(day, identifier, theme),
            "windows": {"20": {"start": day, "end": end, "excess_pct": excess}}}


def headlines(theme="rate_cuts", publishers=("Publisher One", "Publisher Two")):
    return [{"publisher": p, "themes": [theme], "event_match_themes": [theme]}
            for p in publishers]


class EventReactionTests(unittest.TestCase):
    def setUp(self):
        self.rows = prices(date(2024, 1, 2), 80)
        self.benchmark = prices(date(2024, 1, 2), 80, step=2)

    def test_weekend_uses_next_session_and_exact_five_twenty_windows(self):
        report = event_reactions(self.rows, self.benchmark, [event("2024-01-06")])
        self.assertEqual(report["omitted_event_ids"], [])
        windows = report["comparisons"][0]["windows"]
        self.assertEqual(windows["5"]["start"], "2024-01-08")
        self.assertEqual(windows["5"]["end"], "2024-01-15")
        self.assertEqual(windows["20"]["end"], "2024-02-05")
        self.assertAlmostEqual(windows["5"]["return_pct"], round((109 / 104 - 1) * 100, 2))
        self.assertAlmostEqual(windows["20"]["return_pct"], round((124 / 104 - 1) * 100, 2))
        self.assertAlmostEqual(windows["5"]["benchmark_pct"], round((118 / 108 - 1) * 100, 2))
        self.assertAlmostEqual(windows["5"]["excess_pct"], round(((109 / 104) - (118 / 108)) * 100, 2))

    def test_events_outside_history_and_incomplete_horizon_are_omitted(self):
        final_day = datetime.fromtimestamp(self.rows[-1][0], timezone.utc).date().isoformat()
        report = event_reactions(self.rows, self.benchmark, [
            event("2008-09-15", "too_old"), event("2099-01-01", "future"),
            event(final_day, "incomplete"),
        ])
        self.assertEqual(report["comparisons"], [])
        self.assertEqual(set(report["omitted_event_ids"]), {"too_old", "future", "incomplete"})

    def test_holiday_uses_next_available_close(self):
        holiday = date(2024, 1, 15)
        rows = prices(date(2024, 1, 2), 80, skip=(holiday,))
        benchmark = prices(date(2024, 1, 2), 80, step=2, skip=(holiday,))
        windows = event_reactions(rows, benchmark, [event(holiday.isoformat())])["comparisons"][0]["windows"]
        self.assertEqual(windows["5"]["start"], "2024-01-16")
        self.assertEqual(windows["5"]["end"], "2024-01-23")
        self.assertEqual(windows["20"]["end"], "2024-02-13")
        self.assertEqual(windows["5"]["return_pct"], round((114 / 109 - 1) * 100, 2))
        self.assertEqual(windows["20"]["return_pct"], round((129 / 109 - 1) * 100, 2))

    def test_missing_week_of_prices_is_not_silently_bridged(self):
        rows = [row for row in self.rows
                if not date(2024, 1, 10) <= datetime.fromtimestamp(row[0], timezone.utc).date() <= date(2024, 1, 19)]
        report = event_reactions(rows, self.benchmark, [event("2024-01-08")])
        self.assertEqual(report["comparisons"], [])
        self.assertEqual(report["omitted_event_ids"], ["event"])

    def test_isolated_missing_price_cannot_shift_the_twenty_session_window(self):
        missing = datetime(2024, 1, 10, tzinfo=timezone.utc).timestamp()
        rows = [row for row in self.rows if row[0] != missing]
        report = event_reactions(rows, self.benchmark, [event("2024-01-08")])
        self.assertEqual(report["comparisons"], [])
        self.assertEqual(report["omitted_event_ids"], ["event"])

    def test_benchmark_requires_same_exact_start_and_end_dates(self):
        end = datetime(2024, 2, 5, tzinfo=timezone.utc).timestamp()
        benchmark = [row for row in self.benchmark if row[0] != end]
        report = event_reactions(self.rows, benchmark, [event("2024-01-06")])
        self.assertEqual(report["comparisons"], [])
        self.assertEqual(report["omitted_event_ids"], ["event"])

    def test_empty_prices_produce_no_comparison(self):
        report = event_reactions([], [], [event("2024-01-06")])
        self.assertEqual(report["comparisons"], [])
        self.assertEqual(report["omitted_event_ids"], ["event"])

    def test_missing_benchmark_horizon_cannot_supply_two_rank_events(self):
        report = event_reactions(self.rows, self.benchmark[:40], [
            event("2024-01-08", "covered"), event("2024-03-18", "uncovered"),
        ])
        uncovered = next(row for row in report["comparisons"] if row["id"] == "uncovered")
        self.assertIsNone(uncovered["windows"]["20"]["benchmark_pct"])
        self.assertIsNone(uncovered["windows"]["20"]["excess_pct"])
        result = history_adjustment(report, headlines())
        self.assertEqual(result["status"], "insufficient")
        self.assertEqual(result["value"], 0)

    def test_no_benchmark_displays_history_without_excess_or_adjustment(self):
        report = event_reactions(self.rows, [], [
            event("2024-01-08", "first"), event("2024-03-18", "second"),
        ])
        self.assertEqual(len(report["comparisons"]), 2)
        for comparison in report["comparisons"]:
            for window in comparison["windows"].values():
                self.assertIsNone(window["benchmark_pct"])
                self.assertIsNone(window["excess_pct"])
                self.assertIsNotNone(window["return_pct"])
        self.assertEqual(history_adjustment(report, headlines())["value"], 0)


class HistoricalAdjustmentTests(unittest.TestCase):
    def independent(self, excess=5):
        return {"comparisons": [example("2020-01-01", excess, "a"),
                                example("2020-03-01", excess, "b")]}

    def test_two_independent_events_and_two_topic_publishers_are_required(self):
        one_event = {"comparisons": self.independent()["comparisons"][:1]}
        self.assertEqual(history_adjustment(one_event, headlines())["status"], "insufficient")
        same_publisher = headlines(publishers=("Publisher One", "publisher one"))
        self.assertEqual(history_adjustment(self.independent(), same_publisher)["status"], "insufficient")
        unrelated = headlines("bank_stress")
        self.assertEqual(history_adjustment(self.independent(), unrelated)["status"], "insufficient")
        result = history_adjustment(self.independent(), headlines())
        self.assertEqual(result["status"], "applied")
        self.assertAlmostEqual(result["value"], .005)
        self.assertEqual(result["groups"][0]["events"], 2)

    def test_close_events_are_not_counted_as_independent(self):
        history = {"comparisons": [example("2020-01-01", 5, "a"),
                                   example("2020-01-20", 5, "b")]}
        self.assertEqual(history_adjustment(history, headlines())["status"], "insufficient")

    def test_actual_overlapping_windows_are_not_independent_after_45_days(self):
        history = self.independent()
        history["comparisons"][0]["windows"]["20"]["end"] = "2020-03-15"
        result = history_adjustment(history, headlines())
        self.assertEqual(result["status"], "insufficient")
        self.assertEqual(result["value"], 0)

    def test_speculative_second_publisher_is_not_corroboration(self):
        articles = headlines()
        articles[1]["event_match_themes"] = []
        result = history_adjustment(self.independent(), articles)
        self.assertEqual(result["status"], "insufficient")
        self.assertEqual(result["value"], 0)

    def test_contradictory_topics_do_not_adjust_rank(self):
        history = self.independent(5)
        history["comparisons"] += [example("2021-01-01", -5, "c", "rate_hikes"),
                                   example("2021-03-01", -5, "d", "rate_hikes")]
        result = history_adjustment(history, headlines() + headlines("rate_hikes"))
        self.assertEqual(result["status"], "conflicting")
        self.assertEqual(result["value"], 0)
        self.assertEqual(len(result["groups"]), 2)

    def test_adjustment_is_capped_at_one_score_point(self):
        for excess, expected in [(80, .01), (-80, -.01)]:
            with self.subTest(excess=excess):
                self.assertEqual(history_adjustment(self.independent(excess), headlines())["value"], expected)

    def test_missing_benchmark_is_not_rank_evidence(self):
        self.assertEqual(history_adjustment(self.independent(None), headlines())["status"], "insufficient")


class MarketScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recs = importlib.import_module("market_recs")

    def setUp(self):
        today = datetime.now(timezone.utc).date()
        recent = prices(today - timedelta(days=500), 350)
        self.rows = [r for r in recent if datetime.fromtimestamp(r[0], timezone.utc).date() < today]
        # Ensure that there is a fresh completed session for every test calendar date.
        day = datetime.fromtimestamp(self.rows[-1][0], timezone.utc).date() + timedelta(days=1)
        while day < today:
            if day.weekday() < 5:
                self.rows.append((datetime.combine(day, datetime.min.time(), timezone.utc).timestamp(), 100 + len(self.rows)))
            day += timedelta(days=1)
        self.news = {"status": "unavailable", "generated_at": None, "items": []}
        self.evidence = {"status": "unavailable", "headlines": [], "events": []}

    def screen(self, profile, history=None):
        with patch.object(self.recs, "_fetch_history", return_value=self.rows if history is None else history), \
             patch.object(self.recs, "_news_snapshot", return_value=self.news), \
             patch.object(self.recs.news_evidence, "evidence_for", return_value=self.evidence):
            return self.recs.screen(profile, 60)

    def test_area_suggestions_are_funds_and_report_news_missing(self):
        result = self.screen({"scope": "areas", "horizon": "3-10y"})
        self.assertEqual(len(result["items"]), 5)
        self.assertTrue(all(item["kind"] != "stock" for item in result["items"]))
        self.assertEqual(len({item["area"] for item in result["items"]}), 5)
        for item in result["items"]:
            self.assertTrue(any("prices alone" in c for c in item["cautions"]))
            self.assertEqual(item["history_adjustment"]["value"], 0)
            self.assertEqual(item["score_breakdown"]["news_history"], 0)
            self.assertTrue(item["justification"])

    def test_short_horizon_remains_restricted_despite_news(self):
        result = self.screen({"scope": "specific", "horizon": "<1y"})
        self.assertEqual([i["symbol"] for i in result["items"]], ["SHY"])

    def test_one_report_and_one_speculative_snapshot_do_not_adjust_rank(self):
        now = datetime.now(timezone.utc)
        published = (now - timedelta(hours=1)).isoformat()
        snapshot = {"status": "ok", "generated_at": published, "items": [
            {"id": "reported", "title": "Fed cuts interest rates as markets rise",
             "publisher": "Publisher One", "url": "https://example.com/reported",
             "published_at": published, "query_ids": ["market"]},
            {"id": "speculative", "title": "Fed cuts interest rates? Traders weigh policy outlook",
             "publisher": "Publisher Two", "url": "https://example.org/speculative",
             "published_at": published, "query_ids": ["market"]},
        ]}
        start = date(2018, 1, 2)
        rows = [row for row in prices(start, (now.date() - start).days)
                if datetime.fromtimestamp(row[0], timezone.utc).date() < now.date()]
        benchmark = [(stamp, 100.0) for stamp, _ in rows]
        with patch.object(self.recs, "_fetch_history", side_effect=lambda symbol: benchmark if symbol == "SPY" else rows), \
             patch.object(self.recs, "_news_snapshot", return_value=snapshot), \
             patch.object(self.recs.requests, "get", side_effect=AssertionError("Unexpected network call")):
            result = self.recs.screen({"scope": "specific", "horizon": "3-10y"}, 60)
        self.assertTrue(result["items"])
        for item in result["items"]:
            self.assertEqual(len(item["news"]["headlines"]), 2)
            self.assertGreaterEqual(len(item["history"]["comparisons"]), 2)
            self.assertEqual(item["history_adjustment"]["status"], "insufficient")
            self.assertEqual(item["score_breakdown"]["news_history"], 0)

    def test_outage_does_not_invent_recommendations(self):
        result = self.screen({"scope": "specific"}, history=[])
        self.assertEqual(result["items"], [])
        self.assertEqual(result["available"], 0)

    def test_future_series_are_not_current_market_evidence(self):
        future = prices(datetime.now(timezone.utc).date() + timedelta(days=2), 250)
        result = self.screen({"scope": "specific"}, history=future)
        self.assertEqual(result["items"], [])
        self.assertEqual(result["market_behavior"], [])

    def test_shared_base_score_matches_disclosed_components(self):
        result = self.screen({"scope": "specific", "horizon": "3-10y"})
        expected = round(base_score(price_metrics(self.rows), 60) * 100, 3)
        for item in result["items"]:
            self.assertEqual(item["score_breakdown"]["price_risk"], expected)


class HistoryParsingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.recs = importlib.import_module("market_recs")

    def setUp(self):
        self.rows = prices(date(2023, 1, 2), 220)
        self.now = datetime(2024, 12, 10, 16, tzinfo=timezone.utc)

    def history(self, rows, granularity="1d"):
        fixed_now = self.now

        class FixedDatetime(datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed_now.astimezone(tz) if tz else fixed_now.replace(tzinfo=None)

        payload = {"chart": {"result": [{
            "meta": {"dataGranularity": granularity},
            "timestamp": [stamp for stamp, _ in rows],
            "indicators": {"adjclose": [{"adjclose": [value for _, value in rows]}]},
        }]}}
        with patch.object(self.recs.requests, "get") as request, \
             patch.object(self.recs, "datetime", FixedDatetime), \
             patch.dict(self.recs._cache, {}, clear=True):
            request.return_value.json.return_value = payload
            return self.recs._history("TEST", "max")

    def test_history_sorts_and_deduplicates_sessions(self):
        rows = list(reversed(self.rows)) + [self.rows[40], self.rows[100]]
        self.assertEqual(self.history(rows), self.rows)

    def test_history_rejects_silently_monthly_data(self):
        with self.assertRaisesRegex(ValueError, "Daily price interval required"):
            self.history(self.rows, granularity="1mo")

    def test_history_keeps_latest_bar_for_a_duplicated_session(self):
        latest = (self.rows[40][0] + 3600, 200.0)
        expected = self.rows[:40] + [latest] + self.rows[41:]
        self.assertEqual(self.history([latest] + list(reversed(self.rows))), expected)

    def test_duplicates_do_not_count_toward_minimum_history(self):
        with self.assertRaisesRegex(ValueError, "Insufficient price history"):
            self.history(self.rows[:150] + self.rows[:150])

    def test_history_skips_malformed_rows_without_discarding_valid_history(self):
        stamp = self.rows[0][0] + 3600
        malformed = [(None, 100), ("invalid", 100), (float("nan"), 100),
                     (float("inf"), 100), (1e30, 100),
                     (stamp, None), (stamp, "invalid"), (stamp, float("nan")),
                     (stamp, float("inf")), (stamp, 0), (stamp, -1)]
        self.assertEqual(self.history(self.rows + malformed), self.rows)

    def test_history_rejects_future_sessions_even_after_current_close(self):
        self.now = self.now.replace(hour=23)
        future = [(self.now.timestamp() + 86400, 999.0),
                  (self.now.timestamp() + 864000, 1000.0)]
        self.assertEqual(self.history(future[:1] + self.rows + future[1:]), self.rows)

    def test_history_drops_incomplete_current_session_in_any_position(self):
        current = (self.now.replace(hour=14, minute=30).timestamp(), 500.0)
        self.assertEqual(self.history([current] + self.rows + [current]), self.rows)

    def test_history_keeps_completed_current_session(self):
        self.now = self.now.replace(hour=23)
        current = (self.now.replace(hour=14, minute=30).timestamp(), 500.0)
        self.assertEqual(self.history([current] + self.rows), self.rows + [current])


if __name__ == "__main__":
    unittest.main()
