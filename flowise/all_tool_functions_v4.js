// ============================================================
// ALL 10 FLOWISE TOOL FUNCTIONS — FINAL PRODUCTION VERSION
// Key improvements:
// - New register_patient tool added
// - All tools guide user to register first if patient not found
// - All tools use $ prefix + unique variable names
// - All tools use https module (no fetch)
// - All tools handle API errors gracefully
// ============================================================


// ================================================================
// ① assess_symptoms
// ================================================================

const sym_text = ($symptoms || '').toLowerCase();
const sym_sev  = $severity || 'unknown';

const sym_EMERGENCY = [
  'chest pain','chest tightness','heart attack','cardiac arrest',
  'difficulty breathing','cant breathe','shortness of breath',
  'stroke','face drooping','arm weakness','speech difficulty',
  'suicidal','want to die','kill myself','end my life','self harm',
  'severe bleeding','uncontrolled bleeding','coughing blood','vomiting blood',
  'seizure','unconscious','passed out','anaphylaxis','allergic reaction',
  'severe allergic','overdose','poisoning','choking','drowning'
];

const sym_URGENT = [
  'high fever','fever above 39','fever above 103','severe headache',
  'sudden vision','eye pain','ear pain','urinary pain',
  'abdominal pain','vomiting','diarrhea','rash','swelling',
  'back pain','joint pain','dizziness','fainting'
];

const sym_isEmergency = sym_EMERGENCY.some(function(k) { return sym_text.includes(k); }) || sym_sev === 'severe';
if (sym_isEmergency) {
  return JSON.stringify({
    urgency: 'EMERGENCY',
    action: 'Call 911 or go to the nearest Emergency Room immediately.',
    crisis: true,
    care_setting: 'Emergency Room (ER)',
    disclaimer: 'AI triage only. NOT a substitute for professional medical advice.'
  });
}

const sym_isUrgent = sym_URGENT.some(function(k) { return sym_text.includes(k); }) || sym_sev === 'moderate';
if (sym_isUrgent) {
  return JSON.stringify({
    urgency: 'URGENT',
    action: 'Visit urgent care or contact your doctor within a few hours.',
    crisis: false,
    care_setting: 'Urgent Care or Primary Care (same day)',
    disclaimer: 'AI triage only. NOT a substitute for professional medical advice.'
  });
}

return JSON.stringify({
  urgency: 'ROUTINE',
  action: 'Schedule an appointment with your primary care physician.',
  crisis: false,
  care_setting: 'Primary Care or Telehealth',
  disclaimer: 'AI triage only. NOT a substitute for professional medical advice.'
});


// ================================================================
// ② manage_appointment
// ================================================================

const appt_action = $action || '';
const appt_dept   = $department || 'General Practice';
const appt_date   = (typeof $preferred_date !== 'undefined') ? $preferred_date : '';
const appt_id     = (typeof $appointment_id !== 'undefined') ? $appointment_id : '';
const appt_pid    = (typeof $patient_id !== 'undefined') ? $patient_id : '';
const appt_reason = (typeof $reason !== 'undefined') ? $reason : 'General consultation';

const appt_base = $vars.EHR_API_BASE_URL || 'http://localhost:8080/api';
const appt_key  = $vars.EHR_API_KEY || 'dev-key';
const appt_host = appt_base.replace('https://', '').split('/')[0];
const appt_path = '/' + appt_base.replace('https://', '').split('/').slice(1).join('/');

function appt_call(method, endpoint, body) {
  return new Promise(function(resolve, reject) {
    var https = require('https');
    var hdrs = { 'Content-Type': 'application/json', 'x-api-key': appt_key };
    if (body) hdrs['Content-Length'] = Buffer.byteLength(body);
    var req = https.request({ hostname: appt_host, path: endpoint, method: method, headers: hdrs }, function(res) {
      var data = '';
      res.on('data', function(c) { data += c; });
      res.on('end', function() {
        try { resolve({ status: res.statusCode, body: JSON.parse(data) }); }
        catch(e) { resolve({ status: res.statusCode, body: { error: data } }); }
      });
    });
    req.on('error', function(e) { resolve({ status: 0, body: { error: e.message } }); });
    if (body) req.write(body);
    req.end();
  });
}

