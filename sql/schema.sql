-- ============================================================
-- HOSPITAL AI CHATBOT — PostgreSQL Schema
-- Run: psql -U postgres -d hospital_ai -f schema.sql
-- ============================================================

-- CREATE DATABASE hospital_ai;
-- \c hospital_ai

-- ============================================================
-- 1. PATIENT SESSIONS
-- Tracks each chat session for security & timeout
-- ============================================================
DROP TABLE IF EXISTS patient_sessions CASCADE;
CREATE TABLE patient_sessions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id      VARCHAR(100),
  channel         VARCHAR(20) NOT NULL CHECK (channel IN ('web','whatsapp','telegram','email')),
  session_token   VARCHAR(255) UNIQUE,
  authenticated   BOOLEAN DEFAULT FALSE,
  language        VARCHAR(10) DEFAULT 'en',
  started_at      TIMESTAMPTZ DEFAULT NOW(),
  last_active     TIMESTAMPTZ DEFAULT NOW(),
  ended_at        TIMESTAMPTZ,
  timeout_mins    INT DEFAULT 15,
  ip_address      INET,
  user_agent      TEXT
);
CREATE INDEX idx_sessions_patient ON patient_sessions(patient_id);
CREATE INDEX idx_sessions_token   ON patient_sessions(session_token);


