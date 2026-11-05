"""Map view for the Seattle Transit Equity Index app."""

from pathlib import Path

import folium
import geopandas as gpd
import streamlit as st

PREPARED_DIR = Path(__file__).resolve().parents[2] / "data" / "prepared"
BOUNDARY_PATH = PREPARED_DIR / "seattle_boundary.geojson"


def load_boundary() -> gpd.GeoDataFrame:
    """Load the real Seattle boundary GeoJSON.

    Raises:
        FileNotFoundError: if the prepared boundary is missing.
    """
    if not BOUNDARY_PATH.exists():
        raise FileNotFoundError(BOUNDARY_PATH)
    gdf = gpd.read_file(BOUNDARY_PATH)
    if gdf.empty:
        raise ValueError(f"{BOUNDARY_PATH} contains no features")
    return gdf


def render_map() -> None:
    """Render the skeleton map shell with the Seattle boundary layer."""
    boundary = load_boundary()

    bounds = boundary.total_bounds  # (minx, miny, maxx, maxy)
    center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]

    m = folium.Map(location=center, zoom_start=11, tiles="OpenStreetMap")

    folium.GeoJson(
        boundary,
        name="Seattle boundary",
        style_function=lambda _: {
            "color": "#1f3a5f",
            "weight": 2,
            "fillColor": "#d9e2ec",
            "fillOpacity": 0.15,
        },
    ).add_to(m)

    folium.LayerControl().add_to(m)

    # Streamlit-friendly embedding
    st.components.v1.html(m._repr_html_(), height=640, scrolling=False)
