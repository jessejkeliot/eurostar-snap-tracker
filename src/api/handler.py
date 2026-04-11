from src.core.db import get_subscribed_users
from src.core.models import MinimalSearch
from src.bot.myparse import about_trains
from src.core.services import add_subscription, should_run_now
from src.core.db import create_user_from_phone, create_user_from_email, get_search_by_id, get_user_by_phone_number, get_user_by_email, hash_for_db, update_last_run, set_user_paid, delete_all_subscriptions_for_user, get_abuse_strikes, increment_abuse_strikes, reset_abuse_strikes
from src.scraper.tracker import run_search
from src.bot.messaging import parse_message, send_onboarded_message_to_user, send_results_to_user, send_retry_message_to_user, send_message_to_user
import bottle
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import stripe
from datetime import timedelta, datetime

def process_message(user_id, message):
    strikes = get_abuse_strikes(user_id)
    if strikes >= 3:
        # User has repeatedly forced failures. Ignore silently to conserve LLM/WhatsApp API quota.
        delete_all_subscriptions_for_user(user_id)
        return "IGNORED_ABUSE"

    msg_lower = message.strip().lower()
    if msg_lower in ["stop", "unsubscribe", "cancel", "quit", "halt", "end", "remove"]:
        delete_all_subscriptions_for_user(user_id)
        send_message_to_user(user_id, "Unsubscribed", "You have been safely unsubscribed from all train alerts. 🛑\n\nSend a new route whenever you want to track fares again!")
        return "UNSUBSCRIBED"
        
    train_message = about_trains(message)
    if(not train_message):
        increment_abuse_strikes(user_id)
        send_retry_message_to_user(user_id)
        return "BAD"
    
    params_list = parse_message(message) # use gemma
    if params_list:
        reset_abuse_strikes(user_id)
        user = get_user_by_id(user_id)
        
        if len(params_list) > 1:
            if not user.is_paying:
                msg = (
                    "🗓️ Multi-day tracking is a Premium feature!\n\n"
                    "Upgrade for:\n"
                    "⚡ Instant alerts\n"
                    "🔁 Unlimited deals\n"
                    "🗓️ Multi-day tracking ranges\n\n"
                    "👉 £2.49/month\n"
                    f"https://buy.stripe.com/test_checkout_link?client_reference_id={user_id}"
                )
                send_message_to_user(user_id, "Premium Feature", msg)
                return "PAYWALL"
            if len(params_list) > 7:
                send_message_to_user(user_id, "Range Too Large", "Max search range is 7 days. Please try a shorter duration.")
                return "BAD"
        
        existing_dates_message = False
        
        for params in params_list:
            search_id, is_new = add_subscription(user_id, params.origin, params.destination, params.outbound_date, params.inbound_date)
            search = get_search_by_id(search_id)

            if not is_new:
                existing_dates_message = True

            if search and (is_new or should_run_now(search)):
                ms = MinimalSearch(search.origin, search.destination, search.outbound_date, search.inbound_date)
                url, results = run_search(ms)
                result_joined = " ".join([str(tj) for tj in results])
                hd = hash_for_db(result_joined)
                if(not is_new and search.last_results != hd):
                    # broadcast to all
                    users = get_subscribed_users(search.id)
                    for u in users:
                        send_results_to_user(u.id, results)
                else:
                    send_results_to_user(user_id, results)
                update_last_run(search.id, result_joined)
                
        if existing_dates_message:
            if len(params_list) > 1:
                earliest = min(p.outbound_date for p in params_list).strftime("%Y-%m-%d")
                latest = max(p.outbound_date for p in params_list).strftime("%Y-%m-%d")
                body = f"Welcome! You've been subscribed to train search notifications for the range {earliest} -> {latest}. You'll receive updates on your searches."
                send_message_to_user(user_id, "Welcome to Eurostar Bot", body)
            else:
                send_onboarded_message_to_user(user_id)
        return "OK"
    else:
        # LLM parsing failed despite passing regex
        increment_abuse_strikes(user_id)
        send_retry_message_to_user(user_id)
        return "BAD"

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
        logger.info(f"📧 Received email webhook from {email_address}. Processing...")
        
        user = get_user_by_email(email_address)
        if user:
            user_id = user.id
        else:
            user_id = create_user_from_email(email_address)
            
        process_message(user_id, message)
        logger.info(f"✅ Webhook processing complete for {email_address}")
        return {"status": "OK"}
    except Exception as e:
        return {"error": str(e)}

@bottle.route("/webhook/stripe", method="POST")
def stripe_webhook():
    payload = bottle.request.body.read()
    sig_header = bottle.request.headers.get("Stripe-Signature")
    endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    
    event = None
    try:
        if endpoint_secret and sig_header:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        else:
            # Fallback for local testing without verification
            import json
            event = json.loads(payload)
    except Exception as e:
        bottle.response.status = 400
        return str(e)
        
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session.get("client_reference_id")
        
        if user_id:
            # Assuming monthly sub for simplicity:
            expires = datetime.now().date() + timedelta(days=30)
            set_user_paid(user_id, expires)
            
            from src.bot.messaging import notify_user
            msg = (
                "✅ You’re now on premium\n\n"
                "You’ll get:\n"
                "⚡ Instant alerts\n"
                "🎯 Priority deals\n\n"
                "Next deal could drop anytime 👀"
            )
            notify_user(user_id, "Welcome to Premium!", msg)
            
    return "OK"

@bottle.route("/send-email", method="POST")
def send_email():
    try:
        data = bottle.request.json
    except:
        return {"error": "Invalid JSON"}
    
    to_email = data.get("to")
    subject = data.get("subject")
    body = data.get("body")
    html_body = data.get("html_body")
    
    if not to_email or not subject or not body:
        return {"error": "Missing required fields: to, subject, body"}
    
    gmail_address = os.getenv("GMAIL_ADDRESS")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")
    
    if not gmail_address or not gmail_password:
        return {"error": "Gmail credentials not configured"}
    
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
        return {"status": "Email sent successfully"}
    except Exception as e:
        return {"error": str(e)}

app = bottle.default_app()

if __name__ == "__main__":
    bottle.run(app=app, host='localhost', port=8080, debug=True) # fallback for basic local execution