from hashlib import sha256

from db import (
    get_existing_search,
    create_search,
    create_subscription,
)
from datetime import datetime, timedelta

from models import Search

SEARCH_INTERVAL = timedelta(minutes=10)

def add_subscription(user_id, origin, destination, outbound_date, inbound_date):
    search = get_existing_search(origin, destination, outbound_date, inbound_date)

    if not search:
        search = create_search(origin, destination, outbound_date, inbound_date)
        is_new = True
    else:
        is_new = False

    create_subscription(user_id, search.id)

    return search.id, is_new


def should_run_now(search: Search):
    if not search or not search.last_checked:
        return True

    next_run = search.last_checked + SEARCH_INTERVAL
    return (next_run - datetime.now()).total_seconds() < 120

def hash_for_db(to_hash: str):
    sha256_hash = sha256()
    sha256_hash.update(to_hash.encode())
    return sha256_hash.hexdigest()