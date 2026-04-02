"""
utils/email_service.py - Email alert system using Flask-Mail
"""
from flask_mail import Mail, Message
from flask import current_app

mail = Mail()


def send_deadline_reminder(app, student_email, student_name, assignment_title,
                           classroom_name, deadline, hours_left):
    """Send a deadline reminder email to a student."""
    with app.app_context():
        if hours_left <= 1:
            subject = f"🚨 URGENT: 1 Hour Left - {assignment_title}"
            urgency = "URGENT — only 1 hour remaining!"
            color = "#dc2626"
            icon = "🚨"
        else:
            subject = f"⏰ Reminder: 24 Hours Left - {assignment_title}"
            urgency = "24 hours remaining"
            color = "#d97706"
            icon = "⏰"

        deadline_str = deadline.strftime('%d %B %Y, %I:%M %p') if hasattr(deadline, 'strftime') else str(deadline)

        html_body = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #f0f4f8; margin: 0; padding: 20px; }}
    .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
    .header {{ background: {color}; padding: 32px 40px; text-align: center; }}
    .header h1 {{ color: white; margin: 0; font-size: 28px; }}
    .header p {{ color: rgba(255,255,255,0.9); margin: 8px 0 0; font-size: 16px; }}
    .body {{ padding: 36px 40px; }}
    .info-card {{ background: #f8fafc; border-left: 4px solid {color}; border-radius: 8px; padding: 20px 24px; margin: 24px 0; }}
    .info-card .label {{ font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #64748b; margin-bottom: 4px; }}
    .info-card .value {{ font-size: 16px; font-weight: 600; color: #1e293b; }}
    .deadline-banner {{ background: {color}15; border: 2px solid {color}; border-radius: 8px; padding: 16px 24px; text-align: center; margin: 24px 0; }}
    .deadline-banner .time {{ font-size: 24px; font-weight: 700; color: {color}; }}
    .footer {{ background: #f8fafc; padding: 20px 40px; text-align: center; border-top: 1px solid #e2e8f0; color: #94a3b8; font-size: 13px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>{icon} Assignment Deadline Alert</h1>
      <p>Online Assignment Management System</p>
    </div>
    <div class="body">
      <p style="font-size:18px;color:#1e293b;">Hello, <strong>{student_name}</strong>!</p>
      <p style="color:#475569;font-size:15px;">This is an automated reminder. <strong style="color:{color};">{urgency}</strong></p>
      <div class="info-card">
        <div class="label">Assignment</div>
        <div class="value">{assignment_title}</div>
        <div class="label" style="margin-top:12px;">Classroom</div>
        <div class="value">{classroom_name}</div>
      </div>
      <div class="deadline-banner">
        <div class="label">Submission Deadline</div>
        <div class="time">⏰ {deadline_str}</div>
      </div>
      <p style="color:#475569;font-size:14px;">Please log in and submit your work before the deadline.</p>
    </div>
    <div class="footer">
      <p>© 2025 Online Assignment System · Automated message, do not reply.</p>
    </div>
  </div>
</body>
</html>
"""
        msg = Message(
            subject=subject,
            recipients=[student_email],
            html=html_body,
            sender=current_app.config.get('MAIL_DEFAULT_SENDER', 'assignments@system.com')
        )
        try:
            mail.send(msg)
            print(f"[EMAIL] Sent {hours_left}h reminder to {student_email} for '{assignment_title}'")
            return True
        except Exception as e:
            print(f"[EMAIL ERROR] Failed to send to {student_email}: {e}")
            return False
