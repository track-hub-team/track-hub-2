import gpxpy
import gpxpy.gpx
from typing import Dict, List, Tuple
import math
import logging

logger = logging.getLogger(__name__)


class GPXHandler:
    """Handler para archivos GPX."""
    
    def validate(self, file_path: str) -> bool:
        """Valida que el archivo GPX sea correcto."""
        try:
            with open(file_path, 'r', encoding='utf-8') as gpx_file:
                gpxpy.parse(gpx_file)
            logger.info(f"GPX validation passed: {file_path}")
            return True
        except Exception as e:
            logger.error(f"GPX validation failed: {file_path} - {e}")
            raise ValueError(f"Invalid GPX file: {str(e)}")
    
    def parse_gpx(self, file_path: str) -> Dict:
        """Parsea un archivo GPX y extrae información relevante."""
        with open(file_path, 'r', encoding='utf-8') as gpx_file:
            gpx = gpxpy.parse(gpx_file)
        
        # Extraer coordenadas, elevaciones y tiempos
        coordinates = []
        elevations = []
        times = []
        
        for track in gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    coordinates.append([point.latitude, point.longitude])
                    if point.elevation is not None:
                        elevations.append(point.elevation)
                    if point.time:
                        times.append(point.time)
        
        # Calcular estadísticas
        distance = self._calculate_distance(coordinates)
        elevation_gain, elevation_loss = self._calculate_elevation(elevations)
        duration = self._calculate_duration(times)
        bounds = self._calculate_bounds(coordinates)
        
        result = {
            'coordinates': coordinates,
            'distance': round(distance, 2),  # en metros
            'elevation_gain': round(elevation_gain, 2),
            'elevation_loss': round(elevation_loss, 2),
            'duration': duration,  # en segundos
            'points_count': len(coordinates),
            'bounds': bounds,
            'track_name': gpx.tracks[0].name if gpx.tracks else 'Unnamed Track'
        }
        
        logger.info(f"GPX parsed: {result['points_count']} points, {result['distance']}m distance")
        return result
    
    def _calculate_distance(self, coordinates: List[List[float]]) -> float:
        """Calcula distancia total usando fórmula de Haversine."""
        if len(coordinates) < 2:
            return 0.0
        
        total_distance = 0.0
        for i in range(len(coordinates) - 1):
            lat1, lon1 = coordinates[i]
            lat2, lon2 = coordinates[i + 1]
            total_distance += self._haversine(lat1, lon1, lat2, lon2)
        
        return total_distance
    
    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calcula distancia entre dos puntos usando Haversine (en metros)."""
        R = 6371000  # Radio de la Tierra en metros
        
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_phi / 2) ** 2 +
             math.cos(phi1) * math.cos(phi2) *
             math.sin(delta_lambda / 2) ** 2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def _calculate_elevation(self, elevations: List[float]) -> Tuple[float, float]:
        """Calcula desnivel acumulado positivo y negativo."""
        if len(elevations) < 2:
            return 0.0, 0.0
        
        gain = 0.0
        loss = 0.0
        
        for i in range(len(elevations) - 1):
            diff = elevations[i + 1] - elevations[i]
            if diff > 0:
                gain += diff
            else:
                loss += abs(diff)
        
        return gain, loss
    
    def _calculate_duration(self, times: List) -> float:
        """Calcula duración del track en segundos."""
        if len(times) < 2:
            return 0.0
        
        duration = (times[-1] - times[0]).total_seconds()
        return duration
    
    def _calculate_bounds(self, coordinates: List[List[float]]) -> Dict:
        """Calcula bounding box del track."""
        if not coordinates:
            return {
                'min_lat': 0,
                'max_lat': 0,
                'min_lon': 0,
                'max_lon': 0
            }
        
        lats = [c[0] for c in coordinates]
        lons = [c[1] for c in coordinates]
        
        return {
            'min_lat': min(lats),
            'max_lat': max(lats),
            'min_lon': min(lons),
            'max_lon': max(lons)
        }