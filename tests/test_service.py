from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from youtube_mp3_server.config import Settings
from youtube_mp3_server.errors import (
    BinaryNotFoundError,
    ConversionFailedError,
    InvalidYoutubeUrlError,
)
from youtube_mp3_server.service import (
    _materialize_cookies_file,
    build_download_command,
    convert_youtube_to_mp3,
    resolve_binary_path,
    sanitize_filename,
    validate_youtube_url,
)


class ValidateYoutubeUrlTests(unittest.TestCase):
    def test_accepts_standard_youtube_url(self) -> None:
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.assertEqual(validate_youtube_url(url), url)

    def test_rejects_non_youtube_host(self) -> None:
        with self.assertRaises(InvalidYoutubeUrlError):
            validate_youtube_url("https://example.com/watch?v=dQw4w9WgXcQ")

    def test_rejects_missing_scheme(self) -> None:
        with self.assertRaises(InvalidYoutubeUrlError):
            validate_youtube_url("youtube.com/watch?v=dQw4w9WgXcQ")

    def test_rejects_youtube_homepage_url(self) -> None:
        with self.assertRaises(InvalidYoutubeUrlError):
            validate_youtube_url("https://www.youtube.com/")


class SanitizeFilenameTests(unittest.TestCase):
    def test_adds_mp3_extension(self) -> None:
        self.assertEqual(sanitize_filename("Episode 1", "fallback"), "Episode-1.mp3")

    def test_uses_fallback_when_filename_is_empty(self) -> None:
        self.assertEqual(sanitize_filename("???", "fallback"), "fallback.mp3")


class BuildDownloadCommandTests(unittest.TestCase):
    def test_builds_expected_command(self) -> None:
        settings = Settings(yt_dlp_binary="yt-dlp-bin", ffmpeg_binary="ffmpeg-bin")
        with patch("youtube_mp3_server.service.shutil.which", return_value="/usr/bin/ffmpeg"):
            command = build_download_command(
                "https://youtu.be/dQw4w9WgXcQ",
                "/tmp/output.%(ext)s",
                settings,
            )
            self.assertEqual(
                command,
                [
                    "yt-dlp-bin",
                    "--no-playlist",
                    "--extract-audio",
                    "--audio-format",
                    "mp3",
                    "--audio-quality",
                    "0",
                    "--js-runtimes",
                    "deno",
                    "--ffmpeg-location",
                    "/usr/bin/ffmpeg",
                    "--output",
                    "/tmp/output.%(ext)s",
                    "https://youtu.be/dQw4w9WgXcQ",
                ],
            )

    def test_includes_optional_proxy_cookies_and_extra_args(self) -> None:
        settings = Settings(
            yt_dlp_binary="yt-dlp-bin",
            ffmpeg_binary="ffmpeg-bin",
            yt_dlp_proxy_url="http://proxy.example:8080",
            yt_dlp_extra_args="--impersonate chrome --extractor-args youtube:player_client=tv",
        )
        with patch("youtube_mp3_server.service.shutil.which", return_value="/usr/bin/ffmpeg"):
            command = build_download_command(
                "https://youtu.be/dQw4w9WgXcQ",
                "/tmp/output.%(ext)s",
                settings,
                "/tmp/cookies.txt",
            )

        self.assertIn("--proxy", command)
        self.assertIn("http://proxy.example:8080", command)
        self.assertIn("--cookies", command)
        self.assertIn("/tmp/cookies.txt", command)
        self.assertIn("--impersonate", command)
        self.assertIn("chrome", command)
        self.assertIn("youtube:player_client=tv", command)


class ResolveBinaryPathTests(unittest.TestCase):
    def test_resolves_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "ffmpeg.exe"
            binary.write_text("binary")
            self.assertEqual(resolve_binary_path(str(binary)), str(binary))

    def test_raises_when_binary_is_missing(self) -> None:
        with patch("youtube_mp3_server.service.shutil.which", return_value=None):
            with self.assertRaises(BinaryNotFoundError):
                resolve_binary_path("missing-binary")


class CookiesMaterializationTests(unittest.TestCase):
    def test_uses_explicit_cookie_file_when_present(self) -> None:
        settings = Settings(yt_dlp_cookies_file="/tmp/cookies.txt")
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(
                _materialize_cookies_file(settings, Path(directory)),
                "/tmp/cookies.txt",
            )

    def test_materializes_base64_cookie_content(self) -> None:
        settings = Settings(yt_dlp_cookies_base64="Y29va2llLWRhdGE=")
        with tempfile.TemporaryDirectory() as directory:
            cookie_path = Path(_materialize_cookies_file(settings, Path(directory)))
            self.assertEqual(cookie_path.read_bytes(), b"cookie-data")

    def test_rejects_invalid_base64_cookie_content(self) -> None:
        settings = Settings(yt_dlp_cookies_base64="%%invalid%%")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ConversionFailedError):
                _materialize_cookies_file(settings, Path(directory))


class ConvertYoutubeToMp3Tests(unittest.TestCase):
    def test_returns_conversion_result_when_mp3_exists(self) -> None:
        settings = Settings(conversion_timeout_seconds=30)
        with tempfile.TemporaryDirectory() as directory:
            temp_dir = Path(directory)
            expected_output = temp_dir / "sample-title-abc123.mp3"
            expected_output.write_bytes(b"mp3-data")

            with patch("youtube_mp3_server.service.tempfile.mkdtemp", return_value=str(temp_dir)):
                with patch("youtube_mp3_server.service.shutil.which", return_value="binary"):
                    with patch("youtube_mp3_server.service.subprocess.run") as mock_run:
                        mock_run.return_value.returncode = 0
                        mock_run.return_value.stderr = ""
                        mock_run.return_value.stdout = ""

                        result = convert_youtube_to_mp3(
                            "https://youtu.be/dQw4w9WgXcQ",
                            settings,
                            "custom name",
                        )

            self.assertEqual(result.file_path, expected_output)
            self.assertEqual(result.download_name, "custom-name.mp3")
            result.cleanup()
            self.assertFalse(temp_dir.exists())

    def test_raises_binary_not_found_when_yt_dlp_is_missing(self) -> None:
        settings = Settings()
        with patch("youtube_mp3_server.service.shutil.which", side_effect=[None, "ffmpeg"]):
            with self.assertRaises(BinaryNotFoundError):
                convert_youtube_to_mp3(
                    "https://youtu.be/dQw4w9WgXcQ",
                    settings,
                )

    def test_raises_when_download_fails(self) -> None:
        settings = Settings()
        with tempfile.TemporaryDirectory() as directory:
            with patch("youtube_mp3_server.service.tempfile.mkdtemp", return_value=directory):
                with patch("youtube_mp3_server.service.shutil.which", return_value="binary"):
                    with patch("youtube_mp3_server.service.subprocess.run") as mock_run:
                        mock_run.return_value.returncode = 1
                        mock_run.return_value.stderr = "download failed"
                        mock_run.return_value.stdout = ""

                        with self.assertRaises(ConversionFailedError):
                            convert_youtube_to_mp3(
                                "https://youtu.be/dQw4w9WgXcQ",
                                settings,
                            )


if __name__ == "__main__":
    unittest.main()
