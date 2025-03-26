import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "default_secret")
    SQLALCHEMY_DATABASE_URI = "sqlite:///tweets.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
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