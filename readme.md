## Architecture
### Three Components

Email Poller 🔄 (every 45 seconds)
HTTP Bottle Endpoint 🔄 
Scrape Scheduler 🔄 (every 60 seconds)


### Email Poller

Found in email_poller.py . It polls the gmail smtp server for new emails. Should filter to only ones with subject "train" or "stop" ( to unsub ) then sends the body of the messages to the bottle endpoint.

### HTTP Bottle Endpoint

Found in handler.py . Is running continuously. It uses an llm call on a gemma model to parse the user's message into valid JSON form
It sends and recieves messages from the user. It is the interface.

### Scrape Scheduler

Found in scheduler.py, it gets the searches that are due for running and iterates through them and calls the tracking on them.
It then finds the subscribed users to that search and sends an http request to the Bottle endpoint to send a message.

Should have it where tickets for a longer period away are checked less often. Ranging from every 22 mins to every 12

### How to run (subject to change)
Must set up a .env file. Use the .env.sample file and fill in with your own api keys and database information.
If you are running on macos you must make a python virtual environment and then activate it in the terminal with

``` source ~/venv/bin/activate ```

Then install the requirements with

``` pip3 install -r requirements.txt ```

If first time running run
``` PYTHONPATH=. python3 src/core/init_db.py ```

Then in three separate terminal tabs or windows:
1. Start up the bottle API endpoint in **handler.py** using gunicorn by running:
``` PYTHONPATH=. gunicorn -w 2 -b 0.0.0.0:8080 src.api.handler:app ```
2. Start up the faux-cron python script in **pycron.py** by running:
``` PYTHONPATH=. python3 -m src.workers.pycron ```
3. Start up the email poller in **email_poller.py** by running:
``` PYTHONPATH=. python3 -m src.workers.email_poller ```

### How to Run on Linux (Google Cloud e2-micro / Ubuntu)

For production environments, you should run the services via `systemd` so they automatically restart if the machine reboots or the processes crash. We've included a script in `scripts/` to do this automatically.

Once you have cloned the project on your server and activated the virtual environment:
1. Run the deployment script with sudo:
``` sudo bash scripts/install_services_linux.sh ```
2. The script will dynamically generate `.service` wrappers and boot Gunicorn + Pycron + the Email Poller instantly into the background.

To check up on the running logs, you can use built-in journalctl commands:
- `sudo journalctl -u whatsnap-api -f`
- `sudo journalctl -u whatsnap-cron -f`
- `sudo journalctl -u whatsnap-poller -f`

**Managing the Services:**
- Stop all services: `sudo systemctl stop whatsnap-api whatsnap-cron whatsnap-poller`
- Restart (e.g. after pulling code updates): `sudo systemctl restart whatsnap-api whatsnap-cron whatsnap-poller`
- Disable them completely: `sudo systemctl disable whatsnap-api whatsnap-cron whatsnap-poller`

**Viewing the Application Logs:**
All python microservices are hooked up to a centralized logging system. You can view errors, Gemma outputs, and WhatsApp hook metrics by running:
``` tail -f bot.log ```

### Database CLI Management

You can manage the database directly using the `src/core/db.py` CLI tool.

**Basic Usage:**
```bash
PYTHONPATH=. python3 src/core/db.py --help
```

**Common Tasks:**

*   **Add a User:**
    ```bash
    PYTHONPATH=. python3 src/core/db.py --add-user --email james@hotmail.com
    # OR
    PYTHONPATH=. python3 src/core/db.py --add-user --phone +447123456789
    ```
    *The user ID will be printed to the console.*

*   **Elevate User to Premium:**
    ```bash
    PYTHONPATH=. python3 src/core/db.py --elevate-user --email james@hotmail.com
    ```

*   **Delete a User:**
    ```bash
    PYTHONPATH=. python3 src/core/db.py --delete-user --email james@hotmail.com
    ```

*   **Add a Search Route:**
    ```bash
    PYTHONPATH=. python3 src/core/db.py --add-search --origin "London St Pancras" --destination "Paris Gare du Nord" --outbound-date "2026-04-23"
    ```
    *The search ID will be printed to the console.*

*   **Create a Subscription (Link User to Search):**
    ```bash
    PYTHONPATH=. python3 src/core/db.py --add-subscription --user-id 1 --search-id 2
    ```



## Google Cloud

Using gcloud e2 micro vm

```gcloud compute instances describe whatsnap-bot-vm```

connect
```gcloud compute ssh whatsnap-bot-vm ```

From twilio:
{
  "From": "+123456789",
  "Body": "London to Paris 2026-05-01"
}


## Current system prompt:
Parse following text into the form { "origin": "...", "destination": "...", "outbound_date": "...", "inbound_date": "..." } Where the origin/destination can be one from ['Paris Gare du Nord', 'Amsterdam Centraal', 'Brussels', 'Lille Europe', 'Cologne Hbf', 'Rotterdam Centraal', 'London St Pancras’] and the dates must put into yyyy-mm-dd form. Also today’s date is sunday the 5th April 2026. If they don’t provide a return date don’t add an inbound date, they are just getting a single ticket. Either respond with error or with the object specified above. Don’t add any comments inside just have the plain object. Your output will be used to call a tool.

## distilled prompt

Extract train trip details into JSON with fields: origin, destination, outbound_date, inbound_date.

Origin/destination must be one of: Paris Gare du Nord, Amsterdam Centraal, Brussels, Lille Europe, Cologne Hbf, Rotterdam Centraal, London St Pancras.
Dates must be formatted as yyyy-mm-dd.
Assume today is 2026-04-05.
If no return date is given, omit inbound_date.

[["https://ai.google.dev/gemini-api/docs/structured-output?example=recipe"]]

[[https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api]]

[["https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started"]]

[["https://docs.cloud.google.com/compute/docs/ip-addresses/configure-static-external-ip-address"]]

## Command Line Interface

Call tracker.py with parameters. Example

``` PYTHONPATH=. python3 -m src.scraper.tracker --origin "London St Pancras" --destination "Amsterdam Centraal" --outbound_date "2026-04-08" ```

## DB

If we change the tables for now just drop like

``` DROP DATABASE whatsnap_bot_db; ```

Then set role again
``` ALTER DATABASE whatsnap_bot_db OWNER TO whatsnap;```
```GRANT ALL PRIVILEGES ON DATABASE whatsnap_bot_db TO whatsnap;```

Creating a user:
```CREATE USER whatsnap WITH PASSWORD 'xxxx';```

logging in on vm:

to super user
```sudo -u postgres psql ```
to the whatsnap db
```psql -U whatsnap -h localhost -d whatsnap_bot_db```


Eventually should use Alembic
[["https://alembic.sqlalchemy.org/en/latest/"]]