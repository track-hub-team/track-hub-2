# app/modules/fakenodo/app.py
import hashlib
import os
import time
import uuid
from typing import Any

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

app = Flask(__name__)

DEPOSITIONS: dict[str, dict[str, Any]] = {}
CONCEPTS: dict[str, dict[str, Any]] = {}
FILES_DIR = os.environ.get("FAKENODO_FILES_DIR", "./_fakenodo_files")
os.makedirs(FILES_DIR, exist_ok=True)


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id():
    return (max(DEPOSITIONS) + 1) if DEPOSITIONS else 1


def new_concept_id():
    return str(uuid.uuid4())[:8]


def make_doi(concept, version):
    return f"10.9999/fakenodo.{concept}.v{version}"


def files_fingerprint(files):
    # hash determinista del set de ficheros por nombre+size (simple y suficiente)
    h = hashlib.sha256()
    for f in sorted(files, key=lambda x: x["filename"]):
        h.update(f["filename"].encode())
        h.update(str(f["size"]).encode())
    return h.hexdigest()


def serialize(dep):
    return {
        "id": dep["id"],
        "conceptrecid": dep["conceptrecid"],
        "created": dep["created"],
        "modified": dep["modified"],
        "metadata": dep["metadata"],
        "state": dep["state"],  # "draft" | "done"
        "files": [{"filename": f["filename"], "filesize": f["size"]} for f in dep["files"]],
        "version": dep["version"],
        "conceptdoi": dep["conceptdoi"],
        "doi": dep.get("doi"),
        "links": {"self": f"/api/deposit/depositions/{dep['id']}"},
    }


@app.route("/api/deposit/depositions", methods=["GET"])
def list_depositions():
    return jsonify([serialize(d) for d in DEPOSITIONS.values()]), 200


@app.route("/api/deposit/depositions", methods=["POST"])
def create_deposition():
    payload = request.get_json(silent=True) or {}
    dep_id = new_id()
    conceptrecid = new_concept_id()
    dep = {
        "id": dep_id,
        "conceptrecid": conceptrecid,
        "created": now_iso(),
        "modified": now_iso(),
        "metadata": payload.get("metadata") or {},
        "state": "draft",
        "files": [],
        "files_fp": "",  # fingerprint para saber si cambió el set de ficheros
        "version": 1,
        "conceptdoi": f"10.9999/fakenodo.{conceptrecid}",
        # "doi": solo si publicado
    }
    DEPOSITIONS[dep_id] = dep
    CONCEPTS.setdefault(conceptrecid, []).append(dep_id)
    return jsonify(serialize(dep)), 201


@app.route("/api/deposit/depositions/<int:dep_id>", methods=["GET"])
def get_deposition(dep_id):
    dep = DEPOSITIONS.get(dep_id)
    if not dep:
        return jsonify({"message": "Not found"}), 404
    return jsonify(serialize(dep)), 200


@app.route("/api/deposit/depositions/<int:dep_id>", methods=["PUT", "PATCH"])
def update_metadata(dep_id):
    dep = DEPOSITIONS.get(dep_id)
    if not dep:
        return jsonify({"message": "Not found"}), 404
    payload = request.get_json(silent=True) or {}
    if "metadata" in payload:
        dep["metadata"] = payload["metadata"]
        dep["modified"] = now_iso()
        # IMPORTANTE: editar SOLO metadatos no cambia versión ni DOI
    return jsonify(serialize(dep)), 200


@app.route("/api/deposit/depositions/<int:dep_id>", methods=["DELETE"])
def delete_deposition(dep_id):
    dep = DEPOSITIONS.pop(dep_id, None)
    if dep:
        for f in dep["files"]:
            try:
                os.remove(f["path"])
            except Exception:
                pass
        if dep["conceptrecid"] in CONCEPTS and dep_id in CONCEPTS[dep["conceptrecid"]]:
            CONCEPTS[dep["conceptrecid"]].remove(dep_id)
    return ("", 204)


@app.route("/api/deposit/depositions/<int:dep_id>/files", methods=["POST"])
def upload_file(dep_id):
    dep = DEPOSITIONS.get(dep_id)
    if not dep:
        return jsonify({"message": "Not found"}), 404
    file = request.files.get("file")
    name = request.form.get("name")
    if not file or not name:
        return jsonify({"message": "Missing file or name"}), 400
    filename = secure_filename(name)
    save_path = os.path.join(FILES_DIR, f"{dep_id}_{filename}")
    file.save(save_path)
    size = os.path.getsize(save_path)
    dep["files"].append({"filename": filename, "size": size, "path": save_path})
    dep["files_fp"] = files_fingerprint(dep["files"])
    dep["modified"] = now_iso()
    return (
        jsonify(
            {
                "filename": filename,
                "filesize": size,
                "links": {"download": f"/api/deposit/depositions/{dep_id}/files/{filename}"},
            }
        ),
        201,
    )


@app.route("/api/deposit/depositions/<int:dep_id>/files/<path:filename>", methods=["GET"])
def download(dep_id, filename):
    dep = DEPOSITIONS.get(dep_id)
    if not dep:
        return jsonify({"message": "Not found"}), 404
    f = next((x for x in dep["files"] if x["filename"] == filename), None)
    if not f:
        return jsonify({"message": "Not found"}), 404
    directory, fname = os.path.dirname(f["path"]), os.path.basename(f["path"])
    return send_from_directory(directory, fname, as_attachment=True)


@app.route("/api/deposit/depositions/<int:dep_id>/actions/publish", methods=["POST"])
def publish(dep_id):
    dep = DEPOSITIONS.get(dep_id)
    if not dep:
        return jsonify({"message": "Not found"}), 404

    prev_fp = dep.get("published_files_fp", "")
    cur_fp = dep.get("files_fp", "")
    changed_files = cur_fp != prev_fp

    if changed_files or dep.get("doi") is None:
        dep["doi"] = make_doi(dep["conceptrecid"], dep["version"])
        dep["published_files_fp"] = cur_fp

    dep["state"] = "done"
    dep["modified"] = now_iso()
    return jsonify(serialize(dep)), 202


@app.route("/api/records/<conceptid>/versions", methods=["GET"])
def list_versions(conceptid):
    ids = CONCEPTS.get(conceptid, [])
    return jsonify([serialize(DEPOSITIONS[i]) for i in ids]), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5001"))
    app.run(host="0.0.0.0", port=port, debug=True)
