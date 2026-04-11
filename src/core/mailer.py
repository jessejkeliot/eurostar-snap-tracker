import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

def send_gmail_message(to_email, subject, body, html_body=None):
    gmail_address = os.getenv("GMAIL_ADDRESS")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")
    
    if not gmail_address or not gmail_password:
        return False, "Gmail credentials not configured"
    
    msg = MIMEMultipart('alternative')
    msg['From'] = gmail_address
    msg['To'] = to_email
    msg['Subject'] = subject
    
    msg.attach(MIMEText(body, 'plain'))
    if html_body:
        msg.attach(MIMEText(html_body, 'html'))
    
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(gmail_address, gmail_password)
        text = msg.as_string()
        server.sendmail(gmail_address, to_email, text)
        server.quit()
        return True, "Email sent successfully"
    except Exception as e:
        return False, str(e)
