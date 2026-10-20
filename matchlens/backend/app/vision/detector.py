from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np


@dataclass(frozen=True)
class RobotDetection:
    track_id: str
    class_name: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float
    timestamp_seconds: float

    @property
    def center_x(self) -> float:
        return (self.x1 + self.x2) / 2

    @property
    def center_y(self) -> float:
        return (self.y1 + self.y2) / 2


class RobotDetector(Protocol):
    model_name: str
    model_version: str
    confidence_threshold: float
    configuration: str

    def detect(self, frame: np.ndarray, timestamp_seconds: float) -> list[RobotDetection]: ...


class DetectorUnavailable(Exception):
    pass


class UltralyticsRobotDetector:
    def __init__(
        self,
        weights_path: Path,
        class_names: tuple[str, ...],
        confidence_threshold: float,
        tracker: str,
    ) -> None:
        if not weights_path.is_file():
            raise DetectorUnavailable(f"Robot detector weights were not found: {weights_path}")
        if not class_names:
            raise DetectorUnavailable("Configure at least one custom robot class name.")
        if not 0 < confidence_threshold <= 1:
            raise DetectorUnavailable("Detector confidence threshold must be greater than 0 and at most 1.")
        try:
            import ultralytics
            from ultralytics import YOLO

            self._ultralytics_version = ultralytics.__version__
            self._model = YOLO(str(weights_path))
        except ImportError as error:
            raise DetectorUnavailable("Ultralytics is not installed in this environment.") from error
        except Exception as error:
            raise DetectorUnavailable(f"Could not load robot detector weights: {error}") from error

        model_names = self._model.names
        name_items = model_names.items() if isinstance(model_names, dict) else enumerate(model_names)
        self._class_ids = {
            class_id: str(class_name)
            for class_id, class_name in name_items
            if str(class_name).strip().casefold() in class_names
        }
        if not self._class_ids:
            available = ", ".join(str(value) for value in model_names.values()) if isinstance(model_names, dict) else ", ".join(model_names)
            raise DetectorUnavailable(
                f"The configured model has no requested robot classes ({', '.join(class_names)}). "
                f"Model classes: {available}"
            )

        self.model_name = weights_path.name
        self.model_version = self._ultralytics_version
        self.confidence_threshold = confidence_threshold
        self.configuration = f"classes={sorted(self._class_ids.values())}; tracker={tracker}"
        self._tracker = tracker

    def detect(self, frame: np.ndarray, timestamp_seconds: float) -> list[RobotDetection]:
        results = self._model.track(
            frame,
            persist=True,
            tracker=self._tracker,
            classes=list(self._class_ids),
            conf=self.confidence_threshold,
            verbose=False,
        )
        if not results:
            return []
        boxes = results[0].boxes
        if boxes is None or boxes.id is None:
            return []

        coordinates = boxes.xyxy.cpu().numpy()
        confidences = boxes.conf.cpu().numpy()
        class_ids = boxes.cls.cpu().numpy().astype(int)
        track_ids = boxes.id.cpu().numpy().astype(int)
        detections: list[RobotDetection] = []
        for box, confidence, class_id, track_id in zip(coordinates, confidences, class_ids, track_ids):
            class_name = self._class_ids.get(int(class_id))
            if class_name is None:
                continue
            detections.append(
                RobotDetection(
                    track_id=str(track_id),
                    class_name=class_name,
                    confidence=float(confidence),
                    x1=float(box[0]),
                    y1=float(box[1]),
                    x2=float(box[2]),
                    y2=float(box[3]),
                    timestamp_seconds=timestamp_seconds,
                )
            )
        return detections


def create_robot_detector(
    weights: str | None,
    class_names: tuple[str, ...],
    confidence_threshold: float,
    tracker: str,
) -> tuple[RobotDetector | None, str]:
    if not weights:
        return None, "No custom robot detector model configured."
    try:
        detector = UltralyticsRobotDetector(Path(weights).expanduser().resolve(), class_names, confidence_threshold, tracker)
        return detector, ""
    except DetectorUnavailable as error:
        return None, str(error)