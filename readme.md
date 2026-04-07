## Architecture

WhatsApp → Webhook → Store in DB
                         ↓
                Scheduled Lambda
                         ↓
                 Scraper runs
                         ↓
                Send WhatsApp alerts

1. User sends WhatsApp message
2. Store request in DB related to their phone number
3. Scheduled job (Lambda) runs every ~15 min
4. It loops through stored requests
5. Sends alerts if conditions match

Serverless (Lambda) is ideal for periodic tasks
✅ EB (EventBridge) schedules for cron‑like triggers
✅ Store user preferences cheaply in DynamoDB or S3
✅ Use Twilio Sandbox for initial testing (free)

Zip your Lambda function with dependencies:
zip -r lambda_cleanup_postgres.zip lambda_cleanup_postgres.py
Add psycopg2:
Either use Lambda Layers for psycopg2
Or package a compiled psycopg2-binary for Linux x86_64 into your zip
Configure EventBridge:
Schedule: daily, or every X hours
Target: Lambda function

gcloud sql users set-password postgres \
--instance=INSTANCE_NAME \
--password=PASSWORD

From twilio:
{
  "From": "+123456789",
  "Body": "London to Paris 2026-05-01"
}


## Current system prompt:
Parse following text into the form { "origin": "...", "destination": "...", "outbound_date": "...", "inbound_date": "..." } Where the origin/destination can be one from ['Paris Gare du Nord', 'Amsterdam Centraal', 'Brussels', 'Lille Europe', 'Cologne Hbf', 'Rotterdam Centraal', 'London St Pancras’] and the dates must put into yyyy-mm-dd form. Also today’s date is sunday the 5th April 2026. If they don’t provide a return date don’t add an inbound date, they are just getting a single ticket. Either respond with error or with the object specified above. Don’t add any comments inside just have the plain object. Your output will be used to call a tool.

[[https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api]]

[["https://developers.facebook.com/documentation/business-messaging/whatsapp/get-started"]]
