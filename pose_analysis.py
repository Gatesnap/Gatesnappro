# pose_analysis.py
import cv2, numpy as np, tempfile, os
import mediapipe as mp

mp_pose = mp.solutions.pose
mp_draw = mp.solutions.drawing_utils
mp_style = mp.solutions.drawing_styles

def _calc_angle(a, b, c):
    # a,b,c are (x,y)
    ab = np.array(a) - np.array(b)
    cb = np.array(c) - np.array(b)
    ang = np.degrees(
        np.arctan2(cb[1], cb[0]) - np.arctan2(ab[1], ab[0])
    )
    ang = np.abs(ang)
    return 360 - ang if ang > 180 else ang

def _angles_from_landmarks(lm, w, h):
    # Indices: https://google.github.io/mediapipe/solutions/pose#pose-landmark-model-blazepose-ghum-3d
    p = lambda i: (lm[i].x * w, lm[i].y * h)
    # Left side (swap if you prefer right)
    hip = p(23); knee = p(25); ankle = p(27)
    shoulder = p(11); elbow = p(13); wrist = p(15)

    knee_ang = _calc_angle(hip, knee, ankle)
    elbow_ang = _calc_angle(shoulder, elbow, wrist)
    # “Torso” crude proxy = shoulder-hip vs vertical
    torso_vec = np.array(hip) - np.array(shoulder)
    torso_ang = np.degrees(np.arctan2(torso_vec[0], -torso_vec[1]))  # 0 = vertical
    torso_ang = np.abs(torso_ang)

    return {
        "knee": round(knee_ang),
        "elbow": round(elbow_ang),
        "torso": round(torso_ang)
    }

def _feedback(ang):
    notes = []
    # Simple rules; tweak as you like
    notes.append(f"Torso: {ang['torso']}° " + ("(✓ Good)" if 30 <= ang['torso'] <= 55 else "⚠ Adjust"))
    notes.append(f"Hip/Knee: {ang['knee']}° " + ("(✓ Good)" if 95 <= ang['knee'] <= 115 else "⚠ Too open/closed"))
    notes.append(f"Elbow: {ang['elbow']}° " + ("(✓ Good)" if 140 <= ang['elbow'] <= 165 else "⚠ Bend/straighten"))
    tip = "Bring knees forward & soften elbows" if (ang['knee'] > 120 or ang['elbow'] > 165) else "Nice setup—hold tension and drive!"
    return notes, tip

def process_video(file_bytes: bytes, suffix: str = ".mp4"):
    # Save upload to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        f.write(file_bytes)
        in_path = f.name

    cap = cv2.VideoCapture(in_path, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        os.unlink(in_path)
        raise RuntimeError("Could not open video (codec/format unsupported).")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    w  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
    h  = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 360)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    # Temp output video with pose overlays
    out_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    out_path = out_file.name
    out = cv2.VideoWriter(out_path, fourcc, fps, (w, h))

    first_pose_frame = None
    last_pose_frame  = None
    first_angles = last_angles = None

    with mp_pose.Pose(static_image_mode=False, model_complexity=1) as pose:
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            res = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

            if res.pose_landmarks:
                # draw overlays
                mp_draw.draw_landmarks(
                    frame, res.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                    mp_style.get_default_pose_landmarks_style()
                )

                # capture first & last valid frames + angles
                if first_pose_frame is None:
                    first_pose_frame = frame.copy()
                    first_angles = _angles_from_landmarks(res.pose_landmarks.landmark, w, h)
                last_pose_frame = frame.copy()
                last_angles = _angles_from_landmarks(res.pose_landmarks.landmark, w, h)

            out.write(frame)

    cap.release()
    out.release()
    os.unlink(in_path)

    if first_pose_frame is None:
        raise RuntimeError("No rider detected. Try a clearer side view at 1080p/30fps.")

    start_notes, start_tip = _feedback(first_angles)
    end_notes,   end_tip   = _feedback(last_angles or first_angles)

    result = {
        "video_overlay_path": out_path,
        "start_frame": first_pose_frame,
        "end_frame": last_pose_frame or first_pose_frame,
        "start_angles": first_angles,
        "end_angles": last_angles or first_angles,
        "start_notes": start_notes,
        "end_notes": end_notes,
        "tip": f"{start_tip}"
    }
    return result
