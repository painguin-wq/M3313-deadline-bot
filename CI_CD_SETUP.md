# CI/CD Configuration Guide

## Environment Variable Validation

The application validates required environment variables at startup and exits with clear error messages if any are missing or invalid:

- `TOKEN` (required): Telegram Bot API token
- `MAIN_GROUP_ID` (required): Telegram group/chat ID for posting deadlines
- `EDIT_MESSAGE_ID` (optional): Message ID to edit when updating deadlines
- `ADD_CALENDAR_LINK` (optional): `'true'` or `'false'` to add Google Calendar links
- `ADMIN_USER_IDS` (optional): Comma-separated list of Telegram user IDs with admin access

## GitHub Actions Setup

### 1. Configure Repository Secrets

Add the following secrets to your GitHub repository (Settings → Secrets and variables → Actions):

**For Docker Registry (GitHub Container Registry):**
- No additional setup required — uses `GITHUB_TOKEN` automatically

**For SSH Deployment (if deploying to your server):**
- `SSH_PRIVATE_KEY`: Your SSH private key
- `SSH_PORT`: SSH port (default: 22)
- `SERVER_IP`: Server IP address or hostname
- `USERNAME`: SSH username
- `PROJECT_PATH`: Path to project directory on server (e.g., `/home/user/deadline-bot`)

**For Bot Configuration:**
- `TOKEN`: Telegram Bot API token
- `MAIN_GROUP_ID`: Target Telegram group ID
- `EDIT_MESSAGE_ID`: (optional) Message ID to pin/edit
- `ADD_CALENDAR_LINK`: (optional) `'true'` or `'false'`
- `ADMIN_USER_IDS`: (optional) Comma-separated admin user IDs

### 2. Workflows

#### Build Workflow (`build.yml`)
Automatically builds and pushes Docker image to GitHub Container Registry on:
- Commits to `main` branch
- Changes to: `Dockerfile`, `requirements.txt`, `main.py`, `DEADLINES.json`, `.dockerignore`

Image tags:
- `ghcr.io/YOUR_USERNAME/deadline-bot:latest` (always on main)
- `ghcr.io/YOUR_USERNAME/deadline-bot:main` (branch tag)
- `ghcr.io/YOUR_USERNAME/deadline-bot:sha-COMMIT_HASH` (commit hash)

#### Deploy Workflow (`deploy.yml`)
Automatically deploys to your server after a successful build:
- Pulls latest image from GHCR
- Syncs configuration files and data
- Restarts container with `docker compose up -d --pull always`
- Verifies deployment status

## Local Development

### Build Locally
```bash
docker build -t deadline-bot:local .
```

### Run with Environment File
```bash
docker compose --env-file .env up -d
```

### Logs
```bash
docker compose logs -f deadline-bot
```

### Stop
```bash
docker compose down
```

## Using Pre-built Image

Pull and run the pre-built image:
```bash
docker pull ghcr.io/YOUR_USERNAME/deadline-bot:latest
docker run -d \
  --name deadline-bot \
  --env-file .env \
  -v /etc/localtime:/etc/localtime:ro \
  -v ./DEADLINES.json:/app/DEADLINES.json \
  -v ./board-data:/app/board-data \
  ghcr.io/YOUR_USERNAME/deadline-bot:latest
```

## Troubleshooting

### Build Fails with "Configuration validation failed"
Ensure all required environment variables are set in `.env` file before running.

### Image Pull Fails on Private Server
If using GHCR without public access, configure image pull secrets in your deployment.

### SSH Deployment Fails
- Verify SSH key has correct permissions: `chmod 600 ~/.ssh/id_rsa`
- Confirm server IP, port, and credentials in repository secrets
- Test SSH connection manually: `ssh -p PORT user@SERVER_IP`
