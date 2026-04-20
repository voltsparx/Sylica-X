# Silica-X Intelligence Framework — Docker Image
# Build: docker build -f docker/Dockerfile -t silica-x:latest .
# Run:   docker run -it --rm silica-x:latest

FROM python:3.12-slim

LABEL maintainer="voltsparx@gmail.com"
LABEL org.opencontainers.image.title="Silica-X"
LABEL org.opencontainers.image.description="Multi-engine OSINT orchestration framework"
LABEL org.opencontainers.image.source="https://github.com/voltsparx/Silica-X"

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    tor \
    curl \
    wget \
    git \
    nmap \
    dnsutils \
    iputils-ping \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt requirements-dev.txt pyproject.toml ./

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

RUN pip install --no-cache-dir -e .

COPY docker/torrc.silica_x /etc/tor/torrc

RUN mkdir -p /app/output

ENTRYPOINT ["silica-x"]
CMD ["--help"]
