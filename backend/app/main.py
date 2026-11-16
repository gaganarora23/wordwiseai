from fastapi import FastAPI

from app.api import health

app = FastAPI(title="WordWise API")

app.include_router(health.router, prefix="/api/v1")
