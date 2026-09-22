# AI Leasing Agent - Project Architecture & Context

## Tech Stack Overview
- **Backend:** Python, FastAPI, Uvicorn
- **Database & ORM:** SQLite, SQLAlchemy
- **Validation:** Pydantic
- **Frontend:** Streamlit / React
- **Visualization:** PyDeck (Deck.gl wrapper)
- **Data Processing:** Pandas, NumPy

## Core Domain Logic
This agent handles property leasing inquiries (Phone, SMS, Email, Listing Webhooks).

### Architecture & Tools
1. `get_unit_availability(unit_type, timeline)`
2. `get_pricing_and_amenities(unit_id)`
3. `qualify_lead(income, timeline, pet_status)`
4. `check_calendar_availability(date_range)`
5. `schedule_tour(lead_id, slot_time)`
6. `send_confirmation(contact_info, tour_details)`

### Strict Business Guardrails
- NEVER quote stale or hardcoded pricing. Always source directly via live DB query / tool call.
- MUST comply with Fair Housing regulations (non-discriminatory, consistent objective screening).
- ALWAYS provide a human fallback/handoff option if the query is out-of-scope.