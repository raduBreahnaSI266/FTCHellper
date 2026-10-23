from datetime import datetime

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class HealthResponse(BaseModel):
    status: str
    mode: str
    supabase_configured: bool


class TeamDirectoryEntry(BaseModel):
    number: int
    name: str


class VideoFieldRobotInput(BaseModel):
    team_number: int = Field(gt=0)
    team_name: str = Field(min_length=1, max_length=255)
    alliance: Literal["Red", "Blue"]

    @field_validator("team_name")
    @classmethod
    def validate_team_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("Team name cannot be blank.")
        return name


class VideoFieldRobotsUpdate(BaseModel):
    robots: list[VideoFieldRobotInput] = Field(max_length=6)

    @model_validator(mode="after")
    def validate_roster(self) -> "VideoFieldRobotsUpdate":
        team_numbers = [robot.team_number for robot in self.robots]
        if len(team_numbers) != len(set(team_numbers)):
            raise ValueError("A team can only appear once in the video roster.")
        for alliance in ("Red", "Blue"):
            alliance_count = sum(robot.alliance == alliance for robot in self.robots)
            if alliance_count > 3:
                raise ValueError(f"The {alliance.lower()} alliance can have at most three teams.")
        return self


class VideoFieldRobotResponse(VideoFieldRobotInput):
    id: str
    video_id: str


class VideoUploadResponse(BaseModel):
    id: str
    original_filename: str
    event_name: str | None
    season: str | None
    match_number: int | None
    alliance: str | None
    content_type: str
    size_bytes: int
    status: str
    analysis_progress: int
    analysis_message: str | None
    duration_seconds: float | None
    fps: float | None
    frame_count: int | None
    width: int | None
    height: int | None
    sampled_frames: int | None
    detector_status: str | None
    detector_message: str | None
    detector_model: str | None
    detector_version: str | None
    detector_configuration: str | None
    analyzed_at: datetime | None
    created_at: datetime


class VideoAnalysisStartResponse(BaseModel):
    video_id: str
    status: str
    message: str


class RobotBox(BaseModel):
    class_name: str = Field(default="robot", min_length=1, max_length=80)
    x1_normalized: float = Field(ge=0, le=1)
    y1_normalized: float = Field(ge=0, le=1)
    x2_normalized: float = Field(gt=0, le=1)
    y2_normalized: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def validate_box(self) -> "RobotBox":
        if self.x2_normalized <= self.x1_normalized or self.y2_normalized <= self.y1_normalized:
            raise ValueError("Robot bounding boxes must have positive width and height.")
        return self


class RobotFrameLabelsUpdate(BaseModel):
    boxes: list[RobotBox] = Field(max_length=50)


class RobotTrackStart(RobotBox):
    pass


class RobotFrameLabelResponse(RobotBox):
    id: str
    video_id: str
    timestamp_seconds: float


EventType = Literal[
    "autonomous",
    "teleop",
    "candidate_score",
    "confirmed_score",
    "intake_attempt",
    "placement_attempt",
    "contact",
    "suspected_delay",
    "inactivity",
    "endgame",
    "unknown",
]


class AnnotationCreate(BaseModel):
    event_type: EventType
    timestamp_seconds: float = Field(ge=0)
    end_timestamp_seconds: float | None = Field(default=None, ge=0)
    robot_label: str | None = Field(default=None, max_length=80)
    note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_interval(self) -> "AnnotationCreate":
        if self.end_timestamp_seconds is not None and self.end_timestamp_seconds < self.timestamp_seconds:
            raise ValueError("End timestamp must be at or after start timestamp.")
        return self


class AnnotationUpdate(BaseModel):
    event_type: EventType | None = None
    timestamp_seconds: float | None = Field(default=None, ge=0)
    end_timestamp_seconds: float | None = Field(default=None, ge=0)
    robot_label: str | None = Field(default=None, max_length=80)
    note: str | None = Field(default=None, max_length=1000)
    verification_status: Literal["unreviewed", "confirmed", "rejected"] | None = None


class AnnotationResponse(BaseModel):
    id: str
    video_id: str
    event_type: EventType
    timestamp_seconds: float
    end_timestamp_seconds: float | None
    robot_label: str | None
    note: str | None
    detection_source: Literal["manual"]
    verification_status: Literal["unreviewed", "confirmed", "rejected"]
    created_at: datetime
    updated_at: datetime


class TrajectoryPointResponse(BaseModel):
    timestamp_seconds: float
    x_normalized: float
    y_normalized: float
    x1_normalized: float
    y1_normalized: float
    x2_normalized: float
    y2_normalized: float
    confidence: float


class RobotTrackResponse(BaseModel):
    id: str
    source_track_id: str
    class_name: str
    detection_source: Literal["model", "seeded_tracker"]
    model_name: str
    model_version: str
    confidence_threshold: float
    points: list[TrajectoryPointResponse]


class VideoTracksResponse(BaseModel):
    video_id: str
    detector_status: str
    detector_message: str | None
    tracks: list[RobotTrackResponse]