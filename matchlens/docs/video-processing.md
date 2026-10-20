# Video processing and robot detector

## Current analysis behavior

The API decodes the uploaded video incrementally with OpenCV. It measures FPS, dimensions, decoded frame count, and duration, and passes approximately one frame per second to the optional detector. The full video is not loaded into memory. Results are persisted with an analysis status and progress. Unsupported codecs, incomplete metadata, and unreadable videos produce a failed status and a useful message.

Without a configured model, the result records `detector_status=unavailable` and explains why. It does not create tracks. Metadata extraction and manual event annotation remain available.

## Detector interface

`app.vision.detector.RobotDetector` is the replaceable detector boundary. The current optional adapter uses Ultralytics YOLO tracking with ByteTrack and requires:

- A local custom-trained `.pt` model path in `ROBOT_DETECTOR_MODEL`.
- One or more exact class labels in `ROBOT_DETECTOR_CLASSES` that exist in that model's class map. Defaults: `robot,ftc robot`.
- A confidence threshold from 0 to 1 in `ROBOT_DETECTOR_CONFIDENCE`. Default: `0.35`.
- A tracker configuration in `ROBOT_DETECTOR_TRACKER`. Default: `bytetrack.yaml`.

Install the optional Python packages from `backend/requirements-vision.txt`. Weights are not bundled or downloaded. Do not point the detector at generic pretrained weights and assume their “person”, “sports ball”, or other labels identify FTC robots. A model is usable only after it has been trained/validated against representative FTC match footage and its class names are explicitly configured.

When configured and valid, analysis stores each model track ID with class, model name/version, configuration, confidence threshold, sample timestamp, normalized image center/bounding box, and confidence. Coordinates are image-normalized, not FTC field coordinates. They are estimates and require review; they do not confirm scoring, robot identity, collisions, or mechanical causes.

The track API is `GET /api/v1/videos/{video_id}/tracks`. It returns provenance and ordered trajectory points. The UI plots image-coordinate trajectories only when actual model tracks exist.

## Not yet implemented

There is no bundled or trained FTC robot model, training script, annotated training set, field calibration, occlusion recovery policy, or durable job queue. The background task is in-process and may be lost if the API exits while analysis is running. For stable real-world tracking, validate a custom detector on recordings from the intended camera views and season before relying on any output.