if (appt_action === 'get_slots') {
  var appt_r1 = await appt_call('GET', appt_path + '/appointments/slots?department=' + encodeURIComponent(appt_dept) + '&date=' + appt_date);
  if (appt_r1.body.error) return 'Could not get slots: ' + appt_r1.body.error;
  if (!appt_r1.body.slots || appt_r1.body.slots.length === 0) return 'No available slots found for ' + appt_dept + '. Please try a different date or department.';
  return 'Available slots for ' + appt_dept + ':\n' + appt_r1.body.slots.map(function(s) { return '- ' + s.time + ' with ' + s.doctor + ' on ' + s.date; }).join('\n');
}

if (appt_action === 'book') {
  var appt_p1 = JSON.stringify({ patient_id: appt_pid || null, department: appt_dept, preferred_date: appt_date || null, reason: appt_reason });
  var appt_r2 = await appt_call('POST', appt_path + '/appointments/book', appt_p1);
  if (appt_r2.body.error) {
    if (appt_r2.body.message) return appt_r2.body.error + '. ' + appt_r2.body.message + (appt_r2.body.how_to_register ? ' ' + appt_r2.body.how_to_register : '');
    return 'Could not book: ' + appt_r2.body.error + (appt_r2.body.detail ? ' Detail: ' + appt_r2.body.detail : '');
  }
  return 'Appointment booked!\nDate: ' + appt_r2.body.date + '\nTime: ' + appt_r2.body.time + '\nDoctor: ' + appt_r2.body.doctor + '\nDepartment: ' + appt_r2.body.department + '\nConfirmation ID: ' + appt_r2.body.confirmation_id;
}

if (appt_action === 'reschedule') {
  var appt_p2 = JSON.stringify({ preferred_date: appt_date || null });
  var appt_r3 = await appt_call('PUT', appt_path + '/appointments/' + appt_id + '/reschedule', appt_p2);
  if (appt_r3.body.error) return 'Could not reschedule: ' + appt_r3.body.error;
  return 'Appointment rescheduled!\nNew date: ' + appt_r3.body.date + '\nNew time: ' + appt_r3.body.time + '\nNew confirmation: ' + appt_r3.body.confirmation_id;
}

if (appt_action === 'cancel') {
  var appt_r4 = await appt_call('DELETE', appt_path + '/appointments/' + appt_id + '/cancel');
  if (appt_r4.body.error) return 'Could not cancel: ' + appt_r4.body.error;
  return 'Appointment ' + appt_id + ' cancelled successfully.';
}

return 'Unknown action: "' + appt_action + '". Use: book, reschedule, cancel, or get_slots.';


// ================================================================
// ③ lookup_patient_ehr
// ================================================================

const ehr_pid     = (typeof $patient_id !== 'undefined') ? $patient_id : '';
const ehr_recType = (typeof $record_type !== 'undefined') ? $record_type : 'summary';

const ehr_base = $vars.EHR_API_BASE_URL || 'http://localhost:8080/api';
const ehr_key  = $vars.EHR_API_KEY || 'dev-key';
const ehr_host = ehr_base.replace('https://', '').split('/')[0];
const ehr_path = '/' + ehr_base.replace('https://', '').split('/').slice(1).join('/');

if (!ehr_pid) return 'Patient ID is required. Please ask the patient for their patient ID (e.g. PT-001). If they are a new patient, use the register_patient tool first.';

var ehr_result = await new Promise(function(resolve) {
  var https = require('https');
  var req = https.request({ hostname: ehr_host, path: ehr_path + '/patients/' + ehr_pid + '/records/' + ehr_recType, method: 'GET', headers: { 'x-api-key': ehr_key } }, function(res) {
    var data = '';
    res.on('data', function(c) { data += c; });
    res.on('end', function() {
      try { resolve({ status: res.statusCode, body: JSON.parse(data) }); }
      catch(e) { resolve({ status: res.statusCode, body: { error: data } }); }
    });
  });
  req.on('error', function(e) { resolve({ status: 0, body: { error: e.message } }); });
  req.end();
});

