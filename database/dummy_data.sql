-- ============================================================
-- HOSPITAL AI — COMPLETE DUMMY DATA
-- Run this in pgAdmin Query Tool
-- ============================================================

-- ─────────────────────────────────────────
-- 1. PATIENTS (5 test patients)
-- ─────────────────────────────────────────
INSERT INTO patients (patient_id, name, dob, blood_type, allergies, conditions, phone, email, address, last_visit)
VALUES
  ('PT-001', 'Anjali Sharma',   '1985-06-15', 'B+',  ARRAY['Penicillin'],            ARRAY['Type 2 Diabetes', 'Hypertension'],    '+911234567890', 'anjali.sharma@email.com',   '12 MG Road, Pune',       '2026-02-10'),
  ('PT-002', 'Rahul Mehta',     '1992-11-23', 'O+',  ARRAY['Sulfa drugs'],           ARRAY['Asthma'],                             '+912345678901', 'rahul.mehta@email.com',     '45 FC Road, Pune',       '2026-01-20'),
  ('PT-003', 'Priya Nair',      '1978-03-08', 'A-',  ARRAY['Latex', 'Aspirin'],      ARRAY['Anxiety Disorder', 'Hypothyroidism'], '+913456789012', 'priya.nair@email.com',      '8 Koregaon Park, Pune',  '2026-03-01'),
  ('PT-004', 'Vikram Desai',    '1965-09-30', 'AB+', ARRAY[]::text[],                ARRAY['Coronary Artery Disease', 'GERD'],    '+914567890123', 'vikram.desai@email.com',    '23 Baner Road, Pune',    '2026-02-25'),
  ('PT-005', 'Meera Krishnan',  '2001-07-14', 'O-',  ARRAY['Ibuprofen'],             ARRAY['Migraine'],                           '+915678901234', 'meera.k@email.com',         '67 Viman Nagar, Pune',   '2026-03-05')
ON CONFLICT (patient_id) DO NOTHING;


-- ─────────────────────────────────────────
-- 2. MEDICATIONS
-- ─────────────────────────────────────────
INSERT INTO medications (patient_id, name, dosage, frequency, prescriber, start_date, active)
VALUES
  -- PT-001 Anjali — Diabetes + Hypertension
  ('PT-001', 'Metformin',     '500mg',  'Twice daily with meals',    'Dr. Patel',   '2024-01-15', TRUE),
  ('PT-001', 'Amlodipine',    '5mg',    'Once daily in the morning', 'Dr. Patel',   '2024-01-15', TRUE),
  ('PT-001', 'Atorvastatin',  '10mg',   'Once daily at night',       'Dr. Patel',   '2024-06-01', TRUE),

  -- PT-002 Rahul — Asthma
  ('PT-002', 'Salbutamol',    '100mcg', 'As needed (rescue inhaler)','Dr. Joshi',   '2023-08-10', TRUE),
  ('PT-002', 'Budesonide',    '200mcg', 'Twice daily (inhaler)',     'Dr. Joshi',   '2023-08-10', TRUE),

  -- PT-003 Priya — Anxiety + Thyroid
  ('PT-003', 'Escitalopram',  '10mg',   'Once daily in the morning', 'Dr. Kapoor',  '2025-03-20', TRUE),
  ('PT-003', 'Levothyroxine', '50mcg',  'Once daily on empty stomach','Dr. Kapoor', '2024-11-05', TRUE),
  ('PT-003', 'Clonazepam',    '0.5mg',  'As needed for anxiety',     'Dr. Kapoor',  '2025-03-20', TRUE),

  -- PT-004 Vikram — Heart + GERD
  ('PT-004', 'Aspirin',       '75mg',   'Once daily after breakfast', 'Dr. Sharma',  '2023-05-12', TRUE),
  ('PT-004', 'Clopidogrel',   '75mg',   'Once daily',                'Dr. Sharma',  '2023-05-12', TRUE),
  ('PT-004', 'Pantoprazole',  '40mg',   'Once daily before meals',   'Dr. Sharma',  '2023-05-12', TRUE),
  ('PT-004', 'Metoprolol',    '25mg',   'Twice daily',               'Dr. Sharma',  '2023-05-12', TRUE),

  -- PT-005 Meera — Migraine
  ('PT-005', 'Sumatriptan',   '50mg',   'As needed during migraine', 'Dr. Nair',    '2025-07-01', TRUE),
  ('PT-005', 'Propranolol',   '20mg',   'Once daily (preventive)',   'Dr. Nair',    '2025-07-01', TRUE)
