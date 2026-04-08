# YouTube MP3 Server

A small Python service that accepts a YouTube URL and returns the extracted audio as an MP3 file.

The API is designed to be simple to call from automation tools such as n8n, while remaining easy to run locally or deploy as a containerized web service.

## What It Does

- Accepts a YouTube URL over HTTP
- Downloads and converts the audio to MP3
- Returns the MP3 file directly in the response
- Exposes a health endpoint for deployment checks

## API

### `GET /api/v1/health`

Returns runtime status information for the binaries the service depends on.

Example response:

```json
{
  "status": "ok",
  "checks": {
    "yt_dlp": {
      "binary": "yt-dlp",
      "available": true
    },
    "ffmpeg": {
      "binary": "ffmpeg",
      "available": true
    }
  }
}
```

### `POST /api/v1/convert`

Accepts a JSON body:

```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "filename": "optional-download-name"
}
```

Success response:

- `200 OK`
- `Content-Type: audio/mpeg`
- `Content-Disposition: attachment; filename="...mp3"`

Error responses:

- `400 Bad Request` for invalid JSON or invalid YouTube URLs
- `413` for oversized requests
- `502 Bad Gateway` when conversion fails
- `503 Service Unavailable` when `yt-dlp` or `ffmpeg` is unavailable

## Requirements

- Python 3.11+
- `yt-dlp`
- `ffmpeg`

`yt-dlp` is installed from `requirements.txt`. `ffmpeg` is a native system dependency and must be available on the host, or provided explicitly through `FFMPEG_BINARY`.

## Local Setup

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
py -m unittest discover -s tests
py run_server.py
```

If `ffmpeg` is not on `PATH`, set it explicitly before starting the server:

```powershell
$env:FFMPEG_BINARY = "C:\full\path\to\ffmpeg.exe"
py run_server.py
```

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m unittest discover -s tests
python run_server.py
```

## Testing the Service

Health check:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

Convert a video:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/convert \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ","filename":"sample"}' \
  --output sample.mp3
```

## n8n Integration

This service works well behind an n8n HTTP Request node.

Recommended n8n request settings:

- Method: `POST`
- URL: `https://your-service/api/v1/convert`
- Body type: JSON
- Required field: `url`
- Optional field: `filename`
- Response format: binary/file

Because the API returns the MP3 directly, the output can be sent to storage, email, transcription, or upload steps without needing a second download request.

## Deployment

### Recommended: Render with Docker

This repository includes:

- `Dockerfile`
- `render.yaml`

That deployment path is the simplest because the container installs `ffmpeg` itself, which avoids host-specific setup.

Basic flow:

1. Push the repository to GitHub.
2. Create a new Render Web Service from the repo.
3. Use the included Docker configuration.
4. Set the health check path to `/api/v1/health`.
5. Deploy.

After deployment:

```bash
curl https://your-service.onrender.com/api/v1/health
curl -X POST https://your-service.onrender.com/api/v1/convert \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ","filename":"sample"}' \
  --output sample.mp3
```

### Other Hosts

Any host that can run a Python web service and provide `ffmpeg` can run this project. The included `wsgi.py` also makes it compatible with traditional WSGI platforms.

## Configuration

The service can be configured with environment variables:

- `YT_DLP_BINARY`
- `FFMPEG_BINARY`
- `CONVERSION_TIMEOUT_SECONDS`
- `MAX_REQUEST_BYTES`
- `CONVERT_ROUTE_PATH`
- `HEALTH_ROUTE_PATH`
- `HOST`
- `PORT`

## Project Layout

- `youtube_mp3_server/app.py`: HTTP request handling
- `youtube_mp3_server/service.py`: URL validation, runtime checks, conversion logic
- `youtube_mp3_server/config.py`: environment-driven settings
- `run_server.py`: local development server
- `wsgi.py`: WSGI entrypoint
- `tests/`: unit tests

## Notes

- The service returns the MP3 file itself, not a JSON link to a file.
- The current design performs conversion during the request, so very long videos may be a poor fit for low-timeout hosting environments.
