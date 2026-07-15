"""Email the updated recruiting workbook as an attachment.

Reads SMTP credentials and the recipient from environment variables (set as
GitHub Secrets in the workflow - never hardcode credentials in this file).

Required environment variables:
    SENDER_EMAIL       - the Gmail address sending the email
    SENDER_APP_PASSWORD - a Gmail "app password" (NOT your regular password)
    RECIPIENT_EMAIL    - who receives the update (Andrea's email)

Usage:
    python send_email.py --workbook "Recruiting_Workbook.xlsx"
"""

import argparse
import os
import smtplib
from datetime import date
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587


def parse_arguments():
    parser = argparse.ArgumentParser(description="Email the updated workbook.")
    parser.add_argument("--workbook", required=True, help="Path to the .xlsx file to attach.")
    return parser.parse_args()


def main():
    args = parse_arguments()
    workbook_path = Path(args.workbook)

    if not workbook_path.exists():
        raise FileNotFoundError(f"Could not find {workbook_path}")

    sender_email = os.environ["SENDER_EMAIL"]
    sender_password = os.environ["SENDER_APP_PASSWORD"]
    recipient_email = os.environ["RECIPIENT_EMAIL"]

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient_email
    message["Subject"] = f"Recruiting Tracker - Weekly Update ({date.today().isoformat()})"

    body = (
        "Hi Andrea,\n\n"
        "Attached is this week's automated recruiting tracker update.\n\n"
        "This runs on its own every Monday, no action needed unless you want "
        "to make changes to the tracker itself.\n\n"
        "Connor"
    )
    message.attach(MIMEText(body, "plain"))

    with open(workbook_path, "rb") as f:
        attachment = MIMEApplication(f.read(), _subtype="xlsx")
    attachment.add_header(
        "Content-Disposition", "attachment", filename=workbook_path.name
    )
    message.attach(attachment)

    print(f"[email] connecting to {SMTP_SERVER}:{SMTP_PORT}")
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(message)

    print(f"[email] sent to {recipient_email}")


if __name__ == "__main__":
    main()
