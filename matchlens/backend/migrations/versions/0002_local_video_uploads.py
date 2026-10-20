"""Add metadata for locally stored video uploads."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = "0002_local_video_uploads"
down_revision: Union[str, None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    if not inspect(connection).has_table("video_uploads"):
        op.create_table(
            "video_uploads",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("original_filename", sa.String(length=255), nullable=False),
            sa.Column("stored_filename", sa.String(length=80), nullable=False, unique=True),
            sa.Column("event_name", sa.String(length=160), nullable=True),
            sa.Column("season", sa.String(length=24), nullable=True),
            sa.Column("match_number", sa.Integer(), nullable=True),
            sa.Column("alliance", sa.String(length=8), nullable=True),
            sa.Column("content_type", sa.String(length=100), nullable=False),
            sa.Column("size_bytes", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=24), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        return

    existing_columns = {column["name"] for column in inspect(connection).get_columns("video_uploads")}
    with op.batch_alter_table("video_uploads") as batch_op:
        for name, column_type in (
            ("event_name", sa.String(length=160)),
            ("season", sa.String(length=24)),
            ("match_number", sa.Integer()),
            ("alliance", sa.String(length=8)),
        ):
            if name not in existing_columns:
                batch_op.add_column(sa.Column(name, column_type, nullable=True))


def downgrade() -> None:
    op.drop_table("video_uploads")