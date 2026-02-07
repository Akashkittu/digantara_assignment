"""add ground station code

Revision ID: 97a0bf1a9d18
Revises: a36cc62eb40a
Create Date: 2026-02-08
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "97a0bf1a9d18"
down_revision: Union[str, None] = "a36cc62eb40a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add column only if it doesn't exist
    op.execute("ALTER TABLE ground_stations ADD COLUMN IF NOT EXISTS code TEXT;")

    # Backfill any NULL codes (safe even if table empty)
    op.execute("""
        UPDATE ground_stations
        SET code = 'GS' || LPAD(id::text, 3, '0')
        WHERE code IS NULL
    """)

    # Make NOT NULL
    op.execute("ALTER TABLE ground_stations ALTER COLUMN code SET NOT NULL;")

    # Add UNIQUE constraint only if it doesn't exist
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conname = 'uq_ground_stations_code'
        ) THEN
            ALTER TABLE ground_stations
            ADD CONSTRAINT uq_ground_stations_code UNIQUE (code);
        END IF;
    END $$;
    """)


def downgrade() -> None:
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conname = 'uq_ground_stations_code'
        ) THEN
            ALTER TABLE ground_stations DROP CONSTRAINT uq_ground_stations_code;
        END IF;
    END $$;
    """)
    op.execute("ALTER TABLE ground_stations DROP COLUMN IF EXISTS code;")
