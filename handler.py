from models import MinimalSearch
from myparse import about_trains
from scheduler import search_and_send, send_to_subscribed_users
from services import add_subscription, should_run_now
from db import create_user_from_phone, create_user_from_email, get_search_by_id, get_user_by_phone_number, get_user_by_email, hash_for_db, update_last_run
from tracker import run_search
from messaging import parse_message, send_onboarded_message_to_user, send_results_to_user, send_retry_message_to_user
import bottle
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

def process_message(user_id, message):
    train_message = about_trains(message)
    if(not train_message):
        send_retry_message_to_user(user_id)
        return "BAD"
    params = parse_message(message) # use gemma
    if (params):
        search_id, is_new = add_subscription(user_id, params.origin, params.destination, params.outbound_date, params.inbound_date)
        search = get_search_by_id(search_id)

        if search and (is_new or should_run_now(search)):
            ms = MinimalSearch(search.origin, search.destination, search.outbound_date, search.inbound_date)
            url, results = run_search(ms)
            result_joined = " ".join([str(tj) for tj in results])
            hd = hash_for_db(result_joined)
            if(not is_new and search.last_results != hd):
                # broadcast to all
                send_to_subscribed_users(search.id, results)
            else:
                send_results_to_user(user_id, results)
            update_last_run(search.id, result_joined)
        if (not is_new):
            send_onboarded_message_to_user(user_id)
        return "OK"
    else:
        # TODO send a message asking for user to repeat themselves
        pass

@bottle.route("/webhook/whatsapp", method="GET")
def verify_whatsapp_webhook():
    mode = bottle.request.query.get("hub.mode")
    token = bottle.request.query.get("hub.verify_token")
    challenge = bottle.request.query.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == os.getenv("WHATSAPP_VERIFY_TOKEN"):
            return challenge
        else:
            bottle.response.status = 403
            return "Forbidden"
    return "OK"

@bottle.route("/webhook/whatsapp", method="POST")
def whatsapp_handler():
    data = bottle.request.json
    if not data or "object" not in data:
        return "OK"
    
    if data["object"] == "whatsapp_business_account":
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                if "messages" in value:
                    for message in value["messages"]:
                        if message.get("type") == "text":
                            phone_number = message.get("from")
                            message_body = message["text"].get("body")
                            
                            user = get_user_by_phone_number(phone_number)
                            if user:
                                user_id = user.id
                            else:
                                user_id = create_user_from_phone(phone_number)
                                
                            process_message(user_id, message_body)
    return "OK"

@bottle.route("/webhook/email", method="POST")
def email_handler():
    try:
        data = bottle.request.json
        email_address = data.get("from")
        message = data.get("body")
        
        user = get_user_by_email(email_address)
        if user:
            user_id = user.id
        else:
            user_id = create_user_from_email(email_address)
            
        process_message(user_id, message)
        return {"status": "OK"}
    except Exception as e:
        return {"error": str(e)}

@bottle.route("/send-email", method="POST")
def send_email():
    try:
        data = bottle.request.json
    except:
        return {"error": "Invalid JSON"}
    
    to_email = data.get("to")
    subject = data.get("subject")
    body = data.get("body")
    
    if not to_email or not subject or not body:
        return {"error": "Missing required fields: to, subject, body"}
    
    gmail_address = os.getenv("GMAIL_ADDRESS")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")
    
    if not gmail_address or not gmail_password:
        return {"error": "Gmail credentials not configured"}
    
    msg = MIMEMultipart()
    msg['From'] = gmail_address
    msg['To'] = to_email
    msg['Subject'] = subject
    
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(gmail_address, gmail_password)
        text = msg.as_string()
        server.sendmail(gmail_address, to_email, text)
        server.quit()
        return {"status": "Email sent successfully"}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    bottle.run(host='localhost', port=8080, debug=True) # just for dev, should use gunicorn