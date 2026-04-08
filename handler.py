from models import MinimalSearch
from services import add_subscription, should_run_now
from db import get_search_by_id, get_user_by_phone_number
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
        # perhaps create user or something, but for now
        user_id = None
    params = parse_message(message) # use gemma
    if (params):
        search_id, is_new = add_subscription(user_id, params.origin, params.destination, params.outbound_date, params.inbound_date)

        search = get_search_by_id(search_id)

        if search and (is_new or should_run_now(search)):
            ms = MinimalSearch(search.origin, search.destination, search.outbound_date, search.inbound_date)
            results = run_search(ms)
            send_results_to_user(user_id, results)
        return "OK"
    else:
        # TODO send a message asking for user to repeat themselves
        pass

@bottle.route("/webhook/email", method="POST")
def email_handler():
    email = bottle.request.form.get