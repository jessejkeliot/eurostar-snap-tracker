from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional

@dataclass
class User:
    id: int
    phone_number: Optional[str]
    email: Optional[str]
    is_paying: bool
    subscription_expires: Optional[date]
    created_at: datetime

@dataclass
class Search:
    id: int
    origin: int
    destination: int
    outbound_date: date
    inbound_date: Optional[date]
    created_at: datetime
    last_checked: Optional[datetime]
    last_results: Optional[str]
    
@dataclass
class MinimalSearch:
    origin: int
    destination: int
    outbound_date: date
    inbound_date: Optional[date]

@dataclass
class Subscription:
    user_id: int
    search_id: int
    created_at: datetime