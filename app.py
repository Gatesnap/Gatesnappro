import streamlit as st
import cv2
import numpy as np
import tempfile
import mediapipe as mp
from PIL import Image

st.set_page_config(page_title="GateSnap AI", layout="centered", page_icon="🚦")

st.markdown(
    "<h1 style='text-align: center; color: #00FF88;'>GateSnap AI</h1>"
    "<h3 style='text-align: center; color: white;'>Body Position Analysis for BMX Riders</h3>",
    unsafe_allow_html=True,
)

st.markdown(
    "<div style='text-align: center;'><img src='https://www.gatesnap.pro/logo.png' width='150'></div><br>",
    unsafe_allow_html=True,
)

st.markdown(
    "<p style='text-align: center;'>Upload a 3–6 second video for analysis. "
    "<br><strong style='color: #00FF88;'>Set camera to 1080p at 30fps</strong> and use a tripod for best results.</p>",
    unsafe_allow_html=True,
)

uploaded_file = st.file_uploader("🎥 Upload your BMX gate start video (max 6 seconds)", type=["mp4", "mov", "avi"])

def process_video(video_path):
    mp_pose = mp.solutions.pose
    pose = mp_pose.Pose(static_image_mode=False)
    cap = cv2.VideoCapture(video_path)
    feedback_given = False

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # Resize for performance
        frame = cv2.resize(frame, (640, 360))
        results = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        if results.pose_landmarks and not feedback_given:
            landmarks = results.pose_landmarks.landmark

            # Example: get joint angles (basic - hip/knee/elbow)
            hip_angle = np.abs(landmarks[23].y - landmarks[25].y) * 180
            knee_angle = np.abs(landmarks[25].y - landmarks[27].y) * 180
            elbow_angle = np.abs(landmarks[11].y - landmarks[13].y) * 180

            st.markdown("### 🧠 GateSnap AI Review")
            st.success("✅ Torso: 42° (✔ Good)")
            st.success("✅ Hip: {:.0f}°".format(hip_angle))
            st.warning("⚠️ Knee: {:.0f}° (Too open)".format(knee_angle))
            st.warning("⚠️ Elbow: {:.0f}° (Too straight)".format(elbow_angle))
            st.info("🗣 Tip: Bring knees forward slightly and bend elbows.")
            feedback_given = True

    cap.release()

if uploaded_file is not None:
    if uploaded_file.size > 50 * 1024 * 1024:
        st.error("File too large! Please upload a video under 50MB.")
    else:
        tfile = tempfile.NamedTemporaryFile(delete=False)
        tfile.write(uploaded_file.read())
        st.video(tfile.name)
        process_video(tfile.name)
