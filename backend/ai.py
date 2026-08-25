import os
import re

import requests
from sqlalchemy.orm import Session

from .models import Conversation, ConversationMessage, Lead, LeadEvent, Property, Tour, Unit
from .services import get_unit_availability, inventory_freshness, log_event


OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"


def _extract_needs(profile: dict, message: str) -> dict:
    """Capture explicit customer requirements without inferring protected traits."""
    text = message.lower()
    updated = dict(profile or {})
    budgets = re.findall(r"\$\s?(\d[\d,]*(?:\.\d+)?)", text)
    if budgets:
        updated["budget_monthly"] = float(budgets[-1].replace(",", ""))
    bedroom_match = re.search(r"(\d+|one|two|three|four)\s*[- ]?bed(?:room)?s?\b", text)
    if bedroom_match:
        bedroom_value = bedroom_match.group(1)
        word_counts = {"one": 1, "two": 2, "three": 3, "four": 4}
        updated["bedrooms"] = word_counts[bedroom_value] if bedroom_value in word_counts else int(bedroom_value)
    if "studio" in text:
        updated["bedrooms"] = 0
    if any(word in text for word in ("downtown", "central", "near ")):
        location = re.search(
            r"(?:near|in|around)\s+([a-z][a-z ,'-]{2,40}?)(?=\s+(?:with|and|that|under|for|budget)\b|[,.!?]|$)",
            text,
        )
        if location:
            updated["preferred_location"] = location.group(1).strip(" .,!?")
    amenity_terms = [
        "gym", "fitness center", "pool", "balcony", "parking", "pet park",
        "in-unit laundry", "laundry", "elevator", "storage",
    ]
    mentioned = [amenity for amenity in amenity_terms if amenity in text]
    if mentioned:
        updated["amenities"] = sorted(set(updated.get("amenities", [])) | set(mentioned))
    if "no pet" in text or "without pet" in text:
        updated["has_pet"] = False
    elif re.search(r"\b(?:i have|with|my)\s+(?:a\s+)?(?:cat|dog|pet)\b", text):
        updated["has_pet"] = True
    return updated


def _needs_summary(profile: dict) -> str:
    if not profile:
        return "I have not recorded any specific housing needs yet."
    parts = []
    if "budget_monthly" in profile:
        parts.append(f"monthly budget ${profile['budget_monthly']:,.0f}")
    if "bedrooms" in profile:
        parts.append("studio" if profile["bedrooms"] == 0 else f"{profile['bedrooms']} bedroom")
    if profile.get("preferred_location"):
        parts.append(f"location near {profile['preferred_location']}")
    if profile.get("amenities"):
        parts.append("amenities: " + ", ".join(profile["amenities"]))
    if "has_pet" in profile:
        parts.append("has a pet" if profile["has_pet"] else "no pet")
    return "; ".join(parts) + "."


def _availability_context(units, freshness):
    if not freshness["fresh"]:
        return "Live inventory is stale or unavailable. Do not quote prices or availability."
    if not units:
        return "There are no available units in the current live inventory."
    return "\n".join(
        f"Unit {unit.unit_number}: {unit.beds} bed, {unit.baths:g} bath, "
        f"${unit.monthly_rent:,.0f}/month, available {unit.available_date:%Y-%m-%d}, "
        f"floor plan {unit.floor_plan}, amenities: {', '.join(unit.amenities or []) or 'none listed'}"
        for unit in units
    )


def _portfolio_context(db: Session):
    sections = []
    for property_ in db.query(Property).order_by(Property.name).all():
        units = get_unit_availability(db, property_.id)
        freshness = inventory_freshness(units)
        sections.append(
            f"Property {property_.id}: {property_.name}, {property_.address}\n"
            f"Published pet policy: {property_.pet_policy}\n"
            f"Income criterion: {property_.income_multiplier:.1f}x published rent\n"
            f"Inventory freshness: {freshness}\n"
            f"Availability:\n{_availability_context(units, freshness)}"
        )
    return "\n\n".join(sections)


