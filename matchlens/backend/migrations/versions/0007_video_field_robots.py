"""Save manually selected FTC teams for each analyzed video."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0007_video_field_robots"
down_revision: Union[str, None] = "0006_detector_status_backfill"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "video_field_robots",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "video_id",
            sa.String(length=36),
            sa.ForeignKey("video_uploads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("team_number", sa.Integer(), nullable=False),
        sa.Column("team_name", sa.String(length=255), nullable=False),
        sa.Column("alliance", sa.String(length=8), nullable=False),
        sa.UniqueConstraint("video_id", "team_number", name="uq_video_field_robot_team"),
    )
    op.create_index("ix_video_field_robots_video_id", "video_field_robots", ["video_id"])


def downgrade() -> None:
    op.drop_index("ix_video_field_robots_video_id", table_name="video_field_robots")
    op.drop_table("video_field_robots")
