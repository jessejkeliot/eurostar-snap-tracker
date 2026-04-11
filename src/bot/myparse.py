from urllib.parse import urlencode
import re

station_ids = {"Paris Gare du Nord": "8727100", "Amsterdam Centraal": "8400058", "Brussels": "8814001", "Lille Europe": "8722326", "Cologne Hbf":"8015458", "Rotterdam Centraal": "8400530", "London St Pancras": "7015400"}
train_words = (" ".join(station_ids.keys())).lower().split(" ")
train_words.extend(["euro", "eurostar", "train", "eurostar", "railway", "railway"])

def about_trains(message: str) -> bool:
    """
    Check if a message is about trains using regex patterns with train keywords.
    Returns True if the message contains train-related keywords.
    """
    # Create a pattern from key train words
    # Use a subset of train_words to avoid overly complex regex
    key_words = ["eurostar", "train", "paris", "amsterdam", "london", "brussels", "rail", "booking", "ticket"]
    key_words.extend(train_words)
    pattern = r'\b(' + '|'.join(key_words) + r')\b'
    
    # Case-insensitive search
    match = re.search(pattern, message.lower())
    return match is not None
# for the llm
# print(station_ids.keys())

def build_search_url(origin: str | int, destination: str | int, outbound_date, inbound_date=None):
    base_url = "https://snap.eurostar.com/uk-en/search"

    params = {
        "adult": 1,
        "origin": get_station_id(origin),
        "destination": get_station_id(destination),
        "outbound": outbound_date,  # YYYY-MM-DD
    }
    if inbound_date:
        params["inbound"] = inbound_date
    return f"{base_url}?{urlencode(params)}"

def get_station_id(station: str | int) -> int | None:
    if isinstance(station, int):
        return station
    if isinstance(station, str) and station.isdigit():
        return int(station)

    id = station_ids.get(station)
    if id:
        return int(str(id))
    return None

def get_station_name(station_id: int | str) -> str | None:
    # Reverse lookup 
    target_id = str(station_id)
    for name, sid in station_ids.items():
        if sid == target_id:
            return name
    return None