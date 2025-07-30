import streamlit as st
import pyproj
import mgrs
import utm
import re
from typing import Tuple, Optional
import streamlit.components.v1 as components

# --- 페이지 설정 ---
st.set_page_config(
    page_title="Geographic Coordinate Converter",
    page_icon="🗺️",
    layout="wide"
)

# --- 좌표 변환 클래스 ---
class CoordinateConverter:
    """
    경위도, UTM, MGRS 좌표 간의 변환을 담당하는 클래스
    """
    def __init__(self):
        self.mgrs_converter = mgrs.MGRS()

    def lat_lon_to_utm(self, lat: float, lon: float) -> Tuple[int, float, float, str]:
        """경위도(Latitude/Longitude)를 UTM으로 변환"""
        try:
            easting, northing, zone_number, zone_letter = utm.from_latlon(lat, lon)
            return zone_number, easting, northing, zone_letter
        except Exception as e:
            raise ValueError(f"UTM conversion error: {str(e)}")

    def utm_to_lat_lon(self, zone_number: int, zone_letter: str, easting: float, northing: float) -> Tuple[float, float]:
        """UTM을 경위도(Latitude/Longitude)로 변환"""
        try:
            is_northern = zone_letter.upper() >= 'N'
            lat, lon = utm.to_latlon(easting, northing, zone_number, northern=is_northern)
            return lat, lon
        except Exception as e:
            raise ValueError(f"Latitude/Longitude conversion error: {str(e)}")

    def lat_lon_to_mgrs(self, lat: float, lon: float) -> str:
        """경위도(Latitude/Longitude)를 MGRS로 변환"""
        try:
            mgrs_coord = self.mgrs_converter.toMGRS(lat, lon, MGRSPrecision=5)
            return mgrs_coord.decode('utf-8') if isinstance(mgrs_coord, bytes) else mgrs_coord
        except Exception as e:
            raise ValueError(f"MGRS conversion error: {str(e)}")

    def mgrs_to_lat_lon(self, mgrs_coord: str) -> Tuple[float, float]:
        """MGRS를 경위도(Latitude/Longitude)로 변환"""
        try:
            lat, lon = self.mgrs_converter.toLatLon(mgrs_coord)
            return lat, lon
        except Exception as e:
            raise ValueError(f"Latitude/Longitude conversion error: {str(e)}")

    def validate_lat_lon(self, lat: float, lon: float) -> bool:
        """경위도 유효성 검사"""
        return -90 <= lat <= 90 and -180 <= lon <= 180

    def validate_mgrs(self, mgrs_coord: str) -> bool:
        """MGRS 좌표 유효성 검사 (라이브러리 변환 시도)"""
        try:
            self.mgrs_converter.toLatLon(mgrs_coord)
            return True
        except Exception:
            return False

