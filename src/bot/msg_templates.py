premium_message = (
    "✅ You’re now on premium\n\n"
    "You’ll get:\n"
    "⚡ Instant alerts\n"
    "∞ Unlimited usage \n\n"
    "Next deal could drop anytime so keep your eyes peeled!"
)

premium_alert = "⚡ Priority Alert:\n\n"

onboard_msg = "Welcome! You've been subscribed to train search notifications. You'll receive updates on your searches."

misunderstood_msg = "Sorry, I didn't understand your message. Please try again with a train booking request.\n\n(Tip: Reply 'STOP' at any time to cancel all active alerts)"

def free_alert(alerts_used, alerts_limit):
    return f"Free Alert ({alerts_used + 1}/{alerts_limit} used):\n\n"