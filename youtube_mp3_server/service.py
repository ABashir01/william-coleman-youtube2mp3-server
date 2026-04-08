"""Conversion logic isolated from the HTTP boundary."""

from __future__ import annotations

from dataclasses import dataclass
import base64
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
from typing import Callable
from urllib.parse import urlparse

from .config import Settings
from .errors import BinaryNotFoundError, ConversionFailedError, InvalidYoutubeUrlError

ALLOWED_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
}

_FILENAME_SAFE_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True)
class ConversionResult:
    file_path: Path
    download_name: str
    cleanup: Callable[[], None]


def is_binary_available(binary_name: str) -> bool:
    binary_path = Path(binary_name)
    if binary_path.is_absolute():
        return binary_path.is_file()
    return shutil.which(binary_name) is not None


def resolve_binary_path(binary_name: str) -> str:
    binary_path = Path(binary_name)
    if binary_path.is_absolute():
        if binary_path.is_file():
            return str(binary_path)
        raise BinaryNotFoundError(
            f"Required executable {binary_name!r} is not available on the host."
        )

    resolved = shutil.which(binary_name)
    if resolved:
        return resolved

    raise BinaryNotFoundError(
        f"Required executable {binary_name!r} is not available on the host."
    )


def get_runtime_health(settings: Settings) -> dict[str, object]:
    yt_dlp_available = is_binary_available(settings.yt_dlp_binary)
    ffmpeg_available = is_binary_available(settings.ffmpeg_binary)
    return {
        "status": "ok" if yt_dlp_available and ffmpeg_available else "degraded",
        "checks": {
            "yt_dlp": {
                "binary": settings.yt_dlp_binary,
                "available": yt_dlp_available,
            },
            "ffmpeg": {
                "binary": settings.ffmpeg_binary,
                "available": ffmpeg_available,
            },
        },
        "config": {
            "proxy_configured": bool(settings.yt_dlp_proxy_url),
            "cookies_configured": bool(
                settings.yt_dlp_cookies_file or settings.yt_dlp_cookies_base64
            ),
            "extra_args_configured": bool(settings.yt_dlp_extra_args.strip()),
        },
    }


def validate_youtube_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if parsed.scheme not in {"http", "https"}:
        raise InvalidYoutubeUrlError("The URL must use http or https.")
    if host not in ALLOWED_HOSTS:
        raise InvalidYoutubeUrlError("The URL must point to youtube.com or youtu.be.")
    if host in {"youtu.be", "www.youtu.be"}:
        if parsed.path in {"", "/"}:
            raise InvalidYoutubeUrlError("The YouTube short URL is missing a video identifier.")
        return url

    video_path_prefixes = ("/shorts/", "/embed/", "/live/", "/clip/")
    if parsed.path == "/watch":
        query_pairs = dict(
            item.split("=", 1)
            for item in parsed.query.split("&")
            if "=" in item
        )
        if query_pairs.get("v"):
            return url
        raise InvalidYoutubeUrlError("The YouTube watch URL is missing the 'v' parameter.")

    if any(parsed.path.startswith(prefix) for prefix in video_path_prefixes):
        return url

    raise InvalidYoutubeUrlError("The YouTube URL does not reference a specific video.")


def _require_binary(binary_name: str) -> None:
    if is_binary_available(binary_name):
        return
    raise BinaryNotFoundError(
        f"Required executable {binary_name!r} is not available on the host."
    )


def sanitize_filename(filename: str | None, fallback: str) -> str:
    base_name = filename or fallback
    cleaned = _FILENAME_SAFE_PATTERN.sub("-", base_name.strip()).strip("._-")
    if not cleaned:
        cleaned = fallback
    if not cleaned.lower().endswith(".mp3"):
        cleaned = f"{cleaned}.mp3"
    return cleaned


def _materialize_cookies_file(settings: Settings, temp_dir: Path) -> str | None:
    if settings.yt_dlp_cookies_file:
        return settings.yt_dlp_cookies_file

    if not settings.yt_dlp_cookies_base64:
        return None

    try:
        cookie_bytes = base64.b64decode(settings.yt_dlp_cookies_base64)
    except (ValueError, TypeError) as exc:
        raise ConversionFailedError("YT_DLP_COOKIES_BASE64 is not valid base64.") from exc

    cookies_path = temp_dir / "cookies.txt"
    cookies_path.write_bytes(cookie_bytes)
    return str(cookies_path)


def build_download_command(
    url: str,
    output_template: str,
    settings: Settings,
    cookies_file: str | None = None,
) -> list[str]:
    validate_youtube_url(url)
    ffmpeg_path = resolve_binary_path(settings.ffmpeg_binary)
    command = [
        settings.yt_dlp_binary,
        "--no-playlist",
        "--extract-audio",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "0",
        "--js-runtimes",
        "deno",
        "--ffmpeg-location",
        ffmpeg_path,
    ]

    if settings.yt_dlp_proxy_url:
        command.extend(["--proxy", settings.yt_dlp_proxy_url])

    if cookies_file:
        command.extend(["--cookies", cookies_file])

    extra_args = settings.yt_dlp_extra_args.strip()
    if extra_args:
        command.extend(shlex.split(extra_args))

    command.extend(
        [
            "--output",
            output_template,
            url,
        ]
    )
    return command


def convert_youtube_to_mp3(
    url: str,
    settings: Settings,
    requested_filename: str | None = None,
) -> ConversionResult:
    validate_youtube_url(url)
    _require_binary(settings.yt_dlp_binary)
    _require_binary(settings.ffmpeg_binary)

    temp_dir = Path(tempfile.mkdtemp(prefix="youtube-mp3-"))
    output_template = str(temp_dir / "%(title).120B-%(id)s.%(ext)s")
    cookies_file = _materialize_cookies_file(settings, temp_dir)
    command = build_download_command(url, output_template, settings, cookies_file)

    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=settings.conversion_timeout_seconds,
        )
    except FileNotFoundError as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise BinaryNotFoundError(
            f"Required executable {exc.filename!r} is not available on the host."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise ConversionFailedError(
            f"Audio conversion timed out after {settings.conversion_timeout_seconds} seconds."
        ) from exc

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        shutil.rmtree(temp_dir, ignore_errors=True)
        message = stderr or stdout or "yt-dlp failed without returning diagnostics."
        raise ConversionFailedError(message)

    output_files = sorted(temp_dir.glob("*.mp3"))
    if len(output_files) != 1:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise ConversionFailedError(
            "Conversion did not produce exactly one MP3 file."
        )

    output_path = output_files[0]
    download_name = sanitize_filename(requested_filename, output_path.stem)
    return ConversionResult(
        file_path=output_path,
        download_name=download_name,
        cleanup=lambda: shutil.rmtree(temp_dir, ignore_errors=True),
    )
