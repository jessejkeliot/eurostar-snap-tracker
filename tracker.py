import argparse
import random
import requests
from bs4 import BeautifulSoup
import time
import re
from models import MinimalSearch, Search
from myparse import build_search_url

URL = "https://snap.eurostar.com/uk-en/search?adult=1&origin=7015400&destination=8727100&outbound=2026-04-08&outslot=13%3A00"
MAGIC_INPUT_CLASS = "css-1ci7kll"
MAGIC_DIV_CLASS = "css-nfbk4n"
MAGIC_OD_CLASS = "css-1hy2wyu" #class of the div that has origin and destination information
MAGIC_LABEL_CLASS = "css-1ggdddu"

# inside the label div there is a div which always has the class "nfbk4n" and an input with has
#  css-1ci7kll only when the 


# User agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_0) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
    "Mozilla/5.0 (compatible; MSIE 8.0; Windows; U; Windows NT 6.0; Trident/4.0)",
    "Mozilla/5.0 (compatible; MSIE 7.0; Windows; Windows NT 6.0; WOW64; en-US Trident/4.0)",
    "Mozilla/5.0 (Windows; U; Windows NT 6.3;; en-US) AppleWebKit/603.18 (KHTML, like Gecko) Chrome/47.0.1541.349 Safari/533.6 Edge/9.12633",
    "Mozilla/5.0 (Windows NT 10.5; x64; en-US) AppleWebKit/535.12 (KHTML, like Gecko) Chrome/51.0.1999.273 Safari/600.9 Edge/13.38678",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 8_4_5; like Mac OS X) AppleWebKit/534.24 (KHTML, like Gecko) Chrome/54.0.1507.332 Mobile Safari/536.5",
    "Mozilla/5.0 (Linux i666 x86_64) AppleWebKit/603.31 (KHTML, like Gecko) Chrome/49.0.1507.2 AppSafari/533",
    "Mozilla/5.0 (Windows; Windows NT 10.1; Win64; x64; en-US) Gecko/20100101 Firefox/58.6",
    "Mozilla/5.0 (Windows NT 6.0;; en-US) AppleWebKit/534.13 (KHTML, like Gecko) Chrome/47.0.3472.3 Safari/537",
    "Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_4_8) Gecko/20100101 Firefox/73.8",
    "Mozilla/5.0 (U; Linux x86_64; en-US) Gecko/20100101 Firefox/51.4"
]

def create_session():
    session = requests.Session()
    session.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml",
        "Connection": "keep-alive"
    })
    return session

def fetch(session, url, retries=3):
    for attempt in range(retries):
        try:
            response = session.get(url, timeout=10)

            if response.status_code == 200:
                return response.text

            elif response.status_code in (429, 403):
                print(f"Blocked (status {response.status_code}), retrying...")
            
        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")

        # exponential backoff + jitter
        sleep_time = (2 ** attempt) + random.uniform(1, 3)
        time.sleep(sleep_time)

    return None

def scrape(html, ret=False):
    soup = BeautifulSoup(html, "html.parser")
    

    # search for all the input radios with the magic class. Then just get the parent.
    # then inside the parent search for the magic div / just search for the text "leaving between"
    # once we have the magic div do some processing to put it into a nice struct
    options: list[TrainJourney] = []
    direction_sections = soup.find_all("section", {"class": MAGIC_OD_CLASS})
    print("Found direction divs:", len(direction_sections))
    if(len(direction_sections) > 0):
        train_input_elements = direction_sections[0].find_all("input", {"class": MAGIC_INPUT_CLASS}) # outbound
        for magic_input in train_input_elements: 
            parent = magic_input.parent
            if(parent):
                div = parent.find("div", {"class": MAGIC_DIV_CLASS})
                options.append(parse_departure(div))
                
        if ret and len(direction_sections) > 1:
            train_input_elements = direction_sections[1].find_all("input", {"class": MAGIC_INPUT_CLASS}) # inbound
            for magic_input in train_input_elements: 
                parent = magic_input.parent
                if(parent):
                    div = parent.find("div", {"class": MAGIC_DIV_CLASS})
                    options.append(parse_departure(div, outbound=False))
        return options
    else:
        return []
    
def parse_departure(div, outbound=True):
    # --- 1. Extract date from data-testid ---
    testid = div.get("data-testid", "")
    # format: "2026-04-09-outbound-13:00"
    date_match = re.match(r"(\d{4}-\d{2}-\d{2})", testid)
    date = date_match.group(1) if date_match else None

    # --- 2. Extract time range ---
    time_p = div.find("p", string=re.compile(r"\d{2}:\d{2}\s*-\s*\d{2}:\d{2}"))
    
    early_time, late_time = None, None
    if time_p:
        times = re.findall(r"\d{2}:\d{2}", time_p.text)
        if len(times) == 2:
            early_time, late_time = times

    # --- 3. Extract price ---
    price_container = div.find("div", attrs={"data-testid": re.compile(r"price")})
    
    price = None
    currency = None
    if price_container:
        price_text = price_container.get_text(strip=True)
        price_match = re.search(r"\d+", price_text)
        currency_match = re.search(r"[£$€]", price_text)
        if price_match:
            price = int(price_match.group())
        if currency_match:
            currency = currency_match.group()
            
    return TrainJourney(outbound, date, early_time, late_time, price, currency)
        
        
class TrainJourney:
    def __init__(self, outbound, date, early_time, late_time, price, currency) -> None:
        self.outbound = outbound
        self.date = date
        self.early_time = early_time
        self.late_time = late_time
        self.price = price
        self.currency = currency
    def __repr__(self):
        return f"{'Return ' if not self.outbound else ''}TrainDeparture(date={self.date}, early={self.early_time}, late={self.late_time}, price={self.price})"
    

def main(url = URL):
    session = create_session()
    
    html = fetch(session, url)
    returning = url.find("inbound") != -1
    if html:
        journeys = scrape(html, returning)
        print(url)
        if(len(journeys) == 0):
            print("No journeys found")
        else:
            for j in journeys:
                print(j)
        return journeys
    else:
        print("Failed to fetch page")
    emptyList : list[TrainJourney] = []
    return emptyList
    while False:
        html = fetch(session, URL)

        if html:
            scrape(html)
        else:
            print("Failed to fetch page")

        # wait ~15 min + random jitter (±5 min)
        sleep_time = 900 + random.randint(-300, 300)
        time.sleep(max(60, sleep_time))  # never less than 1 min

def run_search_from_params(origin, destination, outbound_date, inbound_date):
    """
    Convenience wrapper (useful for CLI or testing)
    """
    search = MinimalSearch(origin=origin, destination=destination, outbound_date=outbound_date, inbound_date=inbound_date)

    return run_search(search)

def run_search(search: MinimalSearch):
    """
    Main entry point used by the rest of the app.
    """
    url = build_search_url(
        search.origin, # at this point is not actually an int but whatever
        search.destination, # nor here
        search.outbound_date,
        search.inbound_date,
    )

    results = main(url=url)

    return (url,results,)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Snap Search Script")
    parser.add_argument("--origin", required=True, help="Origin Name (e.g. 'London St Pancras')")
    parser.add_argument("--destination", required=True, help="Destination Name (e.g. 'Paris Gare du Nord')")
    parser.add_argument("--outbound-date", required=True, help="Outbound date (YYYY-MM-DD)")
    parser.add_argument("--inbound-date", required=False, help="Inbound date (YYYY-MM-DD)")

    args = parser.parse_args()

    run_search_from_params(args.origin, args.destination, args.outbound_date, args.inbound_date)
    
