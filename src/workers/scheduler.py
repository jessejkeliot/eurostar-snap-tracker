from src.core.db import delete_orphaned_searches, delete_search, delete_expired_searches
from src.core.db import get_searches_due, get_subscribed_users, hash_for_db, update_last_checked, update_last_run, get_user_paired_search
from src.core.models import MinimalSearch, Search
from src.core.services import MAX_SEARCH_DAYS, SEARCH_INTERVAL, get_jittered_search_interval
import time
import random
from src.scraper.tracker import TrainJourney, run_search
from src.bot.messaging import send_results_to_user, send_both_legs_available
from src.bot.myparse import build_search_url, get_station_name
from datetime import datetime, timedelta
from src.core.log_config import get_logger

logger = get_logger(__name__)
def handler():
    # 1. Global Orphan Cleanup (Efficiency: 1 SQL query)
    orphans_count = delete_orphaned_searches()
    if orphans_count > 0:
        logger.info(f"🗑️ Cleaned up {orphans_count} orphaned search(es).")

    # 2. Global Expired Cleanup (Efficiency: 1 SQL query)
    expired_count = delete_expired_searches()
    if expired_count > 0:
        logger.info(f"📅 Cleaned up {expired_count} expired search(es).")

    # 3. Get "Due" Searches
    active_searches = get_active_searches()
    today = datetime.now().date()
    
    for search in active_searches:
        # 4. Filter to the trackable window
        if not (today <= search.outbound_date <= (today + timedelta(days=MAX_SEARCH_DAYS))):
            # Not in window? Update last_checked so it doesn't spam us every minute
            update_last_checked(search.id)
            continue
            

        url, results, results_string, has_changed = check_for_search_updates(search)
        
        if results is None:
            logger.warning(f"⚠️ Background scrape failed for search {search.id}. Skipping this cycle.")
            continue

        if has_changed:
            users = get_subscribed_users(search.id)
            origin_name = get_station_name(search.origin)
            dest_name = get_station_name(search.destination)
            
            for user in users:
                # Check if this user is also tracking the other leg of a return trip
                paired_search = get_user_paired_search(user.id, search.id)
                
                is_leg = False
                if paired_search:
                    is_leg = True
                    # If the other leg also has results, we could send a special "Both Leg" message.
                    # For now, since we only store the Hash in the DB, we pass is_return_leg=True
                    # to give the user context that this is part of their return journey.
                    if paired_search.last_results:
                        print(f"DEBUG: 🎫 Both legs available for user {user.id}! (Search {search.id} and {paired_search.id})")
                
                send_results_to_user(user.id, results, url, origin_name, dest_name, is_return_leg=is_leg)
            
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