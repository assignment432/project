"""
utils/scheduler.py - APScheduler job to check deadlines and send email alerts
Runs every 30 minutes
"""
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timezone

scheduler = BackgroundScheduler()


def check_deadlines(app):
    """Check all assignments for upcoming deadlines and send reminders."""
    try:
        from firebase_config import get_db
        from utils.email_service import send_deadline_reminder
        db = get_db()
        now = datetime.now(timezone.utc)

        classrooms = db.collection('classrooms').stream()

        for classroom_doc in classrooms:
            classroom = classroom_doc.to_dict()
            classroom_id = classroom_doc.id
            classroom_name = classroom.get('name', 'Unknown Classroom')
            student_ids = classroom.get('student_ids', [])

            assignments = db.collection('classrooms').document(classroom_id)\
                            .collection('assignments').stream()

            for assign_doc in assignments:
                assignment = assign_doc.to_dict()
                assign_id = assign_doc.id
                title = assignment.get('title', 'Untitled')
                deadline = assignment.get('deadline')

                if not deadline:
                    continue

                if hasattr(deadline, 'astimezone'):
                    deadline_dt = deadline.astimezone(timezone.utc)
                elif hasattr(deadline, 'to_datetime'):
                    deadline_dt = deadline.to_datetime(timezone.utc)
                else:
                    continue

                time_left = deadline_dt - now
                hours_left = time_left.total_seconds() / 3600

                send_24h = 23.5 <= hours_left <= 24.0
                send_1h = 0.5 <= hours_left <= 1.0

                if not (send_24h or send_1h):
                    continue

                hours_key = '24h' if send_24h else '1h'
                alert_hours = 24 if send_24h else 1

                for student_id in student_ids:
                    submission_ref = db.collection('classrooms').document(classroom_id)\
                                       .collection('assignments').document(assign_id)\
                                       .collection('submissions').document(student_id)
                    if submission_ref.get().exists:
                        continue

                    alert_key = f"{assign_id}_{student_id}_{hours_key}"
                    alert_ref = db.collection('sent_alerts').document(alert_key)
                    if alert_ref.get().exists:
                        continue

                    student_doc = db.collection('users').document(student_id).get()
                    if not student_doc.exists:
                        continue

                    student = student_doc.to_dict()
                    student_email = student.get('email')
                    student_name = student.get('name', 'Student')

                    if not student_email:
                        continue

                    success = send_deadline_reminder(
                        app, student_email, student_name,
                        title, classroom_name, deadline_dt, alert_hours
                    )

                    if success:
                        alert_ref.set({
                            'sent_at': datetime.now(timezone.utc).isoformat(),
                            'type': hours_key,
                            'student_id': student_id,
                            'assignment_id': assign_id
                        })

    except Exception as e:
        print(f"[SCHEDULER ERROR] {e}")


def start_scheduler(app):
    """Start the background scheduler."""
    scheduler.add_job(
        func=lambda: check_deadlines(app),
        trigger='interval',
        minutes=30,
        id='deadline_checker',
        replace_existing=True,
        next_run_time=datetime.now()
    )
    scheduler.start()
    print("[SCHEDULER] Deadline checker started (runs every 30 minutes)")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
