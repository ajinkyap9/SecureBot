from sqlalchemy import Column, Integer, String

from app.db.session import Base


class Alert(Base):
	__tablename__ = "alerts"

	id = Column(Integer, primary_key=True, index=True)
	alert_id = Column(String, unique=True, index=True, nullable=False)
	source = Column(String, nullable=False)
	ip = Column(String, nullable=True)
	process = Column(String, nullable=True)
	command = Column(String, nullable=True)
	timestamp = Column(String, nullable=False)
