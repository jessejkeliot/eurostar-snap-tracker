from db import get_searches_due, get_subscribed_users, hash_for_db, update_last_checked, update_last_run
from models import MinimalSearch, Search
from tracker import TrainJourney, run_search
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
    hd = hash_for_db(result_joined)
    # if the last results are equal to the new ones ( Both are hashed ) then just log it
    if(search.last_results != hd):
        send_to_subscribed_users(search.id, results)
        update_last_run(search.id, result_joined)   
    else:
        update_last_checked(search.id)
        print(f"On lastest run of search (id: {search.id}) the results have not changed")

    
def send_to_subscribed_users(search_id, results: list[TrainJourney]):
    users = get_subscribed_users(search_id)

    for user in users:
        send_results_to_user(user.id, results)