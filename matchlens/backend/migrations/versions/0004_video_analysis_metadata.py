"""Add video analysis status and measured metadata."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0004_video_analysis_metadata"
down_revision: Union[str, None] = "0003_event_annotations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("video_uploads") as batch_op:
        batch_op.add_column(sa.Column("analysis_progress", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("analysis_message", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("duration_seconds", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("fps", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("frame_count", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("width", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("height", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("sampled_frames", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("detector_status", sa.String(length=24), nullable=True))
        batch_op.add_column(sa.Column("analyzed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("video_uploads") as batch_op:
        batch_op.drop_column("analyzed_at")
        batch_op.drop_column("detector_status")
        batch_op.drop_column("sampled_frames")
        batch_op.drop_column("height")
        batch_op.drop_column("width")
        batch_op.drop_column("frame_count")
        batch_op.drop_column("fps")
        batch_op.drop_column("duration_seconds")
        batch_op.drop_column("analysis_message")
        batch_op.drop_column("analysis_progress")