ON CONFLICT DO NOTHING;


-- ─────────────────────────────────────────
-- 3. LAB RESULTS
-- ─────────────────────────────────────────
INSERT INTO lab_results (patient_id, test_name, value, unit, status, test_date, notes)
VALUES
  -- PT-001 Anjali
  ('PT-001', 'HbA1c',              '7.8',  '%',        'abnormal', '2026-02-10', 'Above target of 7.0 — review diet'),
  ('PT-001', 'Fasting Blood Sugar','148',  'mg/dL',    'abnormal', '2026-02-10', 'Slightly elevated'),
  ('PT-001', 'Blood Pressure',     '138/88','mmHg',    'abnormal', '2026-02-10', 'Mildly elevated — monitor'),
  ('PT-001', 'Total Cholesterol',  '195',  'mg/dL',    'normal',   '2026-02-10', NULL),
  ('PT-001', 'Creatinine',         '0.9',  'mg/dL',    'normal',   '2026-02-10', NULL),

  -- PT-002 Rahul
  ('PT-002', 'Peak Flow',          '380',  'L/min',    'abnormal', '2026-01-20', 'Below predicted value — asthma not fully controlled'),
  ('PT-002', 'SpO2',               '97',   '%',        'normal',   '2026-01-20', NULL),
  ('PT-002', 'Eosinophil Count',   '550',  'cells/uL', 'abnormal', '2026-01-20', 'Elevated — consistent with allergic asthma'),

  -- PT-003 Priya
  ('PT-003', 'TSH',                '6.2',  'mIU/L',    'abnormal', '2026-03-01', 'Hypothyroid — on Levothyroxine, recheck in 3 months'),
  ('PT-003', 'Free T4',            '0.85', 'ng/dL',    'abnormal', '2026-03-01', 'Low-normal'),
  ('PT-003', 'Complete Blood Count','Normal','',       'normal',   '2026-03-01', NULL),

  -- PT-004 Vikram
  ('PT-004', 'LDL Cholesterol',    '112',  'mg/dL',    'abnormal', '2026-02-25', 'Target < 70 for CAD patients'),
  ('PT-004', 'HDL Cholesterol',    '42',   'mg/dL',    'normal',   '2026-02-25', NULL),
  ('PT-004', 'Troponin I',         '0.01', 'ng/mL',    'normal',   '2026-02-25', 'Within normal range'),
  ('PT-004', 'ECG',                'Sinus rhythm','',  'normal',   '2026-02-25', 'No acute changes'),

  -- PT-005 Meera
  ('PT-005', 'MRI Brain',          'Normal','',        'normal',   '2026-03-05', 'No structural abnormality detected'),
  ('PT-005', 'Complete Blood Count','Normal','',       'normal',   '2026-03-05', NULL)
ON CONFLICT DO NOTHING;


