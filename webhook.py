import os
from datetime import datetime, timezone
from flask import Flask, request, abort
import stripe
from supabase import create_client

app = Flask(__name__)

stripe.api_key = os.environ["STRIPE_SECRET_KEY"]
endpoint_secret = os.environ["STRIPE_WEBHOOK_SECRET"]

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

def map_plan(amount_total):
    # Stripe sends in the smallest unit (pence)
    if amount_total == 999:    return "pro"    # £9.99
    if amount_total == 4999:   return "team"   # £49.99
    if amount_total == 9999:   return "coach"  # £99.99
    return None

@app.post("/stripe-webhook")
def stripe_webhook():
    payload = request.data
    sig = request.headers.get("Stripe-Signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig, endpoint_secret)
    except Exception as e:
        return str(e), 400

    if event["type"] == "checkout.session.completed":
        s = event["data"]["object"]
        email = (s.get("customer_details") or {}).get("email")
        amount = s.get("amount_total")
        plan = map_plan(amount)
        if email and plan:
            try:
                sb.table("profiles").update({
                    "plan": plan,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).eq("email", email).execute()
            except Exception as e:
                # don’t fail webhook; Stripe will retry on non-200s
                print("Supabase update error:", e)
    return "", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
