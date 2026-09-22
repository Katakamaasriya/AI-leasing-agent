import os
import re
import json
from typing import Optional, Dict, Any
import logging
from datetime import datetime

import requests
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from openai import AzureOpenAI

from .models import Conversation, ConversationMessage, Lead, LeadEvent, Property, Tour, Unit
from .services import get_unit_availability, inventory_freshness, log_event, qualify_lead, schedule_tour

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
AZURE_OPENAI_MODEL = os.getenv("AZURE_OPENAI_MODEL", "gpt-4o-mini")

# Fallback to OpenAI if Azure not configured
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Initialize Azure OpenAI client if configured
azure_client: Optional[AzureOpenAI] = None
if AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT:
    try:
        azure_client = AzureOpenAI(
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT
        )
        logger.info("Azure OpenAI client initialized successfully")
    except Exception as e:
        logger.warning(f"Failed to initialize Azure OpenAI client: {e}")


def _call_azure_openai(message: str, conversation_context: str, lead_needs: str, database_context: str) -> tuple[str, str]:
    """Call Azure OpenAI API for AI responses with fallback to OpenAI."""
    try:
        if azure_client:
            # Use Azure OpenAI
            system_prompt = f"""You are a professional leasing assistant for a property management company. Your role is to help prospects find their perfect home while maintaining compliance and providing excellent customer service.

INSTRUCTIONS:
- Be conversational, friendly, and professional
- Answer questions based ONLY on the provided property and inventory data
- Never invent pricing, availability, or details not in the database
- Apply qualification criteria objectively and consistently
- Never make discriminatory statements or use protected class information
- Always offer human handoff when prospects request it or ask complex questions
- Keep responses concise but helpful
- Ask one focused follow-up question when you need more information
- Proactively suggest next steps (tours, applications, etc.)

SAFETY GUARDRAILS:
- Never quote pricing from stale inventory (check freshness timestamps)
- If inventory is not fresh, explain why and offer human assistance
- For accommodations, exceptions, complaints, or legal questions: "A leasing specialist should help with that"
- Always maintain fair housing compliance

DATABASE CONTEXT:
{database_context}

CONVERSATION HISTORY:
{conversation_context}

CURRENT LEAD NEEDS:
{lead_needs}

Respond to the prospect's message appropriately based on this context."""

            response = azure_client.chat.completions.create(
                model=AZURE_OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            reply = response.choices[0].message.content.strip()
            provider = "azure_openai"
            logger.info(f"Azure OpenAI response generated successfully")
            return reply, provider
            
        elif OPENAI_API_KEY:
            # Fallback to OpenAI
            OPENAI_URL = "https://api.openai.com/v1/chat/completions"
            system_prompt = f"""You are a professional leasing assistant for a property management company. Your role is to help prospects find their perfect home while maintaining compliance and providing excellent customer service.

INSTRUCTIONS:
- Be conversational, friendly, and professional
- Answer questions based ONLY on the provided property and inventory data
- Never invent pricing, availability, or details not in the database
- Apply qualification criteria objectively and consistently
- Never make discriminatory statements or use protected class information
- Always offer human handoff when prospects request it or ask complex questions
- Keep responses concise but helpful
- Ask one focused follow-up question when you need more information
- Proactively suggest next steps (tours, applications, etc.)

SAFETY GUARDRAILS:
- Never quote pricing from stale inventory (check freshness timestamps)
- If inventory is not fresh, explain why and offer human assistance
- For accommodations, exceptions, complaints, or legal questions: "A leasing specialist should help with that"
- Always maintain fair housing compliance

DATABASE CONTEXT:
{database_context}

CONVERSATION HISTORY:
{conversation_context}

CURRENT LEAD NEEDS:
{lead_needs}

Respond to the prospect's message appropriately based on this context."""

            response = requests.post(
                OPENAI_URL,
                headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": OPENAI_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": message}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 500
                },
                timeout=20
            )
            response.raise_for_status()
            payload = response.json()
            reply = payload["choices"][0]["message"]["content"].strip()
            provider = "openai"
            logger.info(f"OpenAI response generated successfully")
            return reply, provider
            
        else:
            logger.warning("No AI provider configured, using fallback")
            return None, "fallback"
            
    except Exception as e:
        logger.error(f"AI API call failed: {e}")
        return None, "fallback"


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
    
    # Greeting and initial inquiry handling
    if any(phrase in text for phrase in ("hi", "hello", "hey", "good morning", "good afternoon", "good evening")):
        if not freshness["fresh"]:
            return (
                f"Hello! Thanks for your interest in {property_.name if property_ else 'our properties'}. "
                "I'd be happy to help you find your new home. However, our live availability feed needs to be refreshed, "
                "so I can't quote current pricing or availability. A leasing specialist can help you directly. "
                "Or reply HUMAN to speak with someone right away."
            )
        if not units:
            return (
                f"Hello! Thanks for your interest in {property_.name if property_ else 'our properties'}. "
                "Unfortunately, there are no available homes in our current listing feed. "
                "A leasing specialist can discuss upcoming availability with you. "
                "Or reply HUMAN to speak with someone right away."
            )
        return (
            f"Hello! Thanks for your interest in {property_.name if property_ else 'our properties'}. "
            "I'd be happy to help you find your new home. I can tell you about available units, pricing, amenities, "
            "and help schedule a tour. What's most important to you in your new home?"
        )
    
    # Budget-related questions
    if any(phrase in text for phrase in ("budget", "afford", "how much can i spend", "price range")) and any(
        phrase in text for phrase in ("what", "which", "my", "mentioned", "tell", "does", "want")
    ):
        budget = profile.get("budget_monthly")
        if budget:
            return f"Your recorded monthly budget is ${budget:,.0f}. Let me find units within that range."
        else:
            return "What's your monthly budget? This will help me find the perfect home for you."
    
    # Amenity questions
    if "amenit" in text:
        amenities = profile.get("amenities", [])
        if amenities:
            return f"You mentioned these amenities: {', '.join(amenities)}. I'll look for homes with these features."
        else:
            return "What amenities are important to you? For example: gym, pool, parking, in-unit laundry, balcony, etc."
    
    # Bedroom/home size questions
    if any(phrase in text for phrase in ("bedroom", "home size", "how many beds")) and any(
        phrase in text for phrase in ("what", "which", "my", "need", "how many", "does", "want")
    ):
        bedrooms = profile.get("bedrooms")
        if bedrooms is not None:
            return f"You're looking for {'a studio' if bedrooms == 0 else f'{bedrooms} bedroom'} home. Perfect!"
        else:
            return "What size home are you looking for? Studio, 1, 2, 3, or 4 bedrooms?"
    
    # Location questions
    if any(phrase in text for phrase in ("where", "location", "located", "area")):
        location = profile.get("preferred_location")
        if location:
            return f"Your preferred location is {location}. I'll focus on that area."
        else:
            return "What area or neighborhood are you most interested in?"
    
    # Summary questions
    if any(phrase in text for phrase in ("summary", "what do you know", "what did i tell", "what have i said")):
        summary = _needs_summary(profile)
        if summary == "I have not recorded any specific housing needs yet.":
            return "I haven't learned about your preferences yet. Tell me about your budget, desired home size, location, and any amenities you'd like."
        return f"Here's what I know about your preferences: {summary}"
    
    # Stale inventory warning
    if not freshness["fresh"]:
        return (
            "Our live availability feed needs to be refreshed, so I can't quote current pricing or availability. "
            "This is important because I want to make sure you get accurate information. "
            "A leasing specialist can help you with the most up-to-date information. "
            "Reply HUMAN to speak with someone right away."
        )
    
    # No units available
    if not units:
        return (
            f"I don't see any available homes in our current listing feed for {property_.name if property_ else 'our properties'}. "
            "This could mean they're all currently reserved. A leasing specialist can check for upcoming availability "
            "or similar options. Reply HUMAN to connect with someone who can help."
        )
    
    # Show available units
    unit_list = "; ".join(
        f"{unit.unit_number} ({unit.beds} bed, ${unit.monthly_rent:,.0f}/month)"
        for unit in units
    )
    return (
        f"Great question! Here's what's currently available at {property_.name if property_ else 'our properties'}: {unit_list}. "
        "Which one interests you most? I can also help you schedule a tour to see it in person. "
        "Just let me know your preferred date and time, or reply HUMAN to speak with a leasing specialist."
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
            "I'd love to help you find the perfect home across our properties, but our live inventory feed needs to be refreshed "
            "before I can quote current pricing or availability. This is important because I want to make sure you get accurate information. "
            "Tell me about your budget, move-in date, home size, and preferred location, and I'll be ready to help once the feed is updated. "
            "Or reply HUMAN to speak with a leasing specialist right away."
        )
    return (
        "Great! Here are the current live options across our properties: " + " | ".join(matches) +
        ". Tell me about your budget, move-in date, home size, and preferred location so I can recommend the best match for you. "
        "I can also help you schedule a tour to see any of these properties in person!"
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


def agent_chat(db: Session, lead: Lead, prompt: str) -> dict:
    """Run a read-first leasing tool loop with explicit side-effect guardrails."""
    units = get_unit_availability(db, lead.property_id) if lead.property_id else []
    text = prompt.lower()
    tool_context = f"The database contains {len(units)} available unit(s) for this lead's property."

    # Qualification requires facts that are not safe to infer from conversational text.
    if any(word in text for word in ("qualify", "qualification", "income requirement")):
        return {
            "reply": "Qualification uses published objective criteria only. Please use the Qualification page with verified monthly income, move-in date, and published pet-policy details; a leasing specialist reviews the result.",
            "tool_context": tool_context,
        }

    # Tour scheduling - provide helpful guidance
    if any(word in text for word in ("book a tour", "schedule a tour", "schedule tour", "tour", "visit", "see", "visit the", "come see")):
        tours = db.query(Tour).filter(Tour.status == "scheduled").order_by(Tour.starts_at).limit(5).all()
        if tours:
            tour_info = "; ".join(
                f"{tour.starts_at:%A, %b %d at %I:%M %p}" 
                for tour in tours
            )
            return {
                "reply": f"I'd be happy to help you schedule a tour! Currently scheduled tours include: {tour_info}. "
                "To book your tour, please use the Tours page where you can select your preferred date and time. "
                "I'll make sure your information is connected to the tour booking. Or reply HUMAN to speak with a leasing specialist directly.",
                "tool_context": tool_context,
            }
        else:
            return {
                "reply": "I'd be happy to help you schedule a tour! Our touring hours are Monday through Saturday, 9 AM to 6 PM. "
                "Please use the Tours page to select your preferred date and time, and I'll help connect it to your information. "
                "Or reply HUMAN to speak with a leasing specialist directly.",
                "tool_context": tool_context,
            }

    # Human handoff request
    if any(word in text for word in ("human", "person", "agent", "specialist", "real person", "talk to someone")):
        lead.human_requested = True
        db.commit()
        return {
            "reply": "I'll connect you with a leasing specialist right away. They'll have access to all our conversation and your preferences. "
            "Is there anything specific you'd like me to pass along to them?",
            "tool_context": tool_context,
        }

    result = respond_to_lead(db, lead, prompt)
    result["reply"] = f"{result['reply']}"
    return result


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
    
    # Enhanced conversation flow with proactive suggestions
    if any(phrase in text for phrase in ("which property", "what property", "suits", "best match", "recommend", "what would you recommend")):
        fallback = _match_reply(db, lead.needs_profile)
        if lead.needs_profile and any(lead.needs_profile.values()):
            fallback += " Would you like me to help you schedule a tour to see this property?"
    elif "amenit" in text:
        fallback = _amenities_reply(db, lead.property_id, message)
        fallback += " I can show you which units have these amenities. Would you like to see specific unit details?"
    elif any(phrase in text for phrase in ("which unit", "what unit", "suits me", "best match", "recommend")):
        fallback = _match_reply(db, lead.needs_profile)
        if lead.needs_profile and any(lead.needs_profile.values()):
            fallback += " I can help you schedule a tour to see this unit in person. When would you like to visit?"
    elif any(phrase in text for phrase in ("tour", "schedule", "calendar", "appointment")):
        fallback = _tour_reply(db)
        fallback += " To book a specific time, let me know your preferred date and time, or use the Tours page for the full calendar."
    elif any(phrase in text for phrase in ("all leads", "recent leads", "lead list", "unit inventory", "show me units", "operations", "database", "whole project", "overview")):
        fallback = _operations_fallback(db, message)
    elif any(phrase in text for phrase in ("where is", "where are", "address", "located")):
        fallback = _portfolio_availability_reply(db)
        fallback += " Would you like more details about any of these properties?"
    elif any(phrase in text for phrase in ("property details", "tell me about", "what is", "what are the properties", "what are properties", "list properties", "show properties")):
        fallback = _property_details_reply(db, message)
        fallback += " Is there a specific property you'd like to know more about?"
    elif any(phrase in text for phrase in ("what properties", "what are properties", "which properties", "list properties", "show properties", "properties available", "available properties")):
        fallback = _portfolio_availability_reply(db)
        fallback += " Tell me about your budget and preferences, and I can recommend the best fit for you."
    elif any(phrase in text for phrase in ("what does", "what do i need", "my needs", "my requirements")):
        fallback = "Here is the current lead-needs summary: " + _needs_summary(lead.needs_profile)
        if not lead.needs_profile or not any(lead.needs_profile.values()):
            fallback += " Please share your budget, desired home size, move-in date, location, and amenities so I can find the perfect home for you."
        else:
            missing_info = []
            if not lead.needs_profile.get("budget_monthly"): missing_info.append("budget")
            if lead.needs_profile.get("bedrooms") is None: missing_info.append("bedroom preference")
            if not lead.needs_profile.get("preferred_location"): missing_info.append("location preference")
            if missing_info:
                fallback += f" To give you better recommendations, could you tell me about your {', '.join(missing_info)}?"
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
    
    # Use new Azure OpenAI integration
    database_context = _whole_database_context(db)
    conversation_context = transcript
    lead_needs = _needs_summary(lead.needs_profile)
    
    ai_reply, provider = _call_azure_openai(message, conversation_context, lead_needs, database_context)
    
    if ai_reply:
        reply = ai_reply
    else:
        reply = fallback
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