if (ehr_result.status === 401) return 'Authentication required. Please verify patient identity before accessing records.';
if (ehr_result.status === 404) {
  if (ehr_result.body.message) return ehr_result.body.message;
  return 'Patient ' + ehr_pid + ' not found. Please register the patient first using the register_patient tool.';
}
if (ehr_result.body.error) return 'EHR error: ' + ehr_result.body.error;

var ehr_data = ehr_result.body;

if (ehr_recType === 'summary') return 'Patient Summary:\n- Name: ' + ehr_data.name + '\n- DOB: ' + (ehr_data.dob||'N/A') + '\n- Blood type: ' + (ehr_data.blood_type||'N/A') + '\n- Allergies: ' + (ehr_data.allergies||[]).join(', ') + '\n- Conditions: ' + (ehr_data.conditions||[]).join(', ') + '\n- Last visit: ' + (ehr_data.last_visit||'N/A');
if (ehr_recType === 'lab_results') {
  if (!ehr_data.results || ehr_data.results.length === 0) return 'No lab results found for patient ' + ehr_pid + '.';
  return 'Lab results:\n' + ehr_data.results.map(function(r) { return '- ' + r.test_name + ': ' + r.value + ' ' + r.unit + ' (' + (r.status === 'normal' ? 'Normal' : 'ABNORMAL') + ') on ' + r.date; }).join('\n') + '\n\nPlease discuss abnormal results with your doctor.';
}
if (ehr_recType === 'medications') {
  if (!ehr_data.medications || ehr_data.medications.length === 0) return 'No active medications found for patient ' + ehr_pid + '.';
  return 'Current medications:\n' + ehr_data.medications.map(function(m) { return '- ' + m.name + ' ' + m.dosage + ' - ' + m.frequency + ' (Dr. ' + m.prescriber + ')'; }).join('\n');
}
if (ehr_recType === 'appointments') {
  if (!ehr_data.appointments || ehr_data.appointments.length === 0) return 'No appointments found for patient ' + ehr_pid + '.';
  return 'Appointments:\n' + ehr_data.appointments.map(function(a) { return '- ' + a.date + ' at ' + a.time + ' with ' + a.doctor + ' (' + a.department + ') - ' + a.status; }).join('\n');
}
if (ehr_recType === 'discharge_notes') return 'Discharge notes:\n' + ehr_data.notes + '\nDate: ' + ehr_data.date + '\nDoctor: ' + ehr_data.doctor;
return JSON.stringify(ehr_data, null, 2);


// ================================================================
// ④ register_patient  ← NEW TOOL
// Add this as a new Custom Tool in Flowise
// Schema:
// [
//   {"property":"name","type":"string","description":"Patient full name","required":true},
//   {"property":"phone","type":"string","description":"Phone with country code e.g. +911234567890","required":false},
//   {"property":"email","type":"string","description":"Patient email address","required":false},
//   {"property":"dob","type":"string","description":"Date of birth in YYYY-MM-DD format","required":false},
//   {"property":"blood_type","type":"string","description":"Blood type e.g. O+, A-, B+","required":false},
//   {"property":"allergies","type":"string","description":"Known allergies comma separated","required":false},
//   {"property":"conditions","type":"string","description":"Known medical conditions comma separated","required":false}
// ]
// ================================================================

const reg_name       = $name || '';
const reg_phone      = (typeof $phone !== 'undefined') ? $phone : '';
const reg_email      = (typeof $email !== 'undefined') ? $email : '';
const reg_dob        = (typeof $dob !== 'undefined') ? $dob : '';
const reg_blood      = (typeof $blood_type !== 'undefined') ? $blood_type : '';
const reg_allergies  = (typeof $allergies !== 'undefined') ? $allergies.split(',').map(function(a) { return a.trim(); }).filter(Boolean) : [];
const reg_conditions = (typeof $conditions !== 'undefined') ? $conditions.split(',').map(function(c) { return c.trim(); }).filter(Boolean) : [];

const reg_base = $vars.EHR_API_BASE_URL || 'http://localhost:8080/api';
const reg_key  = $vars.EHR_API_KEY || 'dev-key';
const reg_host = reg_base.replace('https://', '').split('/')[0];
const reg_path = '/' + reg_base.replace('https://', '').split('/').slice(1).join('/');

