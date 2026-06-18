from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.engine import init_db
from app.api import contracts, baseline, compare


def create_app() -> FastAPI:
    app = FastAPI(title="Contract Analysis Platform")
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"],
                       allow_methods=["*"], allow_headers=["*"])

    @app.on_event("startup")
    def _startup():
        init_db()

    app.include_router(contracts.router)
    app.include_router(baseline.router)
    app.include_router(compare.router)
    return app


app = create_app()
