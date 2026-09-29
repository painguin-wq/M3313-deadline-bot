# ✅ CI/CD Setup Complete

## Status

- ✅ **Docker**: Multi-stage Dockerfile, non-root user, layer caching optimized
- ✅ **Environment Validation**: Required env vars checked on startup
- ✅ **GitHub Actions Build**: `build.yml` automatically builds and pushes to `ghcr.io/painguin-wq/deadline-bot:latest`
- ✅ **GitHub Actions Deploy**: `deploy.yml` (optional, requires SSH secrets)
- ✅ **Repo Secrets**: TOKEN and MAIN_GROUP_ID already configured

## Current Setup

### Build Workflow (`build.yml`)
**Status**: ✅ Running successfully

Triggers on:
- Push to `main` branch
- Changes to: `Dockerfile`, `requirements.txt`, `main.py`, `DEADLINES.json`, `.dockerignore`

Output:
- Image pushed to: `ghcr.io/painguin-wq/deadline-bot:latest`
- Tags: `main`, `latest`, and commit SHA

### Deploy Workflow (`deploy.yml`)
**Status**: Optional (requires SSH secrets)

Will trigger automatically after successful build IF you add these secrets:
- `SSH_PRIVATE_KEY`
- `SSH_PORT`
- `SERVER_IP`
- `USERNAME`
- `PROJECT_PATH`

If secrets are not present, the workflow will skip (no errors).

## What's Working Now

1. **Docker image builds automatically** when you push to main
2. **Image is available** at `ghcr.io/painguin-wq/deadline-bot:latest`
3. **Environment variables are validated** at container startup

## How to Use

### Option A: Local Testing
```bash
# Build locally
docker build -t deadline-bot:test .

# Run with your env file
docker compose --env-file .env up -d

# Check logs
docker compose logs -f deadline-bot

# Stop
docker compose down
```

### Option B: Use Pre-built Image from GitHub
```bash
# Pull the latest built image
docker pull ghcr.io/painguin-wq/deadline-bot:latest

# Run directly
docker run -d \
  --name deadline-bot \
  --env-file .env \
  -v /etc/localtime:/etc/localtime:ro \
  -v ./DEADLINES.json:/app/DEADLINES.json \
  -v ./board-data:/app/board-data \
  ghcr.io/painguin-wq/deadline-bot:latest
```

### Option C: Deploy to Remote Server (Optional Setup)

Add these secrets to GitHub Settings → Secrets and variables → Actions:
```
SSH_PRIVATE_KEY     = your SSH private key (full content)
SSH_PORT            = 22 (or your SSH port)
SERVER_IP           = 192.168.1.100 (your server IP)
USERNAME            = botuser (SSH username)
PROJECT_PATH        = /home/botuser/deadline-bot (project directory)
```

Then the deploy workflow will automatically:
1. SSH into your server
2. Pull the latest image
3. Restart the container with `docker compose up -d --pull always`
4. Show deployment status

## Monitoring Workflows

View workflow runs: https://github.com/painguin-wq/M3313-deadline-bot/actions

**Build workflow**: Shows Docker image build progress
**Deploy workflow**: Only runs if SSH secrets are present

## Image Registry

Your Docker images are available at:
- **Latest**: `ghcr.io/painguin-wq/deadline-bot:latest`
- **By branch**: `ghcr.io/painguin-wq/deadline-bot:main`
- **By commit**: `ghcr.io/painguin-wq/deadline-bot:sha-COMMIT_HASH`

Public access: ✅ Yes (your repo is public)

## Troubleshooting

### Build fails: "Configuration validation failed"
Ensure `.env` file has:
```
TOKEN=your_telegram_token
MAIN_GROUP_ID=your_group_id
```

### Deploy workflow fails (if SSH is configured)
- Verify SSH key is in correct format (PEM or OpenSSH)
- Test manually: `ssh -p PORT user@SERVER_IP 'echo ok'`
- Check server has Docker and Docker Compose installed

### Image pull fails on server
- Ensure server has internet access to `ghcr.io`
- Check firewall rules allow registry access

## Next Steps

1. ✅ Commits to `main` now trigger automatic Docker builds
2. 🔄 Each push creates a new image tagged `latest` + `main` + commit SHA
3. 📦 Images available at `ghcr.io/painguin-wq/deadline-bot`
4. (Optional) Add SSH secrets if you want auto-deployment to a server

## Files Created/Modified

- ✅ `Dockerfile` — Multi-stage build with non-root user
- ✅ `.dockerignore` — Excludes unnecessary files from build
- ✅ `compose.yml` — Uses pre-built GHCR image with `pull_policy: always`
- ✅ `.github/workflows/build.yml` — Builds and pushes to GHCR
- ✅ `.github/workflows/deploy.yml` — Optional SSH deployment
- ✅ `main.py` — Environment validation on startup
- 📄 `CI_CD_SETUP.md` — Detailed CI/CD documentation
- 📄 `SECRETS_SETUP.md` — Secrets configuration guide
- 📄 `IMPLEMENTATION.md` — This file

---

**Your project is production-ready.** Every push to main automatically builds a Docker image. 🚀
