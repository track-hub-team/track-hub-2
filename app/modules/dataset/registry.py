"""
Registro central de tipos de dataset disponibles en la plataforma.
Cada tipo define su modelo, handler de validación, formulario y plantillas.
"""

from typing import Dict, Type
from app.modules.dataset.models import BaseDataset, DataSet, UVLDataset, GPXDataset


class DataTypeHandler:
    """Handler base para validación de archivos por tipo."""
    ext = None
    name = None

    def validate(self, filepath: str):
        """Valida el archivo. Lanza excepción si no es válido."""
        return True


class UVLHandler(DataTypeHandler):
    ext = ".uvl"
    name = "uvl"

    def validate(self, filepath: str):
        # Validación básica: archivo existe y no está vacío
        import os
        if not os.path.exists(filepath):
            raise ValueError("File not found")
        if os.path.getsize(filepath) == 0:
            raise ValueError("File is empty")
        return True


class GPXHandler(DataTypeHandler):
    ext = ".gpx"
    name = "gpx"

    def validate(self, filepath: str):
        """Valida que sea XML válido y tenga raíz <gpx>."""
        import xml.etree.ElementTree as ET
        import os
        
        if not os.path.exists(filepath):
            raise ValueError("File not found")
        
        try:
            tree = ET.parse(filepath)
            root = tree.getroot()
            # Verificar que la raíz sea 'gpx' (ignorando namespace)
            if not root.tag.lower().endswith("gpx"):
                raise ValueError("Invalid GPX file: root element is not <gpx>")
        except ET.ParseError as e:
            raise ValueError(f"Invalid XML structure: {str(e)}")
        
        return True


class DatasetTypeDescriptor:
    """Descriptor completo de un tipo de dataset."""
    
    def __init__(
        self,
        kind: str,
        model_class: Type[BaseDataset],
        handler: DataTypeHandler,
        display_name: str,
        file_extensions: list,
        upload_template: str = None,  # plantilla parcial de dropzone
        detail_template: str = None,  # plantilla parcial de vista detalle
    ):
        self.kind = kind
        self.model_class = model_class
        self.handler = handler
        self.display_name = display_name
        self.file_extensions = file_extensions
        self.upload_template = upload_template
        self.detail_template = detail_template


# ✅ REGISTRO GLOBAL DE TIPOS
DATASET_TYPE_REGISTRY: Dict[str, DatasetTypeDescriptor] = {
    "uvl": DatasetTypeDescriptor(
        kind="uvl",
        model_class=UVLDataset,
        handler=UVLHandler(),
        display_name="UVL Feature Model",
        file_extensions=[".uvl"],
        upload_template="dataset/blocks/upload_uvl.html",
        detail_template="dataset/blocks/uvl_tree.html",
    ),
    "gpx": DatasetTypeDescriptor(
        kind="gpx",
        model_class=GPXDataset,
        handler=GPXHandler(),
        display_name="GPX Track",
        file_extensions=[".gpx"],
        upload_template="dataset/blocks/upload_gpx.html",
        detail_template="dataset/blocks/gpx_preview.html",
    ),
    "base": DatasetTypeDescriptor(
        kind="base",
        model_class=DataSet,
        handler=DataTypeHandler(),
        display_name="Generic Dataset",
        file_extensions=[],
        upload_template=None,
        detail_template=None,
    ),
}


def get_descriptor(kind: str) -> DatasetTypeDescriptor:
    """Obtiene el descriptor de un tipo de dataset."""
    return DATASET_TYPE_REGISTRY.get(kind, DATASET_TYPE_REGISTRY["base"])


def get_allowed_extensions() -> list:
    """Retorna todas las extensiones permitidas por todos los tipos."""
    exts = []
    for desc in DATASET_TYPE_REGISTRY.values():
        exts.extend(desc.file_extensions)
    return exts


def infer_kind_from_filename(filename: str) -> str:
    """Infiere el tipo de dataset según la extensión del archivo."""
    import os
    _, ext = os.path.splitext(filename.lower())
    
    for kind, descriptor in DATASET_TYPE_REGISTRY.items():
        if ext in descriptor.file_extensions:
            return kind
    
    return "base"  # fallback