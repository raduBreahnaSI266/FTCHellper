from collections.abc import Callable
from pathlib import Path
from typing import Any

import cv2

from app.vision.detector import RobotDetection, RobotDetector


class VideoProcessingError(Exception):
    pass


def analyze_video_file(
    path: Path,
    report_progress: Callable[[int], None] | None = None,
    detector: RobotDetector | None = None,
    detector_unavailable_message: str = "No custom robot detector model configured.",
) -> dict[str, Any]:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise VideoProcessingError("OpenCV could not open this video. The MP4 may be damaged or use an unsupported codec.")

    try:
        fps = float(capture.get(cv2.CAP_PROP_FPS))
        reported_frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if fps <= 0 or reported_frame_count <= 0 or width <= 0 or height <= 0:
            raise VideoProcessingError("Video metadata is incomplete; FPS, frame count, or resolution could not be read.")

        duration_seconds = reported_frame_count / fps
        sample_interval = max(round(fps), 1)
        sampled_frames = 0
        decoded_frames = 0
        detections: list[RobotDetection] = []
        while True:
            success, frame = capture.read()
            if not success:
                break
            if decoded_frames % sample_interval == 0:
                sampled_frames += 1
                if detector is not None:
                    detections.extend(detector.detect(frame, decoded_frames / fps))
            decoded_frames += 1
            if report_progress and decoded_frames % 120 == 0:
                progress = min(90, 5 + int(decoded_frames / reported_frame_count * 85))
                report_progress(progress)

        if decoded_frames == 0:
            raise VideoProcessingError("No decodable frames were found in this video.")

        return {
            "duration_seconds": duration_seconds,
            "fps": fps,
            "frame_count": decoded_frames,
            "width": width,
            "height": height,
            "sampled_frames": sampled_frames,
            "detector_status": "available" if detector is not None else "unavailable",
            "detector_message": "" if detector is not None else detector_unavailable_message,
            "detector_model": detector.model_name if detector is not None else "",
            "detector_version": detector.model_version if detector is not None else "",
            "detector_configuration": detector.configuration if detector is not None else "",
            "confidence_threshold": detector.confidence_threshold if detector is not None else 0.0,
            "detections": detections,
        }
    finally:
        capture.release()