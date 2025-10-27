from flask import render_template
from flask import jsonify
import os
import tempfile
import requests
from app.modules.zenodo import zenodo_bp
from app.modules.zenodo.services import ZenodoService


@zenodo_bp.route("/zenodo", methods=["GET"])
def index():
    return render_template("zenodo/index.html")


@zenodo_bp.route("/zenodo/test", methods=["GET"])
def zenodo_test() -> dict:
    service = ZenodoService()
    return service.test_full_connection()


@zenodo_bp.route("/zenodo/demo", methods=["GET"])
def zenodo_demo():
    """
    Demo visual: crea una deposición, la muestra, sube un fichero, vuelve a mostrar y elimina.
    Devuelve un 'timeline' de pasos para que el frontend lo pinte.
    """
    svc = ZenodoService()
    base = svc.ZENODO_API_URL
    params = svc._params()
    headers = {"Content-Type": "application/json"}

    steps = []
    success = True
    dep_id = None

    def add_step(name, method, url, status, payload=None, error=None):
        steps.append({
            "name": name,
            "method": method,
            "url": url,
            "status": status,
            "ok": 200 <= status < 300 or status in (201, 202, 204),
            "payload": payload,
            "error": error
        })

    try:
        # 1) Crear
        meta = {
            "metadata": {
                "title": "Fakenodo Visual Demo",
                "upload_type": "dataset",
                "description": "Demo paso a paso desde UVLHub",
                "creators": [{"name": "UVLHub"}],
            }
        }
        r = requests.post(base, json=meta, params=params, headers=headers, timeout=30)
        dep_json = r.json() if r.status_code == 201 else None
        dep_id = dep_json.get("id") if dep_json else None
        add_step("create", "POST", base, r.status_code, dep_json or r.text)
        if not dep_id:
            success = False
            return jsonify({"success": False, "steps": steps})

        # 2) Mostrar tras crear
        get_url = f"{base}/{dep_id}"
        r = requests.get(get_url, params=params, headers=headers, timeout=30)
        add_step("show_after_create", "GET", get_url, r.status_code, r.json() if r.ok else r.text)
        if not r.ok:
            success = False

        # 3) Subir fichero temporal
        files_url = f"{base}/{dep_id}/files"
        tmpfile = os.path.join(tempfile.gettempdir(), "uvlhub_demo.txt")
        with open(tmpfile, "w") as fh:
            fh.write("Contenido de prueba para la demo visual de Fakenodo.")
        with open(tmpfile, "rb") as fh:
            r = requests.post(files_url, params=params, data={"name": "uvlhub_demo.txt"},
                              files={"file": fh}, timeout=60)
        add_step("upload_file", "POST", files_url, r.status_code, r.json() if r.ok else r.text)
        if r.status_code != 201:
            success = False
        publish_url = f"{base}/{dep_id}/actions/publish"
        r = requests.post(publish_url, params=params, headers=headers, timeout=30)
        add_step("publish", "POST", publish_url, r.status_code, r.json() if r.ok else r.text)
        if r.status_code != 202:
            success = False

        # 4) Mostrar tras subir
        r = requests.get(get_url, params=params, headers=headers, timeout=30)
        add_step("show_after_upload", "GET", get_url, r.status_code, r.json() if r.ok else r.text)
        if not r.ok:
            success = False
    except Exception as exc:
        success = False
        add_step("exception", "?", "n/a", 0, error=str(exc))
    finally:
        # 5) Eliminar (si se creó)
        if dep_id:
            r = requests.delete(f"{base}/{dep_id}", params=params, timeout=30)
            add_step("delete", "DELETE", f"{base}/{dep_id}", r.status_code,
                     None if r.status_code == 204 else r.text)

    return jsonify({"success": success, "steps": steps})
