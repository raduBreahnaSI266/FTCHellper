"""Store locally labeled robot boxes for detector training."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007_robot_frame_labels"
down_revision: Union[str, None] = "0006_detector_status_backfill"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "robot_frame_labels",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("video_id", sa.String(length=36), sa.ForeignKey("video_uploads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("timestamp_seconds", sa.Float(), nullable=False),
        sa.Column("class_name", sa.String(length=80), nullable=False),
        sa.Column("x1_normalized", sa.Float(), nullable=False),
        sa.Column("y1_normalized", sa.Float(), nullable=False),
        sa.Column("x2_normalized", sa.Float(), nullable=False),
        sa.Column("y2_normalized", sa.Float(), nullable=False),
    )
    op.create_index("ix_robot_frame_labels_video_id", "robot_frame_labels", ["video_id"])


def downgrade() -> None:
    op.drop_index("ix_robot_frame_labels_video_id", table_name="robot_frame_labels")
    op.drop_table("robot_frame_labels")