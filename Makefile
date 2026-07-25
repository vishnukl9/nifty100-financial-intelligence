.PHONY: load ratios test report dashboard api clean

PYTHON = .venv/Scripts/python.exe
PYTEST = .venv/Scripts/pytest.exe
UVICORN = .venv/Scripts/uvicorn.exe
STREAMLIT = .venv/Scripts/streamlit.exe

load:
	$(PYTHON) src/etl/loader.py

ratios:
	$(PYTHON) src/analytics/ratios.py

test:
	set PYTHONPATH=. && $(PYTEST) tests/ --html=reports/pytest_report.html --self-contained-html

report:
	$(PYTHON) src/reports/tearsheet.py
	$(PYTHON) src/reports/sector_report.py
	$(PYTHON) src/reports/portfolio_report.py

dashboard:
	$(STREAMLIT) run src/dashboard/app.py

api:
	$(UVICORN) src.api.main:app --reload --host 127.0.0.1 --port 8000

clean:
	$(PYTHON) -c "import os, glob; [os.remove(f) for f in glob.glob('**/*.pyc', recursive=True)]"
	if exist .pytest_cache rmdir /s /q .pytest_cache
