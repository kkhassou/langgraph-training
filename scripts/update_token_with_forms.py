#!/usr/bin/env python3
"""
Re-authenticate with Google to add Forms API scopes.
This will update the existing token with all required scopes.
"""

import os
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Add all required scopes for all Google services
SCOPES = [
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
    # Forms (NEW)
    'https://www.googleapis.com/auth/forms.body',
    'https://www.googleapis.com/auth/forms.responses.readonly',
    # Drive (for file operations)
    'https://www.googleapis.com/auth/drive.file'
]

def main():
    # Get credentials and token paths
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    credentials_path = os.path.join(project_root, 'secrets', 'google_credentials.json')
    token_path = os.path.join(project_root, 'secrets', 'google_token.json')

    print(f"Credentials file: {credentials_path}")
    print(f"Token file: {token_path}")

    if not os.path.exists(credentials_path):
        print(f"Error: Credentials file not found at {credentials_path}")
        print("Please download your OAuth 2.0 credentials from Google Cloud Console")
        sys.exit(1)

    print("\nStarting OAuth flow with all scopes including Forms...")
    print("This will open a browser window for authentication.")
    print("\nRequired scopes:")
    for scope in SCOPES:
        print(f"  - {scope}")

    # Run OAuth flow
    flow = InstalledAppFlow.from_client_secrets_file(
        credentials_path,
        SCOPES
    )

    creds = flow.run_local_server(port=0)

    # Save credentials
    with open(token_path, 'w') as token:
        token.write(creds.to_json())

    print(f"\n✓ Token saved to {token_path}")
    print("\nToken includes the following scopes:")
    if creds.scopes:
        for scope in creds.scopes:
            print(f"  - {scope}")

    print("\n✓ Authentication complete! You can now use all Google services including Forms.")
    print("\nIMPORTANT: Make sure to enable the Forms API in Google Cloud Console:")
    print("https://console.cloud.google.com/apis/library/forms.googleapis.com")

if __name__ == '__main__':
    main()
