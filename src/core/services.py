from src.core.db import (
    get_existing_search,
    create_search,
    create_subscription,
)
from datetime import datetime, timedelta
import random
from src.core.models import Search

MAX_SEARCH_DAYS = 14
SEARCH_INTERVAL = timedelta(minutes=15)

def is_date_trackable(target_date):
    if not target_date:
        return False
    
    today = datetime.now().date()
    # Support today + up to 14 days in the future
    return today <= target_date <= (today + timedelta(days=MAX_SEARCH_DAYS))

def add_subscription(user_id, origin, destination, outbound_date, inbound_date):
    search = get_existing_search(origin, destination, outbound_date, inbound_date)

    if not search:
        search = create_search(origin, destination, outbound_date, inbound_date)
    
    is_sub_new = create_subscription(user_id, search.id)
    return search.id, is_sub_new


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
