from urllib.parse import urlencode

station_ids = {"Paris Gare du Nord": "8727100", "Amsterdam Centraal": "8400058", "Brussels": "8814001", "Lille Europe": "8722326", "Cologne Hbf":"8015458", "Rotterdam Centraal": "8400530", "London St Pancras": "7015400"}



def build_search_url(origin, destination, date):
    base_url = "https://snap.eurostar.com/uk-en/search"

    params = {
    "adult": 1,
    "origin": int(str(station_ids.get(origin))),        # London Paddington
    "destination": int(str(station_ids.get(destination))),   # Paris Gare du Nord
    "outbound": date,
    }
    return f"{base_url}?{urlencode(params)}"
