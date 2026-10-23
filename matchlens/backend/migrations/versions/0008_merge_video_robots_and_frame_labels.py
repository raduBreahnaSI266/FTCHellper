"""Merge FTCScout video rosters and local robot training labels."""

from typing import Sequence, Union

revision: str = "0008_merge_video_robots_and_frame_labels"
down_revision: Union[str, Sequence[str], None] = (
    "0007_video_field_robots",
    "0007_robot_frame_labels",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass