# GitHub Repository Secrets Setup

## Step-by-Step Instructions

### 1. Navigate to Repository Secrets
1. Go to your GitHub repository: `https://github.com/painguin-wq/M3313-deadline-bot`
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** for each one below

### 2. Add Bot Configuration Secrets

| Secret Name | Value | Required |
|---|---|---|
| `TOKEN` | Your Telegram Bot API token (from BotFather) | ✅ Yes |
| `MAIN_GROUP_ID` | Telegram group/chat ID where deadlines post | ✅ Yes |
| `EDIT_MESSAGE_ID` | Message ID to pin/edit (optional, can leave empty) | ⚠️ Optional |
| `ADD_CALENDAR_LINK` | `true` or `false` (default: leave empty) | ⚠️ Optional |
| `ADMIN_USER_IDS` | Comma-separated Telegram user IDs with admin access (optional) | ⚠️ Optional |

**Example:**
```
TOKEN=[REDACTED]:ABCdefGHIjklmnoPQRstuvWXYz-1234567890
MAIN_GROUP_ID=-1001234567890
EDIT_MESSAGE_ID=12345
ADD_CALENDAR_LINK=true
ADMIN_USER_IDS=987654321,[REDACTED]
```

### 3. Add SSH Deployment Secrets (Optional - only if deploying to remote server)

If you're using the SSH deployment workflow, add these secrets:

| Secret Name | Value | Required |
|---|---|---|
| `SSH_PRIVATE_KEY` | Full SSH private key (including `-----BEGIN PRIVATE KEY-----`) | ✅ For remote deploy |
| `SSH_PORT` | SSH port number (default: 22) | ✅ For remote deploy |
| `SERVER_IP` | Server IP address or hostname | ✅ For remote deploy |
| `USERNAME` | SSH username | ✅ For remote deploy |
| `PROJECT_PATH` | Absolute path to project dir on server (e.g., `/home/user/deadline-bot`) | ✅ For remote deploy |

**Example:**
```
SSH_PRIVATE_KEY=-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUtbm9uZS1ub25lAA...
...
-----END OPENSSH PRIVATE KEY-----

SSH_PORT=22
SERVER_IP=192.168.1.100
USERNAME=botuser
PROJECT_PATH=/home/botuser/deadline-bot
```

## Workflows Explained

### `build.yml` — Build & Push to Registry
**Triggers:** Push to `main` branch with changes to code/Dockerfile

**What it does:**
1. Checks out code
2. Builds Docker image
3. Pushes to GitHub Container Registry (GHCR): `ghcr.io/painguin-wq/deadline-bot:latest`
4. Stores build cache for faster subsequent builds

**Required secrets:** None (uses `GITHUB_TOKEN` automatically)

### `deploy.yml` — Deploy to Server
**Triggers:** Successful `build.yml` completion OR push to `main`

**What it does:**
1. Creates `.env` file from bot secrets
2. SSHes into your server
3. Syncs code, config, and data files
4. Pulls latest image from GHCR
5. Restarts container with `docker compose up -d --pull always`
6. Verifies deployment

**Required secrets:** Only if using SSH deployment (all 5 SSH secrets above)

## Local Testing Before Committing

Test that validation works:

```bash
# Missing TOKEN should fail immediately
docker run --env MAIN_GROUP_ID=123 ghcr.io/painguin-wq/deadline-bot:latest

# With valid env, should start polling
docker compose --env-file .env up
```

## Troubleshooting

### Build fails: "Configuration validation failed"
- Check `.env` file has `TOKEN` and `MAIN_GROUP_ID`
- Verify secrets in GitHub match your `.env.sample`

### Deploy fails: "Authentication failed"
- Confirm SSH key is in correct format (PEM or OpenSSH)
- Verify SSH key fingerprint matches server
- Test manually: `ssh -p PORT user@SERVER_IP 'echo ok'`

### Image pull fails on server
- Ensure server can access `ghcr.io` (not behind firewall)
- Or configure GHCR credentials on server if repo is private

## After Setup

1. ✅ Add all required secrets to GitHub (TOKEN, MAIN_GROUP_ID minimum)
2. ✅ Commit and push to main: `git push origin main`
3. ✅ Monitor **Actions** tab to see build progress
4. ✅ Check deploy logs if SSH deployment is configured
5. ✅ Verify bot is running: `docker compose ps` on server

## Next: Test Locally

```bash
# Build locally
docker build -t deadline-bot:test .

# Run with .env file
docker compose --env-file .env up -d

# Check logs
docker compose logs -f deadline-bot

# Stop
docker compose down
```
