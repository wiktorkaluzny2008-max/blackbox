"""Container entrypoint: require durable account storage before serving users."""
import os
import subprocess
import sys

if __name__ == '__main__':
    for key in ('APP_SECRET', 'DATABASE_URL'):
        if not os.environ.get(key):
            raise SystemExit(f'{key} must be configured as a Worker secret')
    subprocess.run([sys.executable, 'bootstrap.py'], check=True)
    os.execvp('gunicorn', ['gunicorn', '--bind', '0.0.0.0:8090', '--workers', '1',
                           '--timeout', '90', '--access-logfile', '-', '--error-logfile', '-', 'app_user:app'])
