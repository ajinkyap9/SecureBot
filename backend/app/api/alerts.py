from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.orchestrator import run_pipeline
from app.db.session import SessionLocal
from app.models.alert import Alert
from app.schemas.alert_schema import AlertInput

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/ingest")
def ingest_alert(alert: AlertInput, db: Session = Depends(get_db)):
    try:
        existing_alert = db.query(Alert).filter(Alert.alert_id == alert.alert_id).first()

        if not existing_alert:
            db_alert = Alert(
                alert_id=alert.alert_id,
                source=alert.source,
                ip=alert.ip,
                process=alert.process,
                command=alert.command,
                timestamp=alert.timestamp,
            )
            db.add(db_alert)
            db.commit()

        result = run_pipeline(alert.model_dump(), db)

        return {
            "status": "success",
            "pipeline_result": result,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))