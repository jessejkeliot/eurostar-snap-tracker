# WhatsApp Bot Database Design & Conversion Logic

This document defines the core database structure and business logic for a conversion-optimised WhatsApp bot tracking Eurostar Snap tickets. It aligns the live tracking database schema with our Stripe-driven payment strategy.

---

# 🧠 Core Idea

The system is based on a simple state machine:

NEW → TRIALING → FREE_LIMITED → PAID → CHURNED

User access to alerts is controlled entirely by:
- Free trial usage limit (3 alerts)
- Subscription status (`is_paying` within the database)

---

# 📦 The Schema

Our schema isolates the heavy lifting (scraping generic routes) from the user mapping so that one search powers many users. We also use supplemental tables to log analytics.

## 1. Core Tables (Active Schema)

**Users**  
Tracks identity and premium status.
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    phone_number TEXT UNIQUE,
    email TEXT UNIQUE,
    is_paying BOOLEAN DEFAULT FALSE,
    subscription_expires DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Searches & Subscriptions**  
Tracks unique route requests and maps users to those routes.
```sql
CREATE TABLE searches (
    id SERIAL PRIMARY KEY,
    origin INTEGER NOT NULL,
    destination INTEGER NOT NULL,
    outbound_date DATE NOT NULL,
    inbound_date DATE,
    last_checked TIMESTAMP,
    last_results CHAR(64)
);

CREATE TABLE subscriptions (
    user_id INTEGER REFERENCES users(id),
    search_id INTEGER REFERENCES searches(id),
    PRIMARY KEY (user_id, search_id)
);
```

## 2. Optimization Tables (To Be Added)

To power the behavioral mechanics and funnel reporting from the conversion plan:

**Trials**  
Tracks free usage limits per user to facilitate the "Soft Paywall".
```sql
CREATE TABLE trials (
  user_id INTEGER PRIMARY KEY REFERENCES users(id),
  alerts_used INT DEFAULT 0,
  alerts_limit INT DEFAULT 3,
  started_at TIMESTAMP DEFAULT NOW()
);
```

**Events**  
Full funnel tracking and A/B test logging.
```sql
CREATE TABLE events (
  id SERIAL PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  event_type TEXT, -- joined | route_set | alert_sent | upgrade_prompt | subscribed | churned
  metadata JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);
```

---

# 🔁 BUSINESS LOGIC & CONVERSION FLOW

## 1. User State Logic

Every time we discover a route match, we assess the user before sending the broadcast:
```python
if user.is_paying:
    state = "PAID"
elif trial.alerts_used < trial.alerts_limit:
    state = "TRIALING"
else:
    state = "FREE_LIMITED"
```

## 2. Delivering the Alert

Based on the state, we adjust the delivery speed and messaging.

**PAID STATE**  
- Instant delivery.
- Unlimited routing.
- Occasional reinforcement messaging: *"You've saved £120+ already 💸"*

**TRIALING STATE**  
- Instant delivery.
- Must execute `UPDATE trials SET alerts_used = alerts_used + 1 WHERE user_id = ?`

**FREE_LIMITED STATE**  
- 5-minute delayed delivery.
- No hard block on alerts, but degraded experience.
- Appended Delay Mechanic Text: *"You’re seeing this 10 minutes later than premium users ⏱️"*

## 3. Stripe Payment Flow & Soft Paywalls

When a user exhausts their free alerts (e.g. they receive their 4th alert), we pitch the upgrade alongside the value we just gathered.

**Pricing Setup:**
- £2.49/month
- £24.99/year

**Paywall Trigger Message:**
```text
🚨 Snap ticket found:
London → Paris £42 (normally £115)

You’ve used your free alerts 👀
You’re seeing this 10 minutes later than premium users ⏱️

Upgrade for:
⚡ Instant alerts
🔁 Unlimited deals

👉 £2.49/month
[Stripe Checkout Link]
```

## 4. Post-Purchase Sync

Once a user completes the flow via the **Stripe Checkout Link**, our endpoint should receive the Stripe webhook.
1. `UPDATE users SET is_paying = TRUE, subscription_expires = {new_date} WHERE id = ?`
2. Send onboarding confirmation message back via WhatsApp/Email immediately praising the transition to instant priority alerts.
