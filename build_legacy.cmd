@echo off
REM Legacy build script disabling BuildKit and using fallback Dockerfile/compose.
SET DOCKER_BUILDKIT=0
echo Building with DOCKER_BUILDKIT=0 using Dockerfile.fallback ...
docker compose -f docker-compose.nobuildkit.yml build
if errorlevel 1 (
  echo Build failed.
  exit /b 1
)
echo Starting services...
docker compose -f docker-compose.nobuildkit.yml up