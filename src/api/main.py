from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import logging

# Import routers
from src.api.routers import health, companies, screener, sectors, peers, valuation, portfolio, documents

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Nifty 100 Financial Intelligence API",
    version="1.0.0",
    description="REST API for the Nifty 100 Financial Intelligence Platform"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Internal use only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.4f}s")
    return response

# Include Routers
prefix = "/api/v1"
app.include_router(health.router, prefix=prefix)
app.include_router(companies.router, prefix=prefix)
app.include_router(screener.router, prefix=prefix)
app.include_router(sectors.router, prefix=prefix)
app.include_router(peers.router, prefix=prefix)
app.include_router(valuation.router, prefix=prefix)
app.include_router(portfolio.router, prefix=prefix)
app.include_router(documents.router, prefix=prefix)
