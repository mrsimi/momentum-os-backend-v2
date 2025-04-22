import os
import resend
from dotenv import load_dotenv

load_dotenv()

class EmailInfra:
    def __init__(self):
        resend.api_key = os.getenv("RESEND_API_KEY")

    def send_email(self, destinationEmail: str, subject: str, type: str, object: dict):
        file_path = f"app/infra/{type}.html"
        with open(file_path, "r") as file:
            html = file.read()
        html = html.replace("{{ link }}", object["link"])
            

        params = {
            "from": "Momentum OS <home@turntablecharts.com>",
            "to": destinationEmail,
            "subject": subject,
            "html": html
        }

        try:
            email = resend.Emails.send(params)
            return email
        except Exception as e:
            print(f"Failed to send email: {e}")
            return None