def _whole_database_context(db: Session):
    """Build a bounded, read-only snapshot for the internal operations assistant."""
    properties = db.query(Property).order_by(Property.id).all()
    units = db.query(Unit).order_by(Unit.property_id, Unit.unit_number).all()
    leads = db.query(Lead).order_by(Lead.created_at.desc()).limit(100).all()
    tours = db.query(Tour).order_by(Tour.starts_at).limit(100).all()
    events = db.query(LeadEvent).order_by(LeadEvent.created_at.desc()).limit(100).all()
    property_names = {item.id: item.name for item in properties}
    property_lines = [
        f"#{item.id} {item.name} | address: {item.address} | income rule: {item.income_multiplier}x | pet policy: {item.pet_policy}"
        for item in properties
    ] or ["none"]
    unit_lines = [
        f"#{item.id} property={property_names.get(item.property_id, item.property_id)} {item.unit_number} | "
        f"status={item.status} | {item.beds} bed/{item.baths:g} bath | rent=${item.monthly_rent:,.0f} | "
        f"available={item.available_date:%Y-%m-%d} | amenities={', '.join(item.amenities or [])} | synced={item.inventory_synced_at}"
        for item in units
    ] or ["none"]
    lead_lines = [
        f"#{item.id} {item.name} | contact={item.contact} | channel={item.channel} | property={property_names.get(item.property_id, item.property_id)} | "
        f"status={item.qualification_status} | needs={item.needs_profile or {}} | human_requested={item.human_requested} | created={item.created_at}"
        for item in leads
    ] or ["none"]
    tour_lines = [
        f"#{item.id} property={property_names.get(item.property_id, item.property_id)} | {item.starts_at:%Y-%m-%d %H:%M} | "
        f"prospect={item.prospect_name} | status={item.status}"
        for item in tours
    ] or ["none"]
    event_lines = [
        f"lead={item.lead_id} | {item.event_type} | {item.created_at} | details={item.details}"
        for item in events
    ] or ["none"]
    return "\n".join([
        "PROPERTIES:\n" + "\n".join(property_lines),
        "UNITS:\n" + "\n".join(unit_lines),
        "LEADS:\n" + "\n".join(lead_lines),
        "TOURS:\n" + "\n".join(tour_lines),
        "RECENT AUDIT EVENTS:\n" + "\n".join(event_lines),
        f"COUNTS: properties={len(properties)}, units={len(units)}, leads={len(leads)}, tours={len(tours)}, events={len(events)}",
    ])


def _fallback_reply(property_, units, freshness, profile, message):
    text = message.lower()
    if any(phrase in text for phrase in ("budget", "afford", "how much can i spend")) and any(
        phrase in text for phrase in ("what", "which", "my", "mentioned", "tell")
    ):
        budget = profile.get("budget_monthly")
        return f"Your recorded monthly budget is ${budget:,.0f}." if budget else "You have not told me a monthly budget yet."
    if "amenit" in text:
        amenities = profile.get("amenities", [])
        return "You mentioned these amenities: " + (", ".join(amenities) if amenities else "none yet") + "."
    if any(phrase in text for phrase in ("bedroom", "home size", "how many beds")) and any(
        phrase in text for phrase in ("what", "which", "my", "need")
    ):
        bedrooms = profile.get("bedrooms")
        return f"You are looking for {bedrooms} bedroom." if bedrooms is not None else "You have not told me your preferred home size yet."
    if any(phrase in text for phrase in ("where", "location", "located")):
        location = profile.get("preferred_location")
        return f"Your recorded preferred location is {location}." if location else "You have not told me a preferred location yet."
    if any(phrase in text for phrase in ("summary", "what do you know", "what did i tell")):
        return "Here is the current lead-needs summary: " + _needs_summary(profile)
    if not freshness["fresh"]:
        return (
            "Thanks for reaching out. Our live availability feed needs to be refreshed, "
            "so I will not quote pricing or availability. A leasing specialist can help you directly."
        )
    if not units:
        return (
            f"Thanks for your interest in {property_.name}. There are no available homes in the "
            "current listing feed. A leasing specialist can discuss upcoming availability."
        )
    unit_list = "; ".join(
        f"{unit.unit_number} ({unit.beds} bed, ${unit.monthly_rent:,.0f}/month)"
        for unit in units
    )
    return (
        f"Thanks for your interest in {property_.name}. Current live availability: {unit_list}. "
        "Tell me your preferred move-in date and home size, or reply HUMAN for a leasing specialist."
    )


