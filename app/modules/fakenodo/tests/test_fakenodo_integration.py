# fakenodo/test_fakenodo_integration.py
import os
import subprocess
import sys
import time
import tempfile
import shutil
import requests
import pytest
from pathlib import Path


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
    Arranca fakenodo en un subproceso para toda la sesión de tests,
    usando un directorio temporal para los ficheros subidos.
    """
    tmpdir = tempfile.mkdtemp(prefix="fakenodo_files_")
    env = os.environ.copy()
    env["PORT"] = str(FAKENODO_PORT)
    env["FAKENODO_FILES_DIR"] = tmpdir

    test_dir = Path(__file__).resolve().parent
    app_path = test_dir.parent / "app.py"   # app/modules/fakenodo/app.py

    if not app_path.exists():
        pytest.skip(f"{app_path} no existe. Crea el microservicio antes de ejecutar estos tests.")
    proc = subprocess.Popen([sys.executable, app_path], env=env)

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


def test_roundtrip_create_upload_publish_delete(fakenodo_server, tmp_path):
    # 1) Crear deposición
    create = requests.post(
        FAKENODO_DEPOSITIONS,
        json={"metadata": {"title": "Demo pytest", "upload_type": "dataset"}},
        timeout=10,
    )
    assert create.status_code == 201, create.text
    dep = create.json()
    dep_id = dep["id"]

    # 2) Subir archivo
    test_file = tmp_path / "file.txt"
    test_file.write_text("hola fakenodo")
    with open(test_file, "rb") as fh:
        up = requests.post(
            f"{FAKENODO_DEPOSITIONS}/{dep_id}/files",
            data={"name": "file.txt"},
            files={"file": fh},
            timeout=15,
        )
    assert up.status_code == 201, up.text

    # 3) Publicar
    pub = requests.post(f"{FAKENODO_DEPOSITIONS}/{dep_id}/actions/publish", timeout=10)
    assert pub.status_code == 202, pub.text
    assert pub.json().get("doi"), "No se devolvió DOI en la publicación"

    # 4) Borrar
    delete = requests.delete(f"{FAKENODO_DEPOSITIONS}/{dep_id}", timeout=10)
    assert delete.status_code == 204, delete.text
