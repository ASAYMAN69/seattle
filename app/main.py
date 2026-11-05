"""DataNova 2026 — Seattle Transit Equity Index.

Interactive demo app. Run with: streamlit run app/main.py
"""

import streamlit as st

from datanova import __version__
from app.views.map_view import render_map

st.set_page_config(page_title="Seattle Transit Equity Index", layout="wide")

st.title("Seattle Transit Equity Index")
st.caption(
    "Who in Seattle is disconnected from opportunity? "
    f"DataNova 2026 · v{__version__}"
)

# Skeleton: render a real Seattle boundary map shell.
# Analysis layers (Need / Access / Gap) are added in later tasks.
try:
    render_map()
except FileNotFoundError as exc:
    st.error(
        f"Prepared data missing: {exc}. Run `python scripts/fetch_geometry.py` "
        "first to create the real Seattle boundary."
    )
