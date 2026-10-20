import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    memberships: Mapped[list["TeamMembership"]] = relationship(back_populates="team", cascade="all, delete-orphan")
    matches: Mapped[list["Match"]] = relationship(back_populates="team", cascade="all, delete-orphan")


class TeamMembership(Base):
    __tablename__ = "team_memberships"
    __table_args__ = (UniqueConstraint("team_id", "user_id", name="uq_team_membership_user"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    team_id: Mapped[str] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="viewer")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    team: Mapped[Team] = relationship(back_populates="memberships")


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    team_id: Mapped[str] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), nullable=False, index=True)
    event_name: Mapped[str] = mapped_column(String(160), nullable=False)
    season: Mapped[str] = mapped_column(String(24), nullable=False)
    match_number: Mapped[int] = mapped_column(Integer, nullable=False)
    alliance: Mapped[str | None] = mapped_column(String(8))
    played_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    team: Mapped[Team] = relationship(back_populates="matches")


class VideoUpload(Base):
    __tablename__ = "video_uploads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    event_name: Mapped[str | None] = mapped_column(String(160))
    season: Mapped[str | None] = mapped_column(String(24))
    match_number: Mapped[int | None] = mapped_column(Integer)
    alliance: Mapped[str | None] = mapped_column(String(8))
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="uploaded")
    analysis_progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    analysis_message: Mapped[str | None] = mapped_column(Text)
    duration_seconds: Mapped[float | None] = mapped_column(Float)
    fps: Mapped[float | None] = mapped_column(Float)
    frame_count: Mapped[int | None] = mapped_column(Integer)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    sampled_frames: Mapped[int | None] = mapped_column(Integer)
    detector_status: Mapped[str | None] = mapped_column(String(24))
    detector_message: Mapped[str | None] = mapped_column(Text)
    detector_model: Mapped[str | None] = mapped_column(String(255))
    detector_version: Mapped[str | None] = mapped_column(String(80))
    detector_configuration: Mapped[str | None] = mapped_column(Text)
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    robot_tracks: Mapped[list["RobotTrack"]] = relationship(back_populates="video", cascade="all, delete-orphan")


class EventAnnotation(Base):
    __tablename__ = "event_annotations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id: Mapped[str] = mapped_column(ForeignKey("video_uploads.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    timestamp_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    end_timestamp_seconds: Mapped[float | None] = mapped_column(Float)
    robot_label: Mapped[str | None] = mapped_column(String(80))
    note: Mapped[str | None] = mapped_column(Text)
    detection_source: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")
    verification_status: Mapped[str] = mapped_column(String(16), nullable=False, default="unreviewed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class RobotTrack(Base):
    __tablename__ = "robot_tracks"
    __table_args__ = (UniqueConstraint("video_id", "source_track_id", name="uq_video_source_track"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    video_id: Mapped[str] = mapped_column(ForeignKey("video_uploads.id", ondelete="CASCADE"), nullable=False, index=True)
    source_track_id: Mapped[str] = mapped_column(String(80), nullable=False)
    class_name: Mapped[str] = mapped_column(String(80), nullable=False)
    detection_source: Mapped[str] = mapped_column(String(16), nullable=False, default="model")
    model_name: Mapped[str] = mapped_column(String(255), nullable=False)
    model_version: Mapped[str] = mapped_column(String(80), nullable=False)
    confidence_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    points: Mapped[list["TrajectoryPoint"]] = relationship(back_populates="track", cascade="all, delete-orphan")
    video: Mapped[VideoUpload] = relationship(back_populates="robot_tracks")


class TrajectoryPoint(Base):
    __tablename__ = "trajectory_points"
    __table_args__ = (UniqueConstraint("track_id", "timestamp_seconds", name="uq_track_timestamp"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    track_id: Mapped[str] = mapped_column(ForeignKey("robot_tracks.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    x_normalized: Mapped[float] = mapped_column(Float, nullable=False)
    y_normalized: Mapped[float] = mapped_column(Float, nullable=False)
    x1_normalized: Mapped[float] = mapped_column(Float, nullable=False)
    y1_normalized: Mapped[float] = mapped_column(Float, nullable=False)
    x2_normalized: Mapped[float] = mapped_column(Float, nullable=False)
    y2_normalized: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    track: Mapped[RobotTrack] = relationship(back_populates="points")