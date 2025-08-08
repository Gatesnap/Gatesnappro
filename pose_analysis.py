# pose_analysis.py
import cv2
import numpy as np
import mediapipe as mp

mp_pose = mp.solutions.pose

def analyze_video(video_bytes):
    # Extract middle frame
    cap = cv2.VideoCapture(video_bytes)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.set(cv2.CAP_PROP_POS_FRAMES, total // 2)
    ret, frame = cap.read()
    cap.release()

    if not ret:
        return None, "Could not read frame"

    with mp_pose.Pose(static_image_mode=True) as pose:
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(image_rgb)
        if not results.pose_landmarks:
            return frame, "No body detected"

    # Joint angle calculation helper
    def angle(a, b, c):
        a, b, c = np.array(a), np.array(b), np.array(c)
        ba, bc = a - b, c - b
        cos_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
        return np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0)))

    lm = results.pose_landmarks.landmark
    # Define required points
    pts = {n: (lm[n].x, lm[n].y) for n in [
        mp_pose.PoseLandmark.LEFT_SHOULDER,
        mp_pose.PoseLandmark.LEFT_ELBOW,
        mp_pose.PoseLandmark.LEFT_HIP,
        mp_pose.PoseLandmark.LEFT_KNEE,
        mp_pose.PoseLandmark.LEFT_ANKLE,
    ]}

    angles = {
        "knee": angle(pts["LEFT_HIP"], pts["LEFT_KNEE"], pts["LEFT_ANKLE"]),
        "elbow": angle(pts["LEFT_SHOULDER"], pts["LEFT_ELBOW"], pts["LEFT_KNEE"]),  # adjust pivot
    }

    # Basic feedback
    tips = []
    if angles["knee"] > 130: tips.append("Knees too open.")
    if angles["elbow"] > 165: tips.append("Arms too straight.")

    return frame, {"angles": angles, "tips": tips}
