from db import get_searches_due, get_subscribed_users, update_last_run
from models import MinimalSearch, Search
from tracker import run_search
from messaging import send_results_to_user

def handler():
    searches = get_searches_due()

    for search in searches:
        # create a minimal search object that only contains the data needed for constructing a search url
        search_and_send(search)
        
def search_and_send(search : Search):
    ms = MinimalSearch(search.origin, search.destination, search.outbound_date, search.inbound_date)
    url, results = run_search(ms)
    result_joined = " ".join([str(tj) for tj in results])
    
    send_to_subscribed_users(search.id, results)

    update_last_run(search.id, result_joined)
    
def send_to_subscribed_users(search_id, results):
    users = get_subscribed_users(search_id)

    for user in users:
        send_results_to_user(user, results)