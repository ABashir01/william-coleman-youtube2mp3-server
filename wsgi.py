"""WSGI entrypoint for PythonAnywhere and similar hosts."""

from youtube_mp3_server import create_app

application = create_app()
