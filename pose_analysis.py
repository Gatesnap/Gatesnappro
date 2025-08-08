# pose_analysis.py  — robust version
import os
import cv2
import numpy as np
import tempfile
import mediapipe as mp

mp_pose = mp.solutions.pose
mp_draw = mp.solutions.drawing_utils
mp_style = mp.solutions.drawing_styles


def _calc_angle(a, b, c):
    """Angle at b from points a-b-c (each is (x, y))."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    c = np.asarray(c, dtype=float)
    ab = a - b
    cb = c - b
    ang = np.degrees(np.arctan2(cb[1], cb[0]) - np.arctan2(ab[1], ab[0]))
    ang = abs(ang)
    return 360.0 - ang if ang > 180.0 else ang


def _angles_from_landmarks(lms, w, h):
    """Compute simple angles (knee, elbow, torso) from pose landmarks."""
    # guard: lms must be list-like of 33 landmarks
    if lms is None or len(lms) < 33:
        return None

    def P(i):
        pt = lms[i]
        return (pt.x * w, pt.y * h)

    # left side indices (swap to right if you prefer)
    hip, knee, ankle = P(23), P(25), P(27)
    shoulder, elbow, wrist = P(11), P(13), P(15)

    knee_ang = _calc_angle(hip, knee, ankle)
    elbow_ang = _calc_angle(shoulder, elbow, wrist)

    # torso: shoulder→hip vs vertical
    sv = np.array(hip) - np.array(shoulder)
    # avoid ambiguous array in condition: compute a scalar explicitly
    torso_ang = float(abs(np.degrees(np.arctan2(sv[0], -sv[1]))))

    return {
        "knee": int(round(knee_ang)),
        "elbow": int(round(elbow_ang)),
        "torso": int(round(torso_ang)),
    }


def _feedback(ang):
    """Generate readable notes and a tip."""
    if ang is None:
        return ["No pose found."], "Try a clear side view at 1080p/30fps."
    notes = []
    notes.append(f"Torso: {ang['torso']}° " + ("(✓ Good)" if 30 <= ang['torso'] <= 55 else "⚠ Adjust"))
    notes.append(f"Knee: {ang['knee']}° " + ("(✓ Good)" if 95 <= ang['knee'] <= 115 else "⚠ Too open/closed"))
    notes.append(f"Elbow: {ang['elbow']}° " + ("(✓ Good)" if 140 <= ang['elbow'] <= 165 else "⚠ Bend/straighten"))
    tip = "Bring knees forward & soften elbows" if (ang["knee"] > 120 or ang["elbow"] > 165) else "Nice setup—hold tension and drive!"
    return notes, tip


def process_video(file_bytes: bytes, suffix: str = ".mp4"):
    """Return overlay video path + start/finish frames + notes/tip."""
    # save upload
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as f:
        f.write(file_bytes)
        in_path = f.name

    cap = cv2.VideoCapture(in_path, cv2.CAP_FFMPEG)
    if not cap.isOpened():
        os.unlink(in_path)
        raise RuntimeError("Could not open video (codec/format unsupported).")

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 640)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 360)
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")

    # output overlay video
    out_tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
    out_path = out_tmp.name
    writer = cv2.VideoWriter(out_path, fourcc, fps, (w, h))

    first_frame = None
    last_frame = None
    first_angles = None
    last_angles = None

    with mp_pose.Pose(static_image_mode=False, model_complexity=1) as pose:
        while True:
            ok, frame = cap.read()
            if not ok:
                break

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            res = pose.process(rgb)

            if res.pose_landmarks is not None:
                # draw overlay
                mp_draw.draw_landmarks(
                    frame,
                    res.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS,
                    mp_style.get_default_pose_landmarks_style(),
                )

                # capture first & last with explicit checks (no array truthiness)
                if first_frame is None:
                    first_frame = frame.copy()
                    first_angles = _angles_from_landmarks(res.pose_landmarks.landmark, w, h)

                last_frame = frame.copy()
                last_angles = _angles_from_landmarks(res.pose_landmarks.landmark, w, h)

            writer.write(frame)

    cap.release()
    writer.release()
    os.unlink(in_path)

    if first_frame is None:
        # never detected a full body
        raise RuntimeError("No rider detected. Try a clearer side view, full body in frame, 1080p/30fps.")

    # build outputs
    start_notes, start_tip = _feedback(first_angles)
    end_notes, end_tip = _feedback(last_angles if last_angles is not None else first_angles)

    return {
        "video_overlay_path": out_path,
        "start_frame": first_frame,
        "end_frame": last_frame if last_frame is not None else first_frame,
        "start_angles": first_angles,
        "end_angles": last_angles if last_angles is not None else first_angles,
        "start_notes": start_notes,
        "end_notes": end_notes,
        "tip": start_tip,
    }
