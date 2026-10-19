PY=/Users/aidan/Desktop/bricks/.venv/bin/python
# Data from closed_system.duckdb (read-only, ~2 min), then the page, then tests, then Vercel.
build:
	caffeinate -i $(PY) scripts/build.py
	$(PY) scripts/build_page.py
page:
	$(PY) scripts/build_page.py
test:
	mkdir -p logs
	$(PY) -m pytest -q tests 2>&1 | tee logs/pytest.log
	node --test tests/api.test.js 2>&1 | tee logs/node.log
serve:
	node scripts/serve.js 4321
deploy:
	$(PY) scripts/deploy.py