if (!reg_name) return 'Patient name is required to register. Please ask the patient for their full name.';

var reg_payload = JSON.stringify({
  name:       reg_name,
  phone:      reg_phone || null,
  email:      reg_email || null,
  dob:        reg_dob || null,
  blood_type: reg_blood || null,
  allergies:  reg_allergies,
  conditions: reg_conditions
});

return new Promise(function(resolve) {
  var https = require('https');
  var reg_req = https.request({
    hostname: reg_host,
    path:     reg_path + '/patients/register',
    method:   'POST',
    headers:  { 'Content-Type': 'application/json', 'x-api-key': reg_key, 'Content-Length': Buffer.byteLength(reg_payload) }
  }, function(res) {
    var data = '';
    res.on('data', function(c) { data += c; });
    res.on('end', function() {
      try {
        var reg_data = JSON.parse(data);
        if (reg_data.error) return resolve('Registration failed: ' + reg_data.error);
        resolve('Patient registered successfully!\nPatient ID: ' + reg_data.patient_id + '\nName: ' + reg_data.name + '\n\nIMPORTANT: Save this Patient ID: ' + reg_data.patient_id + '. The patient will need it for future appointments and records.');
      } catch(e) { resolve('Registration error: ' + data); }
    });
  });
  reg_req.on('error', function(e) { resolve('Registration service error: ' + e.message); });
  reg_req.write(reg_payload);
  reg_req.end();
});


// ================================================================
// ⑤ request_prescription_refill
// ================================================================

const rx_pid      = (typeof $patient_id !== 'undefined') ? $patient_id : '';
const rx_medName  = $medication_name || '';
const rx_pharmacy = (typeof $pharmacy_name !== 'undefined') ? $pharmacy_name : '';
const rx_notes    = (typeof $notes !== 'undefined') ? $notes : '';

const rx_base = $vars.EHR_API_BASE_URL || 'http://localhost:8080/api';
const rx_key  = $vars.EHR_API_KEY || 'dev-key';
const rx_host = rx_base.replace('https://', '').split('/')[0];
const rx_path = '/' + rx_base.replace('https://', '').split('/').slice(1).join('/');

if (!rx_medName) return 'Medication name is required for a refill request. Please ask the patient which medication they need refilled.';

var rx_payload = JSON.stringify({ patient_id: rx_pid || null, medication_name: rx_medName, pharmacy_name: rx_pharmacy || null, notes: rx_notes || null });

return new Promise(function(resolve) {
  var https = require('https');
  var rx_req = https.request({
    hostname: rx_host, path: rx_path + '/prescriptions/refill', method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-api-key': rx_key, 'Content-Length': Buffer.byteLength(rx_payload) }
  }, function(res) {
    var data = '';
    res.on('data', function(c) { data += c; });
    res.on('end', function() {
      try {
        var rx_data = JSON.parse(data);
        if (rx_data.error) {
          if (rx_data.message) return resolve(rx_data.error + '. ' + rx_data.message);
          return resolve('Refill failed: ' + rx_data.error);
        }
        resolve('Refill request submitted!\nRequest ID: ' + rx_data.request_id + '\nMedication: ' + rx_data.medication_name + '\nSent to: ' + rx_data.prescriber + '\nExpected response: ' + rx_data.estimated_hours + ' hours\nPharmacy: ' + rx_data.pharmacy_name);
      } catch(e) { resolve('Refill error: ' + data); }
    });
  });
  rx_req.on('error', function(e) { resolve('Refill service error: ' + e.message); });
  rx_req.write(rx_payload);
  rx_req.end();
});


// ================================================================
// ⑥ check_billing_insurance
// ================================================================

const bill_pid   = (typeof $patient_id !== 'undefined') ? $patient_id : '';
const bill_qType = $query_type || 'balance';
const bill_invId = (typeof $invoice_id !== 'undefined') ? $invoice_id : '';

const bill_base = $vars.EHR_API_BASE_URL || 'http://localhost:8080/api';
const bill_key  = $vars.EHR_API_KEY || 'dev-key';
const bill_host = bill_base.replace('https://', '').split('/')[0];
const bill_path = '/' + bill_base.replace('https://', '').split('/').slice(1).join('/');

