"""
app.py - Main Flask Application
Online Assignment System with Email Alerts
"""
import os
import hashlib
from datetime import datetime, timezone
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from dotenv import load_dotenv
from firebase_config import get_db, seed_admin
from firebase_admin import firestore
from utils.email_service import mail
from utils.scheduler import start_scheduler, stop_scheduler

load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'supersecretkey-change-in-production')

# Mail configuration
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME', 'assignments@system.com')

mail.init_app(app)


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def login_required(role=None):
    def decorator(f):
        from functools import wraps
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if role and session.get('role') != role:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ─── AUTH ROUTES ────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        role = session.get('role')
        return redirect(url_for(f'{role}_dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    data = request.json
    user_id = data.get('user_id', '').strip()
    password = data.get('password', '').strip()

    if not user_id or not password:
        return jsonify({'success': False, 'message': 'User ID and password are required'})

    db = get_db()
    user_doc = db.collection('users').document(user_id).get()

    if not user_doc.exists:
        return jsonify({'success': False, 'message': 'Invalid credentials'})

    user = user_doc.to_dict()
    if user.get('password') != hash_password(password):
        return jsonify({'success': False, 'message': 'Invalid credentials'})

    session['user_id'] = user_id
    session['role'] = user.get('role')
    session['name'] = user.get('name')
    session['email'] = user.get('email')

    return jsonify({'success': True, 'role': user.get('role'), 'redirect': f"/{user.get('role')}"})


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


# ─── ADMIN ROUTES ────────────────────────────────────────────────────────────

@app.route('/admin')
@login_required(role='admin')
def admin_dashboard():
    return render_template('admin.html', name=session.get('name'))


@app.route('/api/admin/users', methods=['GET'])
@login_required(role='admin')
def get_users():
    db = get_db()
    role_filter = request.args.get('role')
    query = db.collection('users')
    if role_filter:
        query = query.where('role', '==', role_filter)
    users = []
    for doc in query.stream():
        u = doc.to_dict()
        u['user_id'] = doc.id
        u.pop('password', None)
        users.append(u)
    return jsonify({'success': True, 'users': users})


@app.route('/api/admin/create_user', methods=['POST'])
@login_required(role='admin')
def create_user():
    db = get_db()
    data = request.json
    role = data.get('role')
    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    department = data.get('department', '').strip()
    user_id = data.get('user_id', '').strip()
    password = data.get('password', '').strip()

    if not all([role, name, email, user_id, password]):
        return jsonify({'success': False, 'message': 'All fields are required'})

    if role not in ['professor', 'student']:
        return jsonify({'success': False, 'message': 'Role must be professor or student'})

    existing = db.collection('users').document(user_id).get()
    if existing.exists:
        return jsonify({'success': False, 'message': 'User ID already exists'})

    db.collection('users').document(user_id).set({
        'user_id': user_id,
        'name': name,
        'email': email,
        'department': department,
        'role': role,
        'password': hash_password(password),
        'created_at': firestore.SERVER_TIMESTAMP
    })
    return jsonify({'success': True, 'message': f'{role.capitalize()} account created successfully'})


@app.route('/api/admin/delete_user/<user_id>', methods=['DELETE'])
@login_required(role='admin')
def delete_user(user_id):
    if user_id == 'admin':
        return jsonify({'success': False, 'message': 'Cannot delete admin'})
    db = get_db()
    db.collection('users').document(user_id).delete()
    return jsonify({'success': True, 'message': 'User deleted'})


@app.route('/api/admin/stats', methods=['GET'])
@login_required(role='admin')
def admin_stats():
    db = get_db()
    professors = len([d for d in db.collection('users').where('role', '==', 'professor').stream()])
    students = len([d for d in db.collection('users').where('role', '==', 'student').stream()])
    classrooms = len([d for d in db.collection('classrooms').stream()])
    return jsonify({'professors': professors, 'students': students, 'classrooms': classrooms})


# ─── PROFESSOR ROUTES ────────────────────────────────────────────────────────

@app.route('/professor')
@login_required(role='professor')
def professor_dashboard():
    return render_template('professor.html', name=session.get('name'))


@app.route('/api/professor/students', methods=['GET'])
@login_required(role='professor')
def get_all_students():
    db = get_db()
    students = []
    for doc in db.collection('users').where('role', '==', 'student').stream():
        s = doc.to_dict()
        s['user_id'] = doc.id
        s.pop('password', None)
        students.append(s)
    return jsonify({'success': True, 'students': students})


@app.route('/api/professor/classrooms', methods=['GET'])
@login_required(role='professor')
def get_professor_classrooms():
    db = get_db()
    prof_id = session['user_id']
    classrooms = []
    for doc in db.collection('classrooms').where('professor_id', '==', prof_id).stream():
        c = doc.to_dict()
        c['classroom_id'] = doc.id
        assigns = list(db.collection('classrooms').document(doc.id).collection('assignments').stream())
        c['assignment_count'] = len(assigns)
        classrooms.append(c)
    return jsonify({'success': True, 'classrooms': classrooms})


@app.route('/api/professor/create_classroom', methods=['POST'])
@login_required(role='professor')
def create_classroom():
    db = get_db()
    data = request.json
    name = data.get('name', '').strip()
    student_ids = data.get('student_ids', [])

    if not name:
        return jsonify({'success': False, 'message': 'Classroom name is required'})

    prof_id = session['user_id']
    doc_ref = db.collection('classrooms').add({
        'name': name,
        'professor_id': prof_id,
        'professor_name': session.get('name'),
        'student_ids': student_ids,
        'created_at': firestore.SERVER_TIMESTAMP
    })
    return jsonify({'success': True, 'message': 'Classroom created', 'classroom_id': doc_ref[1].id})


@app.route('/api/professor/classroom/<classroom_id>', methods=['GET'])
@login_required(role='professor')
def get_classroom(classroom_id):
    db = get_db()
    doc = db.collection('classrooms').document(classroom_id).get()
    if not doc.exists:
        return jsonify({'success': False, 'message': 'Classroom not found'})
    c = doc.to_dict()
    c['classroom_id'] = doc.id

    assignments = []
    for adoc in db.collection('classrooms').document(classroom_id).collection('assignments').stream():
        a = adoc.to_dict()
        a['assignment_id'] = adoc.id
        subs = list(db.collection('classrooms').document(classroom_id)
                      .collection('assignments').document(adoc.id)
                      .collection('submissions').stream())
        a['submission_count'] = len(subs)
        a['total_students'] = len(c.get('student_ids', []))
        if a.get('deadline') and hasattr(a['deadline'], 'isoformat'):
            a['deadline'] = a['deadline'].isoformat()
        assignments.append(a)

    c['assignments'] = assignments

    students = []
    for sid in c.get('student_ids', []):
        sdoc = db.collection('users').document(sid).get()
        if sdoc.exists:
            s = sdoc.to_dict()
            s['user_id'] = sid
            s.pop('password', None)
            students.append(s)
    c['students'] = students
    return jsonify({'success': True, 'classroom': c})


@app.route('/api/professor/create_assignment', methods=['POST'])
@login_required(role='professor')
def create_assignment():
    db = get_db()
    data = request.json
    classroom_id = data.get('classroom_id')
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    deadline_str = data.get('deadline', '')

    if not all([classroom_id, title, deadline_str]):
        return jsonify({'success': False, 'message': 'All fields required'})

    cdoc = db.collection('classrooms').document(classroom_id).get()
    if not cdoc.exists or cdoc.to_dict().get('professor_id') != session['user_id']:
        return jsonify({'success': False, 'message': 'Unauthorized'})

    try:
        deadline_dt = datetime.fromisoformat(deadline_str.replace('Z', '+00:00'))
    except:
        return jsonify({'success': False, 'message': 'Invalid deadline format'})

    db.collection('classrooms').document(classroom_id).collection('assignments').add({
        'title': title,
        'description': description,
        'deadline': deadline_dt,
        'classroom_id': classroom_id,
        'created_by': session['user_id'],
        'created_at': firestore.SERVER_TIMESTAMP
    })
    return jsonify({'success': True, 'message': 'Assignment created successfully'})


@app.route('/api/professor/submissions/<classroom_id>/<assignment_id>', methods=['GET'])
@login_required(role='professor')
def get_submissions(classroom_id, assignment_id):
    db = get_db()
    submissions = []
    for doc in db.collection('classrooms').document(classroom_id)\
                  .collection('assignments').document(assignment_id)\
                  .collection('submissions').stream():
        s = doc.to_dict()
        s['student_id'] = doc.id
        if s.get('submitted_at') and hasattr(s['submitted_at'], 'isoformat'):
            s['submitted_at'] = s['submitted_at'].isoformat()
        submissions.append(s)
    return jsonify({'success': True, 'submissions': submissions})


# ─── STUDENT ROUTES ────────────────────────────────────────────────────────────

@app.route('/student')
@login_required(role='student')
def student_dashboard():
    return render_template('student.html', name=session.get('name'))


@app.route('/api/student/classrooms', methods=['GET'])
@login_required(role='student')
def get_student_classrooms():
    db = get_db()
    student_id = session['user_id']
    classrooms = []

    for doc in db.collection('classrooms').where('student_ids', 'array_contains', student_id).stream():
        c = doc.to_dict()
        c['classroom_id'] = doc.id

        assignments = []
        for adoc in db.collection('classrooms').document(doc.id).collection('assignments').stream():
            a = adoc.to_dict()
            a['assignment_id'] = adoc.id

            sub = db.collection('classrooms').document(doc.id)\
                     .collection('assignments').document(adoc.id)\
                     .collection('submissions').document(student_id).get()
            a['submitted'] = sub.exists
            if sub.exists:
                sub_data = sub.to_dict()
                if sub_data.get('submitted_at') and hasattr(sub_data['submitted_at'], 'isoformat'):
                    a['submitted_at'] = sub_data['submitted_at'].isoformat()

            if a.get('deadline') and hasattr(a['deadline'], 'isoformat'):
                a['deadline'] = a['deadline'].isoformat()
            assignments.append(a)

        c['assignments'] = assignments
        c['pending_count'] = sum(1 for a in assignments if not a.get('submitted'))
        classrooms.append(c)

    return jsonify({'success': True, 'classrooms': classrooms})


@app.route('/api/student/submit', methods=['POST'])
@login_required(role='student')
def submit_assignment():
    db = get_db()
    data = request.json
    classroom_id = data.get('classroom_id')
    assignment_id = data.get('assignment_id')
    content = data.get('content', '').strip()

    if not all([classroom_id, assignment_id, content]):
        return jsonify({'success': False, 'message': 'All fields required'})

    student_id = session['user_id']

    adoc = db.collection('classrooms').document(classroom_id)\
              .collection('assignments').document(assignment_id).get()
    if not adoc.exists:
        return jsonify({'success': False, 'message': 'Assignment not found'})

    assignment = adoc.to_dict()
    deadline = assignment.get('deadline')
    if deadline:
        if hasattr(deadline, 'astimezone'):
            deadline_dt = deadline.astimezone(timezone.utc)
        else:
            deadline_dt = deadline
        if datetime.now(timezone.utc) > deadline_dt:
            return jsonify({'success': False, 'message': 'Deadline has passed. Submission not accepted.'})

    existing = db.collection('classrooms').document(classroom_id)\
                  .collection('assignments').document(assignment_id)\
                  .collection('submissions').document(student_id).get()
    if existing.exists:
        return jsonify({'success': False, 'message': 'You have already submitted this assignment'})

    db.collection('classrooms').document(classroom_id)\
      .collection('assignments').document(assignment_id)\
      .collection('submissions').document(student_id).set({
        'student_id': student_id,
        'student_name': session.get('name'),
        'content': content,
        'submitted_at': firestore.SERVER_TIMESTAMP
    })
    return jsonify({'success': True, 'message': 'Assignment submitted successfully! ✓'})


# ─── APP STARTUP ────────────────────────────────────────────────────────────

with app.app_context():
    try:
        seed_admin()
        start_scheduler(app)
    except Exception as e:
        print(f"[STARTUP WARNING] {e}")

import atexit
atexit.register(stop_scheduler)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
