import os
from datetime import datetime, timezone
from flask import Flask, request
import stripe
from supabase import create_client

app = Flask(__name__)

# Env vars (set these in Railway)
STRIPE_SECRET_KEY = os.environ["STRIPE_SECRET_KEY"]
STRIPE_WEBHOOK_SECRET = os.environ["STRIPE_WEBHOOK_SECRET"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

stripe.api_key = STRIPE_SECRET_KEY
sb = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def map_plan(amount_total, currency):
    # Stripe amounts are in minor units (e.g., GBP pence)
    if currency and currency.lower() != "gbp":
        return None
    if amount_total == 999:   return "pro"    # £9.99
    if amount_total == 4999:  return "team"   # £49.99
    if amount_total == 9999:  return "coach"  # £99.99
    return None

@app.post("/stripe-webhook")
def stripe_webhook():
    # Verify signature
    payload = request.get_data(as_text=False)
    sig_header = request.headers.get("Stripe-Signature", "")
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig_header,
            secret=STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        # Stripe will retry on non-2xx
        return str(e), 400

    if event["type"] == "checkout.session.completed":
        s = event["data"]["object"]
        email = (s.get("customer_details") or {}).get("email")
        amount = s.get("amount_total")
        currency = s.get("currency")
        plan = map_plan(amount, currency)

        if email and plan:
            try:
                sb.table("profiles").update({
                    "plan": plan,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).eq("email", email).execute()
            except Exception as e:
                print("Supabase update error:", e)  # visible in Railway logs

    return "", 200

# Local dev (Railway uses Procfile/gunicorn below)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
