from db import (
    get_existing_search,
    create_search,
    create_subscription,
)
from datetime import datetime, timedelta

SEARCH_INTERVAL = timedelta(minutes=10)

def add_subscription(user_id, origin, destination, outbound_date, inbound_date):
    search = get_existing_search(origin, destination, outbound_date, inbound_date)

    if not search:
        search_id = create_search(origin, destination, outbound_date, inbound_date)
        is_new = True
    else:
        search_id = search["id"]
        is_new = False

    create_subscription(user_id, search_id)

    return search_id, is_new


def should_run_now(search):
    if not search or not search.get("last_checked"):
        return True

    next_run = search["last_checked"] + SEARCH_INTERVAL
    return (next_run - datetime.utcnow()).total_seconds() > 120