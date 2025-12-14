import os
import shutil
from datetime import datetime, timezone

from dotenv import load_dotenv

from app.modules.auth.models import User
from app.modules.dataset.models import Author, DSMetaData, DSMetrics, GPXDataset, PublicationType, UVLDataset
from app.modules.featuremodel.models import FeatureModel, FMMetaData
from app.modules.hubfile.models import Hubfile
from app.modules.versioning.models import DatasetVersion
from core.seeders.BaseSeeder import BaseSeeder


class DataSetSeeder(BaseSeeder):

    priority = 2  # Lower priority

    def run(self):
        # Retrieve users
        user1 = User.query.filter_by(email="user1@example.com").first()
        user2 = User.query.filter_by(email="user2@example.com").first()
        user3 = User.query.filter_by(email="user3@example.com").first()
        user4 = User.query.filter_by(email="user4@example.com").first()

        if not user1 or not user2 or not user3 or not user4:
            raise Exception("Users not found. Please seed users first.")

        # Create DSMetrics instance
        ds_metrics = DSMetrics(number_of_models="5", number_of_features="50")
        seeded_ds_metrics = self.seed([ds_metrics])[0]

        # Create DSMetaData instances
        # 4 UVL (user1 y user2) + 4 GPX (user3 y user4)
        ds_meta_data_list = [
            # User1 - 2 datasets UVL
            DSMetaData(
                deposition_id=1,
                title="Sample dataset 1 UVL",
                description="Description for dataset 1",
                publication_type=PublicationType.DATA_MANAGEMENT_PLAN,
                publication_doi="10.1234/dataset1",
                dataset_doi="10.1234/dataset1",
                tags="tag1, tag2, uvl",
                ds_metrics_id=seeded_ds_metrics.id,
            ),
            DSMetaData(
                deposition_id=2,
                title="Sample dataset 2 UVL",
                description="Description for dataset 2",
                publication_type=PublicationType.DATA_MANAGEMENT_PLAN,
                publication_doi="10.1234/dataset2",
                dataset_doi="10.1234/dataset2",
                tags="tag1, tag2, uvl",
                ds_metrics_id=seeded_ds_metrics.id,
            ),
            # User2 - 2 datasets UVL
            DSMetaData(
                deposition_id=3,
                title="Sample dataset 3 UVL",
                description="Description for dataset 3",
                publication_type=PublicationType.DATA_MANAGEMENT_PLAN,
                publication_doi="10.1234/dataset3",
                dataset_doi="10.1234/dataset3",
                tags="tag1, tag2, uvl",
                ds_metrics_id=seeded_ds_metrics.id,
            ),
            DSMetaData(
                deposition_id=4,
                title="Sample dataset 4 UVL",
                description="Description for dataset 4",
                publication_type=PublicationType.DATA_MANAGEMENT_PLAN,
                publication_doi="10.1234/dataset4",
                dataset_doi="10.1234/dataset4",
                tags="tag1, tag2, uvl",
                ds_metrics_id=seeded_ds_metrics.id,
            ),
            # User3 - 2 datasets GPX
            DSMetaData(
                deposition_id=5,
                title="Sample dataset 5 GPX",
                description="GPS tracks dataset 5",
                publication_type=PublicationType.DATA_MANAGEMENT_PLAN,
                publication_doi="10.1234/dataset5",
                dataset_doi="10.1234/dataset5",
                tags="gpx, gps, tracks",
                ds_metrics_id=seeded_ds_metrics.id,
            ),
            DSMetaData(
                deposition_id=6,
                title="Sample dataset 6 GPX",
                description="GPS tracks dataset 6",
                publication_type=PublicationType.DATA_MANAGEMENT_PLAN,
                publication_doi="10.1234/dataset6",
                dataset_doi="10.1234/dataset6",
                tags="gpx, gps, tracks",
                ds_metrics_id=seeded_ds_metrics.id,
            ),
            # User4 - 2 datasets GPX
            DSMetaData(
                deposition_id=7,
                title="Sample dataset 7 GPX",
                description="GPS tracks dataset 7",
                publication_type=PublicationType.DATA_MANAGEMENT_PLAN,
                publication_doi="10.1234/dataset7",
                dataset_doi="10.1234/dataset7",
                tags="gpx, gps, tracks",
                ds_metrics_id=seeded_ds_metrics.id,
            ),
            DSMetaData(
                deposition_id=8,
                title="Sample dataset 8 GPX",
                description="GPS tracks dataset 8",
                publication_type=PublicationType.DATA_MANAGEMENT_PLAN,
                publication_doi="10.1234/dataset8",
                dataset_doi="10.1234/dataset8",
                tags="gpx, gps, tracks",
                ds_metrics_id=seeded_ds_metrics.id,
            ),
        ]
        seeded_ds_meta_data = self.seed(ds_meta_data_list)

        # Create Author instances
        authors = [
            Author(
                name=f"Author {i+1}",
                affiliation=f"Affiliation {i+1}",
                orcid=f"0000-0000-0000-000{i}",
                ds_meta_data_id=seeded_ds_meta_data[i].id,
            )
            for i in range(8)
        ]
        self.seed(authors)

        # Create DataSet instances - SEPARAR POR TIPO
        # Primero los UVL
        uvl_datasets = [
            # User1 - 2 UVL
            UVLDataset(
                user_id=user1.id,
                ds_meta_data_id=seeded_ds_meta_data[0].id,
                created_at=datetime.now(timezone.utc),
            ),
            UVLDataset(
                user_id=user1.id,
                ds_meta_data_id=seeded_ds_meta_data[1].id,
                created_at=datetime.now(timezone.utc),
            ),
            # User2 - 2 UVL
            UVLDataset(
                user_id=user2.id,
                ds_meta_data_id=seeded_ds_meta_data[2].id,
                created_at=datetime.now(timezone.utc),
            ),
            UVLDataset(
                user_id=user2.id,
                ds_meta_data_id=seeded_ds_meta_data[3].id,
                created_at=datetime.now(timezone.utc),
            ),
        ]
        seeded_uvl_datasets = self.seed(uvl_datasets)

        # Luego los GPX
        gpx_datasets = [
            # User3 - 2 GPX
            GPXDataset(
                user_id=user3.id,
                ds_meta_data_id=seeded_ds_meta_data[4].id,
                created_at=datetime.now(timezone.utc),
            ),
            GPXDataset(
                user_id=user3.id,
                ds_meta_data_id=seeded_ds_meta_data[5].id,
                created_at=datetime.now(timezone.utc),
            ),
            # User4 - 2 GPX
            GPXDataset(
                user_id=user4.id,
                ds_meta_data_id=seeded_ds_meta_data[6].id,
                created_at=datetime.now(timezone.utc),
            ),
            GPXDataset(
                user_id=user4.id,
                ds_meta_data_id=seeded_ds_meta_data[7].id,
                created_at=datetime.now(timezone.utc),
            ),
        ]
        seeded_gpx_datasets = self.seed(gpx_datasets)

        # Combinar todos los datasets en orden
        seeded_datasets = seeded_uvl_datasets + seeded_gpx_datasets

        # Create version 1.0.0 para todos
        versions = [
            DatasetVersion(
                dataset_id=dataset.id,
                version_number="1.0.0",
                changelog="Initial release",
                created_by_id=dataset.user_id,
                files_snapshot={},
                created_at=datetime.now(timezone.utc),
            )
            for dataset in seeded_datasets
        ]
        self.seed(versions)

        # Create UVL files (solo para los 4 primeros datasets - UVL)
        fm_meta_data_list = [
            FMMetaData(
                filename=f"file{i+1}.uvl",
                title=f"Feature Model {i+1}",
                description=f"Description for feature model {i+1}",
                publication_type=PublicationType.SOFTWARE_DOCUMENTATION,
                publication_doi=f"10.1234/fm{i+1}",
                tags="tag1, tag2",
                file_version="1.0",
            )
            for i in range(12)  # 3 archivos × 4 datasets UVL
        ]
        seeded_fm_meta_data = self.seed(fm_meta_data_list)

        # Create Author instances for FMMetaData
        fm_authors = [
            Author(
                name=f"Author {i+9}",
                affiliation=f"Affiliation {i+9}",
                orcid=f"0000-0000-0000-000{i+9}",
                fm_meta_data_id=seeded_fm_meta_data[i].id,
            )
            for i in range(12)
        ]
        self.seed(fm_authors)

        # Create FeatureModels for UVL datasets
        feature_models = [
            FeatureModel(
                data_set_id=seeded_datasets[i // 3].id, fm_meta_data_id=seeded_fm_meta_data[i].id  # 3 files per dataset
            )
            for i in range(12)
        ]
        seeded_feature_models = self.seed(feature_models)

        # Copy UVL files
        load_dotenv()
        working_dir = os.getenv("WORKING_DIR", "")
        src_folder = os.path.join(working_dir, "app", "modules", "dataset", "uvl_examples")

        for i in range(12):
            file_name = f"file{i+1}.uvl"
            feature_model = seeded_feature_models[i]
            dataset = next(ds for ds in seeded_datasets if ds.id == feature_model.data_set_id)
            user_id = dataset.user_id

            dest_folder = os.path.join(working_dir, "uploads", f"user_{user_id}", f"dataset_{dataset.id}")
            os.makedirs(dest_folder, exist_ok=True)
            shutil.copy(os.path.join(src_folder, file_name), dest_folder)

            file_path = os.path.join(dest_folder, file_name)

            uvl_file = Hubfile(
                name=file_name,
                checksum=f"checksum{i+1}",
                size=os.path.getsize(file_path),
                feature_model_id=feature_model.id,
            )
            self.seed([uvl_file])

        # Create GPX files (para los 4 últimos datasets - GPX)
        for dataset_idx in [4, 5, 6, 7]:  # Índices de datasets GPX
            dataset = seeded_datasets[dataset_idx]
            user_id = dataset.user_id

            dest_folder = os.path.join(working_dir, "uploads", f"user_{user_id}", f"dataset_{dataset.id}")
            os.makedirs(dest_folder, exist_ok=True)

            # 3 archivos GPX por dataset
            for file_idx in range(3):
                file_name = f"track{file_idx+1}.gpx"

                # Crear FMMetaData para GPX
                gpx_fm_meta = FMMetaData(
                    filename=file_name,
                    title=f"GPS Track {file_idx+1}",
                    description=f"GPS track for dataset {dataset_idx+1}",
                    publication_type=PublicationType.OTHER,
                    tags="gpx, gps",
                    file_version="1.0",
                )
                seeded_gpx_fm = self.seed([gpx_fm_meta])[0]

                gpx_feature_model = FeatureModel(data_set_id=dataset.id, fm_meta_data_id=seeded_gpx_fm.id)
                seeded_gpx_feature_model = self.seed([gpx_feature_model])[0]

                # Crear archivo GPX mínimo válido
                dest_file = os.path.join(dest_folder, file_name)
                gpx_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="UVLHub Seeder">
  <trk>
    <name>Sample Track {file_idx+1} - Dataset {dataset_idx+1}</name>
    <trkseg>
      <trkpt lat="37.389092" lon="-5.984459"><ele>10</ele></trkpt>
      <trkpt lat="37.389192" lon="-5.984559"><ele>12</ele></trkpt>
      <trkpt lat="37.389292" lon="-5.984659"><ele>15</ele></trkpt>
    </trkseg>
  </trk>
</gpx>"""
                with open(dest_file, "w") as f:
                    f.write(gpx_content)

                gpx_file = Hubfile(
                    name=file_name,
                    checksum=f"gpx_checksum_{dataset_idx}_{file_idx}",
                    size=os.path.getsize(dest_file),
                    feature_model_id=seeded_gpx_feature_model.id,
                )
                self.seed([gpx_file])
