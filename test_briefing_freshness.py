import ast
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, Mock
import ai_features
import news_refresh

class BriefingTests(unittest.TestCase):
    def snapshot(self, age=0):
        return {'generated':(datetime.now(timezone.utc)-timedelta(seconds=age)).isoformat(), 'n_scanned':1, 'assets':{'gold':{'n_items':1,'score':2}}}

    def test_stale_future_missing_and_empty_never_reach_ai(self):
        for doc in [self.snapshot(6000),self.snapshot(-600),{},dict(self.snapshot(),n_scanned=0)]:
            with self.subTest(doc=doc), patch.object(ai_features.ai_client,'available',return_value=True), patch.object(ai_features,'_load',return_value=doc), patch('news_refresh.request_refresh',return_value='refreshing'), patch.object(ai_features.ai_client,'ask') as ask:
                self.assertEqual(ai_features.briefing()['reason'],'refreshing')
                ask.assert_not_called()

    def test_fresh_news_success_and_ai_failure(self):
        with patch.object(ai_features.ai_client,'available',return_value=True), patch.object(ai_features,'_load',return_value=self.snapshot()), patch.object(ai_features.ai_client,'ask',return_value='Report') as ask:
            self.assertEqual(ai_features.briefing()['text'],'Report')
            ask.return_value=None
            self.assertEqual(ai_features.briefing()['reason'],'ai_unavailable')

    def test_refresh_single_flight_and_cooldown(self):
        with patch.object(news_refresh,'_running',False),patch.object(news_refresh,'_last_attempt',None),patch.object(news_refresh.threading,'Thread') as thread:
            self.assertEqual(news_refresh.request_refresh(),'refreshing')
            self.assertEqual(news_refresh.request_refresh(),'refreshing')
            self.assertEqual(thread.call_count,1)
            news_refresh._running=False
            self.assertEqual(news_refresh.request_refresh(),'news_unavailable')

    def test_failed_results_are_not_cached(self):
        from pathlib import Path
        source=Path(__file__).with_name('app_user.py').read_text()
        fn=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='cached')
        import time
        scope={'time':time,'_cache':{}}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),'cached','exec'),scope)
        loader=Mock(side_effect=[{'available':False},{'text':'ok'}])
        scope['cached']('brief',60,loader)
        self.assertEqual(scope['cached']('brief',60,loader),{'text':'ok'})
        scope['cached']('brief',60,loader)
        self.assertEqual(loader.call_count,2)

if __name__=='__main__': unittest.main()
