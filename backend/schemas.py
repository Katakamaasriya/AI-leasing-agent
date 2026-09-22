from datetime import datetime
from pydantic import BaseModel, Field, field_validator

class InquiryIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    contact: str = Field(min_length=3, max_length=160)
    channel: str = Field(pattern="^(phone|sms|email|listing_site)$")
    message: str = Field(min_length=1, max_length=2000)
    property_id: int
    external_message_id: str | None = Field(default=None, max_length=120)
    budget_monthly: float | None = Field(default=None, gt=0)
    bedrooms: int | None = Field(default=None, ge=0, le=10)
    preferred_location: str | None = Field(default=None, max_length=200)
    amenities: list[str] = Field(default_factory=list, max_length=20)
    desired_move_in: datetime | None = None
    has_pet: bool | None = None

class QualificationIn(BaseModel):
    monthly_income: float = Field(gt=0)
    desired_move_in: datetime
    has_pet: bool = False
    pet_type: str | None = None
    unit_id: int

class TourIn(BaseModel):
    property_id: int = Field(gt=0)
    prospect_name: str = Field(min_length=1, max_length=120)
    prospect_contact: str = Field(min_length=3, max_length=160)
    starts_at: datetime
    lead_id: int | None = Field(default=None, gt=0)

    @field_validator("prospect_name", "prospect_contact")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be blank")
        return value

class AvailabilityRequest(BaseModel):
    property_id: int
    starts_at: datetime
    duration_minutes: int = Field(default=30, ge=15, le=120)

class InventoryUnitIn(BaseModel):
    unit_number: str = Field(min_length=1, max_length=30)
    beds: int = Field(ge=0, le=10)
    baths: float = Field(gt=0, le=10)
    square_feet: int = Field(gt=0)
    monthly_rent: float = Field(gt=0)
    available_date: datetime
    status: str = Field(default="available", pattern="^(available|held|leased|offline)$")
    floor_plan: str = Field(min_length=1, max_length=80)
    amenities: list[str] = Field(default_factory=list)

class InventorySyncIn(BaseModel):
    property_id: int
    source: str = Field(default="pms_webhook", max_length=80)
    units: list[InventoryUnitIn] = Field(min_length=1)

class UnitCreateIn(InventoryUnitIn):
    property_id: int

class UnitUpdateIn(BaseModel):
    unit_number: str | None = Field(default=None, min_length=1, max_length=30)
    beds: int | None = Field(default=None, ge=0, le=10)
    baths: float | None = Field(default=None, gt=0, le=10)
    square_feet: int | None = Field(default=None, gt=0)
    monthly_rent: float | None = Field(default=None, gt=0)
    available_date: datetime | None = None
    status: str | None = Field(default=None, pattern="^(available|held|leased|offline)$")
    floor_plan: str | None = Field(default=None, min_length=1, max_length=80)
    amenities: list[str] | None = None

class HandoffIn(BaseModel):
    reason: str = Field(default="Prospect requested a leasing specialist.", min_length=1, max_length=500)

class AIRespondIn(BaseModel):
    lead_id: int
    message: str = Field(min_length=1, max_length=2000)

class AgentChatIn(BaseModel):
    lead_id: int = Field(gt=0)
    prompt: str = Field(min_length=1, max_length=2000)

class PropertyCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    address: str = Field(min_length=1, max_length=200)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    income_multiplier: float = Field(default=3.0, ge=0, le=10)
    pet_policy: str = Field(min_length=1, max_length=2000)
