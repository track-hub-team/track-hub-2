import logging
import os
import xml.etree.ElementTree as ET
from typing import Type

from flask_wtf import FlaskForm

from app.modules.dataset.models import BaseDataset, GPXDataset, UVLDataset

logger = logging.getLogger(__name__)


# === Handlers para validación por tipo ===
class DataTypeHandler:
    """Interfaz base para validadores de tipos de archivo."""

    ext = ""
    name = ""

    def validate(self, filepath: str) -> bool:
        raise NotImplementedError


class UVLHandler(DataTypeHandler):
    ext = ".uvl"
    name = "uvl"

    def validate(self, filepath: str) -> bool:
        if not os.path.exists(filepath):
            raise ValueError("File not found")
        if os.path.getsize(filepath) == 0:
            raise ValueError("File is empty")

        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            # Validación básica: debe contener "features"
            if "features" not in content.lower():
                raise ValueError("Invalid UVL file: missing 'features' section")

        return True


class GPXHandler(DataTypeHandler):
    ext = ".gpx"
    name = "gpx"

    def validate(self, filepath: str) -> bool:
        if not os.path.exists(filepath):
            raise ValueError("File not found")
        if os.path.getsize(filepath) == 0:
            raise ValueError("File is empty")

        try:
            tree = ET.parse(filepath)
            root = tree.getroot()

            # Verificar que es un archivo GPX válido
            if not root.tag.endswith("gpx"):
                raise ValueError("Invalid GPX file: root element is not <gpx>")

            # Verificar que tiene al menos un track o waypoint
            namespaces = {"gpx": "http://www.topografix.com/GPX/1/1"}
            tracks = root.findall(".//gpx:trk", namespaces) or root.findall(".//trk")
            waypoints = root.findall(".//gpx:wpt", namespaces) or root.findall(".//wpt")

            if not tracks and not waypoints:
                raise ValueError("Invalid GPX file: no tracks or waypoints found")

            return True
        except ET.ParseError as e:
            raise ValueError(f"Invalid GPX file: XML parsing error - {str(e)}")


# === Descriptor de tipo de dataset ===
class DatasetTypeDescriptor:
    """Descriptor completo de un tipo de dataset."""

    def __init__(
        self,
        kind: str,
        model_class: Type[BaseDataset],
        handler: DataTypeHandler,
        display_name: str,
        file_extensions: list,
        form_class: Type[FlaskForm],  # ✅ NUEVO
        upload_template: str = None,
        detail_template: str = None,
        icon: str = "file",  # ✅ NUEVO: ícono para UI
        color: str = "primary",  # ✅ NUEVO: color para UI
    ):
        self.kind = kind
        self.model_class = model_class
        self.handler = handler
        self.display_name = display_name
        self.file_extensions = file_extensions
        self.form_class = form_class  # ✅ NUEVO
        self.upload_template = upload_template
        self.detail_template = detail_template
        self.icon = icon  # ✅ NUEVO
        self.color = color  # ✅ NUEVO


# ✅ IMPORTAR los formularios
from app.modules.dataset.forms import (
    GPXFeatureModelForm,
    UVLFeatureModelForm,
)

# === Registro global de tipos ===
DATASET_TYPE_REGISTRY = {
    "uvl": DatasetTypeDescriptor(
        kind="uvl",
        model_class=UVLDataset,
        handler=UVLHandler(),
        display_name="UVL Feature Model",
        file_extensions=[".uvl"],
        form_class=UVLFeatureModelForm,  # ✅ NUEVO
        upload_template="dataset/blocks/upload_uvl.html",
        detail_template="dataset/blocks/uvl_detail.html",
        icon="git-branch",  # ✅ Ícono de árbol (Feather Icons)
        color="success",  # ✅ Verde para UVL
    ),
    "gpx": DatasetTypeDescriptor(
        kind="gpx",
        model_class=GPXDataset,
        handler=GPXHandler(),
        display_name="GPX Track",
        file_extensions=[".gpx"],
        form_class=GPXFeatureModelForm,  # ✅ NUEVO
        upload_template="dataset/blocks/upload_gpx.html",
        detail_template="dataset/blocks/gpx_detail.html",
        icon="map",  # ✅ Ícono de mapa (Feather Icons)
        color="info",  # ✅ Azul para GPX
    ),
}


# === Funciones auxiliares ===
def get_descriptor(kind: str) -> DatasetTypeDescriptor:
    """Obtiene el descriptor de un tipo de dataset."""
    descriptor = DATASET_TYPE_REGISTRY.get(kind)
    if not descriptor:
        raise ValueError(f"Unknown dataset kind: {kind}")
    return descriptor


def infer_kind_from_filename(filename: str) -> str:
    """Infiere el tipo de dataset desde la extensión del archivo."""
    _, ext = os.path.splitext(filename.lower())

    for kind, descriptor in DATASET_TYPE_REGISTRY.items():
        if ext in descriptor.file_extensions:
            return kind

    # Por defecto, retornar "base"
    return "base"


def get_allowed_extensions() -> list:
    """Retorna todas las extensiones permitidas."""
    extensions = []
    for descriptor in DATASET_TYPE_REGISTRY.values():
        extensions.extend(descriptor.file_extensions)
    return extensions


def get_all_descriptors() -> dict:
    """Retorna todos los descriptors registrados."""
    return DATASET_TYPE_REGISTRY
