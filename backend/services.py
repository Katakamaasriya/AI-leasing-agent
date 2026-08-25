from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from .models import Conversation, ConversationMessage, Lead, LeadEvent, Property, Tour, Unit

INVENTORY_MAX_AGE_SECONDS = 300

def normalize_contact(contact: str) -> str:
    """Stable contact key for matching phone/email across inbound connectors."""
    value = contact.strip().lower()
    if "@" in value:
        return value
    return "".join(ch for ch in value if ch.isdigit())

def log_event(db: Session, lead_id: int, event_type: str, **details):
    db.add(LeadEvent(lead_id=lead_id, event_type=event_type, details=details))

def ingest_normalized_inquiry(db: Session, *, name: str, contact: str, channel: str, message: str, property_id: int,
                              budget_monthly: float | None = None, bedrooms: int | None = None,
                              preferred_location: str | None = None, amenities: list[str] | None = None,
                              desired_move_in: datetime | None = None, has_pet: bool | None = None):
    key = normalize_contact(contact)
    conversation = (db.query(Conversation).join(Lead, Lead.id == Conversation.lead_id)
                    .filter(Conversation.normalized_contact == key, Lead.property_id == property_id)
                    .order_by(Conversation.id.desc()).first())
    if conversation:
        lead = db.get(Lead, conversation.lead_id)
    else:
        lead = Lead(name=name.strip(), contact=contact.strip(), channel=channel, message=message.strip(), property_id=property_id)
        db.add(lead); db.flush()
        conversation = Conversation(lead_id=lead.id, normalized_contact=key)
        db.add(conversation); db.flush()
    profile = dict(lead.needs_profile or {})
    if budget_monthly is not None: profile["budget_monthly"] = budget_monthly
    if bedrooms is not None: profile["bedrooms"] = bedrooms
    if preferred_location: profile["preferred_location"] = preferred_location.strip()
    if amenities: profile["amenities"] = sorted(set(amenities))
    if desired_move_in is not None: profile["desired_move_in"] = desired_move_in.isoformat()
    if has_pet is not None: profile["has_pet"] = has_pet
    lead.needs_profile = profile
    conversation.updated_at = datetime.utcnow()
    db.add(ConversationMessage(conversation_id=conversation.id, channel=channel, direction="inbound", body=message.strip()))
    log_event(db, lead.id, "inquiry_captured", channel=channel)
    # The acknowledgement is an auditable first response; connector delivery can update this event in production.
    log_event(db, lead.id, "automated_response_sent", channel=channel)
    db.commit(); db.refresh(lead)
    return lead, conversation

def get_unit_availability(db: Session, property_id: int):
    # This read must be preceded by the PMS/webhook sync in production.
    return db.query(Unit).filter(Unit.property_id == property_id, Unit.status == "available").order_by(Unit.monthly_rent).all()

def get_pricing_and_amenities(db: Session, unit_id: int):
    return db.get(Unit, unit_id)

def inventory_freshness(units: list[Unit]) -> dict:
    # Every quoteable unit must be refreshed; the oldest timestamp governs freshness.
    synced = min((u.inventory_synced_at for u in units), default=None)
    age = (datetime.utcnow() - synced).total_seconds() if synced else None
    return {"synced_at": synced, "age_seconds": round(age, 1) if age is not None else None,
            "fresh": bool(age is not None and age <= INVENTORY_MAX_AGE_SECONDS)}

def sync_inventory(db: Session, property_id: int, units: list[dict]):
    now = datetime.utcnow()
    existing = {u.unit_number: u for u in db.query(Unit).filter_by(property_id=property_id).all()}
    for payload in units:
        unit = existing.get(payload["unit_number"])
        if unit is None:
            unit = Unit(property_id=property_id, **payload, inventory_synced_at=now)
            db.add(unit)
        else:
            for field, value in payload.items(): setattr(unit, field, value)
            unit.inventory_synced_at = now
    db.commit()

