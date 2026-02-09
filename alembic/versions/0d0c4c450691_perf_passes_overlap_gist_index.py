"""perf: passes overlap gist index

Revision ID: 0d0c4c450691
Revises: 97a0bf1a9d18
Create Date: 2026-02-09 12:05:01.149207

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0d0c4c450691'
down_revision: Union[str, None] = '97a0bf1a9d18'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from alembic import op

def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist;")

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_passes_gs_window_gist
        ON passes
        USING GIST (ground_station_id, tstzrange(start_ts, end_ts, '[)'));
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_passes_gs_window_gist;")

