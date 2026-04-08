"""Application-level exceptions."""

from __future__ import annotations


class RequestError(Exception):
    """Raised when the client request is invalid."""


class RequestTooLargeError(RequestError):
    """Raised when the request body exceeds the configured limit."""


class InvalidYoutubeUrlError(RequestError):
    """Raised when the supplied URL is not a supported YouTube URL."""


class BinaryNotFoundError(RuntimeError):
    """Raised when a required host executable is not available."""


class ConversionFailedError(RuntimeError):
    """Raised when yt-dlp or ffmpeg fail to produce the MP3."""
