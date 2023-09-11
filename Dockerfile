FROM python:3.9-slim-buster

# Don't buffer python output
ENV PYTHONUNBUFFERED=1

WORKDIR /stemgen

RUN apt-get update && apt-get install -y \
    ffmpeg \
    sox \
    git \
    gpac \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip \
    && pip install demucs mutagen

COPY . /stemgen/

ENTRYPOINT ["python3", "stemgen.py"]
