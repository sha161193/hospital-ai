"""
Hospital Mock EHR API v3 — PostgreSQL backed
- All patient_id foreign keys allow NULL (for unauthenticated bookings)
- All write endpoints use explicit commit/rollback
- All endpoints return proper JSON errors (no more HTML 500 pages)
- New endpoint: POST /api/patients/register (for new patient registration)
"""

import os
import uuid
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify
import psycopg2
import psycopg2.extras

app = Flask(__name__)

# ─────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────

def get_db():
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        conn = psycopg2.connect(database_url, cursor_factory=psycopg2.extras.RealDictCursor)
    else:
        conn = psycopg2.connect(
            host=os.environ.get("PGHOST", "localhost"),
            port=os.environ.get("PGPORT", 5432),
            user=os.environ.get("PGUSER", "postgres"),
            password=os.environ.get("PGPASSWORD", ""),
            dbname=os.environ.get("PGDATABASE", "railway"),
            cursor_factory=psycopg2.extras.RealDictCursor
        )
    conn.autocommit = False
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                patient_id    TEXT PRIMARY KEY,
                name          TEXT NOT NULL,
                dob           DATE,
                blood_type    TEXT,
                allergies     TEXT[],
                conditions    TEXT[],
                phone         TEXT,
                email         TEXT,
                address       TEXT,
                created_at    TIMESTAMPTZ DEFAULT NOW(),
                last_visit    DATE
            );

            CREATE TABLE IF NOT EXISTS medications (
                id            SERIAL PRIMARY KEY,
                patient_id    TEXT REFERENCES patients(patient_id),
                name          TEXT NOT NULL,
                dosage        TEXT,
                frequency     TEXT,
                prescriber    TEXT,
                start_date    DATE,
                active        BOOLEAN DEFAULT TRUE
            );

            CREATE TABLE IF NOT EXISTS lab_results (
                id            SERIAL PRIMARY KEY,
                patient_id    TEXT REFERENCES patients(patient_id),
                test_name     TEXT NOT NULL,
                value         TEXT,
                unit          TEXT,
                status        TEXT DEFAULT 'normal',
                test_date     DATE DEFAULT CURRENT_DATE,
                notes         TEXT
            );

            CREATE TABLE IF NOT EXISTS appointments (
                id               SERIAL PRIMARY KEY,
                confirmation_id  TEXT UNIQUE,
                patient_id       TEXT,
                doctor           TEXT,
                department       TEXT,
                appointment_date DATE,
                appointment_time TEXT,
                reason           TEXT,
                status           TEXT DEFAULT 'scheduled',
                created_at       TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS refill_requests (
                id               SERIAL PRIMARY KEY,
                request_id       TEXT UNIQUE,
                patient_id       TEXT,
                medication_name  TEXT NOT NULL,
                pharmacy_name    TEXT,
                prescriber       TEXT,
                notes            TEXT,
                status           TEXT DEFAULT 'pending',
                estimated_hours  INT DEFAULT 24,
                created_at       TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS billing (
                id               SERIAL PRIMARY KEY,
                patient_id       TEXT REFERENCES patients(patient_id),
                outstanding      NUMERIC(10,2) DEFAULT 0,
                due_date         DATE,
                last_payment     NUMERIC(10,2) DEFAULT 0,
                last_payment_date DATE,
                insurer          TEXT,
                plan_name        TEXT,
                policy_number    TEXT,
                deductible       NUMERIC(10,2) DEFAULT 0,
                deductible_met   NUMERIC(10,2) DEFAULT 0,
                copay            NUMERIC(10,2) DEFAULT 0,
                in_network       BOOLEAN DEFAULT TRUE
            );

            CREATE TABLE IF NOT EXISTS invoices (
                id               SERIAL PRIMARY KEY,
                invoice_id       TEXT UNIQUE,
                patient_id       TEXT,
                amount           NUMERIC(10,2),
                invoice_date     DATE DEFAULT CURRENT_DATE,
                due_date         DATE,
                services         TEXT[],
                status           TEXT DEFAULT 'unpaid'
            );

            CREATE TABLE IF NOT EXISTS discharge_notes (
                id               SERIAL PRIMARY KEY,
                patient_id       TEXT REFERENCES patients(patient_id),
                notes            TEXT,
                discharge_date   DATE DEFAULT CURRENT_DATE,
                doctor           TEXT
            );

            CREATE TABLE IF NOT EXISTS imaging (
                id               SERIAL PRIMARY KEY,
                patient_id       TEXT REFERENCES patients(patient_id),
                scan_type        TEXT,
                body_part        TEXT,
                result           TEXT,
                scan_date        DATE DEFAULT CURRENT_DATE,
                radiologist      TEXT
            );

            CREATE TABLE IF NOT EXISTS handoff_tickets (
                id               SERIAL PRIMARY KEY,
                ticket_id        TEXT UNIQUE,
                patient_id       TEXT,
                reason           TEXT,
                priority         TEXT,
                summary          TEXT,
                department       TEXT,
                status           TEXT DEFAULT 'open',
                created_at       TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id               SERIAL PRIMARY KEY,
                action           TEXT NOT NULL,
                patient_id       TEXT,
                data_accessed    TEXT,
                channel          TEXT,
                agent_version    TEXT,
                created_at       TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS available_slots (
                id               SERIAL PRIMARY KEY,
                doctor           TEXT NOT NULL,
                department       TEXT NOT NULL,
                slot_date        DATE NOT NULL,
                slot_time        TEXT NOT NULL,
                available        BOOLEAN DEFAULT TRUE
            );
        """)
        conn.commit()
        print("Database tables initialised")
    except Exception as e:
        conn.rollback()
        print(f"DB init warning: {e}")
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("x-api-key") or request.headers.get("X-Api-Key")
        expected = os.environ.get("EHR_API_KEY", "dev-key")
        if key != expected:
            return jsonify({"error": "Unauthorized", "message": "Invalid API key"}), 401
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────

@app.route("/", methods=["GET"])
@require_api_key
def health():
    return jsonify({
        "status": "ok",
        "service": "Hospital Mock EHR API",
        "version": "3.0.0",
        "database": "postgresql",
        "timestamp": datetime.utcnow().isoformat()
    })


# ─────────────────────────────────────────
# PATIENTS
# ─────────────────────────────────────────

@app.route("/api/patients", methods=["POST"])
@app.route("/api/patients/register", methods=["POST"])
@require_api_key
def create_patient():
    """Register a new patient. Returns patient_id."""
    data = request.get_json()
    if not data or not data.get("name"):
        return jsonify({
            "error": "Missing required field: name",
            "required_fields": {
                "name": "Full name (required)",
                "dob": "Date of birth YYYY-MM-DD (optional)",
                "blood_type": "e.g. O+, A-, B+ (optional)",
                "allergies": "List of allergies e.g. ['Penicillin'] (optional)",
                "conditions": "List of conditions e.g. ['Diabetes'] (optional)",
                "phone": "Phone with country code e.g. +911234567890 (optional)",
                "email": "Email address (optional)"
            }
        }), 400

    patient_id = data.get("patient_id") or "PT-" + str(uuid.uuid4())[:8].upper()
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO patients (patient_id, name, dob, blood_type, allergies, conditions, phone, email, address)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (patient_id) DO UPDATE SET
                name = EXCLUDED.name,
                phone = EXCLUDED.phone,
                email = EXCLUDED.email
            RETURNING patient_id
        """, (
            patient_id,
            data.get("name"),
            data.get("dob") or None,
            data.get("blood_type"),
            data.get("allergies", []),
            data.get("conditions", []),
            data.get("phone"),
            data.get("email"),
            data.get("address")
        ))
        row = cur.fetchone()
        conn.commit()
        return jsonify({
            "success": True,
            "patient_id": row["patient_id"],
            "name": data.get("name"),
            "message": "Patient registered successfully. Save your patient_id: " + row["patient_id"]
        }), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/patients/<patient_id>", methods=["GET"])
@require_api_key
def get_patient(patient_id):
    """Check if a patient exists."""
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT patient_id, name, phone, email, created_at FROM patients WHERE patient_id = %s", (patient_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"exists": False, "error": "Patient not found. Please register first."}), 404
        conn.commit()
        return jsonify({"exists": True, "patient": dict(row)})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/patients/<patient_id>/records/<record_type>", methods=["GET"])
@require_api_key
def get_patient_records(patient_id, record_type):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM patients WHERE patient_id = %s", (patient_id,))
        patient = cur.fetchone()
        if not patient:
            conn.commit()
            return jsonify({
                "error": "Patient not found",
                "message": f"No patient with ID {patient_id}. Please register the patient first using the register_patient tool.",
                "patient_id": patient_id
            }), 404

        if record_type == "summary":
            conn.commit()
            return jsonify({
                "patient_id": patient["patient_id"],
                "name": patient["name"],
                "dob": str(patient["dob"]) if patient["dob"] else None,
                "blood_type": patient["blood_type"],
                "allergies": patient["allergies"] or [],
                "conditions": patient["conditions"] or [],
                "phone": patient["phone"],
                "email": patient["email"],
                "last_visit": str(patient["last_visit"]) if patient["last_visit"] else None
            })

        elif record_type == "lab_results":
            cur.execute("""
                SELECT test_name, value, unit, status, test_date::text as date, notes
                FROM lab_results WHERE patient_id = %s ORDER BY test_date DESC
            """, (patient_id,))
            rows = cur.fetchall()
            conn.commit()
            return jsonify({"patient_id": patient_id, "results": [dict(r) for r in rows]})

        elif record_type == "medications":
            cur.execute("""
                SELECT name, dosage, frequency, prescriber, start_date::text
                FROM medications WHERE patient_id = %s AND active = TRUE ORDER BY start_date DESC
            """, (patient_id,))
            rows = cur.fetchall()
            conn.commit()
            return jsonify({"patient_id": patient_id, "medications": [dict(r) for r in rows]})

        elif record_type == "appointments":
            cur.execute("""
                SELECT confirmation_id, doctor, department,
                       appointment_date::text as date, appointment_time as time,
                       reason, status
                FROM appointments WHERE patient_id = %s ORDER BY appointment_date DESC
            """, (patient_id,))
            rows = cur.fetchall()
            conn.commit()
            return jsonify({"patient_id": patient_id, "appointments": [dict(r) for r in rows]})

        elif record_type == "imaging":
            cur.execute("""
                SELECT scan_type, body_part, result, scan_date::text as date, radiologist
                FROM imaging WHERE patient_id = %s ORDER BY scan_date DESC
            """, (patient_id,))
            rows = cur.fetchall()
            conn.commit()
            return jsonify({"patient_id": patient_id, "imaging": [dict(r) for r in rows]})

        elif record_type == "discharge_notes":
            cur.execute("""
                SELECT notes, discharge_date::text as date, doctor
                FROM discharge_notes WHERE patient_id = %s ORDER BY discharge_date DESC LIMIT 1
            """, (patient_id,))
            row = cur.fetchone()
            conn.commit()
            if not row:
                return jsonify({"error": "No discharge notes found"}), 404
            return jsonify(dict(row))

        else:
            conn.commit()
            return jsonify({"error": f"Unknown record type: {record_type}. Valid types: summary, lab_results, medications, appointments, imaging, discharge_notes"}), 400

    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────
# APPOINTMENTS
# ─────────────────────────────────────────

@app.route("/api/appointments/slots", methods=["GET"])
@require_api_key
def get_slots():
    department = request.args.get("department", "General Practice")
    slot_date  = request.args.get("date")
    conn = get_db()
    cur = conn.cursor()
    try:
        if slot_date:
            cur.execute("""
                SELECT doctor, department, slot_date::text as date, slot_time as time
                FROM available_slots
                WHERE department ILIKE %s AND slot_date = %s AND available = TRUE
                ORDER BY slot_time
            """, (f"%{department}%", slot_date))
        else:
            cur.execute("""
                SELECT doctor, department, slot_date::text as date, slot_time as time
                FROM available_slots
                WHERE department ILIKE %s AND available = TRUE AND slot_date >= CURRENT_DATE
                ORDER BY slot_date, slot_time
                LIMIT 10
            """, (f"%{department}%",))
        rows = cur.fetchall()
        conn.commit()
        return jsonify({"department": department, "slots": [dict(r) for r in rows]})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/appointments/book", methods=["POST"])
@require_api_key
def book_appointment():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    patient_id  = data.get("patient_id") or None
    department  = data.get("department", "General Practice")
    pref_date   = data.get("preferred_date") or None
    reason      = data.get("reason", "General consultation")

    conn = get_db()
    cur = conn.cursor()
    try:
        # Verify patient exists if patient_id provided
        if patient_id:
            cur.execute("SELECT patient_id FROM patients WHERE patient_id = %s", (patient_id,))
            if not cur.fetchone():
                conn.commit()
                return jsonify({
                    "error": f"Patient {patient_id} not found",
                    "message": "Please register the patient first before booking an appointment.",
                    "how_to_register": "Use the register_patient tool with the patient's name and details."
                }), 404

        # Find available slot
        if pref_date:
            cur.execute("""
                SELECT id, doctor, department, slot_date, slot_time
                FROM available_slots
                WHERE department ILIKE %s AND slot_date = %s AND available = TRUE
                ORDER BY slot_time LIMIT 1
            """, (f"%{department}%", pref_date))
        else:
            cur.execute("""
                SELECT id, doctor, department, slot_date, slot_time
                FROM available_slots
                WHERE department ILIKE %s AND available = TRUE AND slot_date >= CURRENT_DATE
                ORDER BY slot_date, slot_time LIMIT 1
            """, (f"%{department}%",))

        slot = cur.fetchone()
        if not slot:
            conn.commit()
            return jsonify({
                "error": "No available slots found",
                "department": department,
                "requested_date": pref_date,
                "suggestion": "Try a different date or department."
            }), 404

        confirmation_id = "APT-" + str(uuid.uuid4())[:8].upper()

        cur.execute("""
            INSERT INTO appointments
                (confirmation_id, patient_id, doctor, department, appointment_date, appointment_time, reason)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (confirmation_id, patient_id, slot["doctor"], slot["department"], slot["slot_date"], slot["slot_time"], reason))

        cur.execute("UPDATE available_slots SET available = FALSE WHERE id = %s", (slot["id"],))

        if patient_id:
            cur.execute("UPDATE patients SET last_visit = %s WHERE patient_id = %s", (slot["slot_date"], patient_id))

        conn.commit()
        return jsonify({
            "success": True,
            "confirmation_id": confirmation_id,
            "patient_id": patient_id,
            "doctor": slot["doctor"],
            "department": slot["department"],
            "date": str(slot["slot_date"]),
            "time": slot["slot_time"],
            "reason": reason,
            "status": "scheduled"
        }), 201

    except Exception as e:
        conn.rollback()
        return jsonify({"error": "Booking failed", "detail": str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/appointments/<appointment_id>/reschedule", methods=["PUT"])
@require_api_key
def reschedule_appointment(appointment_id):
    data = request.get_json()
    new_date = (data.get("preferred_date") or None) if data else None
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM appointments WHERE confirmation_id = %s AND status = 'scheduled'", (appointment_id,))
        appt = cur.fetchone()
        if not appt:
            conn.commit()
            return jsonify({"error": f"Appointment {appointment_id} not found or already cancelled"}), 404

        if new_date:
            cur.execute("""
                SELECT id, doctor, department, slot_date, slot_time FROM available_slots
                WHERE department ILIKE %s AND slot_date = %s AND available = TRUE
                ORDER BY slot_time LIMIT 1
            """, (f"%{appt['department']}%", new_date))
        else:
            cur.execute("""
                SELECT id, doctor, department, slot_date, slot_time FROM available_slots
                WHERE department ILIKE %s AND available = TRUE AND slot_date > CURRENT_DATE
                ORDER BY slot_date, slot_time LIMIT 1
            """, (f"%{appt['department']}%",))

        slot = cur.fetchone()
        if not slot:
            conn.commit()
            return jsonify({"error": "No available slots found for rescheduling"}), 404

        new_confirmation = "APT-" + str(uuid.uuid4())[:8].upper()

        cur.execute("UPDATE available_slots SET available = TRUE WHERE department = %s AND slot_date = %s AND slot_time = %s",
                    (appt["department"], appt["appointment_date"], appt["appointment_time"]))
        cur.execute("UPDATE appointments SET status = 'rescheduled' WHERE confirmation_id = %s", (appointment_id,))
        cur.execute("""
            INSERT INTO appointments (confirmation_id, patient_id, doctor, department, appointment_date, appointment_time, reason)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (new_confirmation, appt["patient_id"], slot["doctor"], slot["department"], slot["slot_date"], slot["slot_time"], appt["reason"]))
        cur.execute("UPDATE available_slots SET available = FALSE WHERE id = %s", (slot["id"],))

        conn.commit()
        return jsonify({
            "success": True,
            "confirmation_id": new_confirmation,
            "old_confirmation_id": appointment_id,
            "date": str(slot["slot_date"]),
            "time": slot["slot_time"],
            "doctor": slot["doctor"],
            "status": "rescheduled"
        })
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/appointments/<appointment_id>/cancel", methods=["DELETE"])
@require_api_key
def cancel_appointment(appointment_id):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM appointments WHERE confirmation_id = %s AND status = 'scheduled'", (appointment_id,))
        appt = cur.fetchone()
        if not appt:
            conn.commit()
            return jsonify({"error": f"Appointment {appointment_id} not found or already cancelled"}), 404

        cur.execute("UPDATE appointments SET status = 'cancelled' WHERE confirmation_id = %s", (appointment_id,))
        cur.execute("UPDATE available_slots SET available = TRUE WHERE department = %s AND slot_date = %s AND slot_time = %s",
                    (appt["department"], appt["appointment_date"], appt["appointment_time"]))

        conn.commit()
        return jsonify({
            "success": True,
            "confirmation_id": appointment_id,
            "status": "cancelled",
            "message": "Appointment cancelled successfully."
        })
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────
# PRESCRIPTIONS
# ─────────────────────────────────────────

@app.route("/api/prescriptions/refill", methods=["POST"])
@require_api_key
def request_refill():
    data = request.get_json()
    if not data or not data.get("medication_name"):
        return jsonify({
            "error": "medication_name is required",
            "required_fields": {
                "medication_name": "Name of the medication (required)",
                "patient_id": "Patient ID (optional but recommended)",
                "pharmacy_name": "Preferred pharmacy (optional)",
                "notes": "Notes for the doctor (optional)"
            }
        }), 400

    patient_id      = data.get("patient_id") or None
    medication_name = data.get("medication_name")
    pharmacy_name   = data.get("pharmacy_name")
    notes           = data.get("notes")

    conn = get_db()
    cur = conn.cursor()
    try:
        prescriber = "Your Doctor"
        if patient_id:
            cur.execute("SELECT patient_id FROM patients WHERE patient_id = %s", (patient_id,))
            if not cur.fetchone():
                conn.commit()
                return jsonify({
                    "error": f"Patient {patient_id} not found",
                    "message": "Please register the patient first."
                }), 404
            cur.execute("SELECT prescriber FROM medications WHERE patient_id = %s AND name ILIKE %s AND active = TRUE LIMIT 1",
                        (patient_id, f"%{medication_name}%"))
            med = cur.fetchone()
            if med:
                prescriber = med["prescriber"]

        request_id = "RFL-" + str(uuid.uuid4())[:8].upper()
        cur.execute("""
            INSERT INTO refill_requests (request_id, patient_id, medication_name, pharmacy_name, prescriber, notes)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (request_id, patient_id, medication_name, pharmacy_name, prescriber, notes))

        conn.commit()
        return jsonify({
            "success": True,
            "request_id": request_id,
            "patient_id": patient_id,
            "medication_name": medication_name,
            "prescriber": prescriber,
            "pharmacy_name": pharmacy_name or "On file",
            "estimated_hours": 24,
            "status": "pending"
        }), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────
# BILLING
# ─────────────────────────────────────────

@app.route("/api/billing/<patient_id>/balance", methods=["GET"])
@require_api_key
def get_balance(patient_id):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM billing WHERE patient_id = %s", (patient_id,))
        row = cur.fetchone()
        conn.commit()
        if not row:
            return jsonify({"error": f"No billing record found for patient {patient_id}"}), 404
        return jsonify({
            "patient_id": patient_id,
            "outstanding": float(row["outstanding"]),
            "due_date": str(row["due_date"]) if row["due_date"] else None,
            "last_payment": float(row["last_payment"]),
            "last_payment_date": str(row["last_payment_date"]) if row["last_payment_date"] else None
        })
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/billing/<patient_id>/insurance_coverage", methods=["GET"])
@require_api_key
def get_insurance(patient_id):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM billing WHERE patient_id = %s", (patient_id,))
        row = cur.fetchone()
        conn.commit()
        if not row:
            return jsonify({"error": f"No billing record found for patient {patient_id}"}), 404
        return jsonify({
            "patient_id": patient_id,
            "insurer": row["insurer"],
            "plan_name": row["plan_name"],
            "policy_number": row["policy_number"],
            "deductible": float(row["deductible"]),
            "deductible_met": float(row["deductible_met"]),
            "copay": float(row["copay"]),
            "in_network": row["in_network"]
        })
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/billing/<patient_id>/payment_plan", methods=["GET"])
@require_api_key
def get_payment_plan(patient_id):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT outstanding FROM billing WHERE patient_id = %s", (patient_id,))
        row = cur.fetchone()
        conn.commit()
        if not row:
            return jsonify({"error": f"No billing record found for patient {patient_id}"}), 404
        outstanding = float(row["outstanding"])
        monthly = round(outstanding / 6, 2) if outstanding > 0 else 0
        return jsonify({
            "patient_id": patient_id,
            "total_outstanding": outstanding,
            "monthly_amount": monthly,
            "months": 6,
            "interest": "0%",
            "contact": "Billing Dept ext. 4200"
        })
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/billing/<patient_id>/invoice/<invoice_id>", methods=["GET"])
@require_api_key
def get_invoice(patient_id, invoice_id):
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT invoice_id, amount, invoice_date::text as date, due_date::text as due_date, services, status
            FROM invoices WHERE patient_id = %s AND invoice_id = %s
        """, (patient_id, invoice_id))
        row = cur.fetchone()
        conn.commit()
        if not row:
            return jsonify({"error": f"Invoice {invoice_id} not found for patient {patient_id}"}), 404
        return jsonify(dict(row))
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────
# HANDOFF
# ─────────────────────────────────────────

@app.route("/api/handoff", methods=["POST"])
@require_api_key
def create_handoff():
    data = request.get_json() or {}
    conn = get_db()
    cur = conn.cursor()
    try:
        ticket_id = data.get("ticket_id") or "TKT-" + str(uuid.uuid4())[:8].upper()
        cur.execute("""
            INSERT INTO handoff_tickets (ticket_id, patient_id, reason, priority, summary, department)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (ticket_id, data.get("patient_id"), data.get("reason"), data.get("priority", "normal"), data.get("summary"), data.get("department", "Reception")))
        conn.commit()
        return jsonify({"status": "created", "ticket_id": ticket_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────
# AUDIT LOG
# ─────────────────────────────────────────

@app.route("/api/audit-log", methods=["POST"])
@require_api_key
def write_audit_log():
    data = request.get_json() or {}
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO audit_logs (action, patient_id, data_accessed, channel, agent_version)
            VALUES (%s, %s, %s, %s, %s)
        """, (data.get("action"), data.get("patient_id"), data.get("data_accessed"), data.get("channel"), data.get("agent_version", "hospital-ai-v3")))
        conn.commit()
        return jsonify({"status": "logged"}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────
# ADMIN
# ─────────────────────────────────────────

@app.route("/api/admin/slots", methods=["POST"])
@require_api_key
def add_slots():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400
    slots = data if isinstance(data, list) else [data]
    conn = get_db()
    cur = conn.cursor()
    try:
        inserted = 0
        for slot in slots:
            cur.execute("INSERT INTO available_slots (doctor, department, slot_date, slot_time) VALUES (%s, %s, %s, %s)",
                        (slot["doctor"], slot["department"], slot["date"], slot["time"]))
            inserted += 1
        conn.commit()
        return jsonify({"message": f"{inserted} slot(s) added successfully"}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


@app.route("/api/admin/patients", methods=["GET"])
@require_api_key
def list_patients():
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT patient_id, name, dob, phone, email FROM patients ORDER BY name")
        rows = cur.fetchall()
        conn.commit()
        return jsonify({"patients": [dict(r) for r in rows], "total": len(rows)})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────
# STARTUP
# ─────────────────────────────────────────

with app.app_context():
    try:
        init_db()
    except Exception as e:
        print(f"DB init warning: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
