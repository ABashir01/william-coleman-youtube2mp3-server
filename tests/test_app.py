from __future__ import annotations

import io
import json
from pathlib import Path
import tempfile
import unittest

from youtube_mp3_server.app import create_app, make_test_environ
from youtube_mp3_server.config import Settings
from youtube_mp3_server.errors import BinaryNotFoundError, ConversionFailedError
from youtube_mp3_server.service import ConversionResult


class AppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings(route_path="/api/v1/convert")

    def _call_app(self, app, environ):
        captured = {}

        def start_response(status, headers):
            captured["status"] = status
            captured["headers"] = headers

        body = b"".join(app(environ, start_response))
        captured["body"] = body
        return captured

    def test_returns_404_for_unknown_route(self) -> None:
        app = create_app(settings=self.settings)
        response = self._call_app(
            app,
            make_test_environ(b"{}", "/wrong-path"),
        )
        self.assertEqual(response["status"], "404 Not Found")

    def test_returns_200_for_healthy_runtime(self) -> None:
        def health_checker(settings):
            self.assertEqual(settings.health_route_path, "/api/v1/health")
            return {
                "status": "ok",
                "checks": {
                    "yt_dlp": {"binary": "yt-dlp", "available": True},
                    "ffmpeg": {"binary": "ffmpeg", "available": True},
                },
            }

        app = create_app(settings=self.settings, health_checker=health_checker)
        response = self._call_app(
            app,
            make_test_environ(b"", self.settings.health_route_path, method="GET"),
        )
        self.assertEqual(response["status"], "200 OK")
        payload = json.loads(response["body"])
        self.assertEqual(payload["status"], "ok")

    def test_returns_503_for_degraded_runtime(self) -> None:
        app = create_app(
            settings=self.settings,
            health_checker=lambda settings: {
                "status": "degraded",
                "checks": {
                    "yt_dlp": {"binary": "yt-dlp", "available": True},
                    "ffmpeg": {"binary": "ffmpeg", "available": False},
                },
            },
        )
        response = self._call_app(
            app,
            make_test_environ(b"", self.settings.health_route_path, method="GET"),
        )
        self.assertEqual(response["status"], "503 Service Unavailable")
        payload = json.loads(response["body"])
        self.assertEqual(payload["status"], "degraded")

    def test_rejects_non_get_method_for_health_route(self) -> None:
        app = create_app(settings=self.settings)
        response = self._call_app(
            app,
            make_test_environ(b"{}", self.settings.health_route_path, method="POST"),
        )
        self.assertEqual(response["status"], "405 Method Not Allowed")

    def test_rejects_non_post_methods(self) -> None:
        app = create_app(settings=self.settings)
        response = self._call_app(
            app,
            make_test_environ(b"{}", self.settings.route_path, method="GET"),
        )
        self.assertEqual(response["status"], "405 Method Not Allowed")

    def test_returns_mp3_response_for_valid_request(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            mp3_path = Path(directory) / "clip.mp3"
            mp3_path.write_bytes(b"fake-audio")

            def converter(url, settings, filename):
                self.assertEqual(url, "https://youtu.be/dQw4w9WgXcQ")
                self.assertEqual(filename, "episode")
                return ConversionResult(
                    file_path=mp3_path,
                    download_name="episode.mp3",
                    cleanup=lambda: None,
                )

            app = create_app(settings=self.settings, converter=converter)
            body = json.dumps(
                {"url": "https://youtu.be/dQw4w9WgXcQ", "filename": "episode"}
            ).encode("utf-8")
            response = self._call_app(
                app,
                make_test_environ(body, self.settings.route_path),
            )

        self.assertEqual(response["status"], "200 OK")
        headers = dict(response["headers"])
        self.assertEqual(headers["Content-Type"], "audio/mpeg")
        self.assertEqual(headers["Content-Disposition"], 'attachment; filename="episode.mp3"')
        self.assertEqual(response["body"], b"fake-audio")

    def test_returns_400_for_invalid_json(self) -> None:
        app = create_app(settings=self.settings)
        environ = {
            "REQUEST_METHOD": "POST",
            "PATH_INFO": self.settings.route_path,
            "CONTENT_LENGTH": "7",
            "wsgi.input": io.BytesIO(b"{oops}"),
        }
        response = self._call_app(app, environ)
        self.assertEqual(response["status"], "400 Bad Request")
        payload = json.loads(response["body"])
        self.assertEqual(payload["error"], "bad_request")

    def test_returns_400_for_missing_url(self) -> None:
        app = create_app(settings=self.settings)
        body = json.dumps({"filename": "episode"}).encode("utf-8")
        response = self._call_app(
            app,
            make_test_environ(body, self.settings.route_path),
        )
        self.assertEqual(response["status"], "400 Bad Request")

    def test_returns_413_for_oversized_request(self) -> None:
        settings = Settings(route_path="/api/v1/convert", max_request_bytes=4)
        app = create_app(settings=settings)
        body = json.dumps({"url": "https://youtu.be/dQw4w9WgXcQ"}).encode("utf-8")
        response = self._call_app(
            app,
            make_test_environ(body, settings.route_path),
        )
        self.assertTrue(response["status"].startswith("413 "))
        payload = json.loads(response["body"])
        self.assertEqual(payload["error"], "request_too_large")

    def test_returns_503_when_required_binary_is_missing(self) -> None:
        def converter(url, settings, filename):
            raise BinaryNotFoundError("ffmpeg missing")

        app = create_app(settings=self.settings, converter=converter)
        body = json.dumps({"url": "https://youtu.be/dQw4w9WgXcQ"}).encode("utf-8")
        response = self._call_app(
            app,
            make_test_environ(body, self.settings.route_path),
        )
        self.assertEqual(response["status"], "503 Service Unavailable")

    def test_returns_502_when_conversion_fails(self) -> None:
        def converter(url, settings, filename):
            raise ConversionFailedError("conversion failed")

        app = create_app(settings=self.settings, converter=converter)
        body = json.dumps({"url": "https://youtu.be/dQw4w9WgXcQ"}).encode("utf-8")
        response = self._call_app(
            app,
            make_test_environ(body, self.settings.route_path),
        )
        self.assertEqual(response["status"], "502 Bad Gateway")


if __name__ == "__main__":
    unittest.main()