-- ─────────────────────────────────────────
-- 4. AVAILABLE APPOINTMENT SLOTS
-- ─────────────────────────────────────────
INSERT INTO available_slots (doctor, department, slot_date, slot_time, available)
VALUES
  -- Cardiology — Dr. Sharma
  ('Dr. R. Sharma',       'Cardiology',        '2026-03-17', '09:00 AM', TRUE),
  ('Dr. R. Sharma',       'Cardiology',        '2026-03-17', '10:00 AM', TRUE),
  ('Dr. R. Sharma',       'Cardiology',        '2026-03-17', '11:00 AM', TRUE),
  ('Dr. R. Sharma',       'Cardiology',        '2026-03-18', '09:00 AM', TRUE),
  ('Dr. R. Sharma',       'Cardiology',        '2026-03-18', '02:00 PM', TRUE),
  ('Dr. R. Sharma',       'Cardiology',        '2026-03-20', '10:00 AM', TRUE),
  ('Dr. R. Sharma',       'Cardiology',        '2026-03-21', '11:00 AM', TRUE),

  -- General Practice — Dr. Patel
  ('Dr. S. Patel',        'General Practice',  '2026-03-17', '08:30 AM', TRUE),
  ('Dr. S. Patel',        'General Practice',  '2026-03-17', '09:30 AM', TRUE),
  ('Dr. S. Patel',        'General Practice',  '2026-03-17', '10:30 AM', TRUE),
  ('Dr. S. Patel',        'General Practice',  '2026-03-18', '08:30 AM', TRUE),
  ('Dr. S. Patel',        'General Practice',  '2026-03-19', '09:00 AM', TRUE),
  ('Dr. S. Patel',        'General Practice',  '2026-03-20', '08:30 AM', TRUE),
  ('Dr. S. Patel',        'General Practice',  '2026-03-21', '09:30 AM', TRUE),

  -- Pulmonology — Dr. Joshi
  ('Dr. A. Joshi',        'Pulmonology',       '2026-03-17', '11:00 AM', TRUE),
  ('Dr. A. Joshi',        'Pulmonology',       '2026-03-18', '11:00 AM', TRUE),
  ('Dr. A. Joshi',        'Pulmonology',       '2026-03-20', '02:00 PM', TRUE),
  ('Dr. A. Joshi',        'Pulmonology',       '2026-03-21', '03:00 PM', TRUE),

  -- Psychiatry / Mental Health — Dr. Kapoor
  ('Dr. P. Kapoor',       'Psychiatry',        '2026-03-17', '02:00 PM', TRUE),
  ('Dr. P. Kapoor',       'Psychiatry',        '2026-03-18', '03:00 PM', TRUE),
  ('Dr. P. Kapoor',       'Psychiatry',        '2026-03-19', '02:00 PM', TRUE),
  ('Dr. P. Kapoor',       'Psychiatry',        '2026-03-20', '03:00 PM', TRUE),

  -- Neurology — Dr. Nair
  ('Dr. K. Nair',         'Neurology',         '2026-03-17', '03:00 PM', TRUE),
  ('Dr. K. Nair',         'Neurology',         '2026-03-19', '03:00 PM', TRUE),
  ('Dr. K. Nair',         'Neurology',         '2026-03-20', '11:00 AM', TRUE),
  ('Dr. K. Nair',         'Neurology',         '2026-03-21', '02:00 PM', TRUE),

  -- Endocrinology — Dr. Mehta
  ('Dr. V. Mehta',        'Endocrinology',     '2026-03-18', '10:00 AM', TRUE),
  ('Dr. V. Mehta',        'Endocrinology',     '2026-03-19', '11:00 AM', TRUE),
  ('Dr. V. Mehta',        'Endocrinology',     '2026-03-21', '10:00 AM', TRUE),

  -- Pediatrics — Dr. Singh
  ('Dr. M. Singh',        'Pediatrics',        '2026-03-17', '09:00 AM', TRUE),
  ('Dr. M. Singh',        'Pediatrics',        '2026-03-18', '09:00 AM', TRUE),
  ('Dr. M. Singh',        'Pediatrics',        '2026-03-20', '09:00 AM', TRUE),

  -- Orthopedics — Dr. Rao
  ('Dr. G. Rao',          'Orthopedics',       '2026-03-17', '10:00 AM', TRUE),
  ('Dr. G. Rao',          'Orthopedics',       '2026-03-19', '10:00 AM', TRUE),
  ('Dr. G. Rao',          'Orthopedics',       '2026-03-21', '09:00 AM', TRUE)
ON CONFLICT DO NOTHING;


-- ─────────────────────────────────────────
-- 5. BILLING RECORDS
-- ─────────────────────────────────────────
INSERT INTO billing (patient_id, outstanding, due_date, last_payment, last_payment_date, insurer, plan_name, policy_number, deductible, deductible_met, copay, in_network)
VALUES
  ('PT-001', 2500.00,  '2026-04-01', 1500.00, '2026-02-15', 'Star Health Insurance',  'Family Floater Gold',    'SH-AJ-78432',  10000.00, 4500.00, 300.00, TRUE),
  ('PT-002', 800.00,   '2026-03-30', 2000.00, '2026-01-25', 'HDFC Ergo Health',       'Optima Secure',          'HDFC-RM-23451', 5000.00, 5000.00, 200.00, TRUE),
  ('PT-003', 0.00,     NULL,         3200.00, '2026-03-01', 'ICICI Lombard',           'Complete Health',        'ICL-PN-56123',  7500.00, 2000.00, 250.00, TRUE),
  ('PT-004', 12000.00, '2026-04-15', 5000.00, '2026-02-28', 'New India Assurance',     'Mediclaim Policy',       'NIA-VD-89012', 15000.00, 8000.00, 500.00, TRUE),
  ('PT-005', 450.00,   '2026-04-05', 450.00,  '2026-03-05', 'Bajaj Allianz Health',    'Health Guard',           'BA-MK-34567',   3000.00, 1200.00, 150.00, TRUE)
ON CONFLICT DO NOTHING;


