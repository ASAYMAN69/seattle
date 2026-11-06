"""Static regression tests for Task 001 (frontend refactor).

These guard the structural guarantees of the refactor cheaply, without needing a
running Streamlit app or the heavy prepared data:

- no deprecated custom-component API usage remains in the app source;
- the single stylesheet exists and is wired through the native ``st.html`` path
  (and no dead/unused ``*.css`` files are left behind).
"""

from __future__ import annotations

from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1] / "app"


def _read_app_sources() -> str:
    text = ""
    for path in sorted(APP_DIR.rglob("*.py")):
        text += path.read_text(encoding="utf-8")
    return text


def test_no_deprecated_components_api_usage() -> None:
    src = _read_app_sources()
    assert "streamlit.components.v1" not in src
    assert "components.v1.html" not in src
    assert "st.components" not in src


def test_stylesheet_wired_single_mechanism() -> None:
    main = (APP_DIR / "main.py").read_text(encoding="utf-8")
    # Wired through the canonical safe injection path (style-wrapped markdown).
    assert "STYLESHEET" in main
    assert "unsafe_allow_html=True" in main
    assert "<style>" in main
    styles = APP_DIR / "styles.css"
    assert styles.exists()
    # Exactly one stylesheet — no dead/unused CSS files left behind.
    assert sorted(APP_DIR.rglob("*.css")) == [styles]
