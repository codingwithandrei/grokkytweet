import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev")
    SQLALCHEMY_DATABASE_URI = "sqlite:///tweets.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Firebase configuration
    FIREBASE_PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID', 'tweetdeez-33d7b')
    FIREBASE_PRIVATE_KEY_ID = os.getenv('FIREBASE_PRIVATE_KEY_ID')
    FIREBASE_PRIVATE_KEY = os.getenv('FIREBASE_PRIVATE_KEY')
    FIREBASE_CLIENT_EMAIL = os.getenv('FIREBASE_CLIENT_EMAIL')
    FIREBASE_CLIENT_ID = os.getenv('FIREBASE_CLIENT_ID')
    FIREBASE_CLIENT_CERT_URL = os.getenv('FIREBASE_CLIENT_CERT_URL')
    
    # Load all numbered users dynamically
    user_num = 1
    while True:
        username = os.getenv(f"BASIC_AUTH_USERNAME{user_num}")
        password_hash = os.getenv(f"BASIC_AUTH_PASSWORD_HASH{user_num}")
        
        if not username or not password_hash:
            break
            
        # Set the config values dynamically
        vars()[f"BASIC_AUTH_USERNAME{user_num}"] = username
        vars()[f"BASIC_AUTH_PASSWORD_HASH{user_num}"] = password_hash
        
        user_num += 1