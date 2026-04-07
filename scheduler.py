from db import get_searches_due, get_subscribed_users, update_last_run
from models import MinimalSearch
from tracker import run_search
from messaging import send_results_to_user

def handler():
    searches = get_searches_due()

    for search in searches:
        # create a minimal search object that only contains the data needed for constructing a search url
        ms = MinimalSearch(search.origin, search.destination, search.outbound_date, search.inbound_date)
        results = run_search(ms)

        users = get_subscribed_users(search.id)

        for user in users:
            send_results_to_user(user, results)

        update_last_run(search.id)