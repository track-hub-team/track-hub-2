import logging
import os
from typing import Dict, Optional

import requests
from dotenv import load_dotenv
from flask import Response, jsonify
from flask_login import current_user

from app.modules.dataset.models import BaseDataset
from app.modules.featuremodel.models import FeatureModel
from app.modules.zenodo.repositories import ZenodoRepository
from core.configuration.configuration import uploads_folder_name
from core.services.BaseService import BaseService

logger = logging.getLogger(__name__)
load_dotenv()


class ZenodoService(BaseService):
    def __init__(self):
        super().__init__(ZenodoRepository())
        self.ZENODO_ACCESS_TOKEN: Optional[str] = self.get_zenodo_access_token()
        self.ZENODO_API_URL: str = self.get_zenodo_url()
        self.headers = {"Content-Type": "application/json"}

    # -----------------------------
    # Config helpers
    # -----------------------------
    def get_zenodo_url(self) -> str:
        """
        Prioriza FAKENODO_URL (fake backend local). Si no existe, usa ZENODO_API_URL
        o los valores por defecto (sandbox en dev, zenodo en prod).
        """
        # 1) Si hay fakenodo configurado, úsalo
        fakenodo = os.getenv("FAKENODO_URL")
        if fakenodo:
            return fakenodo.rstrip("/")

        # 2) Si no, decide Zenodo por entorno (con override por ZENODO_API_URL si existe)
        FLASK_ENV = os.getenv("FLASK_ENV", "development").lower()
        default = "https://sandbox.zenodo.org/api/deposit/depositions"
        if FLASK_ENV == "production":
            default = "https://zenodo.org/api/deposit/depositions"
        return os.getenv("ZENODO_API_URL", default).rstrip("/")

    def get_zenodo_access_token(self) -> Optional[str]:
        return os.getenv("ZENODO_ACCESS_TOKEN")

    def _params(self, token: Optional[str] = None) -> Dict[str, str]:
        """Construye los params sin incluir access_token si es None."""
        t = token if token is not None else self.ZENODO_ACCESS_TOKEN
        return {"access_token": t} if t else {}

    # -----------------------------
    # Health / smoke tests
    # -----------------------------
    def test_connection(self) -> bool:
        """
        Test simple de conectividad con Zenodo/Fakenodo.
        """
        try:
            response = requests.get(self.ZENODO_API_URL, params=self._params(), headers=self.headers, timeout=30)
            return response.status_code == 200
        except Exception as exc:
            logger.exception("Zenodo test_connection failed: %s", exc)
            return False

    def test_full_connection(self) -> Response:
        """
        Test E2E: crea una deposición, sube un fichero de prueba y elimina la deposición.
        Devuelve JSON con success/mensajes.
        """
        success = True
        messages = []

        # Crear fichero temporal de prueba
        working_dir = os.getenv("WORKING_DIR", "")
        file_path = os.path.join(working_dir, "test_file.txt")
        try:
            with open(file_path, "w") as f:
                f.write("This is a test file with some content.")
        except Exception as exc:
            logger.exception("Creating local test file failed: %s", exc)
            return jsonify({"success": False, "messages": ["Failed to create local test file."]})

        # 1) Crear deposición
        data = {
            "metadata": {
                "title": "Test Deposition",
                "upload_type": "dataset",
                "description": "This is a test deposition created via Zenodo API",
                "creators": [{"name": "John Doe"}],
            }
        }

        try:
            response = requests.post(
                self.ZENODO_API_URL, json=data, params=self._params(), headers=self.headers, timeout=30
            )
        except Exception as exc:
            logger.exception("Creating deposition failed: %s", exc)
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify({"success": False, "messages": ["Failed to create test deposition (network error)."]})

        if response.status_code != 201:
            if os.path.exists(file_path):
                os.remove(file_path)
            return jsonify(
                {
                    "success": False,
                    "messages": f"Failed to create test deposition. Code: {response.status_code}",
                }
            )

        deposition_id = response.json()["id"]

        # 2) Subir fichero
        upload_data = {"name": "test_file.txt"}
        publish_url = f"{self.ZENODO_API_URL}/{deposition_id}/files"

        try:
            with open(file_path, "rb") as fh:
                files = {"file": fh}
                response = requests.post(publish_url, params=self._params(), data=upload_data, files=files, timeout=60)
        except Exception as exc:
            logger.exception("Uploading file failed: %s", exc)
            messages.append("Failed to upload test file (network/IO error).")
            success = False
        else:
            logger.info("Publish URL: %s", publish_url)
            logger.info("Params: %s", self._params())
            logger.info("Data: %s", upload_data)
            logger.info("Response Status Code: %s", response.status_code)
            logger.info("Response Content: %r", response.content)

            if response.status_code != 201:
                messages.append(f"Failed to upload test file. Response code: {response.status_code}")
                success = False

        # 3) Borrar deposición
        try:
            response = requests.delete(f"{self.ZENODO_API_URL}/{deposition_id}", params=self._params(), timeout=30)
        except Exception as exc:
            logger.exception("Deleting deposition failed: %s", exc)
            messages.append("Failed to delete test deposition (network error).")
            success = False

        # Limpieza del fichero local
        if os.path.exists(file_path):
            os.remove(file_path)

        return jsonify({"success": success, "messages": messages})

    # -----------------------------
    # API wrappers
    # -----------------------------
    def get_all_depositions(self) -> dict:
        """
        Lista todas las deposiciones.
        """
        response = requests.get(self.ZENODO_API_URL, params=self._params(), headers=self.headers, timeout=30)
        if response.status_code != 200:
            raise Exception("Failed to get depositions")
        return response.json()

    def create_new_deposition(self, dataset: BaseDataset) -> dict:
        """
        Crea una nueva deposición usando los metadatos de un DataSet.
        """
        logger.info("Dataset sending to Zenodo...")
        logger.info("Publication type...%s", dataset.ds_meta_data.publication_type.value)

        metadata = {
            "title": dataset.ds_meta_data.title,
            "upload_type": "dataset" if dataset.ds_meta_data.publication_type.value == "none" else "publication",
            "publication_type": (
                dataset.ds_meta_data.publication_type.value
                if dataset.ds_meta_data.publication_type.value != "none"
                else None
            ),
            "description": dataset.ds_meta_data.description,
            "creators": [
                {
                    "name": author.name,
                    **({"affiliation": author.affiliation} if author.affiliation else {}),
                    **({"orcid": author.orcid} if author.orcid else {}),
                }
                for author in dataset.ds_meta_data.authors
            ],
            "keywords": (
                ["uvlhub"] if not dataset.ds_meta_data.tags else dataset.ds_meta_data.tags.split(", ") + ["uvlhub"]
            ),
            "access_right": "open",
            "license": "CC-BY-4.0",
        }

        data = {"metadata": metadata}
        response = requests.post(
            self.ZENODO_API_URL, params=self._params(), json=data, headers=self.headers, timeout=30
        )
        if response.status_code != 201:
            error_message = f"Failed to create deposition. Error details: {response.json()}"
            raise Exception(error_message)
        return response.json()

    def upload_file(self, dataset: BaseDataset, deposition_id: int, feature_model: FeatureModel, user=None) -> dict:
        """
        Sube un fichero a una deposición existente.
        """
        filename = feature_model.fm_meta_data.filename
        data = {"name": filename}
        user_id = current_user.id if user is None else user.id
        file_path = os.path.join(uploads_folder_name(), f"user_{str(user_id)}", f"dataset_{dataset.id}/", filename)

        publish_url = f"{self.ZENODO_API_URL}/{deposition_id}/files"
        try:
            with open(file_path, "rb") as fh:
                files = {"file": fh}
                response = requests.post(publish_url, params=self._params(), data=data, files=files, timeout=60)
        except FileNotFoundError:
            raise Exception(f"File not found: {file_path}")

        if response.status_code != 201:
            error_message = f"Failed to upload files. Error details: {response.json()}"
            raise Exception(error_message)
        return response.json()

    def publish_deposition(self, deposition_id: int) -> dict:
        """
        Publica una deposición.
        """
        publish_url = f"{self.ZENODO_API_URL}/{deposition_id}/actions/publish"
        response = requests.post(publish_url, params=self._params(), headers=self.headers, timeout=30)
        if response.status_code != 202:
            raise Exception("Failed to publish deposition")
        return response.json()

    def get_deposition(self, deposition_id: int) -> dict:
        """
        Obtiene una deposición por ID.
        """
        deposition_url = f"{self.ZENODO_API_URL}/{deposition_id}"
        response = requests.get(deposition_url, params=self._params(), headers=self.headers, timeout=30)
        if response.status_code != 200:
            raise Exception("Failed to get deposition")
        return response.json()

    def get_doi(self, deposition_id: int) -> str:
        """
        Obtiene el DOI de una deposición publicada.
        """
        return self.get_deposition(deposition_id).get("doi")
