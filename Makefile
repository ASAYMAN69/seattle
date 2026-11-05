.PHONY: setup test app fetch-geometry

setup:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements.txt

test:
	.venv/bin/python -m pytest -q

app:
	.venv/bin/streamlit run app/main.py

fetch-geometry:
	.venv/bin/python scripts/fetch_geometry.py
