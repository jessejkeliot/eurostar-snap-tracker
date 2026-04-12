from src.bot import msg_templates
from src.core.models import MinimalSearch
from src.core.services import should_run_now, add_subscription, add_return_trip, is_date_trackable, MAX_SEARCH_DAYS
from src.bot.myparse import about_trains, get_station_name
from src.core.db import get_user_by_id, get_subscribed_users, create_user_from_phone, create_user_from_email, get_search_by_id, get_user_by_phone_number, get_user_by_email, hash_for_db, update_last_run, set_user_paid, delete_all_subscriptions_for_user, get_abuse_strikes, increment_abuse_strikes, reset_abuse_strikes
from src.scraper.tracker import run_search
from src.bot.messaging import parse_message, send_onboarded_message_to_user, send_results_to_user, send_retry_message_to_user, send_message_to_user, send_no_results_message
from src.core.mailer import send_gmail_message
from src.core.log_config import get_logger
import bottle
import os
import stripe
import threading
from datetime import timedelta, datetime

logger = get_logger(__name__)

def process_message(user_id, message, source="whatsapp"):
    print(f"DEBUG: 🔄 Starting process_message for user {user_id}")
    strikes = get_abuse_strikes(user_id)
    if strikes >= 3:
        print(f"DEBUG: 🚫 User {user_id} blocked due to abuse strikes ({strikes})")
        # Actually should have a blocked users table so anything else they send isn't responded to
        delete_all_subscriptions_for_user(user_id)
        return "IGNORED_ABUSE"

    msg_lower = message.strip().lower()
    if msg_lower in ["stop", "unsubscribe", "cancel", "quit", "halt", "end", "remove"]:
        print(f"DEBUG: 🛑 Stop word detected for user {user_id}")
        delete_all_subscriptions_for_user(user_id)
        subject, body = msg_templates.unsubscribed_msg()
        send_message_to_user(user_id, subject, body)
        return "UNSUBSCRIBED"
        
    train_message = about_trains(message)
    if(not train_message):
        print(f"DEBUG: ❓ Message for user {user_id} did not pass train regex. Strike incremented.")
        increment_abuse_strikes(user_id)
        send_retry_message_to_user(user_id)
        return "BAD"
    
    print(f"DEBUG: 🚆 Message for user {user_id} passed regex. Handing to LLM.")
    params_list = parse_message(message) # use gemma
    if params_list:
        print(f"DEBUG: ✨ LLM successfully parsed {len(params_list)} dates.")
        reset_abuse_strikes(user_id)
        user = get_user_by_id(user_id)
        
        if len(params_list) > 1:
            if not user.is_paying:
                print(f"DEBUG: 💰 User {user_id} hit multi-day paywall.")
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
                print(f"DEBUG: 📏 User {user_id} requested range > 7 days.")
                send_message_to_user(user_id, "Range Too Large", "Max search range is 7 days. Please try a shorter duration.")
                return "BAD"
        
        any_new_subscription = False
        rejected_dates = []
        for params in params_list:
            if not is_date_trackable(params.outbound_date):
                print(f"DEBUG: 🛑 Skipping date {params.outbound_date} (outside {MAX_SEARCH_DAYS} day limit)")
                rejected_dates.append(str(params.outbound_date))
                continue

            # NEW: Handle return trip vs one-way
            if params.inbound_date:
                print(f"DEBUG: 📧 Return trip detected: {params.outbound_date} <-> {params.inbound_date}")
                outbound_id, inbound_id, outbound_new, inbound_new = add_return_trip(
                    user_id, params.origin, params.destination, params.outbound_date, params.inbound_date
                )
                search_data = [
                    (outbound_id, outbound_new, True),  # ID, is_new, is_leg
                    (inbound_id, inbound_new, True)
                ]
                if outbound_new or inbound_new:
                    any_new_subscription = True
            else:
                print(f"DEBUG: 📝 One-way subscription: {params.outbound_date}")
                search_id, is_sub_new = add_subscription(user_id, params.origin, params.destination, params.outbound_date)
                search_data = [(search_id, is_sub_new, False)]
                if is_sub_new:
                    any_new_subscription = True

            # Process each search created/found
            for search_id, is_new, is_leg in search_data:
                search = get_search_by_id(search_id)
                if not search: continue
                
                origin_name = get_station_name(search.origin)
                dest_name = get_station_name(search.destination)

                if is_new or should_run_now(search):
                    print(f"DEBUG: 🔍 Running search {search_id} now.")
                    ms = MinimalSearch(search.origin, search.destination, search.outbound_date)
                    url, results = run_search(ms)
                    
                    if results is None:
                        print(f"DEBUG: ⚠️ Scrape failed for search {search_id}. Skipping.")
                        continue
                    
                    print(f"DEBUG: 🎫 Found {len(results)} tickets.")
                    
                    result_joined = " ".join([str(tj) for tj in results])
                    hd = hash_for_db(result_joined)
                    hash_changed = (search.last_results != hd)

                    if not results:
                        print(f"DEBUG: ❌ No results for search {search_id}. Sending no results message if email.")
                        if source == "email":
                            send_no_results_message(user_id, origin_name, dest_name)
                    elif hash_changed:
                        print(f"DEBUG: 📢 Results changed for search {search_id}. Broadcasting to all.")
                        users = get_subscribed_users(search.id)
                        for u in users:
                            send_results_to_user(u.id, results, url, origin_name, dest_name, is_return_leg=is_leg)
                    elif is_new:
                        print(f"DEBUG: 📨 Results unchanged but user {user_id} is new. Sending initial alert.")
                        send_results_to_user(user_id, results, url, origin_name, dest_name, is_return_leg=is_leg)
                    
                    update_last_run(search.id, result_joined)
        
        if rejected_dates:
            rejected_str = ", ".join(rejected_dates)
            send_message_to_user(user_id, "Search Range Limit", f"⚠️ Note: We only support tracking for dates within the next {MAX_SEARCH_DAYS} days. The following dates were skipped: {rejected_str}")

        if any_new_subscription:
            if len(params_list) > 1:
                earliest = min(p.outbound_date for p in params_list).strftime("%Y-%m-%d")
                latest = max(p.outbound_date for p in params_list).strftime("%Y-%m-%d")
                body = f"Welcome! You've been subscribed to train search notifications for the range {earliest} -> {latest}. You'll receive updates on your searches."
                send_message_to_user(user_id, "Welcome to Eurostar Bot", body)
            else:
                send_onboarded_message_to_user(user_id)
        print(f"DEBUG: ✅ process_message finished successfully for user {user_id}")
        return "OK"
    else:
        print(f"DEBUG: ❌ LLM failed to parse message for user {user_id}")
        # LLM parsing failed despite passing regex - don't increment strikes for bot confusion
        send_message_to_user(user_id, "Parsing Error", "Sorry, I couldn't quite understand your request. Please try again with a simpler format (e.g. 'London to Paris next Friday').")
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
                                
                            process_message(user_id, message_body, source="whatsapp")
    return "OK"

