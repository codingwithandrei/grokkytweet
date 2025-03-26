from werkzeug.security import generate_password_hash

password = "admin"
hashed = generate_password_hash(password)
print(f"Password hash for '{password}': {hashed}") 