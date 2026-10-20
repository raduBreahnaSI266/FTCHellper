"""Add manual video event annotations."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_event_annotations"
down_revision: Union[str, None] = "0002_local_video_uploads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "event_annotations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("video_id", sa.String(length=36), sa.ForeignKey("video_uploads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("timestamp_seconds", sa.Float(), nullable=False),
        sa.Column("end_timestamp_seconds", sa.Float(), nullable=True),
        sa.Column("robot_label", sa.String(length=80), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("detection_source", sa.String(length=16), nullable=False),
        sa.Column("verification_status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_event_annotations_video_id", "event_annotations", ["video_id"])


def downgrade() -> None:
    op.drop_index("ix_event_annotations_video_id", table_name="event_annotations")
    op.drop_table("event_annotations")