from services import add_subscription, should_run_now
from db import get_search_by_id, get_user_by_phone_number
from tracker import run_search
# from messaging import send_results_to_user
import bottle

@bottle.route("/", method="POST")
def handler():
    phone_number = bottle.request.form.get("From")
    message = bottle.request.form.get("Body")
    
    user_id = get_user_by_phone_number(phone_number) # table search
    params = parse_message(message) # use gemma

    search_id, is_new = add_subscription(user_id, **params)

    search = get_search_by_id(search_id)

    if is_new or should_run_now(search):
        results = run_search(search)
        send_results_to_user(user_id, results)
    return "OK"

def parse_message(message):
    # make gemma 4 call with our system prompt
    
    
    return {"origin": "Unknown",
    "destination": "Unknown",
    "outbound_date": "Unknown",
    "inbound_date": "Unknown"}