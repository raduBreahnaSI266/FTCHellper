from pathlib import Path
import uuid

import cv2

from app.vision.detector import RobotDetection


class SeededTrackingError(Exception):
    pass


def track_seeded_robot(
    path: Path,
    timestamp_seconds: float,
    box_normalized: tuple[float, float, float, float],
    class_name: str = "robot",
) -> tuple[list[RobotDetection], int, int, str]:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise SeededTrackingError("OpenCV could not open this video.")

    track_id = f"seed-{uuid.uuid4().hex[:12]}"
    detections: list[RobotDetection] = []
    try:
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if fps <= 0 or frame_count <= 0 or width <= 0 or height <= 0:
            raise SeededTrackingError("Video metadata is incomplete; the robot cannot be tracked.")

        seed_frame_index = min(int(timestamp_seconds * fps), frame_count - 1)
        capture.set(cv2.CAP_PROP_POS_FRAMES, seed_frame_index)
        success, frame = capture.read()
        if not success:
            raise SeededTrackingError("Could not read the selected seed frame.")

        x1, y1, x2, y2 = box_normalized
        box = (
            round(x1 * width),
            round(y1 * height),
            max(round((x2 - x1) * width), 1),
            max(round((y2 - y1) * height), 1),
        )
        tracker = cv2.TrackerMIL_create()
        try:
            tracker.init(frame, box)
        except cv2.error as error:
            raise SeededTrackingError("OpenCV could not initialize tracking from this box.")

        detections.append(
            RobotDetection(track_id, class_name, 0.0, x1 * width, y1 * height, x2 * width, y2 * height, seed_frame_index / fps)
        )

        sample_step = max(round(fps / 5), 1)
        frame_index = seed_frame_index
        next_sample = seed_frame_index + sample_step
        while frame_index < frame_count - 1:
            success, frame = capture.read()
            if not success:
                break
            frame_index += 1
            if frame_index < next_sample:
                continue

            tracked, tracked_box = tracker.update(frame)
            next_sample = frame_index + sample_step
            if not tracked:
                break

            left, top, box_width, box_height = tracked_box
            right = left + box_width
            bottom = top + box_height
            left = min(max(float(left), 0.0), float(width))
            top = min(max(float(top), 0.0), float(height))
            right = min(max(float(right), left), float(width))
            bottom = min(max(float(bottom), top), float(height))
            if right <= left or bottom <= top:
                break
            detections.append(
                RobotDetection(track_id, class_name, 0.0, left, top, right, bottom, frame_index / fps)
            )

        return detections, width, height, track_id
    finally:
        capture.release()