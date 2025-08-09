# --- GateSnap AI: app.py ---
import os
import streamlit as st
from supabase import create_client
from datetime import datetime, timedelta, timezone

# ========= Page style =========
st.set_page_config(page_title="GateSnap AI", page_icon="🚦", layout="centered")

st.markdown(
    """
    <style>
        body {
            background-color: black;
            color: white;
        }
        .stButton button {
            background-color: #00ff88;
            color: black;
            font-weight: bold;
        }
        .stTextInput > div > div > input {
            color: black;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# ========= Supabase client =========
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

# Keep token across reruns so RLS works for table reads/writes
st.session_state.setdefault("access_token", None)
st.session_state.setdefault("user", None)
if st.session_state.get("access_token"):
    sb.postgrest.auth(st.session_state["access_token"])

# ========= Daily limit + profile helpers =========
PLAN_LIMITS = {"free": 1, "pro": 3, "team": 15, "coach": 50}

def _today_bounds_utc():
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=1)
    return start.isoformat(), end.isoformat()

def _safe_single(res):
    try:
        d = getattr(res, "data", None)
        if isinstance(d, list):
            return d[0] if d else None
        if isinstance(d, dict):
            return d
    except Exception:
        pass
    return None

def get_or_create_profile(user_id, display_name=None):
    """Ensure a profiles row exists; keep email fresh if we have it."""
    user_email = getattr(st.session_state.get("user"), "email", None)

    # Try read
    try:
        res = sb.table("profiles").select("*").eq("user_id", user_id).limit(1).execute()
        row = _safe_single(res)
        if row:
            # keep email up to date if it changed/was missing
            if user_email and row.get("email") != user_email:
                try:
                    sb.table("profiles").update({"email": user_email}).eq("user_id", user_id).execute()
                except Exception:
                    pass
            return row
    except Exception:
        pass

    # Create default
    payload = {"user_id": user_id, "plan": "free"}
    if display_name:
        payload["name"] = display_name
    if user_email:
        payload["email"] = user_email
    try:
        ins = sb.table("profiles").insert(payload).execute()
        return _safe_single(ins) or payload
    except Exception:
        return payload

def get_plan_limit(user_id, display_name=None):
    prof = get_or_create_profile(user_id, display_name)
    plan = (prof or {}).get("plan", "free")
    if not isinstance(plan, str):
        plan = "free"
    plan = plan.lower()
    return PLAN_LIMITS.get(plan, 1), plan

def analyses_today_count(user_id):
    start, end = _today_bounds_utc()
    try:
        res = (
            sb.table("analyses")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .gte("created_at", start)
            .lt("created_at", end)
            .execute()
        )
        return (getattr(res, "count", 0) or 0)
    except Exception:
        return 0

def record_analysis(user_id):
    try:
        sb.table("analyses").insert({"user_id": user_id}).execute()
    except Exception:
        pass  # never crash UI

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

# ========= Simple text logo =========
st.markdown(
    """
    <h1 style='text-align:center; color:white; font-weight:bold; font-size:48px;'>
        GATESNAP
    </h1>
    """,
    unsafe_allow_html=True
)
st.caption("Body Position Analysis for BMX Riders")

# ========= Auth helpers =========
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
    st.session_state["access_token"] = None
    st.rerun()

# ========= Auth block (top) =========
if st.session_state["user"] is None:
    st.markdown("### Create a Free Account / Log in")
    tab_signup, tab_login = st.tabs(["Create account", "Log in"])

    with tab_signup:
        name = st.text_input("Full name", key="su_name")
        email_su = st.text_input("Email", key="su_email")
        pw_su = st.text_input("Password", type="password", key="su_pw")
        if st.button("Create my free account", key="btn_signup"):
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
        if st.button("Log in", key="btn_login"):
            try:
                res = do_login(email_li, pw_li)
                st.session_state["user"] = res.user
                sess = getattr(res, "session", None)
                st.session_state["access_token"] = getattr(sess, "access_token", None)
                if st.session_state.get("access_token"):
                    sb.postgrest.auth(st.session_state["access_token"])
                display_name = (getattr(res.user, "user_metadata", None) or {}).get("name") \
                               or getattr(res.user, "email", None)
                get_or_create_profile(res.user.id, display_name)
                st.success("Logged in ✅")
                st.rerun()
            except Exception:
                st.error("Log in failed. Check your email & password.")

    st.stop()

# ========= Logged in UI =========
u = st.session_state["user"]
display_name = (getattr(u, "user_metadata", None) or {}).get("name") or getattr(u, "email", "Rider")
st.success(f"Welcome, {display_name}!")

# Daily limit gate
uid = u.id
limit, plan = get_plan_limit(uid, display_name)
used = analyses_today_count(uid)

st.caption(f"Plan: **{plan.capitalize()}** • Today’s analyses: **{used}/{limit}**")
if used >= limit:
    upgrade_panel()
    st.stop()

st.markdown("### 📤 Upload Your Gate Start Video")
st.markdown(
    """
✅ Set your phone to **1080p at 30fps**  
✅ Crop your video to **2–6 seconds**  
✅ Film from the **side**, full body in frame  
⚠️ Videos **>6s** or **<2s** will be rejected
"""
)

uploaded = st.file_uploader(
    "Drag a 3–6s MP4/MOV here",
    type=["mp4", "mov", "m4v", "mpeg", "mpeg4", "mpg"],
)

from pose_analysis import process_video

if uploaded:
    data = uploaded.read()
    suffix = os.path.splitext(uploaded.name)[1] or ".mp4"

    with st.spinner("Analyzing…"):
        try:
            res = process_video(data, suffix=suffix)
        except Exception as e:
            st.error(f"Analysis error: {e}")
        else:
            record_analysis(uid)
            st.markdown("### ▶️ Gate Replay (with pose)")
            st.video(res["video_overlay_path"])
            st.markdown("### 📸 Key Frames")
            c1, c2 = st.columns(2)
            with c1:
                st.image(res["start_frame"], channels="BGR", caption="Start / Pre-Load")
                st.write("• " + "\n• ".join(res["start_notes"]))
            with c2:
                st.image(res["end_frame"], channels="BGR", caption="Release")
                st.write("• " + "\n• ".join(res["end_notes"]))
            st.info(f"💡 Tip: {res['tip']}")
            from uuid import uuid4
            with open(res["video_overlay_path"], "rb") as f:
                st.download_button(
                    "Download analyzed video",
                    f,
                    file_name="gatesnap_analysis.mp4",
                    key=f"dl-{uuid4()}",
                )

st.divider()
st.button("Log out", on_click=do_logout)
