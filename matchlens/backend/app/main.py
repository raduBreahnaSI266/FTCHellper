import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import EventAnnotation, RobotTrack, TrajectoryPoint, VideoFieldRobot, VideoUpload
from app.schemas import (
    AnnotationCreate,
    AnnotationResponse,
    AnnotationUpdate,
    HealthResponse,
    RobotTrackResponse,
    TrajectoryPointResponse,
    TeamDirectoryEntry,
    VideoFieldRobotResponse,
    VideoFieldRobotsUpdate,
    VideoAnalysisStartResponse,
    VideoTracksResponse,
    VideoUploadResponse,
)
from app.vision.detector import RobotDetection, create_robot_detector
from app.vision.processor import VideoProcessingError, analyze_video_file

logger = logging.getLogger(__name__)

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)

app = FastAPI(
    title="MatchLens API",
    version="0.1.0",
    description="FTC match analysis API foundation. Local demo data is synthetic.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:3000", "http://127.0.0.1:3001"],
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
    allow_headers=["Content-Type"],
)

storage_dir = Path(settings.local_storage_dir).resolve()
storage_dir.mkdir(parents=True, exist_ok=True)
MAX_FILENAME_LENGTH = 255
CHUNK_SIZE = 1024 * 1024
FTC_SCOUT_GRAPHQL_URL = "https://api.ftcscout.org/graphql"


def serialize_upload(video: VideoUpload) -> VideoUploadResponse:
    return VideoUploadResponse(
        id=video.id,
        original_filename=video.original_filename,
        event_name=video.event_name,
        season=video.season,
        match_number=video.match_number,
        alliance=video.alliance,
        content_type=video.content_type,
        size_bytes=video.size_bytes,
        status=video.status,
        analysis_progress=video.analysis_progress,
        analysis_message=video.analysis_message,
        duration_seconds=video.duration_seconds,
        fps=video.fps,
        frame_count=video.frame_count,
        width=video.width,
        height=video.height,
        sampled_frames=video.sampled_frames,
        detector_status=video.detector_status,
        detector_message=video.detector_message,
        detector_model=video.detector_model,
        detector_version=video.detector_version,
        detector_configuration=video.detector_configuration,
        analyzed_at=video.analyzed_at,
        created_at=video.created_at,
    )


def serialize_annotation(annotation: EventAnnotation) -> AnnotationResponse:
    return AnnotationResponse(
        id=annotation.id,
        video_id=annotation.video_id,
        event_type=annotation.event_type,
        timestamp_seconds=annotation.timestamp_seconds,
        end_timestamp_seconds=annotation.end_timestamp_seconds,
        robot_label=annotation.robot_label,
        note=annotation.note,
        detection_source="manual",
        verification_status=annotation.verification_status,
        created_at=annotation.created_at,
        updated_at=annotation.updated_at,
    )


@app.get("/healthz", response_model=HealthResponse, tags=["health"])
def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        mode=settings.app_mode,
        supabase_configured=settings.supabase_configured,
    )


