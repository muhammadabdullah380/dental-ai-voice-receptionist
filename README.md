# Dental Clinic AI Voice Receptionist — "Riya"

An AI-powered voice receptionist for a dental clinic, built with **Vapi** (voice AI), a custom **FastAPI** backend, **n8n** for workflow automation/logging, and real integrations with **Google Calendar** and **Google Sheets**.

The assistant ("Riya") answers inbound calls, looks up and registers patients, checks availability, books/reschedules/cancels appointments, answers clinic FAQs, and logs a summary of every call — all without human intervention.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Tech Stack](#tech-stack)
3. [Repository Structure](#repository-structure)
4. [Backend Setup](#backend-setup)
5. [Google Calendar Setup](#google-calendar-setup)
6. [Google Sheets + n8n Setup](#google-sheets--n8n-setup)
7. [Vapi Setup](#vapi-setup)
8. [Exposing the Backend (ngrok)](#exposing-the-backend-ngrok)
9. [Backend API / Tool Reference](#backend-api--tool-reference)
10. [n8n Workflows](#n8n-workflows)
11. [Running the Full System](#running-the-full-system)
12. [Adding a New Clinic](#adding-a-new-clinic)
13. [Known Limitations / Future Work](#known-limitations--future-work)

---

## Architecture Overview

```
                    ┌──────────────────┐
   Phone Call  ───▶ │   Vapi Assistant  │  ("Riya")
                    │  (STT + LLM + TTS)│
                    └─────────┬─────────┘
                              │ tool calls (HTTPS, via ngrok)
                              ▼
                    ┌──────────────────┐
                    │  FastAPI Backend  │ ── Postgres (Supabase) — patients, appointments
                    │  (this repo)      │
                    └─────────┬─────────┘
                              │ webhook (call summary / appointment events)
                              ▼
                    ┌──────────────────┐
                    │       n8n         │
                    │  (workflows)      │
                    └─────────┬─────────┘
                              │
                 ┌────────────┴────────────┐
                 ▼                         ▼
        ┌────────────────┐       ┌──────────────────┐
        │ Google Calendar │       │  Google Sheets    │
        │ (real bookings) │       │ ("Dental Clinic   │
        └────────────────┘       │  Logs" — Call &   │
                                  │  Appointment logs) │
                                  └──────────────────┘
```

- **Vapi** handles the actual phone conversation (speech-to-text, LLM reasoning, text-to-speech) and calls backend "tools" (functions) whenever it needs to do something — look up a patient, check a slot, book an appointment, etc.
- **FastAPI backend** exposes those tools as HTTP endpoints, talks to a real Google Calendar (via a service account) for scheduling, and stores patient/appointment records in a Postgres database.
- **n8n** receives webhook events from the backend after each call (and after each booking/reschedule/cancel) and appends structured log rows to a **Google Sheet**, giving clinic staff a simple, non-technical way to review call activity.
- **ngrok** exposes the locally-running backend to the public internet so Vapi's cloud infrastructure can reach it.

---

## Tech Stack

| Layer            | Technology                                   |
|------------------|-----------------------------------------------|
| Voice AI         | Vapi (assistant, STT, LLM, TTS)               |
| Backend          | Python, FastAPI, Uvicorn                      |
| Database         | PostgreSQL (Supabase free tier)               |
| Calendar         | Google Calendar API (service account)         |
| Logging / Sheets | Google Sheets API, via n8n workflows          |
| Automation       | n8n (self-hosted, `n8n start`)                |
| Tunneling        | ngrok                                         |

---

## Repository Structure

```
dental-ai-backend/
├── app/
│   ├── api/
│   │   └── routes.py            # All Vapi tool endpoints (/tools/*)
│   ├── credentials/              # Google service account key (gitignored)
│   ├── db/                       # Database session/engine setup
│   ├── integrations/
│   │   ├── calendar_google.py    # GoogleCalendarProvider
│   │   └── factory.py            # Picks calendar provider based on .env
│   ├── models/                   # SQLAlchemy models
│   ├── services/
│   │   ├── appointment_service.py  # Booking logic, timezone handling, n8n webhook calls
│   │   └── patient_service.py
│   ├── config.py
│   └── main.py                   # FastAPI app entrypoint
├── venv/                         # Python virtual environment (gitignored)
├── .env                          # Environment variables (gitignored)
├── .gitignore
├── test_slots.json / test_patient.json / test_booking.json   # Manual test payloads
└── README.md
```

> An MCP server counterpart to this backend (`dental-mcp-server`) was also built and tested with Claude Desktop, exposing the same tools via the Model Context Protocol.

---

## Backend Setup

1. **Clone the repo and enter the folder:**
   ```bash
   git clone https://github.com/muhammadabdullah380/dental-ai-voice-receptionist.git
   cd dental-ai-voice-receptionist
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   # source venv/bin/activate   # macOS/Linux
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create a `.env` file** in the project root with the following keys:
   ```env
   DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<db>

   CALENDAR_PROVIDER=google
   GOOGLE_SERVICE_ACCOUNT_FILE=app/credentials/<your-service-account-key>.json
   GOOGLE_CALENDAR_ID=<clinic-calendar-email-or-id>

   N8N_CALL_SUMMARY_WEBHOOK_URL=http://localhost:5678/webhook/call-summary
   N8N_APPOINTMENT_WEBHOOK_URL=http://localhost:5678/webhook/appointment-log
   ```

5. **Run the backend:**
   ```bash
   uvicorn app.main:app --reload
   ```
   The API will be available at `http://127.0.0.1:8000`, with interactive docs at `http://127.0.0.1:8000/docs`.

---

## Google Calendar Setup

1. Create a project in **Google Cloud Console**.
2. Enable the **Google Calendar API** for that project.
3. Create a **Service Account**, and generate/download a JSON key for it.
4. Place the JSON key inside `app/credentials/` (this folder is gitignored — never commit it).
5. In **Google Calendar**, share the clinic's calendar with the service account's email address, granting **"Make changes and see all event details"** permission.
6. Set `GOOGLE_CALENDAR_ID` in `.env` to the calendar's ID (usually the owner's Gmail address, or a dedicated calendar ID from Calendar Settings).

> ⚠️ **Security note:** service account keys are sensitive credentials. If a key is ever accidentally exposed (e.g. pasted in chat, committed to git), rotate it immediately from **Google Cloud Console → IAM & Admin → Service Accounts → Keys**.

---

## Google Sheets + n8n Setup

Call summaries and appointment events are logged to a Google Sheet named **"Dental Clinic Logs"**, with two tabs:

- **Call Logs** — Call ID, Caller Number, Patient Name, Call Reason, Summary, Outcome, Appointment Created, Timestamp
- **Appointment Logs** — booking/reschedule/cancel events

### Setting this up from scratch:

1. **Install n8n** (requires Node.js — an LTS version such as v20 or v22 is recommended; n8n does not yet fully support the very latest Node releases):
   ```bash
   npm install n8n -g
   ```
2. **Start n8n:**
   ```bash
   n8n start
   ```
   n8n will be available at `http://localhost:5678`.
3. In n8n, create a **Google Sheets OAuth credential**:
   - In Google Cloud Console, enable the **Google Sheets API** and **Google Drive API**.
   - Create an **OAuth 2.0 Client ID** (Web application), with redirect URI `http://localhost:5678/rest/oauth2-credential/callback`.
   - Configure the OAuth consent screen (External, add your Google account as a test user).
   - In n8n, add a new Google Sheets credential and complete the OAuth login.
4. **Create two workflows** (or reuse the ones exported/included in this repo, if provided):
   - **Call Summary workflow:** `Webhook (POST)` → `Google Sheets – Append Row` (Call Logs tab)
   - **Appointment Booking workflow:** `Webhook (POST)` → `Google Sheets – Append Row` (Appointment Logs tab)
5. **Activate** both workflows (top-right toggle in each workflow) and copy their **Production URLs**.
6. Paste those Production URLs into your backend's `.env` file (`N8N_CALL_SUMMARY_WEBHOOK_URL`, `N8N_APPOINTMENT_WEBHOOK_URL`).

> **Important:** n8n must be running (`n8n start`) whenever the backend is live — if n8n is down, appointments/patients still save correctly to the database, but the Google Sheets log rows will not be created.

---

## Vapi Setup

1. Create a Vapi account and a new **Assistant** (this project's assistant is named **"Dental Doctor Clinic Receptionist"**, persona **"Riya"**).
2. Set the assistant's **System Prompt** to describe Riya's role and available tools (see `app/api/routes.py` for the exact tool names/behaviors).
3. Under the assistant's **Tools** tab, create one custom tool per backend endpoint, pointing each tool's **Server URL** to:
   ```
   https://<your-ngrok-subdomain>.ngrok-free.dev/tools/<tool_name>
   ```
   Tools implemented in this project:
   - `get_clinic_information`
   - `get_patient`
   - `create_patient`
   - `get_available_slots`
   - `book_appointment`
   - `reschedule_appointment`
   - `cancel_appointment`
   - `save_call_summary`
   - `end_reception_call`
4. Under **Advanced → Start Speaking Plan**, tune:
   - **Wait Seconds** — how long the assistant waits before speaking (raising this from the default reduces the assistant interrupting the caller).
   - **Smart Endpointing** — set to **Vapi** for more accurate detection of when the caller has finished speaking.
5. Test using the **Talk** button in the Vapi dashboard before assigning a real phone number.
6. When ready, assign a phone number under **Phone Numbers** (a free Vapi-provided number works for testing/demo purposes).

> ⚠️ Vapi's ngrok tool URLs must be updated every time ngrok is restarted, since the free ngrok tier assigns a new subdomain on each restart.

---

## Exposing the Backend (ngrok)

With the backend running on `http://127.0.0.1:8000`, expose it publicly:

```bash
ngrok http 8000
```

Copy the `https://...ngrok-free.dev` forwarding URL shown in the terminal, and update it in each Vapi tool's Server URL.

---

## Backend API / Tool Reference

All tool endpoints live under `app/api/routes.py` and follow Vapi's tool-call wrapper format:

- **Request:** `{"message": {"toolCallList": [...]}}`
- **Response:** `{"results": [{"toolCallId": ..., "result": ...}]}`

| Endpoint                        | Purpose                                              |
|----------------------------------|-------------------------------------------------------|
| `POST /tools/get_clinic_information` | Returns clinic hours, location, services, insurance, FAQs |
| `POST /tools/get_patient`        | Looks up an existing patient by phone number          |
| `POST /tools/create_patient`     | Registers a new patient                               |
| `POST /tools/get_available_slots`| Returns open appointment slots for a given date        |
| `POST /tools/book_appointment`   | Books a confirmed slot for a patient (real Google Calendar event) |
| `POST /tools/reschedule_appointment` | Moves an existing appointment to a new time       |
| `POST /tools/cancel_appointment` | Cancels an existing appointment                        |
| `POST /tools/save_call_summary`  | Saves a summary of the call before it ends              |

Interactive Swagger docs are available locally at `http://127.0.0.1:8000/docs` while the backend is running.

---

## n8n Workflows

| Workflow             | Trigger                                     | Action                                             |
|----------------------|----------------------------------------------|-----------------------------------------------------|
| Call Summary          | Webhook (called by `save_call_summary`)      | Appends a row to **Dental Clinic Logs → Call Logs** |
| Appointment Booking   | Webhook (called by `book_appointment`, `reschedule_appointment`, `cancel_appointment`) | Appends a row to **Dental Clinic Logs → Appointment Logs** |

---

## Running the Full System

To run a full end-to-end test (backend + calendar + Sheets logging + live voice call), start **three** processes, each in its own terminal:

```bash
# 1. n8n (workflow engine + Sheets logging)
n8n start

# 2. FastAPI backend
venv\Scripts\activate
uvicorn app.main:app --reload

# 3. ngrok (public tunnel for Vapi)
ngrok http 8000
```

Then:
1. Copy the ngrok forwarding URL into each tool's Server URL in the Vapi dashboard (if it changed since last run).
2. Use the **Talk** button in Vapi (or call the assigned phone number) to start a live conversation with Riya.
3. Verify the results:
   - New/updated events in **Google Calendar**.
   - New rows in the **Dental Clinic Logs** Google Sheet.

---

## Adding a New Clinic

This backend was built to be reusable across different clinics with minimal changes:

1. Create a new Google Cloud project (or reuse one) and a new service account + calendar share for the new clinic.
2. Update `.env` with the new clinic's `GOOGLE_CALENDAR_ID` and service account file path.
3. Update `get_clinic_information` (or its underlying data source) with the new clinic's hours, location, services, and FAQs.
4. Duplicate the two n8n workflows, pointing the Google Sheets node at a new spreadsheet (or a new tab) for the new clinic's logs.
5. Create a new Vapi assistant (or duplicate the existing one), update its persona/system prompt, and point its tools at the same backend (or a separate deployment) with the new clinic's ngrok/production URL.

---

## Known Limitations / Future Work

- Currently relies on **ngrok**, which changes URLs on every restart (a paid ngrok plan or a proper cloud deployment would give a stable URL).
- n8n and the backend are currently run locally; for production use, both should be deployed to a persistent server (e.g. a small VPS or cloud instance) rather than run from a developer machine.
- Error handling and logging could be made more robust (e.g. retries on n8n webhook failures, more structured application logs).
- No phone number is permanently assigned yet — a number should be purchased/assigned before real clinic use.
- The free Supabase Postgres tier can go idle and briefly delay the first request after inactivity.
