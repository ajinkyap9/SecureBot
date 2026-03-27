from fastapi import FastAPI

from app.api.actions import router as actions_router
from app.api.alerts import router as alerts_router
from app.api.approvals import router as approvals_router
from app.api.cases import router as cases_router
from app.db.session import Base, engine
from app.models.action import Action
from app.models.alert import Alert
from app.models.approval import Approval
from app.models.case import Case

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Threat Intelligence & Threat Hunting Copilot",
    version="1.0.0",
)

app.include_router(alerts_router, prefix="/alerts", tags=["Alerts"])
app.include_router(approvals_router, prefix="/approvals", tags=["Approvals"])
app.include_router(actions_router, prefix="/actions", tags=["Actions"])
app.include_router(cases_router, prefix="/cases", tags=["Cases"])


@app.get("/")
def root():
    return {"message": "Secure Bot services is running!"}