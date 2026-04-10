from models import MinimalSearch
from myparse import about_trains
from scheduler import search_and_send, send_to_subscribed_users
from services import add_subscription, hash_for_db, should_run_now
from db import create_user_from_phone, get_search_by_id, get_user_by_phone_number, update_last_run
from tracker import run_search
from messaging import parse_message, send_onboarded_message_to_user, send_results_to_user, send_retry_message_to_user
from hashlib import sha256
import bottle
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

@bottle.route("/webhook/whatsapp", method="POST")
def handler():
    phone_number = bottle.request.form.get("From")
    message = bottle.request.form.get("Body")
    
    user = get_user_by_phone_number(phone_number) # table search
    user_id = None
    if user:
        user_id = user.id
    else:
        user_id = create_user_from_phone(phone_number)
    train_message = about_trains(message)
    if(not train_message):
        send_retry_message_to_user(user_id)
        return "BAD"
    params = parse_message(message) # use gemma
    if (params):
        
        # TODO first should confirm with user
        
        
        search_id, is_new = add_subscription(user_id, params.origin, params.destination, params.outbound_date, params.inbound_date)

        search = get_search_by_id(search_id)

        if search and (is_new or should_run_now(search)):
            ms = MinimalSearch(search.origin, search.destination, search.outbound_date, search.inbound_date)
            # TODO need some logic here that updates the last_searched and last_result in the database but
            # Something similar to in scheduler but we should only broadcast it to other users if the last_result hash is 
            # different
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

@bottle.route("/webhook/email", method="POST")
def email_handler():
    pass

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