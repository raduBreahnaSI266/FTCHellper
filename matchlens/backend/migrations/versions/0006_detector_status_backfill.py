"""Explain unavailable detector state for previously analyzed videos."""

from typing import Sequence, Union

from alembic import op

revision: str = "0006_detector_status_backfill"
down_revision: Union[str, None] = "0005_robot_tracks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE video_uploads SET detector_message = "
        "'No custom robot detector model configured.' "
        "WHERE detector_status = 'unavailable' AND detector_message IS NULL"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE video_uploads SET detector_message = NULL "
        "WHERE detector_message = 'No custom robot detector model configured.'"
    )