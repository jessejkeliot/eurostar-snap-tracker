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
