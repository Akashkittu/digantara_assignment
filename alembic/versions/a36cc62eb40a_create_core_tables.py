"""create core tables

Revision ID: a36cc62eb40a
Revises:
Create Date: 2026-02-07 23:04:03.138097
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a36cc62eb40a"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ground stations
    op.create_table(
        "ground_stations",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),  # NEW: for reproducible 50 GS
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lon", sa.Float(), nullable=False),
        sa.Column("alt_m", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_ground_stations_code"),
    )

    # Satellites
    op.create_table(
        "satellites",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("norad_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("norad_id", name="uq_satellites_norad_id"),
    )

    # Passes
    op.create_table(
        "passes",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("satellite_id", sa.BigInteger(), nullable=False),
        sa.Column("ground_station_id", sa.BigInteger(), nullable=False),
        sa.Column("start_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_s", sa.Integer(), nullable=False),
        sa.Column("max_elev_deg", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(
            ["ground_station_id"], ["ground_stations.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["satellite_id"], ["satellites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        # Prevent duplicate pass rows:
        sa.UniqueConstraint(
            "satellite_id",
            "ground_station_id",
            "start_ts",
            "end_ts",
            name="uq_passes_sat_gs_start_end",
        ),
        # Basic validity check:
        sa.CheckConstraint("end_ts > start_ts", name="ck_passes_end_after_start"),
        sa.CheckConstraint("duration_s >= 0", name="ck_passes_duration_nonneg"),
    )

    # Indexes for fast querying
    op.create_index(
        "ix_passes_gs_start", "passes", ["ground_station_id", "start_ts"], unique=False
    )
    op.create_index(
        "ix_passes_sat_start", "passes", ["satellite_id", "start_ts"], unique=False
    )
    # Optional helpful index for overlap-heavy queries
    op.create_index(
        "ix_passes_gs_end", "passes", ["ground_station_id", "end_ts"], unique=False
    )

    # TLEs
    op.create_table(
        "tles",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("satellite_id", sa.BigInteger(), nullable=False),
        sa.Column("line1", sa.Text(), nullable=False),
        sa.Column("line2", sa.Text(), nullable=False),
        sa.Column("epoch", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["satellite_id"], ["satellites.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_tles_sat_fetched_at",
        "tles",
        ["satellite_id", "fetched_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_tles_sat_fetched_at", table_name="tles")
    op.drop_table("tles")

    op.drop_index("ix_passes_gs_end", table_name="passes")
    op.drop_index("ix_passes_sat_start", table_name="passes")
    op.drop_index("ix_passes_gs_start", table_name="passes")
    op.drop_table("passes")

    op.drop_table("satellites")
    op.drop_table("ground_stations")
