from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.case import Case
from app.schemas.case_schema import CaseResponse, CaseUpdateRequest

router = APIRouter()


def get_db():
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()


@router.get("/{case_id}", response_model=CaseResponse)
def get_case(case_id: str, db: Session = Depends(get_db)):
	case = db.query(Case).filter(Case.case_id == case_id).first()

	if not case:
		raise HTTPException(status_code=404, detail="Case not found")

	return case


@router.patch("/{case_id}")
def update_case(case_id: str, request: CaseUpdateRequest, db: Session = Depends(get_db)):
	case = db.query(Case).filter(Case.case_id == case_id).first()

	if not case:
		raise HTTPException(status_code=404, detail="Case not found")

	case.status = request.status
	db.commit()
	db.refresh(case)

	return {
		"message": "Case updated successfully",
		"case": {"case_id": case.case_id, "status": case.status},
	}


@router.get("/")
def list_cases(db: Session = Depends(get_db)):
	cases = db.query(Case).all()

	return {
		"total_cases": len(cases),
		"cases": [
			{
				"case_id": case.case_id,
				"title": case.title,
				"status": case.status,
				"severity": case.severity,
				"alert_id": case.alert_id,
				"attack_type": case.attack_type,
				"risk_score": case.risk_score,
			}
			for case in cases
		],
	}
