from sqlalchemy import Boolean, Column, ForeignKey, Integer, String

from app.db.session import Base


class Approval(Base):
	__tablename__ = "approvals"

	id = Column(Integer, primary_key=True, index=True)
	action_id = Column(String, ForeignKey("actions.action_id"), nullable=False)
	approved = Column(Boolean, nullable=False)
	analyst = Column(String, nullable=False)
	comment = Column(String, nullable=True)