@app.get("/api/v1/teams/directory", response_model=list[TeamDirectoryEntry], tags=["teams"])
def get_team_directory(search: str | None = Query(default=None, min_length=1, max_length=100)) -> list[TeamDirectoryEntry]:
    query = "{ teamsSearch(limit: 100000) { number name } }"
    variables = None
    if search:
        query = "query($search: String!) { teamsSearch(limit: 100, searchText: $search) { number name } }"
        variables = {"search": search.strip()}
        if not variables["search"]:
            raise HTTPException(status_code=422, detail="Search text cannot be blank.")
    graphql_request: dict[str, object] = {"query": query}
    if variables is not None:
        graphql_request["variables"] = variables
    try:
        response = httpx.post(
            FTC_SCOUT_GRAPHQL_URL,
            json=graphql_request,
            headers={"apollo-require-preflight": "true"},
            timeout=30.0,
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPError as error:
        logger.exception("FTCScout team directory request failed.")
        raise HTTPException(status_code=502, detail="FTCScout is currently unavailable.") from error
    except ValueError as error:
        logger.exception("FTCScout returned an invalid response.")
        raise HTTPException(status_code=502, detail="FTCScout returned an invalid response.") from error

    if not isinstance(payload, dict) or payload.get("errors"):
        logger.warning("FTCScout team directory query returned errors.")
        raise HTTPException(status_code=502, detail="FTCScout could not provide the team directory.")
    teams = payload.get("data", {}).get("teamsSearch") if isinstance(payload.get("data"), dict) else None
    if not isinstance(teams, list):
        logger.warning("FTCScout response did not contain a team directory.")
        raise HTTPException(status_code=502, detail="FTCScout returned an invalid team directory.")
    try:
        return [TeamDirectoryEntry.model_validate(team) for team in teams]
    except (TypeError, ValueError) as error:
        logger.exception("FTCScout returned an invalid team entry.")
        raise HTTPException(status_code=502, detail="FTCScout returned an invalid team directory.") from error


@app.get(
    "/api/v1/videos/{video_id}/field-robots",
    response_model=list[VideoFieldRobotResponse],
    tags=["videos"],
)
def list_video_field_robots(video_id: str) -> list[VideoFieldRobotResponse]:
    with Session(engine) as session:
        if session.get(VideoUpload, video_id) is None:
            raise HTTPException(status_code=404, detail="Video was not found.")
        robots = session.scalars(
            select(VideoFieldRobot)
            .where(VideoFieldRobot.video_id == video_id)
            .order_by(VideoFieldRobot.alliance, VideoFieldRobot.team_number)
        ).all()
        return [VideoFieldRobotResponse.model_validate(robot, from_attributes=True) for robot in robots]


@app.put(
    "/api/v1/videos/{video_id}/field-robots",
    response_model=list[VideoFieldRobotResponse],
    tags=["videos"],
)
def update_video_field_robots(video_id: str, payload: VideoFieldRobotsUpdate) -> list[VideoFieldRobotResponse]:
    with Session(engine) as session:
        video = session.get(VideoUpload, video_id)
        if video is None:
            raise HTTPException(status_code=404, detail="Video was not found.")
        session.execute(delete(VideoFieldRobot).where(VideoFieldRobot.video_id == video_id))
        robots = [
            VideoFieldRobot(
                video_id=video_id,
                team_number=robot.team_number,
                team_name=robot.team_name.strip(),
                alliance=robot.alliance,
            )
            for robot in payload.robots
        ]
        session.add_all(robots)
        session.commit()
        for robot in robots:
            session.refresh(robot)
        return [VideoFieldRobotResponse.model_validate(robot, from_attributes=True) for robot in robots]


@app.get("/api/v1/videos", response_model=list[VideoUploadResponse], tags=["videos"])
def list_videos() -> list[VideoUploadResponse]:
    with Session(engine) as session:
        videos = session.scalars(select(VideoUpload).order_by(VideoUpload.created_at.desc())).all()
        return [serialize_upload(video) for video in videos]


@app.get("/api/v1/videos/{video_id}", response_model=VideoUploadResponse, tags=["videos"])
def get_video(video_id: str) -> VideoUploadResponse:
    with Session(engine) as session:
        video = session.get(VideoUpload, video_id)
        if video is None:
            raise HTTPException(status_code=404, detail="Video was not found.")
        return serialize_upload(video)


@app.post("/api/v1/videos", response_model=VideoUploadResponse, status_code=201, tags=["videos"])
async def upload_video(
    file: UploadFile = File(...),
    event_name: str = Form(..., min_length=1, max_length=160),
    season: str = Form(..., min_length=1, max_length=24),
    match_number: int = Form(..., ge=1, le=9999),
    alliance: str = Form(..., pattern="^(Red|Blue)$"),
) -> VideoUploadResponse:
    original_filename = Path(file.filename or "").name.strip()
    if not original_filename or len(original_filename) > MAX_FILENAME_LENGTH:
        raise HTTPException(status_code=400, detail="Filename is missing or too long.")
    if Path(original_filename).suffix.lower() != ".mp4":
        raise HTTPException(status_code=415, detail="Only .mp4 video files are supported.")
    if file.content_type not in {"video/mp4", "application/mp4", "application/octet-stream"}:
        raise HTTPException(status_code=415, detail="The uploaded file must be an MP4 video.")

    video_id = str(uuid.uuid4())
    stored_filename = f"{video_id}.mp4"
    destination = storage_dir / stored_filename
    size_bytes = 0
    header = b""
    try:
        with destination.open("wb") as output:
            while chunk := await file.read(CHUNK_SIZE):
                size_bytes += len(chunk)
                if size_bytes > settings.max_video_size_bytes:
                    raise HTTPException(status_code=413, detail="Video exceeds the 500 MB upload limit.")
                if len(header) < 12:
                    header += chunk[: 12 - len(header)]
                output.write(chunk)
        if len(header) < 12 or header[4:8] != b"ftyp":
            raise HTTPException(status_code=415, detail="File content is not a valid MP4 container.")
        video = VideoUpload(
            id=video_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            event_name=event_name.strip(),
            season=season.strip(),
            match_number=match_number,
            alliance=alliance,
            content_type="video/mp4",
            size_bytes=size_bytes,
            status="uploaded",
        )
        with Session(engine) as session:
            session.add(video)
            session.commit()
            session.refresh(video)
            return serialize_upload(video)
    except HTTPException:
        destination.unlink(missing_ok=True)
        raise
    except Exception as error:
        destination.unlink(missing_ok=True)
        logger.exception("Video upload failed")
        raise HTTPException(status_code=500, detail="Could not save the uploaded video.") from error
    finally:
        await file.close()


@app.get("/api/v1/videos/{video_id}/file", tags=["videos"])
def get_video_file(video_id: str) -> FileResponse:
    with Session(engine) as session:
        video = session.get(VideoUpload, video_id)
        if video is None:
            raise HTTPException(status_code=404, detail="Video was not found.")
        path = storage_dir / video.stored_filename
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Stored video file is missing.")
        return FileResponse(
            path,
            media_type="video/mp4",
            filename=video.original_filename,
            content_disposition_type="inline",
        )


@app.delete("/api/v1/videos/{video_id}", status_code=204, tags=["videos"])
def delete_video(video_id: str) -> None:
    with Session(engine) as session:
        video = session.get(VideoUpload, video_id)
        if video is None:
            raise HTTPException(status_code=404, detail="Video was not found.")
        session.execute(delete(EventAnnotation).where(EventAnnotation.video_id == video_id))
        (storage_dir / video.stored_filename).unlink(missing_ok=True)
        session.delete(video)
        session.commit()


def process_video_analysis(video_id: str) -> None:
    with Session(engine) as session:
        video = session.get(VideoUpload, video_id)
        if video is None:
            return
        video.status = "processing"
        video.analysis_progress = 3
        video.analysis_message = "Se citesc metadatele și se verifică cadrele video."
        session.commit()
        source_path = storage_dir / video.stored_filename

    def report_progress(progress: int) -> None:
        with Session(engine) as progress_session:
            current = progress_session.get(VideoUpload, video_id)
            if current is not None and current.status == "processing":
                current.analysis_progress = max(current.analysis_progress, progress)
                progress_session.commit()

    try:
        detector, detector_unavailable_message = create_robot_detector(
            settings.robot_detector_model,
            settings.robot_detector_classes,
            settings.robot_detector_confidence,
            settings.robot_detector_tracker,
        )
        metadata = analyze_video_file(source_path, report_progress, detector, detector_unavailable_message)
        with Session(engine) as session:
            video = session.get(VideoUpload, video_id)
            if video is None:
                return
            old_track_ids = select(RobotTrack.id).where(RobotTrack.video_id == video_id)
            session.execute(delete(TrajectoryPoint).where(TrajectoryPoint.track_id.in_(old_track_ids)))
            session.execute(delete(RobotTrack).where(RobotTrack.video_id == video_id))
            video.duration_seconds = float(metadata["duration_seconds"])
            video.fps = float(metadata["fps"])
            video.frame_count = int(metadata["frame_count"])
            video.width = int(metadata["width"])
            video.height = int(metadata["height"])
            video.sampled_frames = int(metadata["sampled_frames"])
            video.detector_status = str(metadata["detector_status"])
            video.detector_message = str(metadata["detector_message"])
            video.detector_model = str(metadata["detector_model"])
            video.detector_version = str(metadata["detector_version"])
            video.detector_configuration = str(metadata["detector_configuration"])
            if detector is not None:
                persist_robot_tracks(
                    session,
                    video_id,
                    metadata["detections"],
                    detector.model_name,
                    detector.model_version,
                    detector.confidence_threshold,
                    int(metadata["width"]),
                    int(metadata["height"]),
                )
            video.status = "needs_review"
            video.analysis_progress = 100
            video.analysis_message = analysis_summary(video, len(metadata["detections"]))
            video.analyzed_at = datetime.now(timezone.utc)
            session.commit()
    except (VideoProcessingError, OSError) as error:
        with Session(engine) as session:
            video = session.get(VideoUpload, video_id)
            if video is not None:
                video.status = "failed"
                video.analysis_message = str(error)
                video.analysis_progress = 0
                session.commit()
    except Exception:
        logger.exception("Video processing failed for %s", video_id)
        with Session(engine) as session:
            video = session.get(VideoUpload, video_id)
            if video is not None:
                video.status = "failed"
                video.analysis_message = "Video analysis failed unexpectedly. Check local logs and retry."
                video.analysis_progress = 0
                session.commit()


def analysis_summary(video: VideoUpload, detection_count: int) -> str:
    if video.detector_status == "available":
        return (
            f"Metadatele video au fost măsurate. Detectorul {video.detector_model} a produs "
            f"{detection_count} detecții-cadru cu confidence; track-urile sunt estimări de model "
            "și necesită revizuire manuală."
        )
    reason = video.detector_message or "No custom robot detector model configured."
    return f"Metadatele au fost măsurate și cadrele au fost eșantionate. Detector indisponibil: {reason}"


def persist_robot_tracks(
    session: Session,
    video_id: str,
    detections: list[RobotDetection],
    model_name: str,
    model_version: str,
    confidence_threshold: float,
    width: int,
    height: int,
) -> None:
    tracks_by_source_id: dict[str, RobotTrack] = {}
    for detection in detections:
        track = tracks_by_source_id.get(detection.track_id)
        if track is None:
            track = RobotTrack(
                video_id=video_id,
                source_track_id=detection.track_id,
                class_name=detection.class_name,
                detection_source="model",
                model_name=model_name,
                model_version=model_version,
                confidence_threshold=confidence_threshold,
            )
            session.add(track)
            session.flush()
            tracks_by_source_id[detection.track_id] = track
        session.add(
            TrajectoryPoint(
                track_id=track.id,
                timestamp_seconds=detection.timestamp_seconds,
                x_normalized=min(max(detection.center_x / width, 0.0), 1.0),
                y_normalized=min(max(detection.center_y / height, 0.0), 1.0),
                x1_normalized=min(max(detection.x1 / width, 0.0), 1.0),
                y1_normalized=min(max(detection.y1 / height, 0.0), 1.0),
                x2_normalized=min(max(detection.x2 / width, 0.0), 1.0),
                y2_normalized=min(max(detection.y2 / height, 0.0), 1.0),
                confidence=detection.confidence,
            )
        )


@app.post(
    "/api/v1/videos/{video_id}/analyze",
    response_model=VideoAnalysisStartResponse,
    status_code=202,
    tags=["analysis"],
)
def start_video_analysis(video_id: str, background_tasks: BackgroundTasks) -> VideoAnalysisStartResponse:
    with Session(engine) as session:
        video = session.get(VideoUpload, video_id)
        if video is None:
            raise HTTPException(status_code=404, detail="Video was not found.")
        if video.status in {"queued", "processing"}:
            raise HTTPException(status_code=409, detail="Video analysis is already in progress.")
        path = storage_dir / video.stored_filename
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Stored video file is missing.")
        video.status = "queued"
        video.analysis_progress = 0
        video.analysis_message = "Analiza a fost pusă în coadă locală."
        session.commit()

    background_tasks.add_task(process_video_analysis, video_id)
    return VideoAnalysisStartResponse(
        video_id=video_id,
        status="queued",
        message="Analiza locală a fost pornită.",
    )


@app.get(
    "/api/v1/videos/{video_id}/tracks",
    response_model=VideoTracksResponse,
    tags=["analysis"],
)
def get_video_tracks(video_id: str) -> VideoTracksResponse:
    with Session(engine) as session:
        video = session.get(VideoUpload, video_id)
        if video is None:
            raise HTTPException(status_code=404, detail="Video was not found.")
        tracks = session.scalars(
            select(RobotTrack).where(RobotTrack.video_id == video_id).order_by(RobotTrack.source_track_id)
        ).all()
        return VideoTracksResponse(
            video_id=video_id,
            detector_status=video.detector_status or "unavailable",
            detector_message=video.detector_message,
            tracks=[
                RobotTrackResponse(
                    id=track.id,
                    source_track_id=track.source_track_id,
                    class_name=track.class_name,
                    detection_source="model",
                    model_name=track.model_name,
                    model_version=track.model_version,
                    confidence_threshold=track.confidence_threshold,
                    points=[
                        TrajectoryPointResponse(
                            timestamp_seconds=point.timestamp_seconds,
                            x_normalized=point.x_normalized,
                            y_normalized=point.y_normalized,
                            x1_normalized=point.x1_normalized,
                            y1_normalized=point.y1_normalized,
                            x2_normalized=point.x2_normalized,
                            y2_normalized=point.y2_normalized,
                            confidence=point.confidence,
                        )
                        for point in sorted(track.points, key=lambda item: item.timestamp_seconds)
                    ],
                )
                for track in tracks
            ],
        )


@app.get(
    "/api/v1/videos/{video_id}/annotations",
    response_model=list[AnnotationResponse],
    tags=["annotations"],
)
def list_annotations(video_id: str) -> list[AnnotationResponse]:
    with Session(engine) as session:
        if session.get(VideoUpload, video_id) is None:
            raise HTTPException(status_code=404, detail="Video was not found.")
        annotations = session.scalars(
            select(EventAnnotation)
            .where(EventAnnotation.video_id == video_id)
            .order_by(EventAnnotation.timestamp_seconds, EventAnnotation.created_at)
        ).all()
        return [serialize_annotation(annotation) for annotation in annotations]


@app.post(
    "/api/v1/videos/{video_id}/annotations",
    response_model=AnnotationResponse,
    status_code=201,
    tags=["annotations"],
)
def create_annotation(video_id: str, payload: AnnotationCreate) -> AnnotationResponse:
    with Session(engine) as session:
        if session.get(VideoUpload, video_id) is None:
            raise HTTPException(status_code=404, detail="Video was not found.")
        annotation = EventAnnotation(
            video_id=video_id,
            event_type=payload.event_type,
            timestamp_seconds=payload.timestamp_seconds,
            end_timestamp_seconds=payload.end_timestamp_seconds,
            robot_label=payload.robot_label,
            note=payload.note,
            detection_source="manual",
            verification_status="unreviewed",
        )
        session.add(annotation)
        session.commit()
        session.refresh(annotation)
        return serialize_annotation(annotation)


@app.patch(
    "/api/v1/videos/{video_id}/annotations/{annotation_id}",
    response_model=AnnotationResponse,
    tags=["annotations"],
)
def update_annotation(video_id: str, annotation_id: str, payload: AnnotationUpdate) -> AnnotationResponse:
    updates = payload.model_dump(exclude_unset=True)
    with Session(engine) as session:
        annotation = session.scalar(
            select(EventAnnotation).where(
                EventAnnotation.id == annotation_id,
                EventAnnotation.video_id == video_id,
            )
        )
        if annotation is None:
            raise HTTPException(status_code=404, detail="Annotation was not found.")
        proposed_start = updates.get("timestamp_seconds", annotation.timestamp_seconds)
        proposed_end = updates.get("end_timestamp_seconds", annotation.end_timestamp_seconds)
        if proposed_end is not None and proposed_end < proposed_start:
            raise HTTPException(status_code=422, detail="End timestamp must be at or after start timestamp.")
        for field, value in updates.items():
            setattr(annotation, field, value)
        session.commit()
        session.refresh(annotation)
        return serialize_annotation(annotation)


@app.delete(
    "/api/v1/videos/{video_id}/annotations/{annotation_id}", status_code=204, tags=["annotations"]
)
def delete_annotation(video_id: str, annotation_id: str) -> None:
    with Session(engine) as session:
        annotation = session.scalar(
            select(EventAnnotation).where(
                EventAnnotation.id == annotation_id,
                EventAnnotation.video_id == video_id,
            )
        )
        if annotation is None:
            raise HTTPException(status_code=404, detail="Annotation was not found.")
        session.delete(annotation)
        session.commit()