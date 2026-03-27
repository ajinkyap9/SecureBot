from sqlalchemy import Column, ForeignKey, Integer, String

from app.db.session import Base


class Case(Base):
	__tablename__ = "cases"

	id = Column(Integer, primary_key=True, index=True)
	case_id = Column(String, unique=True, index=True, nullable=False)
	title = Column(String, nullable=False)
	status = Column(String, default="open")
	severity = Column(String, nullable=False)
	alert_id = Column(String, ForeignKey("alerts.alert_id"), nullable=False)
	attack_type = Column(String, nullable=True)
	risk_score = Column(String, nullable=True)
