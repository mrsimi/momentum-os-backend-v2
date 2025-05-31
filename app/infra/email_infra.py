import logging
import os
import resend
from dotenv import load_dotenv

load_dotenv()
#
logging.basicConfig(
    format="%(asctime)s [%(process)d] [%(levelname)s] %(message)s",
    level=logging.INFO
)
class EmailInfra:
    def __init__(self):
        resend.api_key = os.getenv("RESEND_API_KEY")

    def send_email(self, destinationEmail: str, subject: str, type: str, object: dict):
        file_path = f"app/infra/{type}.html"
        with open(file_path, "r") as file:
            html = file.read()
        placeholders = {
            "{{ link }}": object.get("link", ""),
            "{{ creator_email }}": object.get("creator_email", ""),
            "{{ accept_link }}": object.get("accept_link", ""),
            "{{ reject_link }}": object.get("reject_link", ""),
            "{{ project_name }}": object.get("project_name", ""),
        }

        for key, value in placeholders.items():
            html = html.replace(key, value)

            
        container_path = f"app/infra/container.html"
        with open(container_path, "r") as file:
            container_html = file.read()
        
        full_content = container_html.replace("{{content}}", html)
        params = {
            "from": "DoTellBoard <no_reply@notifications.dotellboard.com>",
            "to": destinationEmail,
            "subject": subject,
            "html": full_content
        }

        try:
            email = resend.Emails.send(params)
            logging.info('email sent successfully', email)
            return email
        except Exception as e:
            logging.info(f"Failed to send email: {e}")
            return None
