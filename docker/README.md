# Forge sandbox

Build the image with:

```bash
docker build -f docker/Dockerfile.sandbox -t forge-sandbox:latest .
```

Hosted Forge should run repository commands through the Docker sandbox rather than directly on the worker host.

The Python Docker SDK currently defaults to a disposable Python 3.13 container with network disabled, CPU/memory/PID limits, and only the workspace mounted.
