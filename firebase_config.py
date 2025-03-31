import firebase_admin
from firebase_admin import credentials, firestore
import os

def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    project_id = os.getenv("FIREBASE_PROJECT_ID")
    if not project_id:
        raise ValueError("FIREBASE_PROJECT_ID environment variable is not set")

    private_key = os.getenv("FIREBASE_PRIVATE_KEY")
    if not private_key:
        raise ValueError("FIREBASE_PRIVATE_KEY environment variable is not set")
        
    # Handle escaped newlines in the private key
    private_key = private_key.replace("\\n", "\n") if private_key else None
    
    cred = credentials.Certificate({
        "type": "service_account",
        "project_id": project_id,
        "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
        "private_key": private_key,
        "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
        "client_id": os.getenv("FIREBASE_CLIENT_ID"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL")
    })
    
    if not firebase_admin._apps:
        # Initialize with explicit project ID
        firebase_admin.initialize_app(cred, {
            'projectId': project_id
        })
    
    return firestore.client()
