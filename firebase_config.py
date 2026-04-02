"""
firebase_config.py - Firebase Admin SDK initialization
All credentials read from environment variables (Railway)
"""
import firebase_admin
from firebase_admin import credentials, firestore
import os
import hashlib

_db = None


def get_db():
    global _db
    if _db is None:
        if not firebase_admin._apps:
            sa_info = {
                "type": "service_account",
                "project_id": os.environ.get("FIREBASE_PROJECT_ID", ""),
                "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID", ""),
                "private_key": os.environ.get("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n"),
                "client_email": os.environ.get("FIREBASE_CLIENT_EMAIL", ""),
                "client_id": os.environ.get("FIREBASE_CLIENT_ID", ""),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "client_x509_cert_url": os.environ.get("FIREBASE_CLIENT_CERT_URL", ""),
                "universe_domain": "googleapis.com"
            }
            cred = credentials.Certificate(sa_info)
            firebase_admin.initialize_app(cred)
        _db = firestore.client()
    return _db


def seed_admin():
    """Pre-create the one admin account if it doesn't exist."""
    db = get_db()
    admin_id = os.environ.get('ADMIN_USER_ID', 'admin123')
    admin_ref = db.collection('users').document(admin_id)
    doc = admin_ref.get()
    if not doc.exists:
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@assignment.com')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin321')
        hashed = hashlib.sha256(admin_password.encode()).hexdigest()
        admin_ref.set({
            'user_id': admin_id,
            'name': 'Administrator',
            'email': admin_email,
            'password': hashed,
            'role': 'admin',
            'department': 'Administration',
            'created_at': firestore.SERVER_TIMESTAMP
        })
        print(f"[SEED] Admin account created: {admin_id}")
    else:
        print("[SEED] Admin already exists.")
