# fakenodo/test_fakenodo_integration.py
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pytest
import requests

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
    app_path = test_dir.parent / "app.py"  # app/modules/fakenodo/app.py

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


def _create_dep():
    r = requests.post(
        FAKENODO_DEPOSITIONS,
        json={"metadata": {"title": "vtest", "upload_type": "dataset"}},
        timeout=10,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"], r.json()


def _upload(dep_id, tmp_path, name="file.txt", content="hola"):
    p = tmp_path / name
    p.write_text(content)
    with open(p, "rb") as fh:
        r = requests.post(
            f"{FAKENODO_DEPOSITIONS}/{dep_id}/files",
            data={"name": name},
            files={"file": fh},
            timeout=15,
        )
    assert r.status_code == 201, r.text
    return r.json()


def _get_dep(dep_id):
    r = requests.get(f"{FAKENODO_DEPOSITIONS}/{dep_id}", timeout=10)
    assert r.status_code == 200, r.text
    return r.json()


def test_publish_first_time_sets_doi_and_version_1(fakenodo_server, tmp_path):
    dep_id, _ = _create_dep()
    _upload(dep_id, tmp_path, "a.txt", "A")
    pub = requests.post(f"{FAKENODO_DEPOSITIONS}/{dep_id}/actions/publish", timeout=10)
    assert pub.status_code == 202, pub.text
    data = pub.json()
    assert data["doi"]
    assert data["version"] == 1
    assert data["state"] == "done"


def test_republish_without_changes_does_not_create_new_version(fakenodo_server, tmp_path):
    dep_id, _ = _create_dep()
    _upload(dep_id, tmp_path, "a.txt", "A")
    pub1 = requests.post(f"{FAKENODO_DEPOSITIONS}/{dep_id}/actions/publish", timeout=10).json()
    doi1, v1 = pub1["doi"], pub1["version"]
    pub2 = requests.post(f"{FAKENODO_DEPOSITIONS}/{dep_id}/actions/publish", timeout=10).json()
    assert pub2["doi"] == doi1
    assert pub2["version"] == v1


def test_publish_after_changing_files_creates_new_version_and_doi(fakenodo_server, tmp_path):
    dep_id, dep0 = _create_dep()
    concept = dep0["conceptrecid"]

    # v1
    _upload(dep_id, tmp_path, "a.txt", "A")
    pub1 = requests.post(f"{FAKENODO_DEPOSITIONS}/{dep_id}/actions/publish", timeout=10).json()
    doi1, v1 = pub1["doi"], pub1["version"]
    assert v1 == 1

    # cambiar archivos y publicar => v2 (nuevo registro)
    _upload(dep_id, tmp_path, "b.txt", "B")
    pub2 = requests.post(f"{FAKENODO_DEPOSITIONS}/{dep_id}/actions/publish", timeout=10).json()
    doi2, v2 = pub2["doi"], pub2["version"]
    assert v2 == 2
    assert doi2 != doi1

    # /versions debe listar v1 y v2 en orden
    vers = requests.get(f"{FAKENODO_BASE}/api/records/{concept}/versions", timeout=10)
    assert vers.status_code == 200, vers.text
    arr = vers.json()
    assert len(arr) >= 2
    assert [x["version"] for x in arr] == sorted([x["version"] for x in arr])


def test_update_metadata_does_not_change_doi_or_version(fakenodo_server, tmp_path):
    dep_id, _ = _create_dep()
    _upload(dep_id, tmp_path, "a.txt", "A")
    pub1 = requests.post(f"{FAKENODO_DEPOSITIONS}/{dep_id}/actions/publish", timeout=10).json()
    doi1, v1 = pub1["doi"], pub1["version"]

    # editar solo metadatos
    r = requests.put(
        f"{FAKENODO_DEPOSITIONS}/{dep_id}",
        json={"metadata": {"title": "nuevo titulo"}},
        timeout=10,
    )
    assert r.status_code == 200, r.text

    pub2 = requests.post(f"{FAKENODO_DEPOSITIONS}/{dep_id}/actions/publish", timeout=10).json()
    assert pub2["doi"] == doi1
    assert pub2["version"] == v1


def test_upload_validation_and_download(fakenodo_server, tmp_path):
    dep_id, _ = _create_dep()

    # falta file y/o name → 400
    bad = requests.post(f"{FAKENODO_DEPOSITIONS}/{dep_id}/files", data={"name": "x"}, timeout=10)
    assert bad.status_code == 400

    # subida válida
    up = _upload(dep_id, tmp_path, "d.txt", "D")
    download_path = up["links"]["download"]
    dl = requests.get(f"{FAKENODO_BASE}{download_path}", timeout=10)
    assert dl.status_code == 200
    assert dl.content == b"D"
