# converter.py
import mgrs
import utm
from typing import Tuple

class CoordinateConverter:
    def __init__(self):
        self.mgrs_converter = mgrs.MGRS()

    def lat_lon_to_utm(self, lat: float, lon: float) -> Tuple[int, float, float, str]:
        easting, northing, zone_number, zone_letter = utm.from_latlon(lat, lon)
        return zone_number, easting, northing, zone_letter

    def utm_to_lat_lon(self, zone_number: int, zone_letter: str, easting: float, northing: float) -> Tuple[float, float]:
        is_northern = zone_letter.upper() >= 'N'
        lat, lon = utm.to_latlon(easting, northing, zone_number, northern=is_northern)
        return lat, lon

    def lat_lon_to_mgrs(self, lat: float, lon: float) -> str:
        mgrs_coord = self.mgrs_converter.toMGRS(lat, lon, MGRSPrecision=5)
        return mgrs_coord.decode('utf-8') if isinstance(mgrs_coord, bytes) else mgrs_coord

    def mgrs_to_lat_lon(self, mgrs_coord: str) -> Tuple[float, float]:
        lat, lon = self.mgrs_converter.toLatLon(mgrs_coord)
        return lat, lon

    def validate_lat_lon(self, lat: float, lon: float) -> bool:
        return -90 <= lat <= 90 and -180 <= lon <= 180

    def validate_mgrs(self, mgrs_coord: str) -> bool:
        try:
            self.mgrs_converter.toLatLon(mgrs_coord)
            return True
        except Exception:
            return False