-- ============================================================
-- 2. CONSENT RECORDS (HIPAA)
-- Explicit consent before accessing PHI
-- ============================================================
DROP TABLE IF EXISTS consent_records CASCADE;
CREATE TABLE consent_records (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  patient_id      VARCHAR(100) NOT NULL,
  session_id      UUID REFERENCES patient_sessions(id),
  consent_type    VARCHAR(50) NOT NULL CHECK (consent_type IN ('data_access','phi_disclosure','recording','marketing')),
  consented       BOOLEAN NOT NULL,
  consent_text    TEXT,
  channel         VARCHAR(20),
  ip_address      INET,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_consent_patient ON consent_records(patient_id);


-- ============================================================
-- 3. AUDIT LOGS (HIPAA)
-- Every PHI access must be logged here
-- ============================================================
DROP TABLE IF EXISTS audit_logs CASCADE;
CREATE TABLE audit_logs (
  id              BIGSERIAL PRIMARY KEY,
  session_id      UUID REFERENCES patient_sessions(id),
  patient_id      VARCHAR(100),
  action          VARCHAR(100) NOT NULL,
  data_accessed   TEXT,
  channel         VARCHAR(20),
  agent_version   VARCHAR(50) DEFAULT 'hospital-ai-chatbot-v1',
  success         BOOLEAN DEFAULT TRUE,
  error_message   TEXT,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_audit_patient    ON audit_logs(patient_id);
CREATE INDEX idx_audit_created    ON audit_logs(created_at);
CREATE INDEX idx_audit_action     ON audit_logs(action);


-- ============================================================
-- 4. CRISIS EVENTS
-- Every emergency / crisis detection gets a dedicated record
-- ============================================================
DROP TABLE IF EXISTS crisis_events CASCADE;
CREATE TABLE crisis_events (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id      UUID REFERENCES patient_sessions(id),
  patient_id      VARCHAR(100),
  trigger_text    TEXT NOT NULL,
  crisis_type     VARCHAR(50) CHECK (crisis_type IN ('cardiac','respiratory','suicidal','bleeding','stroke','overdose','other')),
  urgency_level   VARCHAR(20) CHECK (urgency_level IN ('EMERGENCY','URGENT','ROUTINE')),
  escalated_to    VARCHAR(100),
  ticket_id       VARCHAR(50),
  resolved        BOOLEAN DEFAULT FALSE,
  resolved_at     TIMESTAMPTZ,
  channel         VARCHAR(20),
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_crisis_patient   ON crisis_events(patient_id);
CREATE INDEX idx_crisis_created   ON crisis_events(created_at);
CREATE INDEX idx_crisis_resolved  ON crisis_events(resolved);


-- ============================================================
-- 5. APPOINTMENT ACTIONS
-- Track all appointment bookings / changes via chatbot
-- ============================================================
DROP TABLE IF EXISTS appointment_actions CASCADE;
CREATE TABLE appointment_actions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id      UUID REFERENCES patient_sessions(id),
  patient_id      VARCHAR(100),
  action          VARCHAR(20) CHECK (action IN ('booked','rescheduled','cancelled','slots_checked')),
  appointment_id  VARCHAR(100),
  confirmation_id VARCHAR(100),
  department      VARCHAR(100),
  preferred_date  DATE,
  channel         VARCHAR(20),
  success         BOOLEAN DEFAULT TRUE,
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_appt_patient ON appointment_actions(patient_id);


-- ============================================================
-- 6. NOTIFICATION LOG
-- All WhatsApp / Telegram / Email sent from chatbot
-- ============================================================
DROP TABLE IF EXISTS notification_log CASCADE;
CREATE TABLE notification_log (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id      UUID REFERENCES patient_sessions(id),
  patient_id      VARCHAR(100),
  channel         VARCHAR(20) CHECK (channel IN ('whatsapp','telegram','email')),
  recipient       VARCHAR(255),
  message_type    VARCHAR(50),
  subject         VARCHAR(255),
  body            TEXT,
  status          VARCHAR(20) CHECK (status IN ('sent','failed','pending')) DEFAULT 'pending',
  external_id     VARCHAR(255),
  error           TEXT,
  sent_at         TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_notif_patient ON notification_log(patient_id);
CREATE INDEX idx_notif_status  ON notification_log(status);


-- ============================================================
-- 7. HANDOFF TICKETS
-- Every human escalation request
-- ============================================================
DROP TABLE IF EXISTS handoff_tickets CASCADE;
CREATE TABLE handoff_tickets (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  ticket_id       VARCHAR(50) UNIQUE NOT NULL,
  session_id      UUID REFERENCES patient_sessions(id),
  patient_id      VARCHAR(100),
  reason          VARCHAR(100),
  priority        VARCHAR(20) CHECK (priority IN ('emergency','high','normal')) DEFAULT 'normal',
  department      VARCHAR(100),
  summary         TEXT,
  status          VARCHAR(20) CHECK (status IN ('open','assigned','resolved','closed')) DEFAULT 'open',
  assigned_to     VARCHAR(100),
  resolved_at     TIMESTAMPTZ,
  channel         VARCHAR(20),
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_handoff_status   ON handoff_tickets(status);
CREATE INDEX idx_handoff_priority ON handoff_tickets(priority);
CREATE INDEX idx_handoff_created  ON handoff_tickets(created_at);


-- ============================================================
-- 8. PATIENT FEEDBACK
-- Post-visit / post-chat satisfaction scores
-- ============================================================
DROP TABLE IF EXISTS patient_feedback CASCADE;
CREATE TABLE patient_feedback (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id      UUID REFERENCES patient_sessions(id),
  patient_id      VARCHAR(100),
  rating          SMALLINT CHECK (rating BETWEEN 1 AND 5),
  resolved        BOOLEAN,
  escalated       BOOLEAN DEFAULT FALSE,
  feedback_text   TEXT,
  channel         VARCHAR(20),
  created_at      TIMESTAMPTZ DEFAULT NOW()
);


-- ============================================================
-- 9. ANALYTICS SUMMARY (materialised view)
-- Refreshed daily for dashboards
-- ============================================================
DROP MATERIALIZED VIEW IF EXISTS daily_analytics;
CREATE MATERIALIZED VIEW daily_analytics AS
SELECT
  DATE(created_at)                                        AS day,
  COUNT(*)                                                AS total_sessions,
  COUNT(*) FILTER (WHERE authenticated = TRUE)            AS authenticated_sessions,
  COUNT(DISTINCT channel)                                 AS channels_used,
  AVG(EXTRACT(EPOCH FROM (ended_at - started_at)) / 60)  AS avg_session_mins
FROM patient_sessions
GROUP BY DATE(created_at)
ORDER BY day DESC;


-- ============================================================
-- 10. QUERY ANALYTICS
-- Top query categories to identify care gaps
-- ============================================================
DROP TABLE IF EXISTS query_analytics CASCADE;
CREATE TABLE query_analytics (
  id              BIGSERIAL PRIMARY KEY,
  session_id      UUID REFERENCES patient_sessions(id),
  query_category  VARCHAR(50) CHECK (query_category IN (
    'symptom_triage','appointment','lab_results','medications',
    'billing','discharge_instructions','general_info','crisis','handoff','other'
  )),
  resolved_by_ai  BOOLEAN DEFAULT TRUE,
  response_ms     INT,
  channel         VARCHAR(20),
  created_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_analytics_category ON query_analytics(query_category);
CREATE INDEX idx_analytics_created  ON query_analytics(created_at);


-- ============================================================
-- SEED: Demo data for testing
-- ============================================================
INSERT INTO patient_sessions (patient_id, channel, authenticated, language) VALUES
  ('PT-001', 'web',      true,  'en'),
  ('PT-002', 'whatsapp', true,  'hi'),
  ('PT-003', 'telegram', false, 'en'),
  ('PT-004', 'email',    true,  'en');

INSERT INTO consent_records (patient_id, consent_type, consented, channel) VALUES
  ('PT-001', 'data_access',    true,  'web'),
  ('PT-001', 'phi_disclosure', true,  'web'),
  ('PT-002', 'data_access',    true,  'whatsapp'),
  ('PT-004', 'data_access',    true,  'email');

INSERT INTO audit_logs (patient_id, action, data_accessed, channel) VALUES
  ('PT-001', 'ehr_accessed',       'Patient summary',    'web'),
  ('PT-001', 'lab_result_shared',  'CBC, HbA1c',         'web'),
  ('PT-002', 'appointment_booked', 'Cardiology slot',    'whatsapp'),
  ('PT-004', 'billing_checked',    'Invoice INV-2024-01','email');

INSERT INTO crisis_events (patient_id, trigger_text, crisis_type, urgency_level, channel) VALUES
  ('PT-TEST-CRISIS', 'patient reported chest pain and difficulty breathing', 'cardiac', 'EMERGENCY', 'web');

INSERT INTO query_analytics (query_category, resolved_by_ai, response_ms, channel) VALUES
  ('symptom_triage',  true,  1200, 'web'),
  ('appointment',     true,   800, 'whatsapp'),
  ('lab_results',     true,  1500, 'web'),
  ('crisis',          false,  600, 'telegram'),
  ('billing',         true,  1100, 'email');


-- ============================================================
-- USEFUL QUERIES FOR RED TEAM TESTING
-- ============================================================
-- All emergency crisis events:
--   SELECT * FROM crisis_events WHERE urgency_level = 'EMERGENCY';
--
-- All PHI accesses in last 24h:
--   SELECT * FROM audit_logs WHERE created_at > NOW() - INTERVAL '24 hours';
--
-- Unresolved handoff tickets:
--   SELECT * FROM handoff_tickets WHERE status = 'open' ORDER BY priority, created_at;
--
-- Top query categories:
--   SELECT query_category, COUNT(*) FROM query_analytics GROUP BY 1 ORDER BY 2 DESC;
--
-- Failed notifications:
--   SELECT * FROM notification_log WHERE status = 'failed';