def _portfolio_fallback(db: Session):
    matches = []
    for property_ in db.query(Property).order_by(Property.name).all():
        units = get_unit_availability(db, property_.id)
        freshness = inventory_freshness(units)
        if freshness["fresh"] and units:
            unit_list = "; ".join(
                f"{unit.unit_number} ({unit.beds} bed, ${unit.monthly_rent:,.0f}/month)"
                for unit in units
            )
            matches.append(f"{property_.name} at {property_.address}: {unit_list}")
    if not matches:
        return (
            "I can compare homes across the portfolio, but the live inventory feed needs to be refreshed "
            "before I can quote pricing or availability. Tell me your budget, move-in date, home size, "
            "and preferred location, or reply HUMAN for a specialist."
        )
    return (
        "Here are the current live options across the portfolio: " + " | ".join(matches) +
        ". Tell me your budget, move-in date, home size, and preferred location so I can narrow the match, "
        "or reply HUMAN for a leasing specialist."
    )


def _portfolio_availability_reply(db: Session):
    properties = db.query(Property).order_by(Property.name).all()
    if not properties:
        return "There are no properties recorded yet. A leasing specialist can help add one."
    lines = []
    for property_ in properties:
        units = get_unit_availability(db, property_.id)
        freshness = inventory_freshness(units)
        if freshness["fresh"]:
            count = len(units)
            lines.append(f"{property_.name} at {property_.address}: {count} available home(s) in the live feed")
        else:
            lines.append(f"{property_.name} at {property_.address}: availability feed needs refresh")
    return "Property locations and live-feed status: " + "; ".join(lines) + "."


def _amenities_reply(db: Session, property_id: int | None, message: str):
    text = message.lower()
    named_property = next(
        (item for item in db.query(Property).all() if item.name.lower() in text),
        None,
    )
    if named_property:
        property_id = named_property.id
    query = db.query(Unit)
    if property_id and named_property:
        query = query.filter(Unit.property_id == property_id)
    units = query.order_by(Unit.property_id, Unit.unit_number).all()
    if not units:
        return "No unit amenities are recorded in the database yet."
    grouped = {}
    for unit in units:
        property_ = db.get(Property, unit.property_id)
        key = property_.name if property_ else f"Property {unit.property_id}"
        grouped.setdefault(key, set()).update(unit.amenities or [])
    return "Recorded property amenities: " + "; ".join(
        f"{name}: {', '.join(sorted(amenities)) if amenities else 'none listed'}"
        for name, amenities in grouped.items()
    ) + "."


