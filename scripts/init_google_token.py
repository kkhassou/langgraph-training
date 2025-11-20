#!/usr/bin/env python3
"""
Google Services Token Initialization Script

This script initializes OAuth2 tokens for all Google services.
Run this script once to authenticate and generate unified google_token.json

Supported services:
- Gmail (read/send)
- Google Calendar (read/write)
- Google Sheets (read/write)
- Google Docs (read/write)
- Google Slides (read/write)
- Google Forms (read/write)
- Google Apps Script (projects/deployments)
- Google Drive (file operations)

Note: Google Keep API is not publicly available and is excluded.
"""

import os
import sys
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def main() -> int:
    # Defer imports to avoid requiring google libs where not needed
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except Exception as e:
        print("Google auth libraries are not installed. Run: pip install google-api-python-client google-auth google-auth-oauthlib", file=sys.stderr)
        return 1

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()

    # All available scopes for Google services (excluding Keep - not publicly available)
    scopes = [
        # Gmail
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.send',
        # Calendar
        'https://www.googleapis.com/auth/calendar.readonly',
        'https://www.googleapis.com/auth/calendar.events',
        # Sheets
        'https://www.googleapis.com/auth/spreadsheets',
        # Docs
        'https://www.googleapis.com/auth/documents',
        # Slides
        'https://www.googleapis.com/auth/presentations',
        # Forms
        'https://www.googleapis.com/auth/forms.body',
        'https://www.googleapis.com/auth/forms.responses.readonly',
        # Apps Script
        'https://www.googleapis.com/auth/script.projects',
        'https://www.googleapis.com/auth/script.deployments',
        # Drive (for file operations)
        'https://www.googleapis.com/auth/drive.file'
    ]

    # Unified paths
    token_path = os.getenv("GOOGLE_TOKEN_PATH", "secrets/google_token.json")
    credentials_path = os.getenv("GOOGLE_CREDENTIALS_PATH", "secrets/google_credentials.json")

    print(f"📁 Credentials path: {credentials_path}")
    print(f"📁 Token path: {token_path}")

    if not os.path.exists(credentials_path):
        print(f"❌ Credentials file not found: {credentials_path}")
        print("\nPlease follow these steps:")
        print("1. Go to Google Cloud Console")
        print("2. Enable Gmail API and Calendar API")
        print("3. Create OAuth 2.0 credentials")
        print("4. Download credentials.json and save to secrets/google_credentials.json")
        return 2

    creds = None

    # Load existing token
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, scopes)
            logger.info("Loaded existing token: %s", token_path)
        except Exception:
            logger.warning("Failed to load existing token; will re-authenticate")

    # Refresh or run flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing expired token...")
            creds.refresh(Request())
            logger.info("Refreshed existing token")
        else:
            print("🔐 Starting OAuth2 authentication flow...")
            print("Your browser will open for authentication.")
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, scopes)
            # Run a local server to complete OAuth; binds to random free port
            creds = flow.run_local_server(port=0)
            logger.info("OAuth flow completed")

        # Save token
        os.makedirs(os.path.dirname(token_path) or ".", exist_ok=True)
        with open(token_path, "w") as f:
            f.write(creds.to_json())
        logger.info("Saved token to: %s", token_path)

    # Test main services
    try:
        print("\n📧 Testing Gmail API connection...")
        gmail_service = build('gmail', 'v1', credentials=creds)
        
        # Test Gmail
        profile = gmail_service.users().getProfile(userId='me').execute()
        print(f"✅ Gmail connected! Email: {profile.get('emailAddress', 'Unknown')}")

        print("\n📅 Testing Calendar API connection...")
        calendar_service = build('calendar', 'v3', credentials=creds)
        
        # Test Calendar
        calendar_list = calendar_service.calendarList().list().execute()
        calendars = calendar_list.get('items', [])
        
        if calendars:
            print(f"✅ Calendar connected! Found {len(calendars)} calendar(s):")
            for calendar in calendars[:3]:  # Show first 3
                print(f"   - {calendar.get('summary', 'Unnamed')}")
        else:
            print("⚠️  No calendars found")

        print(f"\n✅ Google services token initialization completed successfully!")
        print(f"📁 Token saved to: {token_path}")
        print(f"\n📝 Token includes {len(scopes)} scopes for the following services:")
        print("   ✓ Gmail (read/send)")
        print("   ✓ Google Calendar (read/write events)")
        print("   ✓ Google Sheets (read/write)")
        print("   ✓ Google Docs (read/write)")
        print("   ✓ Google Slides (read/write)")
        print("   ✓ Google Forms (read/write)")
        print("   ✓ Google Apps Script (projects/deployments)")
        print("   ✓ Google Drive (file operations)")
        print("\n⚠️  Note: Google Keep API is not publicly available and is excluded.")
        print("\n💡 Make sure all required APIs are enabled in Google Cloud Console:")
        print("   https://console.cloud.google.com/apis/library")
        
        return 0

    except Exception as e:
        print(f"❌ Error testing Google services: {e}")
        logger.error(f"Full error: {e}", exc_info=True)
        return 3

if __name__ == "__main__":
    raise SystemExit(main())
