import cv2
import numpy as np
from pathlib import Path

def analyze_speaker_tracking(video_path: str, start_time: float, end_time: float, sample_fps: float = 4.0):
    """
    Samples frames between start_time and end_time to track speaker face positions.
    Determines:
    1. Mode: 'single_speaker' or 'podcast_split'
    2. Smoothed horizontal crop centers over time
    3. Optimal crop window coordinates
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Could not open video {video_path}")

    video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    target_crop_w = int(video_height * 9 / 16)
    half_crop_w = target_crop_w // 2

    # Check for CascadeClassifier or FaceDetectorYN
    face_cascade = None
    if hasattr(cv2, "CascadeClassifier"):
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            face_cascade = cv2.CascadeClassifier(cascade_path)
        except Exception:
            face_cascade = None

    start_frame = int(start_time * fps)
    end_frame = int(end_time * fps)
    frame_step = max(1, int(fps / sample_fps))

    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    current_frame = start_frame

    face_centers_x = []
    speaker_left = []
    speaker_right = []

    while current_frame <= end_frame:
        ret, frame = cap.read()
        if not ret:
            break

        if face_cascade is not None:
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.1,
                    minNeighbors=5,
                    minSize=(60, 60),
                )
                if len(faces) > 0:
                    faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
                    if len(faces) >= 2:
                        f1, f2 = faces[0], faces[1]
                        c1 = f1[0] + f1[2] // 2
                        c2 = f2[0] + f2[2] // 2
                        left_c = min(c1, c2)
                        right_c = max(c1, c2)
                        if left_c < video_width * 0.45 and right_c > video_width * 0.55:
                            speaker_left.append(left_c)
                            speaker_right.append(right_c)

                    primary = faces[0]
                    cx = primary[0] + primary[2] // 2
                    face_centers_x.append(cx)
            except Exception:
                pass

        current_frame += frame_step
        cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)

    cap.release()

    # Determine podcast split screen condition
    is_podcast_split = len(speaker_left) >= 4 and len(speaker_right) >= 4

    if is_podcast_split:
        median_left = int(np.median(speaker_left))
        median_right = int(np.median(speaker_right))
        return {
            "mode": "podcast_split",
            "video_width": video_width,
            "video_height": video_height,
            "speaker_left_x": median_left,
            "speaker_right_x": median_right,
            "target_crop_w": target_crop_w,
        }

    # Single speaker mode: calculate smoothed median center
    if face_centers_x:
        median_x = int(np.median(face_centers_x))
    else:
        # Default to center of screen if no face detected
        median_x = video_width // 2

    # Clamp crop window so it doesn't exceed frame boundaries
    crop_x = max(0, min(video_width - target_crop_w, median_x - half_crop_w))

    return {
        "mode": "single_speaker",
        "video_width": video_width,
        "video_height": video_height,
        "crop_x": crop_x,
        "crop_y": 0,
        "crop_w": target_crop_w,
        "crop_h": video_height,
        "target_crop_w": target_crop_w,
    }

def get_crop_filter(tracking_info: dict, target_w: int = 1080, target_h: int = 1920) -> tuple:
    """
    Generates the FFmpeg video filter string for 9:16 vertical re-framing.
    Handles single-speaker dynamic centering and dual-speaker podcast split-screen.
    """
    mode = tracking_info.get("mode", "single_speaker")

    if mode == "podcast_split":
        crop_w = tracking_info["target_crop_w"]
        vh = tracking_info["video_height"]
        left_x = max(0, tracking_info["speaker_left_x"] - crop_w // 2)
        right_x = min(tracking_info["video_width"] - crop_w, tracking_info["speaker_right_x"] - crop_w // 2)
        
        filter_str = (
            f"[0:v]split=2[vtop_in][vbot_in];"
            f"[vtop_in]crop={crop_w}:{vh}:{left_x}:0,scale={target_w}:{target_h // 2}[top];"
            f"[vbot_in]crop={crop_w}:{vh}:{right_x}:0,scale={target_w}:{target_h // 2}[bottom];"
            f"[top][bottom]vstack=inputs=2[vcropped]"
        )
        return filter_str, "[vcropped]"

    # Single Speaker Mode
    crop_x = tracking_info["crop_x"]
    crop_y = tracking_info["crop_y"]
    crop_w = tracking_info["crop_w"]
    crop_h = tracking_info["crop_h"]

    filter_str = (
        f"[0:v]crop={crop_w}:{crop_h}:{crop_x}:{crop_y},"
        f"scale={target_w}:{target_h}:flags=lanczos[vcropped]"
    )
    return filter_str, "[vcropped]"
