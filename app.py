# --- GateSnap AI (drop-in app.py) ---
import os
import streamlit as st
from supabase import create_client

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

if uploaded:
    import tempfile, cv2
    # save to temp file so OpenCV can read it
    suffix = os.path.splitext(uploaded.name)[1] or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.read())
        path = tmp.name

    st.video(path)

    # Try to run your analysis if pose_analysis.py exists
    try:
        from pose_analysis import analyze_video
        try:
            frame, feedback = analyze_video(open(path, "rb").read(), suffix=suffix)
            st.image(frame, channels="BGR", caption="Analysis frame")
            tip = feedback.get("tip", "Analysis complete.")
            st.info(f"💡 Tip: {tip}")
        except Exception as e:
            st.error(f"Analysis error: {e}")
    except ImportError:
        st.warning("Analysis module not found yet. Upload works — we’ll wire analysis next.")

st.divider()
if st.button("Log out"):
    do_logout()
