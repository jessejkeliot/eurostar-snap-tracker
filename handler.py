from services import add_subscription, should_run_now
from db import get_search_by_id
from tracker import run_search
from messaging import send_results_to_user

def handler(event, context):
    user_id = extract_user(event)
    params = parse_message(event)

    search_id, is_new = add_subscription(user_id, **params)

    search = get_search_by_id(search_id)

    if is_new or should_run_now(search):
        results = run_search(search)
        send_results_to_user(user_id, results)