FROM python:3.9-slim-bookworm

# Don't buffer python output
ENV PYTHONUNBUFFERED=1

WORKDIR /stemgen

RUN apt-get update && apt-get install -y \
    ffmpeg \
    sox \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip \
    && pip install torch torchaudio --index-url https://download.pytorch.org/whl/cpu \
    && pip install demucs mutagen

COPY . /stemgen/

ENTRYPOINT ["python3", "stemgen.py"]
