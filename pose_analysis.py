import tempfile
import os
import cv2
import numpy as np
import mediapipe as mp

mp_pose = mp.solutions.pose

def analyze_video(file_bytes: bytes, suffix: str = ".mp4"):
    # 1. Save uploaded bytes to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        tmp_file.write(file_bytes)
        tmp_path = tmp_file.name

    # 2. Use VideoCapture to open the temp file (with FFMPEG backend)
    cap = cv2.VideoCapture(tmp_path, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        os.unlink(tmp_path)
        raise RuntimeError("Could not open video file.")

    # 3. Jump to the middle frame of the video (for analysis)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames > 0:
        cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames // 2)

    success, frame = cap.read()
    if not success:
        cap.release()
        os.unlink(tmp_path)
        raise RuntimeError("Could not read frame from video.")

    # 4. Run pose estimation on that frame
    with mp_pose.Pose(static_image_mode=True) as pose:
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = pose.process(image_rgb)

        if not results.pose_landmarks:
            cap.release()
            os.unlink(tmp_path)
            raise RuntimeError("No pose detected.")

        # Draw the pose landmarks on the frame (optional)
        annotated_frame = frame.copy()
        mp.solutions.drawing_utils.draw_landmarks(
            annotated_frame,
            results.pose_landmarks,
            mp_pose.POSE_CONNECTIONS
        )

    cap.release()
    os.unlink(tmp_path)

    # Return the frame with pose and dummy angle feedback
    feedback = {
        "landmarks_detected": True,
        "tip": "Keep back straight and knees slightly bent at gate."
    }

    return annotated_frame, feedback

    if angles["elbow"] > 165: tips.append("Arms too straight.")

    return frame, {"angles": angles, "tips": tips}
