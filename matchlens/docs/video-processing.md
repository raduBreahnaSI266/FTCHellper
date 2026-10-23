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

For immediate local tracking before a custom model is trained, draw a robot box on a frame and choose **Urmărește robotul până la final**. OpenCV TrackerMIL follows that selected robot forward from the chosen timestamp and saves estimated trajectory points. This is seeded visual tracking, not automatic robot detection: repeat for each robot, and re-seed after occlusion or a tracking failure. MIL does not provide a calibrated confidence score, so these points are marked with zero confidence and must be reviewed. For automatic multi-robot detection without drawing seed boxes, configure the trained YOLO model described below.

## Local robot labeling and training

Open a local video, choose a timestamp with the frame slider, choose **Pornește etichetarea**, and draw one box around each visible robot in the locally extracted still frame. The frame preview works even if the browser cannot decode the video's codec. Save the frame labels and repeat at different times and camera views. Labels are stored locally in SQLite. **Exportă dataset YOLO** downloads labeled frames and YOLO box labels as a ZIP; when multiple videos are labeled, the last video is reserved for validation to avoid splitting neighboring frames across train and validation.

Install the optional detector dependencies once, then train using a YOLO `.pt` checkpoint already present on this computer. No checkpoint or video is downloaded by the training workflow:

```powershell
cd .\matchlens\backend
python -m pip install -r requirements-vision.txt
python .\train_robot_detector.py "$HOME\Downloads\matchlens-robot-dataset.zip" "C:\models\yolo11n.pt" --epochs 100
```

The trained model is written to `backend/local-models/robot_detector.pt`. Set `ROBOT_DETECTOR_MODEL=./local-models/robot_detector.pt` in `backend/.env`, ensure `ROBOT_DETECTOR_CLASSES=robot`, and restart the API. Run **Analizează video** again to produce model-backed robot tracks. Start with varied, sharp frames from several matches; check labels carefully and keep a separate match for validation. A model trained from a small or visually narrow set may miss robots or assign unstable track IDs.

## Not yet implemented

There is no bundled or trained FTC robot model, training script, annotated training set, field calibration, occlusion recovery policy, or durable job queue. The background task is in-process and may be lost if the API exits while analysis is running. For stable real-world tracking, validate a custom detector on recordings from the intended camera views and season before relying on any output.