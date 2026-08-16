from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from app.backup import (
    BACKUP_FORMAT,
    create_sqlite_backup,
    revoke_restored_web_sessions,
    verify_sqlite_backup,
)

BACKEND_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_TOKEN = "synthetic-backup-bootstrap-token"
ADMIN_PASSWORD = "synthetic admin password 123"
USER_PASSWORD = "synthetic user password 123"
SESSION_COOKIE = "goreecloud_notify_session"


def run_alembic(database_url: str, revision: str = "head") -> None:
    env = os.environ.copy()
    env["GOREECLOUD_NOTIFY_DATABASE_URL"] = database_url
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", revision],
        cwd=BACKEND_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def run_app_script(
    database_url: str,
    code: str,
    *,
    extra_env: dict[str, str] | None = None,
) -> str:
    env = os.environ.copy()
    env.update(
        {
            "GOREECLOUD_NOTIFY_DATABASE_URL": database_url,
            "GOREECLOUD_NOTIFY_ADMIN_TOKEN": BOOTSTRAP_TOKEN,
            "GOREECLOUD_NOTIFY_SESSION_COOKIE_SECURE": "false",
        }
    )
    if extra_env:
        env.update(extra_env)
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=BACKEND_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def seed_application_state(database_url: str) -> dict[str, str]:
    output = run_app_script(
        database_url,
        f"""
import json
from fastapi.testclient import TestClient
from app.config import settings
from app.main import app
from app.user_security import CSRF_HEADER

with TestClient(app) as admin:
    bootstrap = admin.post(
        '/api/v1/bootstrap/administrator',
        headers={{'X-GoreeCloud-Admin-Token': '{BOOTSTRAP_TOKEN}'}},
        json={{
            'username': 'recovery-admin',
            'display_name': 'Recovery Admin',
            'password': '{ADMIN_PASSWORD}',
        }},
    )
    assert bootstrap.status_code == 201, bootstrap.text
    login = admin.post(
        '/api/v1/session',
        json={{'username': 'recovery-admin', 'password': '{ADMIN_PASSWORD}'}},
    )
    assert login.status_code == 200, login.text
    csrf = login.headers[CSRF_HEADER]
    admin_headers = {{CSRF_HEADER: csrf}}

    user = admin.post(
        '/api/v1/users',
        headers=admin_headers,
        json={{
            'username': 'recovery-user',
            'display_name': 'Recovery User',
            'password': '{USER_PASSWORD}',
        }},
    )
    assert user.status_code == 201, user.text

    identity = admin.post(
        '/api/v1/service-identities',
        headers=admin_headers,
        json={{'name': 'Recovery Producer'}},
    )
    assert identity.status_code == 201, identity.text
    identity_id = identity.json()['id']

    source = admin.post(
        '/api/v1/sources',
        headers=admin_headers,
        json={{
            'service_identity_id': identity_id,
            'slug': 'recovery-producer',
            'name': 'Recovery Producer',
        }},
    )
    assert source.status_code == 201, source.text

    channel = admin.post(
        '/api/v1/channels',
        headers=admin_headers,
        json={{'slug': 'goreecloud-recovery', 'name': 'Recovery'}},
    )
    assert channel.status_code == 201, channel.text

    token = admin.post(
        '/api/v1/tokens',
        headers=admin_headers,
        json={{
            'service_identity_id': identity_id,
            'name': 'Recovery Publisher',
            'scopes': ['notifications:write', 'notifications:read'],
        }},
    )
    assert token.status_code == 201, token.text
    producer_token = token.json()['token']

with TestClient(app) as user_client:
    user_login = user_client.post(
        '/api/v1/session',
        json={{'username': 'recovery-user', 'password': '{USER_PASSWORD}'}},
    )
    assert user_login.status_code == 200, user_login.text
    user_csrf = user_login.headers[CSRF_HEADER]
    old_session = user_client.cookies.get(settings.session_cookie_name)
    assert old_session
    subscribed = user_client.put(
        '/api/v1/subscriptions/goreecloud-recovery',
        headers={{CSRF_HEADER: user_csrf}},
    )
    assert subscribed.status_code == 200, subscribed.text

    with TestClient(app) as producer:
        published = producer.post(
            '/api/v1/notifications',
            headers={{'Authorization': f'Bearer {{producer_token}}'}},
            json={{
                'source': 'recovery-producer',
                'channel': 'goreecloud-recovery',
                'title': 'Recovery snapshot notification',
                'body': 'Synthetic recovery evidence',
                'severity': 'normal',
            }},
        )
        assert published.status_code == 201, published.text

    inbox = user_client.get('/api/v1/inbox')
    assert inbox.status_code == 200, inbox.text
    assert [item['title'] for item in inbox.json()] == ['Recovery snapshot notification']

print(json.dumps({{'producer_token': producer_token, 'old_session': old_session}}))
""",
    )
    return json.loads(output)


