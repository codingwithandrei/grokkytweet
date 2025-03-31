# Tweet Management System

A Flask application for managing and categorizing tweets, using Firebase for data storage.

## Features
- Organize tweets into categories
- Download and store tweet media
- HTTP Basic Authentication
- Firebase Firestore integration

## Setup

1. Clone the repository
```bash
git clone <your-repo-url>
cd whatsapp-links
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Set up Firebase
- Create a Firebase project
- Get your service account key from Firebase Console (Project Settings > Service Accounts)
- Save the credentials in `.env` file:
```env
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PRIVATE_KEY_ID=your-private-key-id
FIREBASE_PRIVATE_KEY=your-private-key
FIREBASE_CLIENT_EMAIL=your-client-email
FIREBASE_CLIENT_ID=your-client-id
FIREBASE_CLIENT_CERT_URL=your-client-cert-url
BASIC_AUTH_USERNAME=your-username
BASIC_AUTH_PASSWORD_HASH=your-password-hash
```

## Deployment on Vercel

1. Push your code to GitHub
2. Connect your GitHub repository to Vercel
3. Add all environment variables in Vercel project settings
4. Deploy!

## Development

Run the application locally:
```bash
python app.py
```

The server will start at `http://localhost:5000`

## Environment Variables

Required environment variables:
- `FIREBASE_PROJECT_ID`: Your Firebase project ID
- `FIREBASE_PRIVATE_KEY_ID`: Private key ID from service account
- `FIREBASE_PRIVATE_KEY`: Private key from service account
- `FIREBASE_CLIENT_EMAIL`: Client email from service account
- `FIREBASE_CLIENT_ID`: Client ID from service account
- `FIREBASE_CLIENT_CERT_URL`: Client cert URL from service account
- `BASIC_AUTH_USERNAME`: Username for HTTP Basic Auth
- `BASIC_AUTH_PASSWORD_HASH`: Password hash for HTTP Basic Auth
