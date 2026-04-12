from src.core.services import delete_expired_searches
from src.core.db import delete_search
from src.core.db import get_searches_due, get_subscribed_users, hash_for_db, update_last_checked, update_last_run
from src.core.models import MinimalSearch, Search
from src.core.services import MAX_SEARCH_DAYS, SEARCH_INTERVAL, get_jittered_search_interval
import time
import random
from src.scraper.tracker import TrainJourney, run_search
from src.bot.messaging import send_results_to_user
from src.bot.myparse import build_search_url, get_station_name
from datetime import datetime, timedelta
from src.core.log_config import get_logger

logger = get_logger(__name__)
def handler():
    active_searches = get_active_searches()
    
    today = datetime.now().date()
    # delete the searches that have gone past their outbound date
    active_searches = delete_expired_searches(active_searches)
    # Filter active searches to the 14-day window
    trackable_searches = [s for s in active_searches if today <= s.outbound_date <= (today + timedelta(days=MAX_SEARCH_DAYS))]
    
    for search in trackable_searches:
        users = get_subscribed_users(search.id)
        # clean up searches that have no subscribers
        if(len(users) == 0):
            delete_search(search.id)
            logger.info(f"Search {search.id} has no subscribers, deleting")
            continue

        url, results, results_string, has_changed = check_for_search_updates(search)
        
        if results is None:
            logger.warning(f"⚠️ Background scrape failed for search {search.id}. Skipping this cycle.")
            continue


        if has_changed:
            origin_name = get_station_name(search.origin)
            dest_name = get_station_name(search.destination)
            for user in users:
                send_results_to_user(user.id, results, url, origin_name, dest_name)
            
            update_last_run(search.id, results_string)
        else:
            update_last_checked(search.id)
            logger.info(f"On latest run of search (id: {search.id}) the results have not changed")
        
        # Add random jitter between searches (2-5 seconds) to avoid firewall detection
        sleep_duration = random.uniform(2, 5)
        logger.info(f"Sleeping for {sleep_duration:.2f}s before next search...")
        time.sleep(sleep_duration)

def get_active_searches() -> list[Search]:
    # Use jittered interval for database lookup
    interval_seconds = get_jittered_search_interval().total_seconds()
    return get_searches_due(interval_seconds)

def check_for_search_updates(search: Search) -> tuple[str, list[TrainJourney], str, bool]:
    """Executes the search and checks if the results differ from the last run."""
    # create a minimal search object that only contains the data needed for constructing a search url
    ms = MinimalSearch(search.origin, search.destination, search.outbound_date, search.inbound_date)
    url, results = run_search(ms)
    
    # Use str(tj) for consistent database hashing
    results_string = " ".join([str(tj) for tj in results])
    hashed_results = hash_for_db(results_string)
    
    has_changed = (search.last_results != hashed_results)
    
    return url, results, results_string, has_changed