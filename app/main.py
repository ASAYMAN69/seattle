"""DataNova 2026 — Seattle Transit Equity Index.

Interactive demo app. Run with: streamlit run app/main.py
"""

import streamlit as st

from datanova import __version__
from app.data_io import PreparedDataError, load_prepared
from app.views.map_view import render_map

st.set_page_config(page_title="Seattle Transit Equity Index", layout="wide")

st.title("Seattle Transit Equity Index")
st.caption(
    "Who in Seattle is disconnected from opportunity? "
    f"DataNova 2026 · v{__version__}"
)

# Load all prepared inputs once; show a graceful error panel if any are missing
# or malformed instead of crashing the app.
try:
    data = load_prepared()
except PreparedDataError as exc:
    st.error(f"Prepared data could not be loaded: {exc}")
    st.info(
        "Run the analysis pipeline (`scripts/run_analysis.py`) so the app’s "
        "prepared inputs exist under data/prepared/. Contact the data team if "
        "this persists."
    )
    st.stop()

render_map(data)
