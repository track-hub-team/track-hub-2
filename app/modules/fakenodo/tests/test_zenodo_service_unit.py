import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest
import requests
from flask import Flask

from app.modules.zenodo.services import ZenodoService

FAKENODO_PORT = 5001
FAKENODO_BASE = f"http://localhost:{FAKENODO_PORT}"
FAKENODO_DEPOSITIONS = f"{FAKENODO_BASE}/api/deposit/depositions"


def _wait_for_healthy(url, timeout=10.0):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=1.0)
            if r.status_code in (200, 404):
                return True
        except Exception:
            pass
        time.sleep(0.2)
    return False


@pytest.fixture(scope="session")
def fakenodo_server():
    """
    Arranca fakenodo en un subproceso para la sesión de tests.
    NO usar en el test de fallo.
    """
    tmpdir = tempfile.mkdtemp(prefix="fakenodo_files_")
    env = os.environ.copy()
    env["PORT"] = str(FAKENODO_PORT)
    env["FAKENODO_FILES_DIR"] = tmpdir

    test_dir = Path(__file__).resolve().parent
    app_path = test_dir.parent / "app.py"  # app/modules/fakenodo/app.py
    if not app_path.exists():
        pytest.skip(f"{app_path} no existe. Crea el microservicio antes de ejecutar estos tests.")

    proc = subprocess.Popen([sys.executable, str(app_path)], env=env)

    ok = _wait_for_healthy(FAKENODO_DEPOSITIONS, timeout=15.0)
    if not ok:
        proc.terminate()
        proc.wait(timeout=3)
        shutil.rmtree(tmpdir, ignore_errors=True)
        pytest.fail("fakenodo no arrancó a tiempo")

    yield

    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def env_ok(monkeypatch, fakenodo_server):
    """Fuerza entorno para que el servicio use el fakenodo real."""
    monkeypatch.setenv("FAKENODO_URL", FAKENODO_DEPOSITIONS)
    monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "dummy")
    monkeypatch.setenv("FLASK_ENV", "development")


@pytest.fixture
def env_fail(monkeypatch):
    """Fuerza un endpoint inválido SIN arrancar fakenodo."""
    monkeypatch.setenv("FAKENODO_URL", "http://localhost:9999/api/deposit/depositions")
    monkeypatch.setenv("ZENODO_ACCESS_TOKEN", "dummy")
    monkeypatch.setenv("FLASK_ENV", "development")


def test_test_full_connection_success(env_ok):
    """
    Debe devolver success=True con fakenodo corriendo.
    """
    app = Flask(__name__)
    with app.app_context():
        svc = ZenodoService()
        resp = svc.test_full_connection()
        payload = resp.get_json()
        assert resp.status_code == 200
        assert isinstance(payload, dict)
        assert payload.get("success") is True, payload
        assert "messages" in payload


def test_test_full_connection_fails_gracefully(env_fail):
    """
    Con endpoint inválido, debe devolver success=False (sin lanzar excepción).
    """
    app = Flask(__name__)
    with app.app_context():
        svc = ZenodoService()
        resp = svc.test_full_connection()
        payload = resp.get_json()
        assert resp.status_code == 200
        assert isinstance(payload, dict)
        assert payload.get("success") is False, payload
        assert "messages" in payload
        assert any("Failed" in msg or "error" in msg.lower() for msg in payload["messages"])
