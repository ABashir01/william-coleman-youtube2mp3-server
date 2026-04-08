"""WSGI application for the YouTube to MP3 API."""

from __future__ import annotations

from http import HTTPStatus
import io
import json
from typing import Callable, Iterable

from .config import Settings, load_settings
from .errors import (
    BinaryNotFoundError,
    ConversionFailedError,
    InvalidYoutubeUrlError,
    RequestError,
    RequestTooLargeError,
)
from .service import ConversionResult, convert_youtube_to_mp3, get_runtime_health

ResponseBody = Iterable[bytes]
StartResponse = Callable[[str, list[tuple[str, str]]], None]
Converter = Callable[[str, Settings, str | None], ConversionResult]
HealthChecker = Callable[[Settings], dict[str, object]]


def _json_response(
    status: HTTPStatus,
    payload: dict[str, object],
) -> tuple[str, list[tuple[str, str]], ResponseBody]:
    body = json.dumps(payload).encode("utf-8")
    headers = [
        ("Content-Type", "application/json; charset=utf-8"),
        ("Content-Length", str(len(body))),
    ]
    return f"{status.value} {status.phrase}", headers, [body]


def _read_request_body(environ: dict[str, object], max_bytes: int) -> bytes:
    raw_length = environ.get("CONTENT_LENGTH", "")
    try:
        content_length = int(raw_length) if raw_length else 0
    except ValueError as exc:
        raise RequestError("CONTENT_LENGTH must be an integer.") from exc

    if content_length > max_bytes:
        raise RequestTooLargeError(
            f"Request body exceeds the maximum size of {max_bytes} bytes."
        )

    stream = environ["wsgi.input"]
    if content_length == 0:
        data = stream.read(max_bytes + 1)
    else:
        data = stream.read(content_length)

    if len(data) > max_bytes:
        raise RequestTooLargeError(
            f"Request body exceeds the maximum size of {max_bytes} bytes."
        )
    return data


def _parse_json_request(environ: dict[str, object], settings: Settings) -> dict[str, object]:
    body = _read_request_body(environ, settings.max_request_bytes)
    if not body:
        raise RequestError("Request body is required.")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RequestError("Request body must be valid UTF-8 JSON.") from exc
    if not isinstance(payload, dict):
        raise RequestError("Request body must be a JSON object.")
    return payload


def _stream_file(result: ConversionResult, chunk_size: int = 64 * 1024) -> ResponseBody:
    def iterator() -> Iterable[bytes]:
        try:
            with result.file_path.open("rb") as handle:
                while True:
                    chunk = handle.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
        finally:
            result.cleanup()

    return iterator()


def create_app(
    settings: Settings | None = None,
    converter: Converter = convert_youtube_to_mp3,
    health_checker: HealthChecker = get_runtime_health,
) -> Callable[[dict[str, object], StartResponse], ResponseBody]:
    resolved_settings = settings or load_settings()

    def app(environ: dict[str, object], start_response: StartResponse) -> ResponseBody:
        method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        path = str(environ.get("PATH_INFO", ""))

        if path == resolved_settings.health_route_path:
            if method != "GET":
                status, headers, body = _json_response(
                    HTTPStatus.METHOD_NOT_ALLOWED,
                    {"error": "method_not_allowed", "message": "Use GET for this endpoint."},
                )
                headers.append(("Allow", "GET"))
                start_response(status, headers)
                return body

            payload = health_checker(resolved_settings)
            status_code = HTTPStatus.OK if payload.get("status") == "ok" else HTTPStatus.SERVICE_UNAVAILABLE
            status, headers, body = _json_response(status_code, payload)
            start_response(status, headers)
            return body

        if path != resolved_settings.route_path:
            status, headers, body = _json_response(
                HTTPStatus.NOT_FOUND,
                {"error": "not_found", "message": "The requested path does not exist."},
            )
            start_response(status, headers)
            return body

        if method != "POST":
            status, headers, body = _json_response(
                HTTPStatus.METHOD_NOT_ALLOWED,
                {"error": "method_not_allowed", "message": "Use POST for this endpoint."},
            )
            headers.append(("Allow", "POST"))
            start_response(status, headers)
            return body

        try:
            payload = _parse_json_request(environ, resolved_settings)
            url = payload.get("url")
            filename = payload.get("filename")
            if not isinstance(url, str) or not url.strip():
                raise RequestError("Field 'url' is required and must be a non-empty string.")
            if filename is not None and not isinstance(filename, str):
                raise RequestError("Field 'filename' must be a string when provided.")

            conversion = converter(url.strip(), resolved_settings, filename)
            headers = [
                ("Content-Type", "audio/mpeg"),
                (
                    "Content-Disposition",
                    f'attachment; filename="{conversion.download_name}"',
                ),
            ]
            try:
                headers.append(
                    ("Content-Length", str(conversion.file_path.stat().st_size))
                )
            except OSError:
                pass

            start_response(f"{HTTPStatus.OK.value} {HTTPStatus.OK.phrase}", headers)
            return _stream_file(conversion)
        except RequestTooLargeError as exc:
            status, headers, body = _json_response(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                {"error": "request_too_large", "message": str(exc)},
            )
        except (RequestError, InvalidYoutubeUrlError) as exc:
            status, headers, body = _json_response(
                HTTPStatus.BAD_REQUEST,
                {"error": "bad_request", "message": str(exc)},
            )
        except BinaryNotFoundError as exc:
            status, headers, body = _json_response(
                HTTPStatus.SERVICE_UNAVAILABLE,
                {"error": "missing_binary", "message": str(exc)},
            )
        except ConversionFailedError as exc:
            status, headers, body = _json_response(
                HTTPStatus.BAD_GATEWAY,
                {"error": "conversion_failed", "message": str(exc)},
            )
        except Exception:
            status, headers, body = _json_response(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {
                    "error": "internal_error",
                    "message": "The server hit an unexpected error.",
                },
            )

        start_response(status, headers)
        return body

    return app


def make_test_environ(body: bytes, path: str, method: str = "POST") -> dict[str, object]:
    return {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": io.BytesIO(body),
    }
