"""Isolated account flow tests: no deployed environment, database, or notifications."""
import copy, importlib.util, os, sys, types, unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
with patch.dict(sys.modules, {'state_store':types.SimpleNamespace(with_state_lock=lambda fn:fn), 'dotenv':types.SimpleNamespace(load_dotenv=lambda *a, **k:None)}), patch.dict(os.environ, {'APP_SECRET':'isolated-account-tests'}, clear=True):
    spec=importlib.util.spec_from_file_location('account_test_app',Path(__file__).with_name('app_user.py'))
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
class AccountFlow(unittest.TestCase):
    def setUp(self):
        self.state={mod.ACCOUNTS:{},mod.USERS:{}}
        def load(path,default=None): return copy.deepcopy(self.state.get(path,default))
        def save(path,data): self.state[path]=copy.deepcopy(data)
        self.patches=[patch.object(mod,'_load',side_effect=load),patch.object(mod,'_save_accounts',side_effect=lambda d:save(mod.ACCOUNTS,d)),patch.object(mod,'_save_users',side_effect=lambda d:save(mod.USERS,d)),patch.object(mod,'_notify'),patch.object(mod,'_user_payload',side_effect=lambda uid:dict(load(mod.USERS)[uid],uid=uid))]
        for p in self.patches:p.start();self.addCleanup(p.stop)
        self.client=mod.app.test_client()
        self.credentials={'name':'Flow test','email':'flow@example.invalid','password':'test-only-password-123'}
    def register(self):
        r=self.client.post('/api/auth/register',json=self.credentials)
        self.assertEqual(r.status_code,200)
        return r.get_json()
    def create(self):
        r=self.client.post('/api/user/create',json={'name':'Test portfolio','mix':{'spx_hold':100}})
        self.assertEqual(r.status_code,200)
        return r.get_json()['user_id']
    def test_register_create_logout_login_keeps_portfolio(self):
        self.register();self.assertIsNone(self.client.get('/api/me').json['portfolio'])
        uid=self.create();self.assertEqual(self.client.get('/api/me').json['portfolio']['uid'],uid)
        self.client.post('/api/auth/logout');self.assertFalse(self.client.get('/api/me').json['signed_in'])
        self.assertEqual(self.client.post('/api/auth/password',json=self.credentials).status_code,200)
        self.assertEqual(self.client.get('/api/me').json['portfolio']['uid'],uid)
        other=mod.app.test_client();self.assertFalse(other.get('/api/me').json['signed_in'])
    def test_duplicate_and_wrong_password(self):
        self.register();self.assertEqual(self.client.post('/api/auth/register',json=self.credentials).status_code,409)
        self.client.post('/api/auth/logout')
        self.assertEqual(self.client.post('/api/auth/password',json=dict(self.credentials,password='wrong')).status_code,401)
    def test_guest_portfolio_adopted_only_by_owner(self):
        uid='old-guest'
        self.state[mod.USERS][uid]={'name':'Guest','mix':{'spx_hold':100}}
        with self.client.session_transaction() as sess: sess['anon_uid']=uid
        self.assertEqual(self.client.post('/api/auth/register',json=dict(self.credentials,adopt_uid=uid)).status_code,200)
        self.assertEqual(self.client.get('/api/me').json['portfolio']['uid'],uid)
        other=mod.app.test_client()
        other.post('/api/auth/register',json=dict(self.credentials,email='other@example.invalid',adopt_uid=uid))
        self.assertIsNone(other.get('/api/me').json['portfolio'])
    def test_private_routes_reject_other_account_and_signed_out_clients(self):
        self.register();uid=self.create()
        other=mod.app.test_client()
        other.post('/api/auth/register',json=dict(self.credentials,email='second@example.invalid'))
        guest=mod.app.test_client()
        with guest.session_transaction() as sess: sess['anon_uid']=uid
        for client in [other,guest]:
            for suffix,method in [('', 'get'),('/narrate','get'),('/review','get'),('/ask','post'),('/delete','post')]:
                response=getattr(client,method)('/api/user/'+uid+suffix)
                self.assertEqual(response.status_code,403)
                self.assertIn('no-store',response.headers['Cache-Control'])
        self.assertIn(uid,self.state[mod.USERS])
        self.assertEqual(self.client.get('/api/user/'+uid).status_code,200)
        self.client.post('/api/auth/logout')
        self.assertEqual(self.client.get('/api/user/'+uid).status_code,403)

    def test_guest_cannot_create_portfolio(self):
        self.assertEqual(self.client.post('/api/user/create',json={'mix':{'spx_hold':100}}).status_code,401)
        self.assertEqual(self.state[mod.USERS],{})

    def test_recovery_retains_portfolio(self):
        key=self.register()['recovery_key'];uid=self.create();self.client.post('/api/auth/logout')
        self.assertEqual(self.client.post('/api/auth/recover',json={'key':key}).status_code,200)
        self.assertEqual(self.client.get('/api/me').json['portfolio']['uid'],uid)
if __name__=='__main__':unittest.main()
