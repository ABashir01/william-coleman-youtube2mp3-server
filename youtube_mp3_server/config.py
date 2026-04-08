"""Application settings sourced from environment variables."""

from __future__ import annotations

from dataclasses import dataclass
import os


def _read_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        value = int(raw_value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw_value!r}.") from exc

    if value <= 0:
        raise ValueError(f"{name} must be greater than zero, got {value}.")
    return value


@dataclass(frozen=True)
class Settings:
    yt_dlp_binary: str = "yt-dlp"
    ffmpeg_binary: str = "ffmpeg"
    conversion_timeout_seconds: int = 180
    max_request_bytes: int = 8 * 1024
    route_path: str = "/api/v1/convert"
    health_route_path: str = "/api/v1/health"


def load_settings() -> Settings:
    return Settings(
        yt_dlp_binary=os.getenv("YT_DLP_BINARY", "yt-dlp"),
        ffmpeg_binary=os.getenv("FFMPEG_BINARY", "ffmpeg"),
        conversion_timeout_seconds=_read_int("CONVERSION_TIMEOUT_SECONDS", 180),
        max_request_bytes=_read_int("MAX_REQUEST_BYTES", 8 * 1024),
        route_path=os.getenv("CONVERT_ROUTE_PATH", "/api/v1/convert"),
        health_route_path=os.getenv("HEALTH_ROUTE_PATH", "/api/v1/health"),
    )
