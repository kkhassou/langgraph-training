import os
import sys
import logging


def main() -> int:
    # Defer imports to avoid requiring google libs where not needed
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except Exception as e:
        print("Google auth libraries are not installed. Run: pip install google-api-python-client google-auth google-auth-oauthlib", file=sys.stderr)
        return 1

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    scopes = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.send',
    ]

    token_path = os.getenv("GMAIL_TOKEN_PATH", "secrets/gmail_token.json")
    credentials_path = os.getenv("GMAIL_CREDENTIALS_PATH", "secrets/gmail_credentials.json")

    creds = None

    # load existing token
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, scopes)
            logger.info("Loaded existing token: %s", token_path)
        except Exception:
            logger.warning("Failed to load existing token; will re-authenticate")

    # refresh or run flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            logger.info("Refreshed existing token")
        else:
            if not os.path.exists(credentials_path):
                logger.error("Credentials file not found: %s", credentials_path)
                return 2
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, scopes)
            # Run a local server to complete OAuth; binds to random free port
            creds = flow.run_local_server(port=0)
            logger.info("OAuth flow completed")

        # Save token
        os.makedirs(os.path.dirname(token_path) or ".", exist_ok=True)
        with open(token_path, "w") as f:
            f.write(creds.to_json())
        logger.info("Saved token to: %s", token_path)

    print(f"✅ Token ready: {token_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


