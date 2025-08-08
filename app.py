import streamlit as st
from supabase import create_client, Client
import os

# Supabase credentials (from your environment or paste directly if testing)
SUPABASE_URL = os.environ.get("SUPABASE_URL") or "https://cdoxzmtxcfsuoviinxxd.supabase.co"
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="GateSnap AI", layout="centered")
st.markdown("<h1 style='color: white;'>GateSnap AI</h1>", unsafe_allow_html=True)

# Session State
if "user" not in st.session_state:
    st.session_state.user = None

def show_login():
    st.subheader("Login to GateSnap")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        try:
            res = supabase.auth.sign_in_with_password({"email": email, "password": password})
            st.session_state.user = res.user
            st.success("Logged in!")
            st.experimental_rerun()
        except Exception as e:
            st.error("Login failed. Check your credentials.")

def show_signup():
    st.subheader("Create Free Account")
    name = st.text_input("Your Name")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Create Account"):
        try:
            res = supabase.auth.sign_up({
                "email": email,
                "password": password,
                "options": {"data": {"name": name}}
            })
            st.success("Account created. Please log in.")
        except Exception as e:
            st.error("Signup failed: " + str(e))

def show_upload_ui():
    st.success(f"Welcome, {st.session_state.user.user_metadata.get('name', 'BMX Racer')}!")
    st.subheader("Upload your BMX gate start video")

    uploaded_file = st.file_uploader("Upload MP4/MOV (3–6 seconds)", type=["mp4", "mov"])
    if uploaded_file:
        # Placeholder analysis
        st.video(uploaded_file)
        st.success("✅ Video uploaded. Analysis coming soon.")

    if st.button("Log out"):
        st.session_state.user = None
        st.experimental_rerun()

# Page Routing
if st.session_state.user:
    show_upload_ui()
else:
    login_or_signup = st.radio("Welcome to GateSnap", ["Login", "Create Account"])
    if login_or_signup == "Login":
        show_login()
    else:
        show_signup()
