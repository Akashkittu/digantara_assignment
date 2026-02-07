# Digantara - Ground Pass Prediction (Backend)

## Run Postgres (Docker)
docker compose up -d

## Run API (no venv)
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload

## Test
GET http://127.0.0.1:8000/health
