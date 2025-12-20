.PHONY: install run run-api run-ui test clean docker-up docker-down help

# Default target
help:
	@echo "RBAC Policy Engine - Available Commands"
	@echo "========================================"
	@echo "make install    - Install all dependencies"
	@echo "make run        - Run both API and UI (recommended)"
	@echo "make run-api    - Run only the FastAPI backend"
	@echo "make run-ui     - Run only the Streamlit UI"
	@echo "make test       - Run all tests"
	@echo "make clean      - Clean cache and temporary files"
	@echo "make docker-up  - Start with Docker Compose"
	@echo "make docker-down - Stop Docker containers"

# Install dependencies
install:
	pip install -r requirements.txt

# Run both API and UI
run:
	@echo "Starting RBAC Policy Engine..."
	@echo "API will be available at: http://localhost:8000"
	@echo "UI will be available at: http://localhost:8501"
	@start /B uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
	@timeout /t 3 >nul
	@streamlit run src/ui/app.py

# Run only API
run-api:
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Run only UI
run-ui:
	streamlit run src/ui/app.py

# Run tests
test:
	pytest tests/ -v --tb=short

# Clean cache
clean:
	@if exist "__pycache__" rmdir /s /q __pycache__
	@if exist ".pytest_cache" rmdir /s /q .pytest_cache
	@if exist "data\cache" rmdir /s /q data\cache
	@echo "Cleaned successfully"

# Docker commands
docker-up:
	docker-compose up --build -d

docker-down:
	docker-compose down
