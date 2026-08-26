import logging
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


class GmailService:
    def __init__(self, credentials_path: str, token_path: str):
        self._credentials_path = Path(credentials_path)
        self._token_path = Path(token_path)
        self._service = None

    def _get_service(self):
        if self._service:
            return self._service

        creds = None

        if self._token_path.exists():
            creds = Credentials.from_authorized_user_file(str(self._token_path), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                self._save_token(creds)
            else:
                raise RuntimeError(
                    f"Token de Gmail inválido o inexistente. "
                    f"Ejecuta 'python scripts/generate_gmail_token.py' para generarlo."
                )

        self._service = build("gmail", "v1", credentials=creds)
        return self._service

    def _save_token(self, creds: Credentials):
        self._token_path.parent.mkdir(parents=True, exist_ok=True)
        self._token_path.write_text(creds.to_json())

    def send_email(self, to: str, subject: str, html_body: str) -> bool:
        try:
            service = self._get_service()

            message = MIMEMultipart("alternative")
            message["To"] = to
            # message["To"] = "jobany.nausa@udea.edu.co"
            message["Subject"] = subject
            message.attach(MIMEText(html_body, "html"))

            encoded = base64.urlsafe_b64encode(message.as_bytes()).decode()
            service.users().messages().send(
                userId="me",
                body={"raw": encoded}
            ).execute()

            logger.info(f"Email enviado a {to}: {subject}")
            return True

        except HttpError as e:
            logger.error(f"Error HTTP al enviar email a {to}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error al enviar email a {to}: {e}")
            return False
