from dotenv import load_dotenv

# ✅ Load .env BEFORE importing anything that reads env vars
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.db.conn import check_db

app = FastAPI(title="Digantara Ground Pass Prediction", version="0.1.0")

# Rate limiting (in-memory for now)
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Global error handler (so stacktraces don't leak to user)
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "message": "Something went wrong."},
    )

@app.get("/health")
@limiter.limit("60/minute")
def health(request: Request):
    return {"status": "ok"}

@app.get("/")
@limiter.limit("60/minute")
def root(request: Request):
    return {"service": "ground-pass-prediction", "status": "running"}

@app.get("/db/health")
@limiter.limit("30/minute")
def db_health(request: Request):
    try:
        check_db()
        return {"db": "ok"}
    except Exception as e:
        return JSONResponse(status_code=503, content={"db": "down", "error": str(e)})
