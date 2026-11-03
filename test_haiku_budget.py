"""Paid API safety tests: no network or real credentials."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import types
import unittest
from contextlib import contextmanager
from unittest.mock import patch, MagicMock

with patch.dict(sys.modules, {'config': types.SimpleNamespace(GROQ_API_KEY='')}):
    spec = importlib.util.spec_from_file_location('haiku_test_client', Path(__file__).with_name('ai_client.py'))
    ai = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ai)

@contextmanager
def no_lock(): yield

class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.usage = {}
        def save(kind, path, value): self.usage = copy.deepcopy(value)
        store = types.SimpleNamespace(locked=no_lock, load=lambda *a: copy.deepcopy(self.usage), save=save)
        env = patch.dict(os.environ, {'AI_PROVIDER':'anthropic', 'ANTHROPIC_ENABLED':'1',
            'ANTHROPIC_API_KEY':'fake-test-key', 'DATABASE_URL':'test-only', 'AI_MONTHLY_LIMIT_USD':'10'}, clear=True)
        modules = patch.dict(sys.modules, {'state_store':store})
        for p in [env, modules]:p.start();self.addCleanup(p.stop)
        self.response = MagicMock()
        self.response.__enter__.return_value = self.response
        self.response.read.return_value = json.dumps({'content':[{'type':'text','text':'Reply'}], 'stop_reason':'end_turn'}).encode()
    def test_disabled_never_calls_api(self):
        with patch.dict(os.environ, {'ANTHROPIC_ENABLED':'0'}), patch.object(ai.urllib.request,'urlopen') as request:
            self.assertIsNone(ai.ask('Hello'));request.assert_not_called()
    def test_cap_blocks_even_after_client_restart(self):
        from datetime import datetime, timezone
        self.usage[datetime.now(timezone.utc).strftime('%Y-%m')] = 1000
        with patch.object(ai.urllib.request,'urlopen') as request:
            self.assertIsNone(ai.ask('Hello'));request.assert_not_called()
    def test_reservation_is_saved_before_paid_call(self):
        def paid(req, timeout):
            self.assertEqual(sum(self.usage.values()),1)
            payload=json.loads(req.data)
            self.assertEqual(payload['model'],'claude-haiku-5-5')
            self.assertEqual(payload['max_tokens'],1000)
            self.assertEqual(payload['system'],'Keep facts grounded')
            return self.response
        with patch.object(ai.urllib.request,'urlopen', side_effect=paid):
            self.assertEqual(ai.ask('Hello',system='Keep facts grounded',max_tokens=5000),'Reply')
    def test_failed_attempt_keeps_reservation_and_never_retries(self):
        with patch.object(ai.urllib.request,'urlopen',side_effect=TimeoutError) as request:
            self.assertIsNone(ai.ask('Hello'));request.assert_called_once()
        self.assertEqual(sum(self.usage.values()),1)
    def test_oversized_prompt_is_rejected_before_spend(self):
        with patch.object(ai.urllib.request,'urlopen') as request:
            self.assertIsNone(ai.ask('ą'*24001));request.assert_not_called()
        self.assertFalse(self.usage)
    def test_database_failure_prevents_spend(self):
        with patch('state_store.load',side_effect=RuntimeError), patch.object(ai.urllib.request,'urlopen') as request:
            self.assertIsNone(ai.ask('Hello'));request.assert_not_called()
    def test_environment_cannot_raise_approved_ten_dollar_cap(self):
        from datetime import datetime, timezone
        self.usage[datetime.now(timezone.utc).strftime('%Y-%m')]=1000
        with patch.dict(os.environ, {'AI_MONTHLY_LIMIT_USD':'100'}), patch.object(ai.urllib.request,'urlopen') as request:
            self.assertIsNone(ai.ask('Hello'));request.assert_not_called()
if __name__=='__main__':unittest.main()
