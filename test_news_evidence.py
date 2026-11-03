import unittest
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from unittest.mock import patch
from xml.sax.saxutils import escape

import news_evidence as news


NOW = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)


def rss(*rows):
    body = "".join(
        "<item><title>{}</title><link>{}</link><pubDate>{}</pubDate>"
        '<source url="https://example.com">{}</source></item>'.format(
            escape(title), escape(url), escape(date), escape(publisher))
        for title, url, date, publisher in rows
    )
    return ("<rss><channel>" + body + "</channel></rss>").encode()


def article(title, publisher="Publisher A", age=1, url=None):
    url = url or "https://news.google.com/rss/articles/" + str(abs(hash(title)))
    rows, _ = news._parse_feed(rss((title, url, format_datetime(NOW - timedelta(hours=age)), publisher)), "test", NOW)
    return rows[0]


class NewsEvidenceTests(unittest.TestCase):
    def setUp(self):
        news._cache = None
        news._cache_time = 0

    def test_requires_dated_fresh_nonfuture_items_and_safe_links(self):
        rows = [
            ("Nvidia earnings rise", "https://example.com/fresh", format_datetime(NOW - timedelta(hours=1)), "A"),
            ("Nvidia old news", "https://example.com/old", format_datetime(NOW - timedelta(hours=73)), "A"),
            ("Nvidia future news", "https://example.com/future", format_datetime(NOW + timedelta(seconds=1)), "A"),
            ("Nvidia undated", "https://example.com/undated", "", "A"),
            ("Nvidia unsafe link", "javascript:alert(1)", format_datetime(NOW), "A"),
        ]
        parsed, rejected = news._parse_feed(rss(*rows), "test", NOW)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(rejected, 4)
        self.assertEqual(parsed[0]["symbols"], ["NVDA"])

    def test_opposing_events_are_not_conflated(self):
        self.assertEqual(news.classify_themes("Fed cuts interest rates as stocks rise"), ["rate_cuts"])
        self.assertEqual(news.classify_themes("Federal Reserve raises rates"), ["rate_hikes"])
        self.assertEqual(news.classify_themes("Fed rate cut and Fed rate hike debate"), [])
        self.assertEqual(news.classify_themes("Fed rules out rate cuts"), [])
        self.assertEqual(news.classify_themes("Fed will not cut rates"), [])
        self.assertEqual(news.classify_themes("ECB cuts rates while Fed holds steady"), [])
        self.assertEqual(news.classify_themes("Oil supply disruption hits markets"), ["oil_supply_disruption"])
        self.assertEqual(news.classify_themes("Oil surplus weighs on crude prices"), ["oil_surplus"])
        self.assertEqual(news.classify_themes("Inflation cools as oil surplus grows"), ["inflation_cooling", "oil_surplus"])

    def test_sector_news_is_not_company_evidence_and_no_forced_analogue(self):
        snapshot = {"status": "ok", "generated_at": news._iso(NOW), "items": [
            article("Technology stocks rise on semiconductor demand"),
            article("Nvidia launches new chips"),
        ]}
        evidence = news.evidence_for("AAPL", "Technology", snapshot, now=NOW)
        self.assertEqual(evidence["company_headline_count"], 0)
        self.assertEqual({row["scope"] for row in evidence["headlines"]}, {"area"})
        self.assertEqual(evidence["events"], [])
        nvidia = news.evidence_for("NVDA", "Technology", snapshot, now=NOW)
        self.assertEqual(nvidia["company_headline_count"], 1)

    def test_rate_history_requires_positive_occurrence_not_bare_topic(self):
        excluded = (
            "Fed rate cuts ruled out as inflation rises",
            "Fed rate cut off the table as inflation rises",
            "Fed rate cuts on hold until next year",
            "Fed rate cuts seen next year",
            "Fed rate cut pricing rises after weak jobs data",
            "Fed rate hikes seen after inflation surprise",
            "Fed rate hikes on hold amid uncertainty",
            "Fed rate cut boosts investor confidence",
            "If Fed cuts rates, stocks could rally",
            "Fed cuts rates in a hypothetical scenario",
            "Fed cuts rates when inflation cools",
        )
        for title in excluded:
            with self.subTest(title=title):
                classified = news._classify(title)
                self.assertFalse(classified["historical_support_eligible"])
                self.assertEqual(classified["event_ids"], [])
                self.assertEqual(classified["event_match_themes"], [])
        for title, theme in (
            ("Fed cuts interest rates in surprise move", "rate_cuts"),
            ("Federal Reserve has lowered rates", "rate_cuts"),
            ("Fed announced a rate cut as stocks rise", "rate_cuts"),
            ("Fed approves a rate hike", "rate_hikes"),
            ("Fed raises its policy rate", "rate_hikes"),
        ):
            with self.subTest(title=title):
                self.assertEqual(news._classify(title)["event_match_themes"], [theme])

    def test_war_resolution_does_not_support_invasion_analogue(self):
        for title in (
            "Russia-Ukraine war ends as ceasefire begins",
            "Russia-Ukraine war: peace agreement signed",
            "Russia-Ukraine war moves toward de-escalation",
            "Russia-Ukraine war ends after troop withdrawal",
        ):
            with self.subTest(title=title):
                self.assertEqual(news._classify(title)["event_ids"], [])
                self.assertFalse(news._classify(title)["historical_support_eligible"])
        self.assertEqual(news._classify("Russia invades Ukraine in military invasion")["event_ids"],
                         ["russia_invasion_2022"])

    def test_fresh_context_links_only_reported_topics_and_distinct_publishers(self):
        snapshot = {"status": "ok", "generated_at": news._iso(NOW), "items": [
            article("Fed cuts rates as markets rally", "A"),
            article("Fed lowers interest rates and bond prices climb", "B"),
            article("Fed rate cut expected next month", "C"),
            article("Fed rate cut in 2024: looking back", "D"),
        ]}
        evidence = news.evidence_for("TLT", "Bonds", snapshot, now=NOW)
        self.assertEqual(len(evidence["events"]), 3)
        self.assertTrue(all(event["theme"] == "rate_cuts" for event in evidence["events"]))
        self.assertEqual(evidence["theme_support"]["rate_cuts"]["publisher_count"], 2)
        self.assertEqual(evidence["theme_support"]["rate_cuts"]["headline_count"], 2)

    def test_dedupe_title_and_url_cannot_inflate_support(self):
        first = article("Fed cuts rates as markets rally", "A", url="https://example.com/a")
        second = article("Fed cuts rates as markets rally", "B", url="https://example.com/b")
        third = article("Fed cuts rates: bond markets advance", "A", url="https://example.com/a")
        rows = news._dedupe([first, second, third])
        self.assertEqual(len(rows), 1)

    def test_expired_cache_is_not_reused_on_failure(self):
        with patch.object(news, "QUERIES", (("test", "fixed query"),)), patch.object(news, "_fetch_feed", return_value=([article("Fed cuts rates")], {"id": "test", "status": "ok"})) as fetch:
            first = news.get_snapshot(now=NOW)
            second = news.get_snapshot(now=NOW)
            self.assertEqual(first["status"], "ok")
            self.assertTrue(second["cache_hit"])
            self.assertEqual(fetch.call_count, 1)
            old = news.get_snapshot(now=NOW + timedelta(hours=80))
            self.assertEqual(old["items"], [])
            self.assertEqual(old["status"], "unavailable")
        with patch.object(news, "QUERIES", (("test", "fixed query"),)), patch.object(news, "_fetch_feed", side_effect=TimeoutError):
            failed = news.get_snapshot(now=NOW, force=True)
            self.assertEqual(failed["status"], "unavailable")
            self.assertEqual(failed["items"], [])
            self.assertEqual(failed["errors"][0]["reason"], "TimeoutError")

    def test_saved_snapshot_cannot_inject_event_or_ticker_associations(self):
        fake = article("Gold market steadies")
        fake.update(symbols=["AAPL"], event_ids=["fed_hike_2022_03"], themes=["rate_hikes"])
        evidence = news.evidence_for("AAPL", "Technology", {"items": [fake]}, now=NOW)
        self.assertEqual(evidence["headlines"], [])
        self.assertEqual(evidence["events"], [])


if __name__ == "__main__":
    unittest.main()
