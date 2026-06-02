from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import router as api_router
from app.db import init_db
from app.web.routes import router as web_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="OpsPilot Lite", version="0.1.0", lifespan=lifespan)
app.include_router(api_router)
app.include_router(web_router)
app.mount("/static", StaticFiles(directory="app/web/static"), name="static")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
