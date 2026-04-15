import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.actions import router as actions_router
from app.api.alerts import router as alerts_router
from app.api.approvals import router as approvals_router
from app.api.cases import router as cases_router
from app.db.session import Base, engine
from app.models.action import Action
from app.models.alert import Alert
from app.models.approval import Approval
from app.models.case import Case
from app.api import detection
from app.core.settings import get_settings


def _configure_app_logging() -> None:
    settings = get_settings()
    log_path = Path(settings.app_log_file_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, settings.app_log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
        force=False,
    )

Base.metadata.create_all(bind=engine)
_configure_app_logging()
settings = get_settings()

app = FastAPI(
    title="Threat Intelligence & Threat Hunting Copilot",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(alerts_router, prefix="/alerts", tags=["Alerts"])
app.include_router(approvals_router, prefix="/approvals", tags=["Approvals"])
app.include_router(actions_router, prefix="/actions", tags=["Actions"])
app.include_router(cases_router, prefix="/cases", tags=["Cases"])
app.include_router(detection.router, prefix="/detect")


@app.on_event("startup")
def initialize_ml_services():
    detection.initialize_risk_services()

@app.get("/")
def root():
    return {"message": "Secure Bot services is running!"}