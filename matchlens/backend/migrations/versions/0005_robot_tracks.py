"""Persist optional model robot tracks and trajectory points."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0005_robot_tracks"
down_revision: Union[str, None] = "0004_video_analysis_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("video_uploads") as batch_op:
        batch_op.add_column(sa.Column("detector_message", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("detector_model", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("detector_version", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("detector_configuration", sa.Text(), nullable=True))

    op.create_table(
        "robot_tracks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("video_id", sa.String(length=36), sa.ForeignKey("video_uploads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_track_id", sa.String(length=80), nullable=False),
        sa.Column("class_name", sa.String(length=80), nullable=False),
        sa.Column("detection_source", sa.String(length=16), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("model_version", sa.String(length=80), nullable=False),
        sa.Column("confidence_threshold", sa.Float(), nullable=False),
        sa.UniqueConstraint("video_id", "source_track_id", name="uq_video_source_track"),
    )
    op.create_index("ix_robot_tracks_video_id", "robot_tracks", ["video_id"])
    op.create_table(
        "trajectory_points",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("track_id", sa.String(length=36), sa.ForeignKey("robot_tracks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("timestamp_seconds", sa.Float(), nullable=False),
        sa.Column("x_normalized", sa.Float(), nullable=False),
        sa.Column("y_normalized", sa.Float(), nullable=False),
        sa.Column("x1_normalized", sa.Float(), nullable=False),
        sa.Column("y1_normalized", sa.Float(), nullable=False),
        sa.Column("x2_normalized", sa.Float(), nullable=False),
        sa.Column("y2_normalized", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.UniqueConstraint("track_id", "timestamp_seconds", name="uq_track_timestamp"),
    )
    op.create_index("ix_trajectory_points_track_id", "trajectory_points", ["track_id"])
    op.execute(
        "UPDATE video_uploads SET detector_message = "
        "'No custom robot detector model configured.' "
        "WHERE detector_status = 'unavailable' AND detector_message IS NULL"
    )


def downgrade() -> None:
    op.drop_index("ix_trajectory_points_track_id", table_name="trajectory_points")
    op.drop_table("trajectory_points")
    op.drop_index("ix_robot_tracks_video_id", table_name="robot_tracks")
    op.drop_table("robot_tracks")
    with op.batch_alter_table("video_uploads") as batch_op:
        batch_op.drop_column("detector_configuration")
        batch_op.drop_column("detector_version")
        batch_op.drop_column("detector_model")
        batch_op.drop_column("detector_message")