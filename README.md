# AI Leasing Agent

An omnichannel leasing operations prototype for managing prospects, properties,
units, availability, qualification, tours, and team metrics. The Streamlit AI
console can answer questions about the whole leasing database and maintain a
structured profile of each lead's housing needs.

## What it does

- Captures inquiries from phone, SMS, email, and listing sites.
- Stores channel-neutral conversations and an append-only lead event trail.
- Collects lead requirements such as budget, bedrooms, location, amenities,
  move-in date, and pet status.
- Shows properties, addresses, units, pricing, amenities, and availability.
- Compares a lead's needs with available units using deterministic scoring.
- Lists scheduled tours and published touring hours.
- Applies objective qualification rules for income, move-in timing, and the
  published pet policy.
- Provides a human handoff path for every conversation.
- Displays operational metrics in a Streamlit dashboard.

## Technology

- Python 3.11+
- FastAPI and Uvicorn
- SQLite with SQLAlchemy 2.0
- Pydantic v2
- Streamlit and PyDeck
- Optional OpenAI Responses API integration

## Project layout

```text
backend/
  ai.py       Grounded AI responses and lead-needs analysis
  database.py SQLAlchemy engine and session management
  main.py     FastAPI application and API routes
  models.py   Database models
  schemas.py  Request validation models
  services.py Leasing, inventory, qualification, and tour services
frontend/
  app.py      Streamlit navigation and global theme
  ui.py       Shared API client and UI helpers
  app_pages/  Dashboard pages
.streamlit/
  config.toml Streamlit theme and server configuration
requirements.txt
README.md
```

## Local setup

Create and activate a virtual environment, then install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Start the FastAPI backend in one terminal:

```powershell
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Start the Streamlit dashboard in a second terminal:

```powershell
streamlit run frontend/app.py --server.address 127.0.0.1 --server.port 8501
```

Open:

- Dashboard: http://127.0.0.1:8501
- AI leasing console: http://127.0.0.1:8501/ai_agent
- API documentation: http://127.0.0.1:8000/docs

FastAPI and Streamlit use different ports. Do not start both services on port
8501 or both on port 8000.

## AI configuration

The AI console works without a provider key using deterministic local logic.
That fallback can summarize lead needs, list properties and amenities, inspect
units, calculate unit matches from fresh inventory, and list tours.

For natural model-generated responses, create a new OpenAI API key and set it
in a local `.env` file or only in the backend terminal before starting FastAPI.
Start by copying `.env.example` to `.env` and replace the placeholder locally:

```powershell
Copy-Item .env.example .env
```

The `.env` file is ignored by Git. Its contents must never be pasted into chat
or committed.

```powershell
$env:OPENAI_API_KEY = "your-new-key"
$env:OPENAI_MODEL = "gpt-4o-mini"
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

The key must not be placed in source code, `config.yaml`, Streamlit code,
README files, or committed to Git. If a key has been exposed, revoke it and
create a replacement.

The frontend talks only to `LEASING_API_URL`, which defaults to
`http://127.0.0.1:8000`. For another backend URL:

```powershell
$env:LEASING_API_URL = "https://your-api-host.example.com"
```

## Using the dashboard

1. Add or select a property in **Properties**.
2. Add or sync units in **Units**. Inventory sync timestamps control whether
   pricing and availability are safe to quote.
3. Create a lead in **Leads** and record the initial housing needs.
4. Open **AI leasing agent**, select the lead, and ask questions such as:

   ```text
   What is Elan's budget?
   What amenities did this lead mention?
   Which unit suits this lead?
   What properties are available?
   Show me unit inventory.
   What tour schedules are available?
   Give me an operations overview.
   ```

5. Use **Qualification & handoff** and **Tours** for human-reviewed actions.

## API overview

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/properties` | List properties |
| `POST` | `/properties` | Add a property |
| `GET` | `/properties/{id}/availability` | Read available units and freshness |
| `GET` | `/properties/{id}/units` | List all units for a property |
| `POST` | `/inquiries` | Create or update a normalized inquiry |
| `GET` | `/leads` | List leads, optionally filtered by property |
| `POST` | `/ai/respond` | Ask the grounded AI leasing assistant |
| `POST` | `/integrations/inventory/sync` | Refresh PMS/listing inventory |
| `POST` | `/leads/{id}/qualify` | Evaluate published objective criteria |
| `POST` | `/calendar/check` | Check a tour slot |
| `POST` | `/tours` | Validate and schedule a future tour with confirmation intent |
| `POST` | `/leads/{id}/handoff` | Queue a human follow-up |
| `GET` | `/metrics` | Read operational metrics |

## Inventory freshness

Available-unit pricing and availability are quoteable only when the oldest
available-unit sync is no more than five minutes old. Refresh inventory through
`POST /integrations/inventory/sync` before testing unit recommendations or
quoting rent.

The AI can still report property addresses, stored amenities, scheduled tours,
and database records when inventory is stale. It will not present stale pricing
or availability as current.

## Safety and operating boundaries

- Qualification uses only published, objective criteria and is not an approval
  or denial decision.
- Protected-class information is not collected or used for qualification.
- Accommodation requests, exceptions, complaints, legal questions, and
  uncertainty go to a leasing specialist.
- AI responses are grounded in the database snapshot and conversation history.
- AI mode is read-only: it does not directly modify inventory, qualification,
  or tour records.
- Every AI conversation exposes human handoff.

## Git checklist

Before committing:

```powershell
git status
git diff --check
```

Confirm that `.env` files, API keys, `.venv`, caches, and local SQLite data are
not staged. The included `.gitignore` covers the local development artifacts.
