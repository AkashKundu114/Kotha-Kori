from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    ForeignKey,
    String,
    Numeric,
    Boolean,
    Text,
    Integer,
    ARRAY,
    DateTime,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SHGGroup(Base):
    __tablename__ = "shg_groups"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    district: Mapped[str | None] = mapped_column(String(100))
    block: Mapped[str | None] = mapped_column(String(100))
    grade_level: Mapped[int | None] = mapped_column(Integer)
    total_members: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    whatsapp_number: Mapped[str] = mapped_column(
        String(15), unique=True, nullable=False
    )
    name: Mapped[str | None] = mapped_column(String(255))
    shg_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("shg_groups.id"))
    district: Mapped[str | None] = mapped_column(String(100))
    block: Mapped[str | None] = mapped_column(String(100))
    consent_given: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_given_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    onboarded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    business_categories: Mapped[list[str] | None] = mapped_column(ARRAY(String))
    self_reported_literacy: Mapped[str | None] = mapped_column(String(30))
    preferred_modality: Mapped[str] = mapped_column(String(10), default="voice")
    dialect_hint: Mapped[str | None] = mapped_column(String(30))
    ledger_correction_rate: Mapped[float] = mapped_column(Numeric(4, 3), default=0.0)
    sessions_count: Mapped[int] = mapped_column(Integer, default=0)
    trust_stage: Mapped[str] = mapped_column(String(15), default="new")


class LedgerEntry(Base):
    __tablename__ = "ledger_entries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    entry_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )
    entry_type: Mapped[str] = mapped_column(String(10))
    amount_inr: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100))
    description_bengali: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[float | None] = mapped_column(Numeric(10, 2))
    unit: Mapped[str | None] = mapped_column(String(20))
    raw_transcript: Mapped[str | None] = mapped_column(Text)
    is_corrected: Mapped[bool] = mapped_column(Boolean, default=False)
    correction_of: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("ledger_entries.id")
    )
    extracted_by: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )


class CatalogCreation(Base):
    __tablename__ = "catalog_creations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    raw_image_s3_key: Mapped[str] = mapped_column(String(500), nullable=False)
    processed_image_s3_key: Mapped[str | None] = mapped_column(String(500))
    product_type: Mapped[str | None] = mapped_column(String(100))
    caption_bengali: Mapped[str | None] = mapped_column(Text)
    price_suggestion_min: Mapped[float | None] = mapped_column(Numeric(10, 2))
    price_suggestion_max: Mapped[float | None] = mapped_column(Numeric(10, 2))
    vision_model_used: Mapped[str | None] = mapped_column(String(30))

    user_reported_shared: Mapped[bool | None] = mapped_column(Boolean)
    user_reported_sale_resulted: Mapped[bool | None] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow
    )


class MarketPrice(Base):
    __tablename__ = "market_prices"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    block: Mapped[str] = mapped_column(String(100), primary_key=True)
    district: Mapped[str] = mapped_column(String(100))
    product_category: Mapped[str] = mapped_column(String(100), primary_key=True)
    avg_price_inr_per_unit: Mapped[float | None] = mapped_column(Numeric(8, 2))
    unit: Mapped[str | None] = mapped_column(String(20))
    data_source: Mapped[str] = mapped_column(String(20), primary_key=True)
    sample_count: Mapped[int | None] = mapped_column(Integer)
