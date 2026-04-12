import imaplib
import email
import os
import requests
import time
from src.core.log_config import get_logger

logger = get_logger(__name__)
from dotenv import load_dotenv

load_dotenv()

# Account credentials
USERNAME = os.getenv("GMAIL_ADDRESS")
PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
IMAP_SERVER = "imap.gmail.com"
BOTTLE_ENDPOINT = "http://localhost:8080/webhook/email"

def poll_emails():
    try:
        imap = imaplib.IMAP4_SSL(IMAP_SERVER)
        imap.login(USERNAME, PASSWORD)
        imap.select("INBOX")
        
        # Search for unread emails with subject "train" or "Train"
        status, messages = imap.search(None, '(UNSEEN OR SUBJECT "train" SUBJECT "stop")')
        
        if status == "OK":
            unread_ids = messages[0].split()
            logger.info(f"Found {len(unread_ids)} unread email(s) during check")
            
            for num in unread_ids:
                status, msg_data = imap.fetch(num, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        # Get metadata
                        from_header = msg.get("From")
                        subject_header = msg.get("Subject", "")
                        email_address = email.utils.parseaddr(from_header)[1]
                        
                        # Get body
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                content_type = part.get_content_type()
                                if content_type == "text/plain":
                                    body = part.get_payload(decode=True).decode()
                                    break
                        else:
                            body = msg.get_payload(decode=True).decode()
                        
                        # Send to bottle endpoint
                        if body and email_address:
                            payload = {
                                "from": email_address,
                                "subject": subject_header,
                                "body": body
                            }
                            # Note: No auth header used for local service-to-service call
                            requests.post("http://localhost:8080/webhook/email", json=payload)
                            logger.info(f"Forwarded email from {email_address} to webhook")
        
        imap.logout()
    except Exception as e:
        logger.error(f"Error polling emails: {e}")

if __name__ == "__main__":
    while True:
        poll_emails()
        time.sleep(45)
