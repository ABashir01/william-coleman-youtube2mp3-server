"""Development entrypoint using the standard library WSGI server."""

from __future__ import annotations

import os
from wsgiref.simple_server import make_server

from youtube_mp3_server import create_app


def main() -> None:
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    application = create_app()
    with make_server(host, port, application) as server:
        print(f"Serving on http://{host}:{port}")
        server.serve_forever()


if __name__ == "__main__":
    main()