def _match_reply(db: Session, profile: dict):
    budget = profile.get("budget_monthly")
    bedrooms = profile.get("bedrooms")
    wanted = set(profile.get("amenities", []))
    location = (profile.get("preferred_location") or "").lower()
    scored = []
    stale_properties = []
    for property_ in db.query(Property).order_by(Property.name).all():
        units = get_unit_availability(db, property_.id)
        freshness = inventory_freshness(units)
        if not freshness["fresh"]:
            stale_properties.append(property_.name)
            continue
        for unit in units:
            property_text = f"{property_.name} {property_.address}".lower()
            score = 0
            reasons = []
            if budget is not None:
                if unit.monthly_rent <= budget:
                    score += 3
                    reasons.append("within budget")
                else:
                    score -= 3
            if bedrooms is not None:
                if unit.beds == bedrooms:
                    score += 3
                    reasons.append("bedroom count matches")
                else:
                    score -= abs(unit.beds - bedrooms)
            unit_amenities = {amenity.lower() for amenity in (unit.amenities or [])}
            amenity_matches = wanted & unit_amenities
            score += len(amenity_matches) * 2
            if amenity_matches:
                reasons.append("matches " + ", ".join(sorted(amenity_matches)))
            if location and location in property_text:
                score += 2
                reasons.append("location matches")
            scored.append((score, property_, unit, reasons))
    if not scored:
        suffix = f" Refresh required for: {', '.join(stale_properties)}." if stale_properties else ""
        return "I cannot calculate a safe unit match until live inventory is refreshed." + suffix
    scored.sort(key=lambda item: (-item[0], item[2].monthly_rent))
    lines = []
    for score, property_, unit, reasons in scored[:3]:
        why = ", ".join(reasons) if reasons else "available in the live feed"
        lines.append(
            f"{property_.name} {unit.unit_number} at {property_.address}: "
            f"{unit.beds} bed, ${unit.monthly_rent:,.0f}/month ({why})"
        )
    return "Best current unit matches: " + "; ".join(lines) + "."


def _tour_reply(db: Session):
    tours = db.query(Tour).filter(Tour.status == "scheduled").order_by(Tour.starts_at).limit(10).all()
    if not tours:
        return "There are no scheduled tours in the calendar yet. Published touring hours are Monday through Saturday, 9 AM to 6 PM."
    lines = []
    for tour in tours:
        property_ = db.get(Property, tour.property_id)
        lines.append(f"{property_.name if property_ else 'Property'} on {tour.starts_at:%A, %b %d at %I:%M %p}")
    return "Scheduled tours: " + "; ".join(lines) + "."


def _property_details_reply(db: Session, message: str):
    properties = db.query(Property).order_by(Property.name).all()
    if not properties:
        return "There are no properties recorded in the database yet."
    text = message.lower()
    selected = next((item for item in properties if item.name.lower() in text), None)
    selected_properties = [selected] if selected else properties
    lines = []
    for property_ in selected_properties:
        unit_count = db.query(Unit).filter(Unit.property_id == property_.id).count()
        lines.append(
            f"{property_.name}: {property_.address}; {unit_count} unit(s) recorded; "
            f"published pet policy: {property_.pet_policy}"
        )
    return "Property details: " + " | ".join(lines) + "."


def _operations_fallback(db: Session, message: str):
    text = message.lower()
    properties = db.query(Property).count()
    units = db.query(Unit).count()
    leads = db.query(Lead).count()
    tours = db.query(Tour).filter(Tour.status == "scheduled").count()
    if "how many" in text or "count" in text or "overview" in text or "dashboard" in text:
        return f"Operations overview: {properties} properties, {units} units, {leads} leads, and {tours} scheduled tours."
    if "lead" in text:
        items = db.query(Lead).order_by(Lead.created_at.desc()).limit(10).all()
        return "Recent leads: " + "; ".join(
            f"#{item.id} {item.name} ({item.qualification_status}, needs: {_needs_summary(item.needs_profile or {})})"
            for item in items
        ) + "."
    if "unit" in text or "inventory" in text:
        items = db.query(Unit).order_by(Unit.monthly_rent).limit(10).all()
        return "Units in the database: " + "; ".join(
            f"{item.unit_number} {item.beds} bed ${item.monthly_rent:,.0f}/month ({item.status})"
            for item in items
        ) + "."
    return "I have access to the database for properties, units, leads, tours, and audit events. Ask for an operations overview, lead list, unit inventory, property details, or tour schedule."


