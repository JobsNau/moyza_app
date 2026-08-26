"""
Script one-shot para generar gmail_token.json via OAuth2.

Ejecutar UNA SOLA VEZ desde la raíz del proyecto backend:
    cd backend
    python scripts/generate_gmail_token.py

Abrirá el navegador para que autorices la cuenta de Gmail desde la que
se enviarán los emails. El token resultante se guarda en
app/credentials/gmail_token.json y se renueva automáticamente.

En modo prueba (app no publicada) el token dura 7 días. Para producción,
publica la app en Google Cloud Console para que dure indefinidamente.
"""
import json
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
CREDENTIALS_PATH = Path("app/credentials/gmail_credentials.json")
TOKEN_PATH = Path("app/credentials/gmail_token.json")


def main():
    if not CREDENTIALS_PATH.exists():
        print(f"\n[ERROR] No se encontró: {CREDENTIALS_PATH}")
        print("Coloca el archivo credentials.json descargado de Google Cloud Console en:")
        print(f"  {CREDENTIALS_PATH.resolve()}")
        return

    print("Iniciando flujo OAuth2 de Gmail...")
    print("Se abrirá el navegador. Autoriza la cuenta desde la que se enviarán los emails.")

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_PATH), SCOPES)
    creds = flow.run_local_server(port=0)

    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(creds.to_json())

    token_data = json.loads(creds.to_json())
    client_email = token_data.get("token_uri", "desconocido")

    print(f"\n[OK] Token guardado en: {TOKEN_PATH.resolve()}")
    print("El recordatorio de compradores ya puede enviar emails.")
    print("\nNOTA: En modo prueba el token caduca en 7 días.")
    print("Vuelve a ejecutar este script cuando expire.")


if __name__ == "__main__":
    main()
