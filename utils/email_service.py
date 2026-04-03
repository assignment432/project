"""
utils/email_service.py - Email alert system using Flask-Mail
Handles: deadline reminders, classroom invites, new assignments, submission notify
"""
from flask_mail import Mail, Message
from flask import current_app

mail = Mail()

# ── Shared HTML wrapper ────────────────────────────────────────────────────

def _wrap(header_color, icon, header_title, header_sub, body_html):
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8">
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; background:#f0f4f8; margin:0; padding:20px; }}
  .container {{ max-width:600px; margin:0 auto; background:#fff; border-radius:12px; overflow:hidden; box-shadow:0 4px 20px rgba(0,0,0,0.1); }}
  .header {{ background:{header_color}; padding:32px 40px; text-align:center; }}
  .header h1 {{ color:white; margin:0; font-size:26px; }}
  .header p  {{ color:rgba(255,255,255,0.9); margin:8px 0 0; font-size:15px; }}
  .body {{ padding:36px 40px; color:#334155; font-size:15px; line-height:1.7; }}
  .info-card {{ background:#f8fafc; border-left:4px solid {header_color}; border-radius:8px; padding:20px 24px; margin:20px 0; }}
  .info-card .lbl {{ font-size:11px; text-transform:uppercase; letter-spacing:1px; color:#64748b; margin-bottom:3px; }}
  .info-card .val {{ font-size:15px; font-weight:600; color:#1e293b; }}
  .btn-link {{ display:inline-block; margin-top:20px; background:{header_color}; color:white; padding:12px 28px; border-radius:8px; text-decoration:none; font-weight:600; }}
  .footer {{ background:#f8fafc; padding:20px 40px; text-align:center; border-top:1px solid #e2e8f0; color:#94a3b8; font-size:13px; }}
</style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>{icon} {header_title}</h1>
      <p>{header_sub}</p>
    </div>
    <div class="body">{body_html}</div>
    <div class="footer"><p>© 2025 Online Assignment System · Automated message, do not reply.</p></div>
  </div>
</body>
</html>"""


def _send(app, subject, recipient, html):
    with app.app_context():
        msg = Message(
            subject=subject,
            recipients=[recipient],
            html=html,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'assignments@system.com')
        )
        try:
            mail.send(msg)
            print(f"[EMAIL] Sent '{subject}' → {recipient}")
            return True
        except Exception as e:
            print(f"[EMAIL ERROR] Failed → {recipient}: {e}")
            return False


# ── 1. Deadline reminder ───────────────────────────────────────────────────

def send_deadline_reminder(app, student_email, student_name, assignment_title,
                           classroom_name, deadline, hours_left):
    if hours_left <= 1:
        color   = "#dc2626"
        icon    = "🚨"
        urgency = "URGENT — only 1 hour remaining!"
        subject = f"🚨 URGENT: 1 Hour Left - {assignment_title}"
    else:
        color   = "#d97706"
        icon    = "⏰"
        urgency = "24 hours remaining"
        subject = f"⏰ Reminder: 24 Hours Left - {assignment_title}"

    deadline_str = deadline.strftime('%d %B %Y, %I:%M %p') if hasattr(deadline, 'strftime') else str(deadline)

    body = f"""
<p>Hello, <strong>{student_name}</strong>!</p>
<p>This is an automated reminder — <strong style="color:{color}">{urgency}</strong></p>
<div class="info-card">
  <div class="lbl">Assignment</div><div class="val">{assignment_title}</div>
  <div class="lbl" style="margin-top:10px">Classroom</div><div class="val">{classroom_name}</div>
  <div class="lbl" style="margin-top:10px">Deadline</div><div class="val">⏰ {deadline_str}</div>
</div>
<p>Please log in and submit your work before the deadline.</p>
"""
    html = _wrap(color, icon, "Assignment Deadline Alert", "Online Assignment Management System", body)
    return _send(app, subject, student_email, html)


# ── 2. Classroom invite ────────────────────────────────────────────────────

def send_classroom_invite(app, student_email, student_name, classroom_name, professor_name):
    body = f"""
<p>Hello, <strong>{student_name}</strong>!</p>
<p>You have been added to a new classroom on the Assignment Management System.</p>
<div class="info-card">
  <div class="lbl">Classroom</div><div class="val">🏫 {classroom_name}</div>
  <div class="lbl" style="margin-top:10px">Professor</div><div class="val">🎓 {professor_name}</div>
</div>
<p>Log in to your student dashboard to view your classroom and upcoming assignments.</p>
"""
    html = _wrap("#6366f1", "🏫", "You've Been Added to a Classroom",
                 "Online Assignment Management System", body)
    return _send(app, f"🏫 New Classroom: {classroom_name}", student_email, html)


# ── 3. New assignment notification ────────────────────────────────────────

def send_new_assignment(app, student_email, student_name, assignment_title,
                        classroom_name, description, deadline_str, professor_name):
    desc_html = f'<div class="lbl" style="margin-top:10px">Description</div><div class="val">{description}</div>' if description else ''
    body = f"""
<p>Hello, <strong>{student_name}</strong>!</p>
<p>A new assignment has been posted in <strong>{classroom_name}</strong>.</p>
<div class="info-card">
  <div class="lbl">Assignment</div><div class="val">📄 {assignment_title}</div>
  <div class="lbl" style="margin-top:10px">Classroom</div><div class="val">🏫 {classroom_name}</div>
  <div class="lbl" style="margin-top:10px">Professor</div><div class="val">🎓 {professor_name}</div>
  {desc_html}
  <div class="lbl" style="margin-top:10px">Deadline</div><div class="val" style="color:#dc2626">⏰ {deadline_str}</div>
</div>
<p>Log in to your dashboard to view the full details and submit before the deadline.</p>
"""
    html = _wrap("#10b981", "📄", "New Assignment Posted",
                 "Online Assignment Management System", body)
    return _send(app, f"📄 New Assignment: {assignment_title}", student_email, html)


# ── 4. Submission notification to professor ───────────────────────────────

def send_submission_notify(app, professor_email, professor_name, student_name,
                           assignment_title, classroom_name, pdf_url):
    pdf_btn = f'<a class="btn-link" href="{pdf_url}" target="_blank">📎 View Submitted PDF</a>' if pdf_url else ''
    body = f"""
<p>Hello, <strong>{professor_name}</strong>!</p>
<p>A student has submitted their assignment for your review.</p>
<div class="info-card">
  <div class="lbl">Student</div><div class="val">👤 {student_name}</div>
  <div class="lbl" style="margin-top:10px">Assignment</div><div class="val">📄 {assignment_title}</div>
  <div class="lbl" style="margin-top:10px">Classroom</div><div class="val">🏫 {classroom_name}</div>
</div>
{pdf_btn}
<p style="margin-top:20px">You can also review and accept the submission from your professor dashboard.</p>
"""
    html = _wrap("#6366f1", "📬", "New Assignment Submission",
                 "Online Assignment Management System", body)
    return _send(app, f"📬 New Submission: {assignment_title} by {student_name}", professor_email, html)
