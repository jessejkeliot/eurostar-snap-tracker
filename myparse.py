from urllib.parse import urlencode

station_ids = {"Paris Gare du Nord": "8727100", "Amsterdam Centraal": "8400058", "Brussels": "8814001", "Lille Europe": "8722326", "Cologne Hbf":"8015458", "Rotterdam Centraal": "8400530", "London St Pancras": "7015400"}

# for the llm
# print(station_ids.keys())

def build_search_url(origin, destination, outbound_date, inbound_date= None):
    base_url = "https://snap.eurostar.com/uk-en/search"

    params = {
    "adult": 1,
    "origin": get_station_id(origin),        # London Paddington
    "destination": get_station_id(destination),   # Paris Gare du Nord
    "outbound": outbound_date, #YYYY-MM-DD
    }
    if(inbound_date):
        params["inbound"] = inbound_date
    return f"{base_url}?{urlencode(params)}"

def get_station_id(station: str) -> int | None:
    id = station_ids.get(station)
    if(id):
        return int(str(id))
    return None 

# print(build_search_url("London St Pancras", "Paris Gare du Nord", "2026-04-17"))