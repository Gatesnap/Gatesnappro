# --- GateSnap AI (drop-in app.py) ---
import os
import streamlit as st
from supabase import create_client

from datetime import datetime, timedelta, timezone
import streamlit as st

PLAN_LIMITS = {"free": 1, "pro": 3, "team": 15, "coach": 50}

def _today_bounds_utc():
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start.isoformat(), end.isoformat()

def get_or_create_profile(user_id):
    # read
    res = sb.table("profiles").select("*").eq("user_id", user_id).maybe_single().execute()
    if res.data:
        return res.data
    # create (default free)
    newp = {"user_id": user_id, "plan": "free"}
    sb.table("profiles").insert(newp).execute()
    return newp

def get_plan_limit(user_id):
    prof = get_or_create_profile(user_id)
    plan = (prof or {}).get("plan", "free").lower()
    return PLAN_LIMITS.get(plan, 1), plan

def analyses_today_count(user_id):
    start, end = _today_bounds_utc()
    res = sb.table("analyses")\
            .select("id", count="exact")\
            .eq("user_id", user_id)\
            .gte("created_at", start)\
            .lt("created_at", end)\
            .execute()
    return res.count or 0

def record_analysis(user_id):
    sb.table("analyses").insert({"user_id": user_id}).execute()

def upgrade_panel():
    st.error("You’ve used your free analysis for today.")
    st.markdown("**Upgrade for more daily analyses:**")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.link_button("Go Pro (3/day) £9.99/yr",
                       "https://buy.stripe.com/eVqeVdamUgkQ7Isgd19EI00")
    with col2:
        st.link_button("Team (15/day) £49.99/yr",
                       "https://buy.stripe.com/cNi4gzfHe1pW5AkaSH9EI01")
    with col3:
        st.link_button("Coach (50/day) £99.99/yr",
                       "https://buy.stripe.com/4gM14n52A3y47Is8Kz9EI02")


# ⛳ Supabase (make sure these are set in Railway Variables)
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://cdoxzmtxcfsuoviinxxd.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="GateSnap AI", page_icon="🚦", layout="centered")

# Session
st.session_state.setdefault("user", None)

# -------- Auth helpers --------
def do_signup(name, email, password):
    return sb.auth.sign_up({
        "email": email,
        "password": password,
        "options": {"data": {"name": name}}
    })

def do_login(email, password):
    return sb.auth.sign_in_with_password({"email": email, "password": password})

def do_logout():
    sb.auth.sign_out()
    st.session_state["user"] = None
    st.rerun()

# -------- UI --------
st.markdown("<h1 style='color:#00ff88;'>GateSnap AI</h1>", unsafe_allow_html=True)
st.caption("Body Position Analysis for BMX Riders")

# ---- Auth block (always on top) ----
if st.session_state["user"] is None:
    st.markdown("### Create a Free Account / Log in")

    tab_signup, tab_login = st.tabs(["Create account", "Log in"])

    with tab_signup:
        name = st.text_input("Full name", key="su_name")
        email_su = st.text_input("Email", key="su_email")
        pw_su = st.text_input("Password", type="password", key="su_pw")
        if st.button("Create my free account"):
            if not (name and email_su and pw_su):
                st.warning("Please fill all fields.")
            else:
                try:
                    do_signup(name, email_su, pw_su)
                    st.success("Account created. Now log in →")
                except Exception as e:
                    st.error(f"Signup failed: {e}")

    with tab_login:
        email_li = st.text_input("Email", key="li_email")
        pw_li = st.text_input("Password", type="password", key="li_pw")
        if st.button("Log in"):
            try:
                res = do_login(email_li, pw_li)
                st.session_state["user"] = res.user
                st.success("Logged in ✅")
                st.rerun()
            except Exception:
                st.error("Log in failed. Check your email & password.")

    st.stop()  # don’t show upload until logged in

# ---- Logged in: show uploader ----
u = st.session_state["user"]
name = (getattr(u, "user_metadata", None) or {}).get("name") or getattr(u, "email", "Rider")
st.success(f"Welcome, {name}!")

st.markdown("### 📤 Upload Your Gate Start Video")
st.markdown(
"""
✅ Set your phone to **1080p at 30fps**  
✅ Crop your video to **2–6 seconds**  
✅ Film from the **side**, full body in frame  
⚠️ Videos **>6s** or **<2s** will be rejected
"""
)

uploaded = st.file_uploader("Drag a 3–6s MP4/MOV here", type=["mp4","mov","m4v","mpeg","mpeg4","mpg"])

from pose_analysis import process_video

if uploaded:
    import tempfile, os
    data = uploaded.read()
    suffix = os.path.splitext(uploaded.name)[1] or ".mp4"

    with st.spinner("Analyzing…"):
        try:
            res = process_video(data, suffix=suffix)
        except Exception as e:
            st.error(f"Analysis error: {e}")
        else:
            # 1) Replay with pose overlay
            st.markdown("### ▶️ Gate Replay (with pose)")
            st.video(res["video_overlay_path"])

            # 2) Key frames + notes
            st.markdown("### 📸 Key Frames")
            c1, c2 = st.columns(2)
            with c1:
                st.image(res["start_frame"], channels="BGR", caption="Start / Pre-Load")
                st.write("• " + "\n• ".join(res["start_notes"]))
            with c2:
                st.image(res["end_frame"], channels="BGR", caption="Release")
                st.write("• " + "\n• ".join(res["end_notes"]))

            # 3) Summary tip
            st.info(f"💡 Tip: {res['tip']}")

            # Optional: let rider download the analyzed video
            with open(res["video_overlay_path"], "rb") as f:
                st.download_button("Download analyzed video", f, file_name="gatesnap_analysis.mp4")
