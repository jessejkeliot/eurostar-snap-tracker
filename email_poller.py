import imaplib
import email
import os
import requests
import time
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
        
        # Search for unread emails with subject "train"
        status, messages = imap.search(None, '(UNSEEN SUBJECT "train")')
        
        if status == "OK" and messages[0]:
            for num in messages[0].split():
                status, msg_data = imap.fetch(num, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        
                        # Get sender
                        from_header = msg.get("From")
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
                            requests.post(BOTTLE_ENDPOINT, json={
                                "from": email_address,
                                "body": body
                            })
                            print(f"Forwarded email from {email_address} to webhook")
        
        imap.logout()
    except Exception as e:
        print(f"Error polling emails: {e}")

if __name__ == "__main__":
    while True:
        poll_emails()
        time.sleep(45)
