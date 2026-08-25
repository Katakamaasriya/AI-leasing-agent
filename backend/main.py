from datetime import datetime, timedelta
import numpy as np
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from .ai import respond_to_lead
from .database import Base, SessionLocal, engine, get_db
from .models import Lead, LeadEvent, Property, Tour, Unit
from .schemas import (AvailabilityRequest, HandoffIn, InquiryIn, InventorySyncIn, QualificationIn,
                      TourIn, UnitCreateIn, UnitUpdateIn, PropertyCreateIn, AIRespondIn)
from .services import (check_calendar_availability, get_pricing_and_amenities, get_unit_availability,
                       ingest_normalized_inquiry, inventory_freshness, qualify_lead, request_handoff,
                       schedule_tour, send_confirmation, sync_inventory)

app = FastAPI(title="Leasing Concierge API", version="1.0.0")

@app.on_event("startup")
def seed():
    Base.metadata.create_all(engine)
    # Lightweight, non-destructive migrations for prototype databases.
    lead_columns = {column["name"] for column in inspect(engine).get_columns("leads")}
    if "property_id" not in lead_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE leads ADD COLUMN property_id INTEGER"))
    if "needs_profile" not in lead_columns:
        with engine.begin() as connection:
            connection.execute(text("ALTER TABLE leads ADD COLUMN needs_profile JSON"))
    db = SessionLocal()
    if not db.query(Property).first():
        p = Property(name="Juniper Commons", address="101 Market Street, Austin, TX", latitude=30.2672, longitude=-97.7431, income_multiplier=3.0, pet_policy="Cats and dogs welcome; breed/weight details reviewed using published policy.")
        db.add(p); db.flush()
        today = datetime.utcnow()
        db.add_all([
          Unit(property_id=p.id, unit_number="A-204", beds=1, baths=1, square_feet=720, monthly_rent=1695, available_date=today+timedelta(days=5), floor_plan="Cedar", amenities=["Balcony", "In-unit laundry", "Pool"]),
          Unit(property_id=p.id, unit_number="B-311", beds=2, baths=2, square_feet=1040, monthly_rent=2195, available_date=today+timedelta(days=12), floor_plan="Willow", amenities=["Corner home", "Fitness center", "Pet park"]),
        ])
        db.commit()
    first_property = db.query(Property).order_by(Property.id).first()
    if first_property:
        db.query(Lead).filter(Lead.property_id.is_(None)).update({Lead.property_id: first_property.id})
        db.commit()
    db.close()

@app.get("/properties")
def properties(db: Session = Depends(get_db)): return db.query(Property).all()
@app.post("/properties")
def create_property(data: PropertyCreateIn, db: Session = Depends(get_db)):
    property_ = Property(**data.model_dump())
    db.add(property_); db.commit(); db.refresh(property_)
    return property_
@app.get("/leads")
def list_leads(property_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Lead)
    if property_id is not None: query = query.filter(Lead.property_id == property_id)
    return query.order_by(Lead.created_at.desc()).limit(100).all()
@app.get("/properties/{property_id}/availability")
def availability(property_id: int, db: Session = Depends(get_db)):
    units = get_unit_availability(db, property_id)
    return {"units": units, "freshness": inventory_freshness(units)}
@app.get("/properties/{property_id}/units")
def property_units(property_id: int, db: Session = Depends(get_db)):
    if not db.get(Property, property_id): raise HTTPException(404, "Property not found")
    return db.query(Unit).filter_by(property_id=property_id).order_by(Unit.unit_number).all()
@app.get("/units/{unit_id}/details")
def unit_details(unit_id: int, db: Session = Depends(get_db)):
    unit = get_pricing_and_amenities(db, unit_id)
    if not unit: raise HTTPException(404, "Unit not found")
    return unit
@app.post("/units")
def create_unit(data: UnitCreateIn, db: Session = Depends(get_db)):
    if not db.get(Property, data.property_id): raise HTTPException(404, "Property not found")
    duplicate = db.query(Unit).filter_by(property_id=data.property_id, unit_number=data.unit_number).first()
    if duplicate: raise HTTPException(409, "That unit number already exists at this property.")
    unit = Unit(**data.model_dump(), inventory_synced_at=datetime.utcnow())
    db.add(unit); db.commit(); db.refresh(unit)
    return unit
