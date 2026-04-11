import os
from pathlib import Path
from google import genai
from google.genai import types
from src.core.models import MinimalSearch, MinimalSearchModel, User
from datetime import datetime
from dotenv import load_dotenv
from src.scraper.tracker import TrainJourney
import requests
import threading
from src.bot.myparse import get_station_id
from src.core.log_config import get_logger

logger = get_logger(__name__)
from src.core.db import get_user_by_id, get_user_trial, increment_user_trial

load_dotenv()
import argparse

load_dotenv()

prompt_path = Path(__file__).resolve().parent / "prompt.txt"
if prompt_path.exists():
    with prompt_path.open("r", encoding="utf-8") as f:
        systemprompt = f.read()
else:
    systemprompt = ""

def send_whatsapp_message(phone_number, text):
    token = os.getenv("WHATSAPP_TOKEN")
    phone_id = os.getenv("WHATSAPP_PHONE_ID")
    if not token or not phone_id:
        logger.error("WhatsApp credentials not configured")
        return
        
    url = f"https://graph.facebook.com/v17.0/{phone_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": phone_number,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": text
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Failed to send WhatsApp message: {e}")

def notify_user(user_id, subject, body):
    user = get_user_by_id(user_id)
    if not user:
        return
        
    if user.phone_number:
        send_whatsapp_message(user.phone_number, body)
    elif user.email:
        data = {
            "to": user.email,
            "subject": subject,
            "body": body
        }
        try:
            response = requests.post("http://localhost:8080/send-email", json=data)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to send email: {e}")

def send_results_to_user(user_id, results: list[TrainJourney]):
    user = get_user_by_id(user_id)
    if not user:
        return
        
    trial = get_user_trial(user_id)
    
    body = ""
    for result in results:
        body += str(result) + "\n"

    subject = "Eurostar Train Search Results"
    
    if user.is_paying:
        notify_user(user_id, subject, f"⚡ Priority Alert:\n\n{body}\n💸 You've saved £120+ already!")
    elif trial and trial.alerts_used < trial.alerts_limit:
        increment_user_trial(user_id)
        notify_user(user_id, subject, f"🆓 Free Alert ({trial.alerts_used + 1}/{trial.alerts_limit} used):\n\n{body}")
    else:
        paywall_msg = (
            "🚨 Snap ticket found:\n\n"
            f"{body}\n"
            "You’ve used your free alerts 👀\n"
            "You’re seeing this 10 minutes later than premium users ⏱️\n\n"
            "Upgrade for:\n"
            "⚡ Instant alerts\n"
            "🔁 Unlimited deals\n"
            "🗓️ Multi-day tracking ranges\n\n"
            "👉 £2.49/month\n"
            f"https://buy.stripe.com/test_checkout_link?client_reference_id={user_id}"
        )
        t = threading.Timer(600.0, notify_user, args=[user_id, "Delayed Eurostar Search", paywall_msg])
        t.start()
        logger.info(f"Scheduled delayed alert for user {user.phone_number or user.email}")

def send_retry_message_to_user(user_id):
    body = "Sorry, I didn't understand your message. Please try again with a train booking request.\n\n(Tip: Reply 'STOP' at any time to cancel all active alerts)."
    notify_user(user_id, "Eurostar Bot - Message Not Understood", body)

def send_message_to_user(user_id, subject, body):
    notify_user(user_id, subject, body)

def send_onboarded_message_to_user(user_id):
    body = "Welcome! You've been subscribed to train search notifications. You'll receive updates on your searches."
    notify_user(user_id, "Welcome to Eurostar Bot", body)

def parse_message(message):
    # make gemma 4 call with our system prompt
    client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
    schema = MinimalSearchModel.model_json_schema()
    today = datetime.today()
    response = client.models.generate_content(
        model="gemma-4-26b-a4b-it",
        contents=f"{systemprompt}\nToday's date is {today.strftime('%Y-%m-%d-%A')}\n\nUser: {message}",
        config=types.GenerateContentConfig(
        thinking_config=types.ThinkingConfig(thinking_level=types.ThinkingLevel("minimal")),
        response_mime_type="application/json",
        response_json_schema=schema
    ),
    )
    if response.text:
        logger.debug(f"LLM Response: {response.text}")
        search = MinimalSearchModel.model_validate_json(response.text)
        origin_id = get_station_id(search.origin)
        dest_id = get_station_id(search.destination)
        if not origin_id or not dest_id:
             return None
             
        searches = []
        if search.end_date:
            from datetime import timedelta
            delta = (search.end_date - search.outbound_date).days
            if delta < 0:
                return None
            for i in range(delta + 1):
                current_date = search.outbound_date + timedelta(days=i)
                searches.append(MinimalSearch(origin=origin_id, destination=dest_id, outbound_date=current_date, inbound_date=search.inbound_date))
        else:
            searches.append(MinimalSearch(origin=origin_id, destination=dest_id, outbound_date=search.outbound_date, inbound_date=search.inbound_date))
            
        return searches
    return None

def list_models():
    client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
    
    pages = client.models.list()
    for page in pages:
        print(page)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse a message about train bookings")
    parser.add_argument("message", nargs="?", default="Hi there I want to book a train from London to Amsterdam leaving on the 16th of april", help="Message to parse")
    
    args = parser.parse_args()
    parse_message(args.message)
