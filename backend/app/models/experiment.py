"""
Evaluation Experiment Models
----------------------------
Implements the Evaluation Experiments and Runs tables specified in Master Implementation Prompt §17.
Enables reproducible evaluation benchmarking across baseline, structure-aware, and verification RAG.
"""
from datetime import datetime
import uuid
from typing import Any, List, Optional
from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import GUID


class Experiment(Base):
    __tablename__ = "experiments"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID, primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    configuration_json: Mapped[Optional[Any]] = mapped_column("configuration", JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    runs: Mapped[List["ExperimentRun"]] = relationship(
        "ExperimentRun", back_populates="experiment", cascade="all, delete-orphan"
    )


class ExperimentRun(Base):
    __tablename__ = "experiment_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID, primary_key=True, default=uuid.uuid4
    )
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    retrieval_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    embedding_version: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    dataset_name: Mapped[str] = mapped_column(String(128), nullable=False, default="qasper")
    dataset_split: Mapped[str] = mapped_column(String(64), nullable=False, default="test")
    metrics_json: Mapped[Optional[Any]] = mapped_column("metrics", JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="PENDING")
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    experiment: Mapped["Experiment"] = relationship("Experiment", back_populates="runs")
