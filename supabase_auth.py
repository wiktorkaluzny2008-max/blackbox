"""Server-only Supabase Auth adapter. Never expose keys or tokens to the UI."""
import os
import re
import requests
from datetime import datetime, timezone


class AuthError(Exception):
    def __init__(self, code='auth_unavailable', status=503):
        self.code, self.status = code, status
        super().__init__(code)


def enabled():
    return os.getenv('SUPABASE_AUTH_ENABLED') == '1'


def _request(method, path, body=None, admin=False, token=None):
    url = os.getenv('SUPABASE_URL', '').rstrip('/')
    key = os.getenv('SUPABASE_SECRET_KEY' if admin else 'SUPABASE_PUBLISHABLE_KEY', '')
    if not re.fullmatch(r'https://[a-z0-9]+\.supabase\.co', url) or not key:
        raise AuthError('auth_not_configured')
    headers = {'apikey': key, 'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    elif key.startswith('eyJ'):
        headers['Authorization'] = 'Bearer ' + key
    try:
        response = requests.request(method, url + '/auth/v1' + path,
                                    json=body, headers=headers, timeout=15)
        data = response.json() if response.content else {}
    except (requests.RequestException, ValueError):
        raise AuthError() from None
    if not response.ok:
        code = data.get('error_code') or data.get('code') or 'auth_failed'
        status = 503 if response.status_code >= 500 else response.status_code
        raise AuthError(code, status)
    return data


def signup(email, password, name):
    return _request('POST', '/signup', {'email': email, 'password': password,
                                      'data': {'name': name}})


def signin(email, password):
    return _request('POST', '/token?grant_type=password', {'email': email, 'password': password})


def migrate(email, password, name, aid):
    # Only called after verifying the legacy password. No existing Auth user is
    # overwritten. On a conflict the caller must prove both account passwords.
    return _request('POST', '/admin/users', {
        'email': email, 'password': password, 'email_confirm': True,
        'user_metadata': {'name': name},
        'app_metadata': {'blackbox_legacy_account_id': aid},
    }, admin=True)


def get_user(token):
    return _request('GET', '/user', token=token)


def refresh(token):
    return _request('POST', '/token?grant_type=refresh_token', {'refresh_token': token})


def signout(token):
    return _request('POST', '/logout?scope=local', token=token)


def assert_active(user):
    if not user or not user.get('id') or user.get('deleted_at'):
        raise AuthError('invalid_credentials', 401)
    banned = user.get('banned_until')
    if banned and datetime.fromisoformat(banned.replace('Z', '+00:00')) > datetime.now(timezone.utc):
        raise AuthError('user_banned', 401)
