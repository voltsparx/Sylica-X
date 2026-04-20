# Silica-X Docker Guide

## Quick Start

Run Silica-X in Docker with a single flag:

    silica-x --docker

This will:
1. Detect your OS and check if Docker is installed
2. Install Docker automatically if missing (with your permission)
3. Build the Silica-X Docker image on first run
4. Launch the framework inside the container with output mounted to ./output

## Prompt Mode in Docker

    silica-x prompt --docker

Launches the full interactive prompt mode inside Docker. All scan artifacts
are saved to ./output on your host machine.

## With Tor Anonymization

    silica-x prompt --docker --tor

Starts Tor inside the container before launching the framework.

## Force Rebuild Image

    silica-x --docker --docker-rebuild

Forces a full rebuild of the Docker image. Use after pulling updates.

## Running Any Command in Docker

    silica-x profile johndoe --docker
    silica-x surface example.com --docker
    silica-x fusion johndoe example.com --docker
    silica-x quicktest --docker

## Manual Docker Usage

Build the image manually:

    docker build -f docker/Dockerfile -t silica-x:latest .

Run prompt mode:

    docker run -it --rm -v $(pwd)/output:/app/output silica-x:latest prompt

Using docker compose:

    docker compose -f docker/docker-compose.yml up silica-x

## Checking Docker Status

    silica-x doctor

The doctor command shows Docker binary status, daemon status, and whether
the Silica-X image is built.

## What is Installed in the Container

- Python 3.12
- Tesseract OCR
- Tor
- nmap
- All Python dependencies from requirements.txt
- The full Silica-X framework

## Output Persistence

All scan artifacts are written to /app/output inside the container, which
is mounted from ./output on your host. Results persist after container exits.

## Environment Variables

- SILICA_X_DOCKER=1  Set automatically when running in Docker
- SILICA_X_TOR=1     Set when Tor is active inside the container
