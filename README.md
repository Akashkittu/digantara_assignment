docker compose up -d

py -3.12 -m pip install --user -r requirements.txt

py -3.12 -m alembic upgrade head

py -3.12 app/scripts/seed_ground_stations.py
py -3.12 app/scripts/fetch_tles.py --group active --limit 200
py -3.12 app/scripts/generate_passes_bulk.py --hours 6 --gs-limit 5 --step 30 --delete-existing

py -3.12 -m uvicorn app.main:app --reload