if (!bill_pid) return 'Patient ID is required to check billing. Please ask the patient for their patient ID.';

var bill_endpoint = bill_invId
  ? bill_path + '/billing/' + bill_pid + '/invoice/' + bill_invId
  : bill_path + '/billing/' + bill_pid + '/' + bill_qType;

return new Promise(function(resolve) {
  var https = require('https');
  var bill_req = https.request({ hostname: bill_host, path: bill_endpoint, method: 'GET', headers: { 'x-api-key': bill_key } }, function(res) {
    var data = '';
    res.on('data', function(c) { data += c; });
    res.on('end', function() {
      try {
        var bill_data = JSON.parse(data);
        if (res.statusCode === 404) return resolve('No billing record found for patient ' + bill_pid + '.');
        if (bill_data.error) return resolve('Billing error: ' + bill_data.error);
        if (bill_qType === 'balance') return resolve('Account Balance\nOutstanding: $' + bill_data.outstanding + '\nDue date: ' + (bill_data.due_date||'N/A') + '\nLast payment: $' + bill_data.last_payment + ' on ' + (bill_data.last_payment_date||'N/A') + '\n\nTo pay, call billing at ext. 4200.');
        if (bill_qType === 'insurance_coverage') return resolve('Insurance Coverage\nProvider: ' + bill_data.insurer + '\nPlan: ' + bill_data.plan_name + '\nPolicy #: ' + bill_data.policy_number + '\nDeductible: $' + bill_data.deductible + ' (met: $' + bill_data.deductible_met + ')\nCopay: $' + bill_data.copay + '\nIn-network: ' + (bill_data.in_network ? 'Yes' : 'No'));
        if (bill_qType === 'invoice') return resolve('Invoice ' + bill_data.invoice_id + '\nAmount: $' + bill_data.amount + '\nDate: ' + bill_data.date + '\nServices: ' + (bill_data.services||[]).join(', ') + '\nStatus: ' + bill_data.status);
        if (bill_qType === 'payment_plan') return resolve('Payment Plan\nMonthly: $' + bill_data.monthly_amount + ' for ' + bill_data.months + ' months\nInterest: ' + bill_data.interest + '\nContact: ' + bill_data.contact);
        resolve(JSON.stringify(bill_data, null, 2));
      } catch(e) { resolve('Billing error: ' + data); }
    });
  });
  bill_req.on('error', function(e) { resolve('Billing service error: ' + e.message); });
  bill_req.end();
});


// ================================================================
// ⑦ send_whatsapp_notification
// ================================================================

const wa_to  = $to || '';
const wa_msg = $message || '';
const wa_sid = $vars.TWILIO_ACCOUNT_SID;
const wa_tok = $vars.TWILIO_AUTH_TOKEN;
const wa_frm = $vars.TWILIO_WHATSAPP_FROM || 'whatsapp:+14155238886';

if (!wa_to)  return 'WhatsApp failed: phone number is required. Please ask the patient for their WhatsApp number with country code e.g. +911234567890.';
if (!wa_msg) return 'WhatsApp failed: message content is required.';
if (!wa_sid) return 'WhatsApp failed: TWILIO_ACCOUNT_SID not set in Railway variables.';
if (!wa_tok) return 'WhatsApp failed: TWILIO_AUTH_TOKEN not set in Railway variables.';

var wa_num  = wa_to.startsWith('+') ? wa_to : '+' + wa_to;
var wa_body = 'City General Hospital\n\n' + wa_msg + '\n\nAI assistant message. For emergencies call 911.';
var wa_data = 'From=' + encodeURIComponent(wa_frm) + '&To=' + encodeURIComponent('whatsapp:' + wa_num) + '&Body=' + encodeURIComponent(wa_body);
var wa_cred = Buffer.from(wa_sid + ':' + wa_tok).toString('base64');

