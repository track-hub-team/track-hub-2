import csv
import io
import sys
import json
from datetime import datetime
from typing import Optional

from app.modules.auth.models import User
from app.modules.gpx.repositories import GPXDatasetRepository, GPXMetaDataRepository
from app.modules.gpx.models import GPXDifficultyRating
from core.services.BaseService import BaseService
from app import db
from app.modules.gpx.models import GPXDataset, GPXMetaData
from app.modules.dataset.models import BaseDataset

class GPXDatasetService(BaseService):
    def __init__(self):
        super().__init__(GPXDatasetRepository())
        self.gpx_metadata_repository = GPXMetaDataRepository()

    def create_from_upload(self, user_id, name, difficulty, description, gpx_content, gpx_data):
        """Create GPX dataset from user upload"""
        
        # Create metadata
        metadata = GPXMetaData(
            name=name,
            difficulty=GPXDifficultyRating[difficulty] if difficulty else None,
            length_3d=gpx_data.get('length_3d'),
            uphill=gpx_data.get('uphill'),
            downhill=gpx_data.get('downhill'),
            moving_time=gpx_data.get('moving_time'),
            max_elevation=gpx_data.get('max_elevation'),
            max_speed=gpx_data.get('max_speed'),
            gpx_content=gpx_content,
            bounds_min_lat=gpx_data.get('bounds_min_lat'),
            bounds_max_lat=gpx_data.get('bounds_max_lat'),
            bounds_min_lon=gpx_data.get('bounds_min_lon'),
            bounds_max_lon=gpx_data.get('bounds_max_lon'),
            start_time=gpx_data.get('start_time'),
            hikr_user=None,  # User upload, not from hikr
            hikr_url=None,
            hikr_id=None
        )
        
        # Create dataset
        dataset = GPXDataset(
            dataset_type='gpx',
            user_id=user_id,
            gpx_meta_data=metadata
        )
        
        db.session.add(metadata)
        db.session.add(dataset)
        db.session.commit()
        
        return dataset

    def import_from_csv(self, file, user: User) -> dict:
        """Import GPX datasets from CSV file"""
        
        # Increase CSV field size limit for large GPX content
        maxInt = sys.maxsize
        while True:
            try:
                csv.field_size_limit(maxInt)
                break
            except OverflowError:
                maxInt = int(maxInt/10)
        
        # ✅ VERIFICAR que user.id existe
        if not user or not user.id:
            return {
                'imported': 0,
                'total_rows': 0,
                'errors': ['Invalid user provided']
            }
        
        user_id = user.id  # ← GUARDAR el ID al inicio
        
        imported = 0
        errors = []
        total_rows = 0
        
        try:
            # Decode file
            content = file.read().decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(content))
            
            for row in csv_reader:
                    
                total_rows += 1
                
                try:
                    # Check if already exists
                    hikr_id = row.get('_id')
                    if hikr_id and self.gpx_metadata_repository.get_by_hikr_id(hikr_id):
                        continue
                    
                    # Parse difficulty
                    difficulty = None
                    diff_str = row.get('difficulty', '').strip()
                    if diff_str:
                        difficulty_code = diff_str.split('-')[0].strip().split()[0]
                        try:
                            difficulty = GPXDifficultyRating(difficulty_code)
                        except ValueError:
                            pass
                    
                    # Parse bounds
                    bounds_data = self._parse_bounds(row.get('bounds'))
                    
                    # Parse dates
                    start_time = self._parse_datetime(row.get('start_time'))
                    end_time = self._parse_datetime(row.get('end_time'))
                    
                    # Create GPX metadata
                    gpx_data = {
                        'name': row.get('name', 'Unnamed Track'),
                        'description': None,
                        'hikr_id': hikr_id,
                        'hikr_user': row.get('user'),
                        'hikr_url': row.get('url'),
                        'length_2d': self._parse_float(row.get('length_2d')),
                        'length_3d': self._parse_float(row.get('length_3d')),
                        'max_elevation': self._parse_float(row.get('max_elevation')),
                        'min_elevation': self._parse_float(row.get('min_elevation')),
                        'uphill': self._parse_float(row.get('uphill')),
                        'downhill': self._parse_float(row.get('downhill')),
                        'start_time': start_time,
                        'end_time': end_time,
                        'moving_time': self._parse_float(row.get('moving_time')),
                        'max_speed': self._parse_float(row.get('max_speed')),
                        'difficulty': difficulty,
                        'bounds_min_lat': bounds_data['min_lat'],
                        'bounds_max_lat': bounds_data['max_lat'],
                        'bounds_min_lon': bounds_data['min_lon'],
                        'bounds_max_lon': bounds_data['max_lon'],
                        'gpx_content': row.get('gpx'),
                        'tags': None,
                    }
                    
                    print(f"  Row {total_rows}: Creating '{gpx_data['name']}'...")  # ← DEBUG
                    
                    # Create dataset - ✅ PASAR user_id, no user
                    dataset = self.create_gpx_dataset(
                        user_id=user_id,  # ← USAR la variable
                        gpx_data=gpx_data
                    )
                    
                    if dataset:
                        imported += 1
                    
                except Exception as e:
                    error_msg = f"Row {total_rows}: {str(e)}"
                    errors.append(error_msg)
                    print(f"    ✗ Error: {e}")  # ← DEBUG
                    continue
            
            return {
                'imported': imported,
                'total_rows': total_rows,
                'errors': errors
            }
            
        except Exception as e:
            return {
                'imported': 0,
                'total_rows': 0,
                'errors': [f"Fatal error: {str(e)}"]
            }
    
    def _parse_bounds(self, bounds_str: str) -> dict:
        """Parse bounds JSON string"""
        try:
            if not bounds_str:
                return {
                    'min_lat': None,
                    'max_lat': None,
                    'min_lon': None,
                    'max_lon': None
                }
            
            # Parse JSON (with single quotes, need to convert)
            bounds_str = bounds_str.replace("'", '"')
            bounds = json.loads(bounds_str)
            
            return {
                'min_lat': bounds.get('min', {}).get('coordinates', [None, None])[1],
                'max_lat': bounds.get('max', {}).get('coordinates', [None, None])[1],
                'min_lon': bounds.get('min', {}).get('coordinates', [None, None])[0],
                'max_lon': bounds.get('max', {}).get('coordinates', [None, None])[0],
            }
        except:
            return {
                'min_lat': None,
                'max_lat': None,
                'min_lon': None,
                'max_lon': None
            }
    
    def _parse_datetime(self, date_str: str) -> Optional[datetime]:
        """Parse datetime string"""
        if not date_str:
            return None
        try:
            # Try parsing "2018-05-11 07:37:40" format
            return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        except:
            try:
                # Try ISO format
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            except:
                return None
    
    def _parse_float(self, value) -> Optional[float]:
        """Safely parse float value"""
        if not value:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
        
    def get_all(self):
        """Get all GPX datasets with metadata"""
        from app.modules.gpx.models import GPXDataset
        from app import db
        
        return db.session.query(GPXDataset).join(
            GPXDataset.gpx_meta_data
        ).order_by(GPXDataset.created_at.desc()).all()
    
    def get_by_id(self, dataset_id: int):
        """Get GPX dataset by ID"""
        from app.modules.gpx.models import GPXDataset
        return GPXDataset.query.get(dataset_id)
    
    def get_all_gpx_datasets(self):
        """Alias for get_all() - compatibility"""
        return self.get_all()
    
    def create_gpx_dataset(self, user_id: int, gpx_data: dict):
        """Create GPX dataset with metadata"""
        from app.modules.gpx.models import GPXDataset, GPXMetaData
        from app import db
        
        
        if not user_id:
            raise ValueError("user_id cannot be None")
        
        try:
            # Create GPX metadata FIRST
            gpx_metadata = GPXMetaData(**gpx_data)
            db.session.add(gpx_metadata)
            db.session.flush()
            
            # Create GPX dataset directly (inherits from BaseDataset)
            # NO crear BaseDataset por separado
            gpx_dataset = GPXDataset(
                dataset_type='gpx',
                user_id=user_id,  # ← Pasar directamente a GPXDataset
                gpx_meta_data_id=gpx_metadata.id
            )
            db.session.add(gpx_dataset)
            db.session.commit()
            
            return gpx_dataset
            
        except Exception as e:
            print(f"      ✗ ERROR: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            raise e