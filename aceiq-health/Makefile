.PHONY: install up down seed api ui eval test lint clean

install:
	pip install -r requirements.txt

up:
	docker compose up -d
	@echo "Waiting for postgres to be ready..."
	@sleep 5

down:
	docker compose down

seed:
	python scripts/seed.py

api:
	uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

ui:
	streamlit run streamlit_app/app.py --server.port 8501

eval:
	@python eval/run_eval.py 2>/dev/null || node eval/run_eval.js

eval-node:
	node eval/run_eval.js

eval-http:
	python eval/run_eval.py

test:
	pytest tests/ -v

lint:
	ruff check backend/ eval/ scripts/ tests/
	ruff format --check backend/ eval/ scripts/ tests/

clean:
	docker compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
