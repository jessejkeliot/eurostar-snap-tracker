from db import get_searches_due, get_subscribed_users, hash_for_db, update_last_checked, update_last_run
from models import MinimalSearch, Search
from tracker import TrainJourney, run_search
from messaging import send_results_to_user
from datetime import datetime, timedelta
from log_config import get_logger

logger = get_logger(__name__)
def handler():
    active_searches = get_active_searches()
    
    for search in active_searches:
        results, results_string, has_changed = check_for_search_updates(search)
        
        if has_changed:
            users = get_subscribed_users(search.id)
            for user in users:
                send_results_to_user(user.id, results)
                
            update_last_run(search.id, results_string)
        else:
            update_last_checked(search.id)
            logger.info(f"On latest run of search (id: {search.id}) the results have not changed")

def get_active_searches() -> list[Search]:
    """Retrieves searches that are due and within the 15-day active window."""
    searches = get_searches_due()
    today = datetime.now().date()
    return [search for search in searches if (search.outbound_date - timedelta(days=15) < today)]

def check_for_search_updates(search: Search) -> tuple[list[TrainJourney], str, bool]:
    """Executes the search and checks if the results differ from the last run."""
    # create a minimal search object that only contains the data needed for constructing a search url
    ms = MinimalSearch(search.origin, search.destination, search.outbound_date, search.inbound_date)
    url, results = run_search(ms)
    
    results_string = " ".join([str(tj) for tj in results])
    hashed_results = hash_for_db(results_string)
    
    has_changed = (search.last_results != hashed_results)
    
    return results, results_string, has_changed