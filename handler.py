from models import MinimalSearch
from services import add_subscription, should_run_now
from db import create_user_from_phone, get_search_by_id, get_user_by_phone_number
from tracker import run_search
from messaging import parse_message, send_results_to_user
# from messaging import send_results_to_user
import bottle

@bottle.route("/webhook/whatsapp", method="POST")
def handler():
    phone_number = bottle.request.form.get("From")
    message = bottle.request.form.get("Body")
    
    user = get_user_by_phone_number(phone_number) # table search
    if user:
        user_id = user.id
    else:
        user_id = create_user_from_phone(phone_number)
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
            results = run_search(ms)
            send_results_to_user(user_id, results)
        return "OK"
    else:
        # TODO send a message asking for user to repeat themselves
        pass

@bottle.route("/webhook/email", method="POST")
def email_handler():
    pass