def respond_to_lead(db: Session, lead: Lead, message: str):
    lead.needs_profile = _extract_needs(lead.needs_profile or {}, message)
    property_ = db.get(Property, lead.property_id) if lead.property_id else None
    units = get_unit_availability(db, lead.property_id) if lead.property_id else []
    freshness = inventory_freshness(units)
    text = message.lower()
    if "amenit" in text:
        fallback = _amenities_reply(db, lead.property_id, message)
    elif any(phrase in text for phrase in ("which unit", "what unit", "suits me", "best match", "recommend")):
        fallback = _match_reply(db, lead.needs_profile)
    elif any(phrase in text for phrase in ("tour", "schedule", "calendar", "appointment")):
        fallback = _tour_reply(db)
    elif any(phrase in text for phrase in ("all leads", "recent leads", "lead list", "unit inventory", "show me units", "operations", "database", "whole project", "overview")):
        fallback = _operations_fallback(db, message)
    elif any(phrase in text for phrase in ("where is", "where are", "address", "located")):
        fallback = _portfolio_availability_reply(db)
    elif any(phrase in text for phrase in ("property details", "tell me about", "what is", "what are the properties", "what are properties", "list properties", "show properties")):
        fallback = _property_details_reply(db, message)
    elif any(phrase in text for phrase in ("what properties", "what are properties", "which properties", "list properties", "show properties", "properties available", "available properties")):
        fallback = _portfolio_availability_reply(db)
    elif any(phrase in text for phrase in ("what does", "what do i need", "my needs", "my requirements")):
        fallback = "Here is the current lead-needs summary: " + _needs_summary(lead.needs_profile)
        if not lead.needs_profile:
            fallback += " Please share your budget, desired home size, move-in date, location, and amenities."
    else:
        fallback = _fallback_reply(property_, units, freshness, lead.needs_profile, message) if property_ else _portfolio_fallback(db)
    conversation = db.query(Conversation).filter_by(lead_id=lead.id).order_by(Conversation.id.desc()).first()
    if not conversation:
        raise ValueError("Lead conversation not found")
    db.add(ConversationMessage(
        conversation_id=conversation.id,
        channel=lead.channel,
        direction="inbound",
        body=message.strip(),
    ))
    db.flush()
    history = db.query(ConversationMessage).filter_by(conversation_id=conversation.id).order_by(ConversationMessage.id).all()
    transcript = "\n".join(f"{item.direction}: {item.body}" for item in history[-12:])
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    reply = fallback
    provider = "fallback"

    if api_key:
        instructions = (
            "You are a leasing information assistant. Answer only from the supplied property and live "
            "inventory context. Never invent or estimate pricing, availability, fees, policies, or tour "
            "times. Apply no protected-class or demographic criteria and never approve or deny an applicant. "
            "Do not provide legal advice. For accommodations, exceptions, complaints, uncertainty, or any "
            "request outside this context, say a leasing specialist should help. Always offer HUMAN handoff. "
            "Keep the response concise and friendly.\n\n"
            "When comparing properties, recommend only homes whose inventory is marked fresh. "
            "If no fresh match exists, explain that a specialist should follow up. Ask one focused "
            "question when the lead has not provided enough preferences.\n\n"
            f"Whole database snapshot (read-only):\n{_whole_database_context(db)}\n\n"
            f"Conversation so far:\n{transcript}\n\n"
            f"Current analyzed lead needs: {_needs_summary(lead.needs_profile)}"
        )
        try:
            response = requests.post(
                OPENAI_RESPONSES_URL,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "instructions": instructions, "input": message},
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
            reply = payload.get("output_text", "").strip() or fallback
            provider = "openai" if reply != fallback else "fallback"
        except (requests.RequestException, ValueError, AttributeError):
            provider = "fallback"

    db.add(ConversationMessage(
        conversation_id=conversation.id,
        channel=lead.channel,
        direction="outbound",
        body=reply,
    ))
    log_event(db, lead.id, "ai_response_sent", provider=provider, inventory_fresh= freshness["fresh"])
    db.commit()
    return {"reply": reply, "provider": provider, "inventory_fresh": freshness["fresh"],
            "needs_profile": lead.needs_profile, "needs_summary": _needs_summary(lead.needs_profile),
            "human_handoff_available": True}