def verify_restored_application(
    database_url: str,
    *,
    producer_token: str,
    old_session: str,
) -> None:
    output = run_app_script(
        database_url,
        f"""
from fastapi.testclient import TestClient
from app.main import app

with TestClient(app) as stale:
    stale.cookies.set('{SESSION_COOKIE}', __import__('os').environ['TEST_OLD_SESSION'])
    rejected = stale.get('/api/v1/me')
    assert rejected.status_code == 401, rejected.text
    assert rejected.json()['detail'] == 'invalid user session'

with TestClient(app) as admin:
    health = admin.get('/healthz')
    assert health.status_code == 200, health.text
    admin_login = admin.post(
        '/api/v1/session',
        json={{'username': 'recovery-admin', 'password': '{ADMIN_PASSWORD}'}},
    )
    assert admin_login.status_code == 200, admin_login.text
    sources = admin.get('/api/v1/sources')
    channels = admin.get('/api/v1/channels')
    assert sources.status_code == channels.status_code == 200
    assert [item['slug'] for item in sources.json()] == ['recovery-producer']
    assert [item['slug'] for item in channels.json()] == ['goreecloud-recovery']

with TestClient(app) as user:
    user_login = user.post(
        '/api/v1/session',
        json={{'username': 'recovery-user', 'password': '{USER_PASSWORD}'}},
    )
    assert user_login.status_code == 200, user_login.text
    subscriptions = user.get('/api/v1/subscriptions')
    inbox = user.get('/api/v1/inbox')
    assert subscriptions.status_code == inbox.status_code == 200
    assert subscriptions.json()[0]['channel'] == 'goreecloud-recovery'
    assert subscriptions.json()[0]['subscribed'] is True
    assert inbox.json()[0]['title'] == 'Recovery snapshot notification'

with TestClient(app) as producer:
    history = producer.get(
        '/api/v1/notifications',
        headers={{'Authorization': 'Bearer ' + __import__('os').environ['TEST_PRODUCER_TOKEN']}},
    )
    assert history.status_code == 200, history.text
    assert history.json()[0]['title'] == 'Recovery snapshot notification'

print('restored-ok')
""",
        extra_env={
            "TEST_PRODUCER_TOKEN": producer_token,
            "TEST_OLD_SESSION": old_session,
        },
    )
    assert output == "restored-ok"


def test_sqlite_backup_manifest_and_verification(tmp_path: Path) -> None:
    source = tmp_path / "source.db"
    database_url = f"sqlite:///{source}"
    run_alembic(database_url)
    seed_application_state(database_url)

    backup = tmp_path / "snapshots" / "notify.db"
    manifest = create_sqlite_backup(database_url, backup)
    verification = verify_sqlite_backup(backup)
    manifest_path = Path(f"{backup}.manifest.json")
    manifest_document = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest.format == BACKUP_FORMAT
    assert manifest.sha256 == verification.sha256
    assert manifest.size_bytes == verification.size_bytes
    assert manifest.alembic_revision == verification.alembic_revision
    assert manifest.table_count == verification.table_count
    assert manifest_document["sha256"] == verification.sha256
    assert manifest_document["format"] == BACKUP_FORMAT

    serialized = manifest_path.read_text(encoding="utf-8")
    assert BOOTSTRAP_TOKEN not in serialized
    assert ADMIN_PASSWORD not in serialized
    assert USER_PASSWORD not in serialized


def test_alternate_restore_revokes_historical_sessions_and_preserves_application_state(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source.db"
    source_url = f"sqlite:///{source}"
    run_alembic(source_url)
    credentials = seed_application_state(source_url)

    backup = tmp_path / "notify-backup.db"
    create_sqlite_backup(source_url, backup)

    restored = tmp_path / "restore" / "goreecloud_notify.db"
    restored.parent.mkdir(parents=True)
    shutil.copy2(backup, restored)
    before_reconciliation = verify_sqlite_backup(restored)

    revoked = revoke_restored_web_sessions(restored)
    assert revoked == 2

    restored_url = f"sqlite:///{restored}"
    run_alembic(restored_url)
    after_reconciliation = verify_sqlite_backup(restored)
    assert after_reconciliation.alembic_revision == before_reconciliation.alembic_revision
    assert after_reconciliation.table_count == before_reconciliation.table_count

    verify_restored_application(
        restored_url,
        producer_token=credentials["producer_token"],
        old_session=credentials["old_session"],
    )
