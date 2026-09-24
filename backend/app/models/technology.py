from sqlalchemy import Column, Integer, String, Table, ForeignKey
from .base import Base

# Association table for many-to-many relationship
job_technologies = Table(
    "job_technologies",
    Base.metadata,
    Column("job_id", Integer, ForeignKey("jobs.id"), primary_key=True),
    Column("technology_id", Integer, ForeignKey("technologies.id"), primary_key=True),
)

class Technology(Base):
    __tablename__ = "technologies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    category = Column(String, nullable=True)  # "language", "framework", "tool", "cloud", etc.