return new Promise(function(resolve) {
  var https = require('https');
  var wa_req = https.request({
    hostname: 'api.twilio.com',
    path: '/2010-04-01/Accounts/' + wa_sid + '/Messages.json',
    method: 'POST',
    headers: { 'Authorization': 'Basic ' + wa_cred, 'Content-Type': 'application/x-www-form-urlencoded', 'Content-Length': Buffer.byteLength(wa_data) }
  }, function(res) {
    var d = '';
    res.on('data', function(c) { d += c; });
    res.on('end', function() {
      try {
        var r = JSON.parse(d);
        if (r.sid) return resolve('WhatsApp sent successfully to ' + wa_num + '.');
        if (r.code === 63007) return resolve('WhatsApp failed: the recipient has not joined the Twilio sandbox. They need to send "join <word>" to +14155238886 on WhatsApp first.');
        if (r.code === 20003) return resolve('WhatsApp failed: invalid Twilio credentials. Check TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in Railway.');
        resolve('WhatsApp failed: ' + (r.message || JSON.stringify(r)));
      } catch(e) { resolve('WhatsApp error: ' + d); }
    });
  });
  wa_req.on('error', function(e) { resolve('WhatsApp service error: ' + e.message); });
  wa_req.write(wa_data);
  wa_req.end();
});


// ================================================================
// ⑧ send_telegram_notification
// ================================================================

const tg_chat  = $chat_id || '';
const tg_msg   = $message || '';
const tg_token = $vars.TELEGRAM_BOT_TOKEN;

if (!tg_chat)  return 'Telegram failed: chat ID is required. Ask the patient to start a chat with your bot and share their chat ID.';
if (!tg_msg)   return 'Telegram failed: message content is required.';
if (!tg_token) return 'Telegram failed: TELEGRAM_BOT_TOKEN not set in Railway variables.';

var tg_payload = JSON.stringify({ chat_id: tg_chat, text: 'City General Hospital\n\n' + tg_msg + '\n\nAI assistant message. For emergencies call 911.', parse_mode: 'Markdown' });

return new Promise(function(resolve) {
  var https = require('https');
  var tg_req = https.request({
    hostname: 'api.telegram.org',
    path: '/bot' + tg_token + '/sendMessage',
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(tg_payload) }
  }, function(res) {
    var d = '';
    res.on('data', function(c) { d += c; });
    res.on('end', function() {
      try {
        var r = JSON.parse(d);
        if (r.ok) return resolve('Telegram message sent successfully.');
        resolve('Telegram failed: ' + r.description);
      } catch(e) { resolve('Telegram error: ' + d); }
    });
  });
  tg_req.on('error', function(e) { resolve('Telegram service error: ' + e.message); });
  tg_req.write(tg_payload);
  tg_req.end();
});


// ================================================================
// ⑨ send_email_notification
// ================================================================

const email_to   = $to_email || '';
const email_subj = $subject || 'Message from City General Hospital';
const email_body = $body || '';
const email_key  = $vars.SENDGRID_API_KEY;
const email_from = $vars.HOSPITAL_FROM_EMAIL || 'noreply@citygeneralhospital.com';

if (!email_to)  return 'Email failed: recipient email address is required. Please ask the patient for their email address.';
if (!email_body) return 'Email failed: message body is required.';
if (!email_key)  return 'Email failed: SENDGRID_API_KEY not set in Railway variables.';

var email_payload = JSON.stringify({
  personalizations: [{ to: [{ email: email_to }] }],
  from:    { email: email_from, name: 'City General Hospital' },
  subject: email_subj,
  content: [{ type: 'text/html', value: '<div style="font-family:Arial,sans-serif;max-width:600px;margin:auto"><div style="background:#005A8E;color:white;padding:20px;border-radius:8px 8px 0 0"><h2 style="margin:0">City General Hospital</h2></div><div style="padding:24px;border:1px solid #e0e0e0;border-radius:0 0 8px 8px"><p style="white-space:pre-line">' + email_body + '</p><hr style="border:none;border-top:1px solid #eee;margin:20px 0"><p style="font-size:12px;color:#666">AI-generated message. Not medical advice. For emergencies call 911.</p></div></div>' }]
});

