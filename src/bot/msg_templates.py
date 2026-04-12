def premium_upgrade():
    subject = "Welcome to Premium!"
    body = (
        "✅ You’re now on premium\n\n"
        "You’ll get:\n"
        "⚡ Instant alerts\n"
        "∞ Unlimited usage \n\n"
        "Next deal could drop anytime so keep your eyes peeled!"
    )
    return subject, body

def premium_alert():
    return None, "⚡ Priority Alert:\n\n"

def onboard_msg():
    subject = "Welcome to Eurostar Bot"
    body = "Welcome! You've been subscribed to train search notifications. You'll receive updates on your searches."
    return subject, body

def misunderstood_msg():
    subject = "Eurostar Bot - Message Not Understood"
    body = "Sorry, I didn't understand your message. Please try again with a train booking request.\n\n(Tip: Reply 'STOP' at any time to cancel all active alerts)"
    return subject, body

def unsubscribed_msg():
    subject = "Unsubscribed"
    body = "You have been safely unsubscribed from all train alerts. 🛑\n\nSend a new route whenever you want to track fares again!"
    return subject, body

def no_results_msg(origin=None, destination=None):
    if origin and destination:
        subject = f"Search Started: {origin} to {destination}"
    else:
        subject = "Eurostar Search Started"
    body = "We couldn't find any tickets for this search at the moment, but don't worry! We'll keep tracking it and let you know as soon as some become available. 🔎"
    return subject, body

def free_alert(alerts_used, alerts_limit):
    body = f"Free Alert ({alerts_used + 1}/{alerts_limit} used):\n\n"
    return None, body

def both_legs_msg(origin_name, dest_name, outbound_date, inbound_date):
    subject = f"🎉 Both legs available: {origin_name} <-> {dest_name}"
    body = (
        f"Great news! We found Snap tickets for BOTH directions of your return journey. 🎫🎫\n\n"
        f"📅 Outbound: {outbound_date}\n"
        f"📅 Inbound: {inbound_date}\n\n"
        f"Check the links below to book your deals before they're gone!"
    )
    return subject, body