from werkzeug.security import generate_password_hash
import os

# Generate hash for password 'admin'
password = "admin"
hashed = generate_password_hash(password)

# Read the current .env file
with open('.env', 'r') as f:
    lines = f.readlines()

# Update the password hash line
new_lines = []
for line in lines:
    if line.startswith('BASIC_AUTH_PASSWORD_HASH='):
        new_lines.append(f'BASIC_AUTH_PASSWORD_HASH={hashed}\n')
    else:
        new_lines.append(line)

# Write back to .env file
with open('.env', 'w') as f:
    f.writelines(new_lines)

print("Password hash has been updated successfully!")
print(f"Username: admin")
print(f"Password: admin") 