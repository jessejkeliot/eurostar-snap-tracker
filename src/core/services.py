from src.core.db import (
    get_existing_search,
    create_search,
    create_subscription,
    create_search_pair,
    delete_search,
)
from datetime import datetime, timedelta
import random
from src.core.models import Search
from src.core.log_config import get_logger

logger = get_logger(__name__)

MAX_SEARCH_DAYS = 14
SEARCH_INTERVAL = timedelta(minutes=15)

def is_date_trackable(target_date):
    if not target_date:
        return False
    
    today = datetime.now().date()
    # Support today + up to 14 days in the future
    return today <= target_date <= (today + timedelta(days=MAX_SEARCH_DAYS))

def add_subscription(user_id, origin, destination, outbound_date):
    """Creates or gets a one-way search and subscribes the user to it."""
    search = get_existing_search(origin, destination, outbound_date)

    if not search:
        search = create_search(origin, destination, outbound_date)
    
    is_sub_new = create_subscription(user_id, search.id)
    return search.id, is_sub_new

def add_return_trip(user_id, origin, destination, outbound_date, inbound_date):
    """
    Creates two one-way searches (outbound leg + inbound leg) and links them
    in search_pairs. Subscribes the user to both.
    Returns (outbound_search_id, inbound_search_id, outbound_is_new, inbound_is_new).
    """
    # Outbound leg: origin -> destination on outbound_date
    outbound_search = get_existing_search(origin, destination, outbound_date)
    if not outbound_search:
        outbound_search = create_search(origin, destination, outbound_date)
    outbound_is_new = create_subscription(user_id, outbound_search.id)

    # Inbound leg: destination -> origin on inbound_date (reversed!)
    inbound_search = get_existing_search(destination, origin, inbound_date)
    if not inbound_search:
        inbound_search = create_search(destination, origin, inbound_date)
    inbound_is_new = create_subscription(user_id, inbound_search.id)

    # Link them
    create_search_pair(outbound_search.id, inbound_search.id)
    logger.info(f"🔗 Linked searches {outbound_search.id} (outbound) and {inbound_search.id} (inbound) as return pair for user {user_id}")

    return outbound_search.id, inbound_search.id, outbound_is_new, inbound_is_new


def get_jittered_search_interval():
    """Returns SEARCH_INTERVAL with a random jitter of ±120 seconds (2 minutes)."""
    jitter_seconds = random.randint(-120, 120)
    return SEARCH_INTERVAL + timedelta(seconds=jitter_seconds)


def should_run_now(search: Search):
    if not search or not search.last_checked:
        return True

    # Use a small random jitter (±30s) for manual search checks too
    jitter = timedelta(seconds=random.randint(-30, 30))
    next_run = search.last_checked + SEARCH_INTERVAL + jitter
    return (next_run - datetime.now()).total_seconds() < 120