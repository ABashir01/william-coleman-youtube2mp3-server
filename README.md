# YouTube MP3 Server

This repository now contains a small Python WSGI service that accepts a YouTube URL and returns an MP3 download. The API is designed to be easy to call from n8n and simple to deploy on a host that supports Python WSGI apps.

## API

- Health check:
  - Method: `GET`
  - Path: `/api/v1/health`
- Method: `POST`
- Path: `/api/v1/convert`
- Request body:

```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "filename": "optional-download-name"
}
```

- Success response:
  - `200 OK`
  - `Content-Type: audio/mpeg`
  - `Content-Disposition: attachment; filename="...mp3"`

- Error responses:
  - `400` for invalid JSON or invalid YouTube URLs
  - `502` for downloader/conversion failures
  - `503` when a required host binary is unavailable

The health endpoint returns JSON indicating whether `yt-dlp` and `ffmpeg` are currently available to the app process.

## Implementation Notes

The server itself uses only the Python standard library. Media conversion is delegated to two host executables:

- `yt-dlp`
- `ffmpeg`

This keeps the repo free of Python package dependencies while still making the service deployable on a standard Python host.

## Files

- `youtube_mp3_server/app.py`: WSGI request handling and response formatting
- `youtube_mp3_server/service.py`: YouTube URL validation and `yt-dlp` execution
- `wsgi.py`: host-facing WSGI entrypoint
- `run_server.py`: local development server
- `tests/`: focused `unittest` coverage
- `Dockerfile`: container image for Render or any Docker host
- `render.yaml`: Render service definition with health check wiring

## Running Locally

You need Python 3.11+ and `ffmpeg` available on `PATH`. The project now includes a `requirements.txt` that installs `yt-dlp` into a virtual environment.

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
ffmpeg -version
py -m unittest discover -s tests
py run_server.py
```

### macOS or Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
ffmpeg -version
python -m unittest discover -s tests
python run_server.py
```

Then send a request like:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/convert \
  -H "Content-Type: application/json" \
  -d "{\"url\":\"https://www.youtube.com/watch?v=dQw4w9WgXcQ\",\"filename\":\"episode\"}" \
  --output episode.mp3
```

Check runtime readiness with:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

## PythonAnywhere Deployment Shape

1. Upload this project.
2. Create a Python web app.
3. Point the PythonAnywhere WSGI configuration at `wsgi.py`.
4. Create a virtualenv for the app and install `requirements.txt` so `yt-dlp` is available inside that environment.
5. Ensure `ffmpeg` is installed and reachable by the app process.
6. Optionally set:
   - `YT_DLP_BINARY`
   - `FFMPEG_BINARY`
   - `CONVERSION_TIMEOUT_SECONDS`
   - `MAX_REQUEST_BYTES`
   - `CONVERT_ROUTE_PATH`
   - `HEALTH_ROUTE_PATH`

## n8n Integration

Use an HTTP Request node configured to:

- send `POST` requests
- target `/api/v1/convert`
- send JSON with the `url` field
- treat the response as a file/binary payload

Because the server returns raw MP3 bytes, n8n can hand the result directly to downstream storage, email, transcription, or upload nodes.

For deployment monitoring, point a simple HTTP check at `/api/v1/health` before sending real conversion traffic.

## Render Deployment

The easiest deployment path for this project is a Docker-based Render web service. The container image installs `ffmpeg`, installs `yt-dlp` from `requirements.txt`, binds the server to `0.0.0.0`, and exposes `/api/v1/health` for Render health checks.

### Local Docker smoke test

```bash
docker build -t youtube-mp3-server .
docker run --rm -p 10000:10000 youtube-mp3-server
```

Then verify:

```bash
curl http://127.0.0.1:10000/api/v1/health
```

### Deploy on Render

1. Push this repository to GitHub.
2. In Render, create a new Web Service from the repo.
3. Let Render detect the included `Dockerfile` or `render.yaml`.
4. Confirm the health check path is `/api/v1/health`.
5. Deploy.

After the first deploy, test:

```bash
curl https://your-service-name.onrender.com/api/v1/health
curl -X POST https://your-service-name.onrender.com/api/v1/convert \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=dQw4w9WgXcQ","filename":"episode"}' \
  --output episode.mp3
```

## Deployment Recommendation

For this codebase, Render with Docker is the easiest host to operate because the runtime is fully defined in the repo. That avoids host-specific setup for `ffmpeg`, which is the awkward part of PythonAnywhere-style deployment.
