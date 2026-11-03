"""API evidence integration, with no network, account state, or credentials."""
import importlib.util
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

import market_recs
from test_market_evidence import prices
from datetime import date

# Loading the app under test must never load a deployed .env or connect to state.
with patch.dict(sys.modules, {
    'state_store': types.SimpleNamespace(with_state_lock=lambda fn: fn),
    'dotenv': types.SimpleNamespace(load_dotenv=lambda *a, **k: None),
}), patch.dict(os.environ, {'APP_SECRET': 'isolated-test-key'}, clear=True):
    spec = importlib.util.spec_from_file_location('evidence_route_app', Path(__file__).with_name('app_user.py'))
    app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app_module)


class MarketRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = app_module.app.test_client()
        # 300 weekdays ending on the most recent weekday before today.
        from datetime import datetime, timedelta, timezone
        end = datetime.now(timezone.utc).date() - timedelta(days=1)
        while end.weekday() > 4:
            end -= timedelta(days=1)
        begin = end
        count = 1
        while count < 300:
            begin -= timedelta(days=1)
            count += begin.weekday() < 5
        self.rows = prices(begin, 300, step=.1)
        self.profile = {'scope':'specific','horizon':'3-10y','max_dd':'-25%',
                        'experience':'some','react':'hold','goal':'steady','priority':'beat'}

    def request(self, rows):
        with patch.object(market_recs, '_fetch_history', return_value=rows), \
             patch.object(market_recs, '_news_snapshot', return_value={'status':'unavailable','items':[]}), \
             patch.object(app_module, '_load', return_value={'strategies':[]}):
            return self.client.post('/api/recommend', json=self.profile)

    def test_english_route_returns_evidence_and_explains_no_news(self):
        response = self.request(self.rows)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(sum(data['mix'].values()), 100)
        market = data['market']
        self.assertEqual(market['available'], 13)
        self.assertEqual(market['news_status'], 'unavailable')
        self.assertEqual(len(market['items']), 5)
        for item in market['items']:
            self.assertTrue(item['justification'])
            self.assertTrue(any('prices alone' in reason for reason in item['cautions']))
            self.assertEqual(item['score_breakdown']['news_history'], 0)
            self.assertTrue(item['price_source_url'].startswith('https://'))

    def test_language_cookie_selects_polish_explanations(self):
        self.client.set_cookie('bb_lang', 'pl')
        response = self.request(self.rows)
        self.assertEqual(response.status_code, 200)
        market = response.get_json()['market']
        self.assertIn('Cena', market['method'])
        self.assertIn('Cena zmieniła', market['items'][0]['justification'][0])
        self.assertTrue(any('Brak świeżych' in reason for reason in market['items'][0]['cautions']))

    def test_price_outage_returns_empty_market_recommendations(self):
        response = self.request([])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['market']['items'], [])
        self.assertEqual(response.get_json()['market']['available'], 0)


if __name__ == '__main__':
    unittest.main()
