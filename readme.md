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
