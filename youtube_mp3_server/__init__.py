"""WSGI application package for YouTube to MP3 conversion."""

from .app import create_app

__all__ = ["create_app"]
