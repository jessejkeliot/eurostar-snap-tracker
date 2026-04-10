import os
from pathlib import Path
from google import genai
from google.genai import types
from models import MinimalSearch, MinimalSearchModel, User
from datetime import datetime
from dotenv import load_dotenv
from tracker import TrainJourney
import requests
from db import get_user_by_id

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
        print("WhatsApp credentials not configured")
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
        print(f"Failed to send WhatsApp message: {e}")

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
            print(f"Failed to send email: {e}")

def send_results_to_user(user_id, results: list[TrainJourney]):
    body = "Your train search results:\n\n"
    for result in results:
        body += str(result) + "\n"
    notify_user(user_id, "Eurostar Train Search Results", body)

def send_retry_message_to_user(user_id):
    body = "Sorry, I didn't understand your message. Please try again with a train booking request."
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
        print(response.text)
        search = MinimalSearchModel.model_validate_json(response.text)
        print(search)
        return MinimalSearch(**search.model_dump())
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
