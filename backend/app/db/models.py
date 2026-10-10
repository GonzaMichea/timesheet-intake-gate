"""Modelos SQLAlchemy: espejo de supabase/migrations (los tests comparan ambos)."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON, Boolean, DateTime, ForeignKey, Integer, LargeBinary, Numeric, String, Text,
    UniqueConstraint, Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# jsonb en Postgres y json genérico en SQLite (tests)
Json = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Batch(Base):
    __tablename__ = "batches"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    period: Mapped[str] = mapped_column(String)
    analyst_name: Mapped[str] = mapped_column(String)
    contract_yaml: Mapped[str] = mapped_column(Text)
    master_csv: Mapped[str] = mapped_column(Text)
    contract_hash: Mapped[str] = mapped_column(String)
    processing_ms: Mapped[int | None] = mapped_column(Integer)
    ready_for_load: Mapped[bool] = mapped_column(Boolean, default=False)


class BatchFile(Base):
    __tablename__ = "batch_files"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("batches.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String)
    filename: Mapped[str | None] = mapped_column(String)
    site: Mapped[str | None] = mapped_column(String)
    content: Mapped[bytes | None] = mapped_column(LargeBinary)
    row_count: Mapped[int | None] = mapped_column(Integer)
    applied_mapping: Mapped[dict] = mapped_column(Json, default=dict)
    computed_disposition: Mapped[str] = mapped_column(String)
    disposition_rule: Mapped[str | None] = mapped_column(String)
    disposition_explanation: Mapped[str | None] = mapped_column(Text)
    processing_ms: Mapped[int | None] = mapped_column(Integer)


class Finding(Base):
    __tablename__ = "findings"
    __table_args__ = (UniqueConstraint("file_id", "ref"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    file_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("batch_files.id", ondelete="CASCADE"))
    ref: Mapped[str] = mapped_column(String)
    code: Mapped[str] = mapped_column(String)
    severity: Mapped[str] = mapped_column(String)
    column_name: Mapped[str | None] = mapped_column(String)
    rule_id: Mapped[str] = mapped_column(String)
    rule_text: Mapped[str] = mapped_column(Text)
    affected_count: Mapped[int] = mapped_column(Integer, default=0)
    affected_rows: Mapped[list] = mapped_column(Json, default=list)
    sample_rows: Mapped[list] = mapped_column(Json, default=list)
    evidence: Mapped[dict] = mapped_column(Json, default=dict)
    status: Mapped[str] = mapped_column(String, default="open")


class MappingReview(Base):
    __tablename__ = "mapping_reviews"
    __table_args__ = (UniqueConstraint("file_id", "source_column"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    file_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("batch_files.id", ondelete="CASCADE"))
    source_column: Mapped[str] = mapped_column(String)
    candidate_column: Mapped[str | None] = mapped_column(String)
    candidate_score: Mapped[float | None] = mapped_column(Numeric(4, 3))
    status: Mapped[str] = mapped_column(String, default="pending")
    chosen_column: Mapped[str | None] = mapped_column(String)
    decided_by: Mapped[str | None] = mapped_column(String)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Override(Base):
    """Solo inserción: vale la última fila del archivo (disposition nula = override retirado)."""
    __tablename__ = "overrides"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    file_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("batch_files.id", ondelete="CASCADE"))
    disposition: Mapped[str | None] = mapped_column(String)
    justification: Mapped[str] = mapped_column(Text)
    actor: Mapped[str] = mapped_column(String)
    computed_disposition: Mapped[str | None] = mapped_column(String)  # migración 002


class AiResult(Base):
    __tablename__ = "ai_results"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    file_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("batch_files.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    model: Mapped[str | None] = mapped_column(String)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    payload: Mapped[dict | None] = mapped_column(Json)
    reason: Mapped[str | None] = mapped_column(Text)
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False)


class AuditLog(Base):
    """Solo inserción (R10.2)."""
    __tablename__ = "audit_log"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("batches.id", ondelete="CASCADE"))
    actor: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)
    entity_type: Mapped[str] = mapped_column(String)
    entity_id: Mapped[str] = mapped_column(String)
    before: Mapped[dict | None] = mapped_column(Json)
    after: Mapped[dict | None] = mapped_column(Json)
    justification: Mapped[str | None] = mapped_column(Text)