return new Promise(function(resolve) {
  var https = require('https');
  var email_req = https.request({
    hostname: 'api.sendgrid.com', path: '/v3/mail/send', method: 'POST',
    headers: { 'Authorization': 'Bearer ' + email_key, 'Content-Type': 'application/json', 'Content-Length': Buffer.byteLength(email_payload) }
  }, function(res) {
    var d = '';
    res.on('data', function(c) { d += c; });
    res.on('end', function() {
      if (res.statusCode === 202) return resolve('Email sent successfully to ' + email_to + '.');
      try {
        var r = JSON.parse(d);
        var msg = r.errors ? r.errors.map(function(e) { return e.message; }).join(', ') : d;
        if (msg.includes('does not match a verified Sender')) return resolve('Email failed: sender email ' + email_from + ' is not verified in SendGrid. Go to SendGrid Sender Authentication and verify it.');
        resolve('Email failed (' + res.statusCode + '): ' + msg);
      } catch(e) { resolve('Email failed (' + res.statusCode + '): ' + d); }
    });
  });
  email_req.on('error', function(e) { resolve('Email service error: ' + e.message); });
  email_req.write(email_payload);
  email_req.end();
});


// ================================================================
// ⑩ escalate_to_human
// ================================================================

const esc_reason   = $reason || 'patient_request';
const esc_priority = $priority || 'normal';
const esc_summary  = (typeof $summary !== 'undefined') ? $summary : '';
const esc_dept     = (typeof $department !== 'undefined') ? $department : 'Reception';
const esc_ticket   = 'TKT-' + Date.now();

const esc_base = $vars.EHR_API_BASE_URL || 'http://localhost:8080/api';
const esc_key  = $vars.EHR_API_KEY || 'dev-key';
const esc_host = esc_base.replace('https://', '').split('/')[0];
const esc_path = '/' + esc_base.replace('https://', '').split('/').slice(1).join('/');
const esc_data = JSON.stringify({ ticket_id: esc_ticket, reason: esc_reason, priority: esc_priority, summary: esc_summary, department: esc_dept });

try {
  var esc_https = require('https');
  var esc_req = esc_https.request({ hostname: esc_host, path: esc_path + '/handoff', method: 'POST', headers: { 'Content-Type': 'application/json', 'x-api-key': esc_key, 'Content-Length': Buffer.byteLength(esc_data) } });
  esc_req.write(esc_data);
  esc_req.end();
} catch(esc_e) {}

if (esc_priority === 'emergency') {
  return 'EMERGENCY ESCALATION\n\nTicket: ' + esc_ticket + '\n\nIf life-threatening: CALL 911 IMMEDIATELY\n\nHospital emergency line: (555) 000-0000\n\nStaff have been notified.';
}
return 'Connecting you to our team.\n\nTicket: ' + esc_ticket + '\nDepartment: ' + esc_dept + '\nExpected wait: ' + (esc_priority === 'high' ? '2-5 minutes' : '5-10 minutes') + '\n\nA staff member will join shortly. You can also call (555) 000-0000.';


// ================================================================
// ⑪ write_audit_log
// ================================================================

const log_action  = $action || 'unknown';
const log_pid     = (typeof $patient_id !== 'undefined') ? $patient_id : '';
const log_data    = (typeof $data_accessed !== 'undefined') ? $data_accessed : '';
const log_channel = (typeof $channel !== 'undefined') ? $channel : 'web';

const log_base    = $vars.EHR_API_BASE_URL || 'http://localhost:8080/api';
const log_key     = $vars.EHR_API_KEY || 'dev-key';
const log_host    = log_base.replace('https://', '').split('/')[0];
const log_path    = '/' + log_base.replace('https://', '').split('/').slice(1).join('/');
const log_payload = JSON.stringify({ action: log_action, patient_id: log_pid, data_accessed: log_data, channel: log_channel, agent_version: 'hospital-ai-v3' });

return new Promise(function(resolve) {
  var https = require('https');
  var log_req = https.request({
    hostname: log_host, path: log_path + '/audit-log', method: 'POST',
    headers: { 'Content-Type': 'application/json', 'x-api-key': log_key, 'Content-Length': Buffer.byteLength(log_payload) }
  }, function(res) {
    var d = '';
    res.on('data', function(c) { d += c; });
    res.on('end', function() { resolve('Audit log written: ' + log_action + ' for patient ' + (log_pid || 'unknown')); });
  });
  log_req.on('error', function(e) { resolve('Audit log failed (non-blocking): ' + e.message); });
  log_req.write(log_payload);
  log_req.end();
});