-- ─────────────────────────────────────────
-- 6. INVOICES
-- ─────────────────────────────────────────
INSERT INTO invoices (invoice_id, patient_id, amount, invoice_date, due_date, services, status)
VALUES
  ('INV-001', 'PT-001', 1800.00, '2026-02-10', '2026-03-10', ARRAY['Consultation', 'HbA1c Test', 'Lipid Panel', 'Blood Pressure Monitoring'], 'unpaid'),
  ('INV-002', 'PT-001',  700.00, '2026-01-15', '2026-02-15', ARRAY['Consultation', 'Fasting Blood Sugar'], 'paid'),
  ('INV-003', 'PT-002',  800.00, '2026-01-20', '2026-02-20', ARRAY['Consultation', 'Pulmonary Function Test', 'Inhaler Prescription'], 'unpaid'),
  ('INV-004', 'PT-003',  950.00, '2026-03-01', '2026-04-01', ARRAY['Psychiatry Consultation', 'TSH Test', 'T4 Test', 'CBC'], 'paid'),
  ('INV-005', 'PT-004', 8500.00, '2026-02-25', '2026-03-25', ARRAY['Cardiology Consultation', 'ECG', 'Echocardiogram', 'Lipid Panel', 'Troponin Test'], 'unpaid'),
  ('INV-006', 'PT-004', 3500.00, '2026-01-10', '2026-02-10', ARRAY['Angioplasty Follow-up', 'Clopidogrel Prescription'], 'unpaid'),
  ('INV-007', 'PT-005',  450.00, '2026-03-05', '2026-04-05', ARRAY['Neurology Consultation', 'MRI Brain', 'Migraine Management Plan'], 'unpaid')
ON CONFLICT DO NOTHING;


-- ─────────────────────────────────────────
-- 7. IMAGING
-- ─────────────────────────────────────────
INSERT INTO imaging (patient_id, scan_type, body_part, result, scan_date, radiologist)
VALUES
  ('PT-004', 'Echocardiogram', 'Heart',    'Mild left ventricular hypertrophy. EF 55%. No significant valvular disease.',           '2026-02-25', 'Dr. R. Sharma'),
  ('PT-004', 'Chest X-Ray',    'Chest',    'Mild cardiomegaly. No acute pulmonary infiltrates.',                                    '2026-02-25', 'Dr. T. Iyer'),
  ('PT-002', 'Chest X-Ray',    'Chest',    'Mild hyperinflation consistent with asthma. No consolidation.',                        '2026-01-20', 'Dr. T. Iyer'),
  ('PT-005', 'MRI',            'Brain',    'No structural abnormality detected. No intracranial mass or haemorrhage.',              '2026-03-05', 'Dr. T. Iyer'),
  ('PT-003', 'Ultrasound',     'Thyroid',  'Mildly enlarged thyroid gland. No nodules identified. Consistent with hypothyroidism.', '2026-01-10', 'Dr. T. Iyer')
ON CONFLICT DO NOTHING;


-- ─────────────────────────────────────────
-- 8. DISCHARGE NOTES
-- ─────────────────────────────────────────
INSERT INTO discharge_notes (patient_id, notes, discharge_date, doctor)
VALUES
  ('PT-004', 'Patient admitted for chest pain evaluation. Ruled out NSTEMI. Discharged on optimised cardiac medications. Follow up in 4 weeks. Advised lifestyle changes: low sodium diet, 30 mins walking daily, no smoking.', '2026-01-15', 'Dr. R. Sharma'),
  ('PT-002', 'Patient admitted for acute asthma exacerbation. Responded well to nebulisation. Discharged with revised inhaler regimen. Advised to avoid known triggers and carry rescue inhaler at all times.', '2025-11-20', 'Dr. A. Joshi')
ON CONFLICT DO NOTHING;


-- ─────────────────────────────────────────
-- VERIFY — run this to confirm everything loaded
-- ─────────────────────────────────────────
SELECT 'patients'       AS table_name, COUNT(*) AS rows FROM patients
UNION ALL
SELECT 'medications',      COUNT(*) FROM medications
UNION ALL
SELECT 'lab_results',      COUNT(*) FROM lab_results
UNION ALL
SELECT 'available_slots',  COUNT(*) FROM available_slots
UNION ALL
SELECT 'billing',          COUNT(*) FROM billing
UNION ALL
SELECT 'invoices',         COUNT(*) FROM invoices
UNION ALL
SELECT 'imaging',          COUNT(*) FROM imaging
UNION ALL
SELECT 'discharge_notes',  COUNT(*) FROM discharge_notes;
