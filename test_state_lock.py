import importlib.util
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch, MagicMock

with patch.dict(sys.modules, {'dotenv':types.SimpleNamespace(load_dotenv=lambda *a, **k:None)}):
    spec=importlib.util.spec_from_file_location('lock_under_test',Path(__file__).with_name('state_store.py'))
    store=importlib.util.module_from_spec(spec);spec.loader.exec_module(store)

class LockTests(unittest.TestCase):
    def test_nested_session_lock_uses_same_outer_lock(self):
        conn=MagicMock()
        with patch.dict(os.environ,{'DATABASE_URL':'not-a-real-url'}),patch.object(store,'_connection',return_value=conn) as connect:
            with store.locked():
                with store.locked():pass
            connect.assert_called_once()
    def test_failed_operation_releases_reentrant_marker(self):
        conn=MagicMock()
        with patch.dict(os.environ,{'DATABASE_URL':'not-a-real-url'}),patch.object(store,'_connection',return_value=conn) as connect:
            with self.assertRaises(ValueError):
                with store.locked():raise ValueError()
            with store.locked():pass
            self.assertEqual(connect.call_count,2)
if __name__=='__main__':unittest.main()
