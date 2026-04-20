import os
import dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.exceptions import RefreshError
import requests


SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.compose',
]


def get_gmail_service(user_data: dict):
    creds = Credentials(
        token=user_data["access_token"],
        refresh_token=user_data["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("CLIENT_ID"),
        client_secret=os.getenv("CLIENT_SECRET"),
    )

    try:
       
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except RefreshError:
                    response = requests.post(
                        "https://oauth2.googleapis.com/token",
                        data={
                            "client_id": os.getenv("CLIENT_ID"),
                            "client_secret": os.getenv("CLIENT_SECRET"),
                            "refresh_token": user_data["refresh_token"],
                            "grant_type": "refresh_token",
                        },
                    )

                    if response.status_code != 200:
                        raise Exception(f"Re-auth required: {response.json()}")

                    tokens = response.json()
                    creds.token = tokens["access_token"]
                user_data["access_token"] = creds.token

            else:
                raise Exception("Re-authentication required (no valid refresh token)")

    except Exception as e:
        raise Exception(f"Gmail auth failed: {str(e)}")

    return build("gmail", "v1", credentials=creds)
