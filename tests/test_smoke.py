"""Smoke tests for the project skeleton."""

import datanova


def test_version_exists() -> None:
    assert isinstance(datanova.__version__, str)
    assert datanova.__version__ == "0.1.0"


def test_app_main_imports() -> None:
    import app.main  # noqa: F401

    assert True
