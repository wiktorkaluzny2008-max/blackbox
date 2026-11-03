"""Migration and ownership regressions, isolated from all live credentials."""
import copy
import importlib.util
import os
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

with patch.dict(sys.modules, {
    'state_store': types.SimpleNamespace(with_state_lock=lambda fn: fn),
    'dotenv': types.SimpleNamespace(load_dotenv=lambda *a, **k: None),
}), patch.dict(os.environ, {'APP_SECRET': 'isolated-auth-test'}, clear=True):
    spec = importlib.util.spec_from_file_location('migration_test_app', Path(__file__).with_name('app_user.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.state = {mod.ACCOUNTS: {}, mod.USERS: {}, 'sessions': {}}
        def load(path, default=None): return copy.deepcopy(self.state.get(path, default))
        def save(path, data): self.state[path] = copy.deepcopy(data)
        replacements = [
            patch.object(mod, '_load', side_effect=load),
            patch.object(mod, '_save_accounts', side_effect=lambda d: save(mod.ACCOUNTS, d)),
            patch.object(mod, '_save_users', side_effect=lambda d: save(mod.USERS, d)),
            patch.object(mod, '_auth_sessions', side_effect=lambda: load('sessions')),
            patch.object(mod, '_save_auth_sessions', side_effect=lambda d: save('sessions', d)),
            patch.object(mod, '_notify'),
            patch.object(mod, '_user_payload', side_effect=lambda uid: dict(load(mod.USERS)[uid], uid=uid)),
            patch.object(mod.sa, 'enabled', return_value=True),
        ]
        for p in replacements: p.start(); self.addCleanup(p.stop)
        self.client = mod.app.test_client()
        self.creds = {'email': 'owner@example.invalid', 'password': 'legacy-password-123'}
        self.tokens = {'user': {'id': 'auth-owner', 'email': self.creds['email']},
                       'access_token': 'private-access', 'refresh_token': 'private-refresh',
                       'expires_at': 9999999999}
        self.state[mod.ACCOUNTS]['old-aid'] = {'name': 'Owner', 'email': self.creds['email'],
            'password_hash': mod.generate_password_hash(self.creds['password'], method='pbkdf2:sha256:600000'),
            'uid': 'portfolio-1', 'portfolio_ids': ['portfolio-1', 'portfolio-2']}
        self.state[mod.USERS]['portfolio-1'] = {'name': 'Saved portfolio', 'mix': {'spx_hold': 100}}

    def login(self):
        return self.client.post('/api/auth/password', json=self.creds)

    def test_migration_preserves_ids_portfolio_and_hides_tokens(self):
        with patch.object(mod.sa, 'migrate') as migrate, patch.object(mod.sa, 'signin', return_value=self.tokens), patch.object(mod.sa, 'get_user', return_value=self.tokens['user']):
            response = self.login()
            self.assertEqual(response.status_code, 200)
            migrate.assert_called_once()
            account = self.state[mod.ACCOUNTS]['old-aid']
            self.assertEqual(account['portfolio_ids'], ['portfolio-1', 'portfolio-2'])
            self.assertEqual(account['supabase_user_id'], 'auth-owner')
            self.assertNotIn('password_hash', account)
            self.assertNotIn('private-access', response.get_data(as_text=True))
            self.assertNotIn('private-access', response.headers.get('Set-Cookie', ''))
            self.assertEqual(self.client.get('/api/me').json['portfolio']['uid'], 'portfolio-1')

    def test_wrong_legacy_password_never_creates_or_links_auth_user(self):
        with patch.object(mod.sa, 'migrate') as migrate, patch.object(mod.sa, 'signin') as signin:
            self.creds['password'] = 'incorrect-password'
            self.assertEqual(self.login().status_code, 401)
            migrate.assert_not_called(); signin.assert_not_called()

    def test_migration_outage_keeps_old_credentials_and_portfolio(self):
        before = copy.deepcopy(self.state)
        with patch.object(mod.sa, 'migrate', side_effect=mod.sa.AuthError()):
            self.assertEqual(self.login().status_code, 503)
        self.assertEqual(self.state, before)

    def test_duplicate_auth_user_requires_provider_password_proof(self):
        with patch.object(mod.sa, 'migrate', side_effect=mod.sa.AuthError('email_exists', 422)), patch.object(mod.sa, 'signin', side_effect=mod.sa.AuthError('invalid_credentials', 400)):
            self.assertEqual(self.login().status_code, 400)
        self.assertNotIn('supabase_user_id', self.state[mod.ACCOUNTS]['old-aid'])

    def test_migrated_account_never_falls_back_to_legacy_password(self):
        self.state[mod.ACCOUNTS]['old-aid']['supabase_user_id'] = 'auth-owner'
        with patch.object(mod.sa, 'migrate') as migrate, patch.object(mod.sa, 'signin', side_effect=mod.sa.AuthError('user_banned', 403)):
            self.assertEqual(self.login().status_code, 403)
            migrate.assert_not_called()
        self.assertFalse(self.client.get('/api/me').json['signed_in'])

    def test_signup_requires_confirmation_without_creating_app_session(self):
        with patch.object(mod.sa, 'signup', return_value={'id': 'pending-auth-id'}):
            r = self.client.post('/api/auth/register', json={'email': 'new@example.invalid', 'password': 'new-password-123', 'name': 'New'})
        self.assertTrue(r.json['confirmation_required'])
        self.assertFalse(self.client.get('/api/me').json['signed_in'])
        self.assertEqual(len(self.state[mod.ACCOUNTS]), 1)

    def test_expired_tokens_refresh_and_logout_revokes_local_session(self):
        with patch.object(mod.sa, 'migrate'), patch.object(mod.sa, 'signin', return_value=self.tokens): self.login()
        next(iter(self.state['sessions'].values()))['tokens']['expires_at'] = 0
        with patch.object(mod.sa, 'refresh', return_value=self.tokens) as refresh, patch.object(mod.sa, 'get_user', return_value=self.tokens['user']):
            self.assertTrue(self.client.get('/api/me').json['signed_in'])
            refresh.assert_called_once()
        with patch.object(mod.sa, 'signout') as signout:
            self.assertEqual(self.client.post('/api/auth/logout').status_code, 200)
            signout.assert_called_once()
        self.assertFalse(self.state['sessions'])
        self.assertFalse(self.client.get('/api/me').json['signed_in'])

    def test_provider_outage_does_not_destroy_session(self):
        with patch.object(mod.sa, 'migrate'), patch.object(mod.sa, 'signin', return_value=self.tokens): self.login()
        with patch.object(mod.sa, 'get_user', side_effect=mod.sa.AuthError()):
            self.assertEqual(self.client.get('/api/me').status_code, 503)
        self.assertTrue(self.state['sessions'])

    def test_deleted_auth_user_cannot_read_existing_portfolio(self):
        with patch.object(mod.sa, 'migrate'), patch.object(mod.sa, 'signin', return_value=self.tokens): self.login()
        with patch.object(mod.sa, 'get_user', side_effect=mod.sa.AuthError('user_not_found', 401)):
            self.assertFalse(self.client.get('/api/me').json['signed_in'])
        self.assertTrue(self.state[mod.USERS])


if __name__ == '__main__': unittest.main()
