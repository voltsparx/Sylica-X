ARG PYTHON_VERSION=3.13
FROM python:${PYTHON_VERSION}-slim-bookworm

LABEL org.opencontainers.image.title="Silica-X" \
      org.opencontainers.image.description="Silica-X multi-OSINT runtime container" \
      org.opencontainers.image.source="https://github.com/voltsparx/Silica-X"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV SILICA_OUTPUT_DIR=/app/output
ENV SILICA_RUNTIME=docker

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY core ./core
COPY platforms ./platforms
COPY plugins ./plugins
COPY filters ./filters
COPY modules ./modules
COPY intel ./intel
COPY docs ./docs
COPY silica-x.py LICENSE README.md ./

RUN useradd --create-home --shell /usr/sbin/nologin silica \
    && mkdir -p /app/output/json /app/output/html /app/output/cli /app/output/csv /app/output/logs \
    && chown -R silica:silica /app

USER silica

VOLUME ["/app/output"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import core; import core.runner; print('ok')" || exit 1

ENTRYPOINT ["python", "silica-x.py"]
