from datetime import datetime, timedelta, timezone
import logging
from app.infra.email_infra import EmailInfra
import os 
from dotenv import load_dotenv
import asyncpg
import socket

from app.utils.security import encrypt_payload
load_dotenv()

logging.basicConfig(
    format="%(asctime)s [%(process)d] [%(levelname)s] %(message)s",
    level=logging.INFO
)

DATABASE_URL = os.getenv("DATABASE_URL")
FRONTEND_URL = os.getenv('FRONTEND_URL')

async def fetch_checkins_and_notify():
    try:
        conn = await asyncpg.connect(DATABASE_URL)

        now_utc = datetime.now(timezone.utc)
        current_hour = now_utc.time().hour
        current_day = now_utc.strftime("%A")
        

        checkin_query = """
            SELECT c.project_id, c.id, c.checkin_time_utc, c.user_timezone 
            FROM checkins c
            WHERE
                c.is_active = true
                AND c.project_ended = false
                AND EXTRACT(HOUR FROM c.checkin_time_utc) = $1
                AND $2 = ANY(c.checkin_days_utc)
        """

        logging.info(checkin_query, current_hour, current_day)

        checkins = await conn.fetch(checkin_query, current_hour, current_day)
        

        logging.info(f'-- found {len(checkins)} notifications')
        logging.info(checkins)

        for row in checkins:
            email_infra = EmailInfra()
            project_id = row['project_id']
            #checkin_time_utc = row['checkin_time_utc']
            user_timezone = row['user_timezone']
            user_datetime = now_utc.astimezone(timezone(timedelta(hours=int(user_timezone))))
            user_checkinday = user_datetime.strftime("%A")
            checkin_id = row['id']

            members_query = """
            SELECT user_email
            FROM project_members
            WHERE
                project_id = $1
                AND is_active = true
            """
            members = await conn.fetch(members_query, project_id)
            logging.info(f'-- found {len(members)} members for project_id: {project_id}')

            for member in members:
                user_email = member["user_email"]
                payload = {
                        "user_email": user_email,
                        "user_datetime":user_datetime.isoformat(),
                        "user_checkinday": user_checkinday,
                        "user_timezone": user_timezone,
                        "checkin_id": checkin_id
                }
                logging.info(payload)
                encrypted_payload = encrypt_payload(payload)
                link = f"{FRONTEND_URL}/check-in?project_id={project_id}&payload={encrypted_payload}"

                logging.info(f'-- found member and link: {link}')
                email_infra.send_email(user_email, "Submit Your CheckIn", "submit_checkin", {"link": link})

            insert_tracker_query = """
                insert into checkin_response_tracker
                (status, number_of_responses_expecting, user_checkin_date, checkin_id, date_created, from_server_name)
                values ($1, $2, $3, $4, $5, $6)
                """
            await conn.execute(insert_tracker_query, 'EMAILS_SENT', len(members), user_datetime, checkin_id, datetime.now(timezone.utc), socket.gethostname())

        await conn.close()
    except Exception as e:
        logging.error(f"Failed fetch_checkins_and_notify {e}")
