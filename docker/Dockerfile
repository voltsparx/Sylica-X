FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV SILICA_OUTPUT_DIR=/app/output

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY core ./core
COPY platforms ./platforms
COPY plugins ./plugins
COPY filters ./filters
COPY docs ./docs
COPY silica-x.py LICENSE README.md ./

RUN useradd --create-home --shell /usr/sbin/nologin silica \
    && mkdir -p /app/output/data /app/output/html /app/output/cli /app/output/logs \
    && chown -R silica:silica /app

USER silica

VOLUME ["/app/output"]

ENTRYPOINT ["python", "silica-x.py"]
