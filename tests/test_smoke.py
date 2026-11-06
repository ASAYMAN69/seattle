"""Smoke tests for the project skeleton."""

from pathlib import Path

import datanova


def test_version_exists() -> None:
    assert isinstance(datanova.__version__, str)
    assert datanova.__version__ == "0.1.0"


def test_app_main_imports() -> None:
    import app.main  # noqa: F401

    assert True


def test_app_main_guards_repo_root_on_syspath() -> None:
    """Regression: `streamlit run app/main.py` does NOT put the repo root on
    sys.path, so the app must insert it itself before importing `datanova`.
    (Runtime failure seen 2026-11-06: ModuleNotFoundError: datanova.)"""
    main_src = Path(__file__).resolve().parents[1] / "app" / "main.py"
    text = main_src.read_text()
    assert 'sys.path.insert(0, str(Path(__file__).resolve().parents[1]))' in text
    assert text.index("sys.path.insert") < text.index("from datanova import")