# --- 지도 생성 함수 ---
def create_openlayers_map(lat: float, lon: float) -> str:
    """OpenLayers 지도 HTML 생성"""
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <title>OpenLayers Map</title>
      <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/ol@v9.1.0/ol.css" type="text/css">
      <style>
        .map {{ height: 450px; width: 100%; }}
        .info {{
          background: rgba(255, 255, 255, 0.8); padding: 10px; border-radius: 5px;
          margin: 10px; font-family: sans-serif;
        }}
      </style>
      <script src="https://cdn.jsdelivr.net/npm/ol@v9.1.0/dist/ol.js"></script>
    </head>
    <body>
      <div id="map" class="map"></div>
      <div class="info"><b>Location:</b> Latitude {lat:.6f}°, Longitude {lon:.6f}°</div>
      <script type="text/javascript">
        const coordinates = ol.proj.fromLonLat([{lon}, {lat}]);
        const marker = new ol.Feature({{ geometry: new ol.geom.Point(coordinates) }});
        marker.setStyle(new ol.style.Style({{
          image: new ol.style.Icon({{
            anchor: [0.5, 1], scale: 0.8,
            src: 'data:image/svg+xml;base64,' + btoa('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="red"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/></svg>')
          }})
        }}));
        const map = new ol.Map({{
          target: 'map',
          layers: [
            new ol.layer.Tile({{ source: new ol.source.OSM() }}),
            new ol.layer.Vector({{ source: new ol.source.Vector({{ features: [marker] }}) }})
          ],
          view: new ol.View({{ center: coordinates, zoom: 10 }})
        }});
      </script>
    </body>
    </html>
    """
    return html_code

# --- 메인 애플리케이션 ---
def main():
    st.title("🗺️ Geographic Coordinate Converter")
    st.markdown("Convert between Latitude/Longitude, UTM, and MGRS coordinates.")

    converter = CoordinateConverter()

    st.sidebar.header("Coordinate Input Settings")
    coord_type = st.sidebar.selectbox(
        "Select the input coordinate type:",
        ["Latitude/Longitude", "UTM", "MGRS"],
        key="coord_type_select"
    )

    if 'lat' not in st.session_state:
        st.session_state.lat = 37.5665
        st.session_state.lon = 126.9780

    col1, col2 = st.columns([1, 1])

    with col1:
        st.header("Coordinate Input & Conversion Results")
        lat, lon = None, None

        try:
            if coord_type == "Latitude/Longitude":
                st.subheader("Enter Latitude/Longitude Coordinates")
                # ✨ FIX: step과 format 인자를 명시적으로 지정
                lat_in = st.number_input("Latitude", min_value=-90.0, max_value=90.0, value=st.session_state.lat, step=0.000001, format="%.6f")
                lon_in = st.number_input("Longitude", min_value=-180.0, max_value=180.0, value=st.session_state.lon, step=0.000001, format="%.6f")

                if converter.validate_lat_lon(lat_in, lon_in):
                    lat, lon = lat_in, lon_in
                else:
                    st.error("Invalid Latitude/Longitude coordinates.")

            elif coord_type == "UTM":
                st.subheader("Enter UTM Coordinates")
                zone_num_in = st.number_input("Zone Number", 1, 60, 52)
                zone_letter_in = st.text_input("Zone Letter", "S", max_chars=1).upper()
                easting_in = st.number_input("Easting (m)", value=321000.0, step=1.0, format="%.1f")
                northing_in = st.number_input("Northing (m)", value=4160000.0, step=1.0, format="%.1f")

                if zone_letter_in and 'A' <= zone_letter_in <= 'Z':
                    lat, lon = converter.utm_to_lat_lon(zone_num_in, zone_letter_in, easting_in, northing_in)
                else:
                    st.error("Zone Letter must be a valid alphabet character.")

            elif coord_type == "MGRS":
                st.subheader("Enter MGRS Coordinate")
                mgrs_in = st.text_input("MGRS Coordinate", "52SCE2100060000").upper()

                if mgrs_in and converter.validate_mgrs(mgrs_in):
                    lat, lon = converter.mgrs_to_lat_lon(mgrs_in)
                elif mgrs_in:
                    st.error("Invalid MGRS coordinate format.")

            if lat is not None and lon is not None:
                st.session_state.lat, st.session_state.lon = lat, lon
                utm_zone_num, utm_easting, utm_northing, utm_zone_letter = converter.lat_lon_to_utm(lat, lon)
                mgrs_val = converter.lat_lon_to_mgrs(lat, lon)

                st.write("---")
                st.header("Conversion Results")
                st.subheader("📍 Latitude/Longitude")
                st.write(f"**Latitude:** `{lat:.6f}°`")
                st.write(f"**Longitude:** `{lon:.6f}°`")
                st.subheader("🗺️ UTM")
                st.write(f"**Zone:** `{utm_zone_num}{utm_zone_letter}`")
                st.write(f"**Easting:** `{utm_easting:,.1f} m`")
                st.write(f"**Northing:** `{utm_northing:,.1f} m`")
                st.subheader("🎯 MGRS")
                st.write(f"**MGRS:** `{mgrs_val}`")

        except Exception as e:
            st.error(f"An error occurred: {e}")

    with col2:
        st.header("Map Location")
        if 'lat' in st.session_state and st.session_state.lat is not None:
            map_html = create_openlayers_map(st.session_state.lat, st.session_state.lon)
            components.html(map_html, height=500)
        else:
            st.info("Enter and convert coordinates to display the location on the map.")


if __name__ == "__main__":
    main()