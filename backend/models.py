from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

class Property(Base):
    __tablename__ = "properties"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    address: Mapped[str] = mapped_column(String(200))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    income_multiplier: Mapped[float] = mapped_column(Float, default=3.0)
    pet_policy: Mapped[str] = mapped_column(Text)
    units: Mapped[list["Unit"]] = relationship(back_populates="property")

class Unit(Base):
    __tablename__ = "units"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"))
    unit_number: Mapped[str] = mapped_column(String(30))
    beds: Mapped[int] = mapped_column(Integer)
    baths: Mapped[float] = mapped_column(Float)
    square_feet: Mapped[int] = mapped_column(Integer)
    monthly_rent: Mapped[float] = mapped_column(Float)
    available_date: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(30), default="available")
    floor_plan: Mapped[str] = mapped_column(String(80))
    amenities: Mapped[list] = mapped_column(JSON, default=list)
    inventory_synced_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    property: Mapped[Property] = relationship(back_populates="units")

class Lead(Base):
    __tablename__ = "leads"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    contact: Mapped[str] = mapped_column(String(160))
    channel: Mapped[str] = mapped_column(String(30))
    message: Mapped[str] = mapped_column(Text)
    property_id: Mapped[int | None] = mapped_column(ForeignKey("properties.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    qualification_status: Mapped[str] = mapped_column(String(30), default="pending")
    qualification_notes: Mapped[list] = mapped_column(JSON, default=list)
    needs_profile: Mapped[dict] = mapped_column(JSON, default=dict)
    human_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    tour_id: Mapped[int | None] = mapped_column(ForeignKey("tours.id"), nullable=True)

class Conversation(Base):
    """Channel-neutral context; one prospect may write from several channels."""
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), index=True)
    normalized_contact: Mapped[str] = mapped_column(String(160), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    channel: Mapped[str] = mapped_column(String(30))
    direction: Mapped[str] = mapped_column(String(12), default="inbound")
    body: Mapped[str] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class LeadEvent(Base):
    """Append-only audit trail for responses, handoffs, qualification, and tours."""
    __tablename__ = "lead_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    lead_id: Mapped[int] = mapped_column(ForeignKey("leads.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(50), index=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Tour(Base):
    __tablename__ = "tours"
    id: Mapped[int] = mapped_column(primary_key=True)
    property_id: Mapped[int] = mapped_column(ForeignKey("properties.id"))
    starts_at: Mapped[datetime] = mapped_column(DateTime)
    prospect_name: Mapped[str] = mapped_column(String(120))
    prospect_contact: Mapped[str] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(30), default="scheduled")
    confirmation_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
