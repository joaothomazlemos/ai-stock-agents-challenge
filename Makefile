.PHONY: install dev-api lint format test build-index build push apply

install:
	uv sync --all-extras

dev-api:
	uv run uvicorn ai_stock_agent.infrastructure.app:app --host 0.0.0.0 --port 8080 --reload

lint:
	uv run ruff check src/

format:
	uv run ruff format src/

test:
	uv run pytest -m "not e2e and not llm" -v

build-index:
	uv run python scripts/build_index.py

build:
	docker build --platform linux/arm64 -t ai-stock-agent .

push:
	@echo "Tag and push to ECR — set ECR_REPO env var first"
	docker tag ai-stock-agent:latest $(ECR_REPO):latest
	docker push $(ECR_REPO):latest

apply:
	cd terraform && terraform apply
