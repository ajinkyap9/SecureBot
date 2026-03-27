from sqlalchemy import Column, ForeignKey, Integer, String

from app.db.session import Base


class Action(Base):
    __tablename__ = "actions"

    id = Column(Integer, primary_key=True, index=True)
    action_id = Column(String, unique=True, index=True, nullable=False)
    playbook = Column(String, nullable=False)
    status = Column(String, nullable=False)
    alert_id = Column(String, ForeignKey("alerts.alert_id"), nullable=False)
    case_id = Column(String, nullable=True)
    risk_score = Column(String, nullable=True)
    attack_type = Column(String, nullable=True)