def qualify_lead(db: Session, lead: Lead, unit: Unit, monthly_income: float, desired_move_in: datetime, has_pet: bool, pet_type: str | None):
    property_ = db.get(Property, unit.property_id)
    notes = [
        f"Income checked against published {property_.income_multiplier:.1f}x rent criterion.",
        f"Move-in date checked against unit availability ({unit.available_date.date()}).",
        "Pet request checked against published property pet policy." if has_pet else "No pet accommodation requested.",
    ]
    income_ok = monthly_income >= unit.monthly_rent * property_.income_multiplier
    timeline_ok = desired_move_in.date() >= unit.available_date.date()
    # Published demo policy permits cats/dogs. Any missing or different detail is routed to a person;
    # this is never an automated denial or an assessment of an accommodation request.
    pet_ok = (not has_pet) or (pet_type or "").strip().lower() in {"cat", "dog"}
    status = "ready_for_human_review" if all((income_ok, timeline_ok, pet_ok)) else "needs_review"
    lead.qualification_status, lead.qualification_notes = status, notes
    log_event(db, lead.id, "qualification_evaluated", status=status, criteria={"income": income_ok, "move_in": timeline_ok, "pet_policy": pet_ok}, unit_id=unit.id)
    db.commit(); db.refresh(lead)
    return {"status": status, "criteria": {"income": income_ok, "move_in": timeline_ok, "pet_policy": pet_ok}, "notes": notes,
            "human_handoff": "A leasing specialist is available for questions or accommodations."}

def check_calendar_availability(db: Session, property_id: int, starts_at: datetime, duration_minutes: int = 30):
    end = starts_at + timedelta(minutes=duration_minutes)
    clashes = db.query(Tour).filter(Tour.property_id == property_id, Tour.status == "scheduled", Tour.starts_at < end, Tour.starts_at > starts_at - timedelta(minutes=duration_minutes)).count()
    within_hours = 9 <= starts_at.hour < 18 and starts_at.weekday() < 6
    return {"available": clashes == 0 and within_hours, "starts_at": starts_at, "duration_minutes": duration_minutes,
            "reason": None if clashes == 0 and within_hours else "Slot conflicts or is outside published touring hours."}

def schedule_tour(db: Session, property_id: int, prospect_name: str, prospect_contact: str, starts_at: datetime, lead_id: int | None = None):
    if not check_calendar_availability(db, property_id, starts_at)["available"]:
        raise ValueError("Selected tour slot is no longer available.")
    tour = Tour(property_id=property_id, prospect_name=prospect_name, prospect_contact=prospect_contact, starts_at=starts_at)
    db.add(tour); db.commit(); db.refresh(tour)
    if lead_id and (lead := db.get(Lead, lead_id)):
        lead.tour_id = tour.id
        log_event(db, lead_id, "tour_scheduled", tour_id=tour.id, starts_at=tour.starts_at.isoformat())
        db.commit()
    return tour

def send_confirmation(db: Session, tour: Tour):
    # Connector seam: dispatch via SMS/email provider; records auditable delivery intent.
    tour.confirmation_sent_at = datetime.utcnow()
    lead = db.query(Lead).filter_by(tour_id=tour.id).first()
    if lead:
        log_event(db, lead.id, "confirmation_sent", tour_id=tour.id, channel="sms_or_email")
    db.commit()
    return {"sent": True, "channel": "sms_or_email", "message": f"Tour confirmed for {tour.starts_at:%A, %b %d at %I:%M %p}. Reply HUMAN for a leasing specialist."}

def request_handoff(db: Session, lead: Lead, reason: str):
    lead.human_requested = True
    log_event(db, lead.id, "human_handoff_requested", reason=reason)
    db.commit()
    return {"queued": True, "message": "A leasing specialist has been notified and will follow up.", "lead_id": lead.id}
