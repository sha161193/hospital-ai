# Hospital AI Chatbot — Aria
### Built with Flowise + GPT-4o

---

## What's Included

| File | Purpose |
|---|---|
| `flowise/patient_chatflow.json` | Import directly into Flowise |
| `sql/schema.sql` | PostgreSQL schema (audit logs, sessions, consent) |
| `.env.example` | All environment variables needed |

---

## Step 1 — Start Flowise

```bash
npm install -g flowise
npx flowise start --FLOWISE_USERNAME=admin --FLOWISE_PASSWORD=yourpassword
```

Open http://localhost:3000

---

## Step 2 — Import the Chatflow

1. Flowise → **Add New** chatflow
2. Click ⚙️ Settings → **Load Chatflow**
3. Upload `flowise/patient_chatflow.json`

---

## Step 3 — Add Credentials

Go to **Credentials** in Flowise sidebar and add:

| Credential Type | Fields |
|---|---|
| OpenAI API | API Key |
| Google API (optional for Gmail) | Client ID, Client Secret |

---

## Step 4 — Set Environment Variables

Flowise → **Settings → Environment Variables**, add all from `.env.example`:

```
OPENAI_API_KEY
EHR_API_BASE_URL
EHR_API_KEY
TWILIO_ACCOUNT_SID
TWILIO_AUTH_TOKEN
TWILIO_WHATSAPP_FROM
TELEGRAM_BOT_TOKEN
SENDGRID_API_KEY
HOSPITAL_FROM_EMAIL
```

---

## Step 5 — Set Up PostgreSQL

```bash
psql -U postgres -c "CREATE DATABASE hospital_ai;"
psql -U postgres -d hospital_ai -f sql/schema.sql
```

---

## Step 6 — Connect Channels

### Web Widget
1. Flowise → your chatflow → **</> Embed**
2. Copy the iframe or script tag
3. Paste into your hospital website

### WhatsApp
1. Sign up at twilio.com
2. Activate WhatsApp Sandbox
3. Set webhook URL: `https://yourdomain.com/api/v1/prediction/<chatflow-id>`

### Telegram
1. Create bot via @BotFather → get token
2. Set webhook:
```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -d "url=https://yourdomain.com/api/v1/prediction/<chatflow-id>"
```

### Email
1. Sign up at sendgrid.com
2. Verify sender domain
3. Set inbound parse webhook to Flowise prediction endpoint

---

## Tool Summary

| Tool | What It Does |
|---|---|
| `assess_symptoms` | Triage: EMERGENCY / URGENT / ROUTINE + crisis detection |
| `manage_appointment` | Book, reschedule, cancel, get available slots |
| `lookup_patient_ehr` | Access patient history, labs, medications (auth required) |
| `request_prescription_refill` | Route refill requests to prescribing doctor |
| `check_billing_insurance` | Balance, invoice, coverage queries |
| `send_whatsapp_notification` | WhatsApp confirmations and reminders |
| `send_telegram_notification` | Telegram notifications |
| `send_email_notification` | Email via SendGrid |
| `escalate_to_human` | Human handoff with priority routing |
| `write_audit_log` | HIPAA audit trail for all PHI access |

---

## EHR API Endpoints Expected

Your custom REST API must implement:

```
GET  /api/appointments/slots?department=&date=
POST /api/appointments/book
PUT  /api/appointments/:id/reschedule
DEL  /api/appointments/:id/cancel

GET  /api/patients/:id/records/summary
GET  /api/patients/:id/records/lab_results
GET  /api/patients/:id/records/medications
GET  /api/patients/:id/records/appointments

POST /api/prescriptions/refill
GET  /api/billing/:id/balance
GET  /api/billing/:id/insurance_coverage

POST /api/handoff
POST /api/audit-log
```

---

## Crisis Escalation Flow

```
Patient message
      ↓
assess_symptoms (crisis keywords detected)
      ↓
urgency = EMERGENCY
      ↓
escalate_to_human (priority=emergency)
      ↓
write_audit_log (crisis event)
      ↓
Aria responds: "Call 911 immediately. Staff notified."
```

---

## HIPAA Compliance Checklist

- [x] Consent collected before PHI access (`consent_records` table)
- [x] All PHI access logged (`audit_logs` table)
- [x] Session timeout (15 min default)
- [x] AI identity always disclosed
- [x] Medical disclaimer on every clinical response
- [x] Crisis events logged separately (`crisis_events` table)
- [x] Human handoff always available
- [ ] Data encryption at rest (configure at DB/cloud level)
- [ ] TLS for all API calls (configure at infra level)
- [ ] BAA with Flowise/OpenAI vendors (arrange separately)

---

## Test Prompts

```
"I have chest pain and can't breathe"          → Should trigger EMERGENCY + handoff
"I need to book an appointment for next Monday" → Should use manage_appointment
"What are my latest lab results?"               → Should check auth → lookup_patient_ehr
"Can I get a refill for my metformin?"          → Should use request_prescription_refill
"What's my outstanding balance?"                → Should use check_billing_insurance
"I want to talk to a real person"               → Should use escalate_to_human
"مرحباً، أحتاج مساعدة"                          → Should respond in Arabic
```
