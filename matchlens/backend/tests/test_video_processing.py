import cv2
import numpy as np

from app.vision.detector import RobotDetection, create_robot_detector
from app.vision.processor import VideoProcessingError, analyze_video_file


def test_analyze_video_file_measures_metadata_and_samples_frames(tmp_path) -> None:
    video_path = tmp_path / "tiny.avi"
    writer = cv2.VideoWriter(
        str(video_path),
        cv2.VideoWriter_fourcc(*"MJPG"),
        10.0,
        (64, 48),
    )
    assert writer.isOpened()
    for frame_index in range(20):
        frame = np.full((48, 64, 3), frame_index, dtype=np.uint8)
        writer.write(frame)
    writer.release()

    progress: list[int] = []
    result = analyze_video_file(video_path, progress.append)

    assert result["duration_seconds"] == 2.0
    assert result["fps"] == 10.0
    assert result["frame_count"] == 20
    assert result["width"] == 64
    assert result["height"] == 48
    assert result["sampled_frames"] == 2
    assert result["detector_status"] == "unavailable"
    assert progress == []


def test_analyze_video_file_reports_unreadable_video(tmp_path) -> None:
    video_path = tmp_path / "broken.mp4"
    video_path.write_bytes(b"not a video")

    try:
        analyze_video_file(video_path)
    except VideoProcessingError as error:
        assert "could not open" in str(error).lower()
    else:
        raise AssertionError("Unreadable video should raise VideoProcessingError")


def test_analyze_video_file_calls_detector_only_on_sampled_frames(tmp_path) -> None:
    video_path = tmp_path / "tiny.avi"
    writer = cv2.VideoWriter(str(video_path), cv2.VideoWriter_fourcc(*"MJPG"), 10.0, (64, 48))
    assert writer.isOpened()
    for frame_index in range(20):
        writer.write(np.full((48, 64, 3), frame_index, dtype=np.uint8))
    writer.release()

    class FakeDetector:
        model_name = "fixture-robot.pt"
        model_version = "unit-test"
        confidence_threshold = 0.35
        configuration = "classes=['robot']; tracker=bytetrack.yaml"

        def __init__(self):
            self.timestamps: list[float] = []

        def detect(self, frame, timestamp_seconds):
            self.timestamps.append(timestamp_seconds)
            return [RobotDetection("1", "robot", 0.9, 4, 5, 24, 25, timestamp_seconds)]

    detector = FakeDetector()
    result = analyze_video_file(video_path, detector=detector)

    assert result["detector_status"] == "available"
    assert result["detector_model"] == "fixture-robot.pt"
    assert result["sampled_frames"] == 2
    assert detector.timestamps == [0.0, 1.0]
    assert len(result["detections"]) == 2
    assert result["detections"][1].timestamp_seconds == 1.0


def test_detector_factory_does_not_download_unconfigured_weights(tmp_path) -> None:
    detector, message = create_robot_detector(
        str(tmp_path / "not-downloaded.pt"),
        ("robot",),
        0.35,
        "bytetrack.yaml",
    )

    assert detector is None
    assert "were not found" in message


def test_detector_factory_reports_unavailable_without_configured_model() -> None:
    detector, message = create_robot_detector(None, ("robot",), 0.35, "bytetrack.yaml")

    assert detector is None
    assert "No custom robot detector model configured" in message