from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field
from typing import List, Optional

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

class MinimalSearchModel(BaseModel): # with the names for origin and destination because my parsing will be done
    origin: str = Field(description="Origin station name")
    destination: str = Field(description="Destination station name")
    outbound_date: date = Field(description="Outbound travel date")
    end_date: Optional[date] = Field(default=None, description="End date if a range is requested")
    inbound_date: Optional[date] = Field(default=None, description="Optional inbound travel date")

@dataclass
class Subscription:
    user_id: int
    search_id: int
    created_at: datetime

@dataclass
class Trial:
    user_id: int
    alerts_used: int
    alerts_limit: int
    started_at: datetime