from sqlalchemy import (
    BigInteger, Integer, Float, Text, ForeignKey,
    DateTime, func, Index
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Satellite(Base):
    __tablename__ = "satellites"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    norad_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    tles = relationship("TLE", back_populates="satellite", cascade="all, delete-orphan")


class TLE(Base):
    __tablename__ = "tles"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    satellite_id: Mapped[int] = mapped_column(ForeignKey("satellites.id", ondelete="CASCADE"), nullable=False)

    line1: Mapped[str] = mapped_column(Text, nullable=False)
    line2: Mapped[str] = mapped_column(Text, nullable=False)

    # (We’ll parse epoch properly later when we implement TLE fetch)
    epoch: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=True)
    fetched_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    satellite = relationship("Satellite", back_populates="tles")


class GroundStation(Base):
    __tablename__ = "ground_stations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)

    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lon: Mapped[float] = mapped_column(Float, nullable=False)
    alt_m: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


class Pass(Base):
    __tablename__ = "passes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    satellite_id: Mapped[int] = mapped_column(ForeignKey("satellites.id", ondelete="CASCADE"), nullable=False)
    ground_station_id: Mapped[int] = mapped_column(ForeignKey("ground_stations.id", ondelete="CASCADE"), nullable=False)

    start_ts: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)
    end_ts: Mapped[object] = mapped_column(DateTime(timezone=True), nullable=False)

    duration_s: Mapped[int] = mapped_column(Integer, nullable=False)
    max_elev_deg: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    __table_args__ = (
        Index("ix_passes_gs_start", "ground_station_id", "start_ts"),
        Index("ix_passes_sat_start", "satellite_id", "start_ts"),
    )