@bottle.route("/webhook/email", method="POST")
def email_handler():
    try:
        data = bottle.request.json
        email_address = data.get("from")
        message = data.get("body")
        subject = data.get("subject", "")
        
        print(f"DEBUG: 📧 Incoming email from {email_address} with subject: {subject}")
        logger.info(f"📧 Received email webhook from {email_address}. Processing...")
        
        # Check subject for "stop" to trigger unsubscribe
        if "stop" in subject.lower():
            logger.info(f"🛑 'stop' found in email subject from {email_address}. Treating as unsubscribe.")
            message = "stop"
            
        user = get_user_by_email(email_address)
        if user:
            user_id = user.id
        else:
            user_id = create_user_from_email(email_address)
            
        process_message(user_id, message, source="email")
        logger.info(f"✅ Webhook processing complete for {email_address}")
        return {"status": "OK"}
    except Exception as e:
        import traceback
        print(f"ERROR in email_handler: {e}")
        print(traceback.format_exc())
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
            subject, body = msg_templates.premium_upgrade()
            notify_user(user_id, subject, body)
            
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
    
    success, error = send_gmail_message(to_email, subject, body, html_body)
    
    if success:
        return {"status": "Email sent successfully"}
    else:
        return {"error": error}

app = bottle.default_app()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Eurostar Snap Tracker API & CLI")
    parser.add_argument("--msg", type=str, help="Message to process (e.g. 'London to Paris next Friday')")
    parser.add_argument("--email", type=str, help="User email for lookup/creation")
    parser.add_argument("--phone", type=str, help="User phone for lookup/creation")
    parser.add_argument("--source", type=str, default="email", help="Source of the message (default: email)")
    parser.add_argument("--server", action="store_true", help="Start the bottle server")
    
    args = parser.parse_args()

    if args.msg:
        # CLI Mode
        if not args.email and not args.phone:
            print("❌ Error: Must provide --email or --phone for CLI testing.")
            exit(1)
        
        print(f"🧪 CLI Test Mode: Processing '{args.msg}' from {args.email or args.phone} via {args.source}")
        
        if args.email:
            user = get_user_by_email(args.email)
            user_id = user.id if user else create_user_from_email(args.email)
        else:
            user = get_user_by_phone_number(args.phone)
            user_id = user.id if user else create_user_from_phone(args.phone)
            
        result = process_message(user_id, args.msg, source=args.source)
        print(f"🏁 Result: {result}")
        
    else:
        # Server Mode (Default)
        print("🚀 Starting Eurostar Snap Tracker API...")
        if not os.getenv("GEMINI_KEY"):
            print("🛑 ERROR: GEMINI_KEY not found in environment!")
        else:
            print("✅ GEMINI_KEY detected.")
        
        print("📡 Listening on http://0.0.0.0:8080...")
        bottle.run(app=app, host='0.0.0.0', port=8080, debug=True)