FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV HOST=0.0.0.0
ENV PORT=10000
ENV YT_DLP_BINARY=yt-dlp
ENV FFMPEG_BINARY=ffmpeg

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg unzip curl \
    && curl -fsSL https://deno.land/install.sh | sh \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.deno/bin:${PATH}"

WORKDIR /app

COPY requirements.txt ./
RUN python -m pip install --upgrade pip \
    && python -m pip install -r requirements.txt

COPY . .

EXPOSE 10000

CMD ["python", "run_server.py"]