@app.put("/units/{unit_id}")
def update_unit(unit_id: int, data: UnitUpdateIn, db: Session = Depends(get_db)):
    unit = db.get(Unit, unit_id)
    if not unit: raise HTTPException(404, "Unit not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(unit, field, value)
    unit.inventory_synced_at = datetime.utcnow()
    db.commit(); db.refresh(unit)
    return unit
@app.post("/inquiries")
def ingest_inquiry(data: InquiryIn, db: Session = Depends(get_db)):
    if not db.get(Property, data.property_id): raise HTTPException(404, "Property not found")
    lead, conversation = ingest_normalized_inquiry(db, **data.model_dump(exclude={"external_message_id"}))
    return {"lead_id": lead.id, "conversation_id": conversation.id, "conversation_context": {"channel": data.channel, "message": data.message}, "human_handoff_available": True}
@app.post("/leads/{lead_id}/handoff")
def handoff(lead_id: int, data: HandoffIn, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)
    if not lead: raise HTTPException(404, "Lead not found")
    return request_handoff(db, lead, data.reason)
@app.post("/ai/respond")
def ai_respond(data: AIRespondIn, db: Session = Depends(get_db)):
    lead = db.get(Lead, data.lead_id)
    if not lead: raise HTTPException(404, "Lead not found")
    return respond_to_lead(db, lead, data.message)
@app.post("/leads/{lead_id}/qualify")
def qualify(lead_id: int, data: QualificationIn, db: Session = Depends(get_db)):
    lead, unit = db.get(Lead, lead_id), db.get(Unit, data.unit_id)
    if not lead or not unit: raise HTTPException(404, "Lead or unit not found")
    if lead.property_id != unit.property_id: raise HTTPException(400, "Lead and unit must belong to the same property")
    return qualify_lead(db, lead, unit, **data.model_dump(exclude={"unit_id"}))
@app.post("/calendar/check")
def calendar_check(data: AvailabilityRequest, db: Session = Depends(get_db)): return check_calendar_availability(db, **data.model_dump())
@app.post("/tours")
def book_tour(data: TourIn, db: Session = Depends(get_db)):
    try: tour = schedule_tour(db, **data.model_dump())
    except ValueError as exc: raise HTTPException(409, str(exc))
    return {"tour": tour, "confirmation": send_confirmation(db, tour)}
@app.post("/tours/{tour_id}/confirmation")
def confirm(tour_id: int, db: Session = Depends(get_db)):
    tour = db.get(Tour, tour_id)
    if not tour: raise HTTPException(404, "Tour not found")
    return send_confirmation(db, tour)
@app.post("/integrations/inventory/sync")
def inventory_sync(data: InventorySyncIn, db: Session = Depends(get_db)):
    if not db.get(Property, data.property_id): raise HTTPException(404, "Property not found")
    sync_inventory(db, data.property_id, [u.model_dump() for u in data.units])
    units = get_unit_availability(db, data.property_id)
    return {"updated": len(data.units), "freshness": inventory_freshness(units), "source": data.source}
@app.get("/metrics")
def metrics(db: Session = Depends(get_db)):
    leads = db.query(Lead).all(); tours = db.query(Tour).all()
    after_hours = sum(1 for x in leads if x.created_at.hour < 9 or x.created_at.hour >= 18)
    events = db.query(LeadEvent).all()
    response_by_lead = {}
    for event in events:
        response_by_lead.setdefault(event.lead_id, {})[event.event_type] = event.created_at
    response_minutes = [
        (times["automated_response_sent"] - times["inquiry_captured"]).total_seconds() / 60
        for times in response_by_lead.values()
        if "inquiry_captured" in times and "automated_response_sent" in times
    ]
    median_response = round(float(np.median(response_minutes)), 2) if response_minutes else None
    return {"leads": len(leads), "response_time_minutes": median_response, "lead_to_tour_rate": round(len(tours)/len(leads)*100, 1) if leads else 0, "after_hours_capture": after_hours, "tour_show_up_rate": round(sum(x.status=="completed" for x in tours)/len(tours)*100, 1) if tours else 0, "audited_events": len(events)}
