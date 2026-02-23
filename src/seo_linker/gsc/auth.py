"""GSC authentication — OAuth and service account."""

from __future__ import annotations

import ssl
from pathlib import Path

import httplib2
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
TOKEN_PATH = Path.home() / ".seo-linker" / "gsc_token.json"


def _build_http_no_ssl_verify():
    """Create an httplib2.Http instance that skips SSL certificate verification."""
    return httplib2.Http(disable_ssl_certificate_validation=True)


def authenticate(
    service_account_path: str | None = None,
    oauth_client_secrets_path: str | None = None,
) -> object:
    """Return an authenticated GSC service object.

    Priority:
      1. Service account JSON (if provided)
      2. OAuth client secrets (if provided) — opens browser for consent on first run,
         then caches token at ~/.seo-linker/gsc_token.json

    Raises ValueError if neither is provided.
    """
    if service_account_path:
        creds = service_account.Credentials.from_service_account_file(
            service_account_path, scopes=SCOPES
        )
        # Use http with SSL verification disabled for corporate proxy environments
        authed_http = google_auth_httplib2_request(creds)
        return build("searchconsole", "v1", http=authed_http)

    if oauth_client_secrets_path:
        # Check for cached token first
        creds = None
        if TOKEN_PATH.exists():
            from google.oauth2.credentials import Credentials
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                from google.auth.transport.requests import Request
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    oauth_client_secrets_path, SCOPES
                )
                creds = flow.run_local_server(port=0)
            # Cache token
            TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
            TOKEN_PATH.write_text(creds.to_json())

        authed_http = google_auth_httplib2_request(creds)
        return build("searchconsole", "v1", http=authed_http)

    raise ValueError(
        "GSC credentials not configured. Run:\n"
        "  seo-linker config --gsc-service-account /path/to/credentials.json\n"
        "  OR\n"
        "  seo-linker config --gsc-oauth-secrets /path/to/client_secrets.json"
    )


def google_auth_httplib2_request(creds):
    """Create an authorized httplib2.Http with SSL verification disabled."""
    import google_auth_httplib2
    http = _build_http_no_ssl_verify()
    return google_auth_httplib2.AuthorizedHttp(creds, http=http)
