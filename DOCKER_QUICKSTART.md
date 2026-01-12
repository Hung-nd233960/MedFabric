# MedFabric Docker Quick Start Guide

## One-Minute Setup

```bash
# 1. Install Docker (if needed)
bash docker/install-docker.sh && newgrp docker

# 2. Setup environment
bash docker/setup-env.sh

# 3. Build image
bash docker/build.sh

# 4. Run application
bash docker/run-dev.sh
```

Then open: **<http://localhost:8501>**

---

## Detailed Steps

### Step 1: Install Docker

First-time installation only:

```bash
bash docker/install-docker.sh
```

After installation, log out and log back in (or run `newgrp docker`).

**Verify**:

```bash
docker --version
docker-compose --version
```

### Step 2: Setup Environment

```bash
bash docker/setup-env.sh
```

This creates `.env` file with:

- Database configuration
- Optional Tailscale setup
- Directory structure

**Example prompt**:

```
Enter DATABASE_URL [sqlite:///./medfabric.db]: 
Enter Tailscale Auth Key (optional, leave empty for dev):
```

For development, just press Enter for defaults.

### Step 3: Build Image

```bash
bash docker/build.sh
```

This:

- Downloads base Python image
- Installs dependencies
- Creates MedFabric image

**Takes**: ~5-10 minutes on first build

To rebuild without cache:

```bash
bash docker/build.sh --no-cache
```

### Step 4: Run Application

```bash
bash docker/run-dev.sh
```

This:

- Starts Streamlit server
- Mounts code for hot-reload
- Listens on port 8501

**Access**: <http://localhost:8501>

**Stop**: Press `Ctrl+C`

---

## Common Tasks

### View Logs

```bash
# Follow dev logs in real-time
bash docker/logs.sh dev -f

# View prod logs
bash docker/logs.sh prod -f
```

### Stop Containers

```bash
# Stop dev
bash docker/stop.sh dev

# Stop all
bash docker/stop.sh all
```

### Check Status

```bash
bash docker/status.sh
```

Shows:

- Docker daemon status
- Running containers
- Images and volumes
- Configuration validation

### Production Deployment

1. Get Tailscale Auth Key: <https://login.tailscale.com/admin/authkeys>

2. Update `.env`:

   ```bash
   TS_AUTH_KEY=tskey-auth-XXXXX...
   ```

3. Run production:

   ```bash
   bash docker/run-prod.sh
   ```

---

## Troubleshooting

### "Docker daemon is not running"

```bash
sudo systemctl start docker
sudo systemctl enable docker  # Auto-start on boot
```

### "Permission denied while trying to connect to Docker daemon"

```bash
sudo usermod -aG docker $USER
newgrp docker
```

### "Port 8501 already in use"

```bash
# Stop existing containers
bash docker/stop.sh all

# Or find and kill the process
sudo lsof -i :8501 | awk 'NR>1 {print $2}' | xargs kill -9
```

### "Build failed" / "Module not found"

```bash
# Clean and rebuild
bash docker/clean.sh --all --confirm
bash docker/build.sh --no-cache
```

### Changes not showing up in dev

- Ensure you're in dev mode: `bash docker/run-dev.sh`
- Streamlit auto-reloads on file changes
- Check logs: `bash docker/logs.sh dev -f`

---

## File Structure

```
docker/
├── install-docker.sh    # Install Docker & Docker Compose
├── setup-env.sh         # Configure environment  
├── build.sh             # Build image
├── run-dev.sh           # Start development
├── run-prod.sh          # Start production
├── logs.sh              # View logs
├── stop.sh              # Stop containers
├── status.sh            # Check status
├── clean.sh             # Cleanup resources
├── app.Dockerfile       # Application container recipe
└── README.md            # Full documentation
```

---

## What Each Script Does

| Script | Purpose | Profile |
|--------|---------|---------|
| `install-docker.sh` | Install Docker + Docker Compose | - |
| `setup-env.sh` | Configure environment variables | - |
| `build.sh` | Build MedFabric Docker image | - |
| `run-dev.sh` | Start with hot-reloading | dev |
| `run-prod.sh` | Start with Tailscale VPN | prod |
| `logs.sh` | View container logs | - |
| `stop.sh` | Stop running containers | - |
| `status.sh` | Show Docker status | - |
| `clean.sh` | Remove containers/images/volumes | - |

---

## Services & Ports

### Development

- Service: `app-dev`
- Port: `8501` (Streamlit)
- Access: `http://localhost:8501`
- Code reload: Yes

### Production  

- Service: `app-prod`
- Service: `tailscale`
- Networking: Tailscale VPN
- Access: Via VPN tunnel

---

## Environment Variables

Configured in `.env`:

```bash
# Database connection
DATABASE_URL=sqlite:///./medfabric.db

# Production only: Tailscale auth key
TS_AUTH_KEY=tskey-auth-XXXXX...
```

---

## Volumes

### Development

```
./medfabric      ↔ /app/medfabric    (read-write)
./data_sets      ↔ /app/data_sets    (read-only)
./config.toml    ↔ /app/config.toml  (read-write)
./.streamlit     ↔ /app/.streamlit   (read-write)
```

Changes to code automatically reload in browser.

### Production

```
./medfabric      ↔ /app/medfabric    (read-only)
./data_sets      ↔ /app/data_sets    (read-only)
./config.toml    ↔ /app/config.toml  (read-only)
./.streamlit     ↔ /app/.streamlit   (read-only)
```

---

## Tips & Tricks

### Run commands in container

```bash
# Execute Python code
docker exec medfabric_app_dev python -c "print('Hello')"

# Run tests
docker exec medfabric_app_dev pytest tests/

# Interactive shell
docker exec -it medfabric_app_dev /bin/bash
```

### View running processes

```bash
docker ps                    # Running containers
docker ps -a                 # All containers
docker images | grep medfabric   # Images
```

### Development workflow

```bash
# Terminal 1: Start dev environment
bash docker/run-dev.sh

# Terminal 2: Follow logs
bash docker/logs.sh dev -f

# Terminal 3: Edit code
# Changes auto-reload in browser
```

### Rebuild specific image

```bash
docker-compose --profile dev build --no-cache app-dev
```

---

## Getting Help

**Full documentation**: See `docker/README.md`

**Scripts help**:

```bash
bash docker/setup-env.sh  # Shows interactive help
bash docker/build.sh      # Shows build options
bash docker/logs.sh       # Shows usage examples
```

**Check configuration**:

```bash
bash docker/status.sh
```

**View all logs**:

```bash
bash docker/logs.sh dev -f
```

---

## Next Steps

1. ✅ Docker installed and running
2. ✅ Image built
3. ✅ Application started at <http://localhost:8501>
4. ❓ What's next?

- **Develop**: Make code changes, they auto-reload
- **Test**: `docker exec medfabric_app_dev pytest`
- **Deploy**: Setup `.env` with Tailscale, run `bash docker/run-prod.sh`
- **Monitor**: `bash docker/logs.sh dev -f`

---

## FAQ

**Q: How do I update dependencies?**
A: Edit `requirements.txt`, then rebuild:

```bash
bash docker/build.sh --no-cache
bash docker/run-dev.sh
```

**Q: Can I use PostgreSQL instead of SQLite?**
A: Yes, edit `DATABASE_URL` in `.env`:

```bash
DATABASE_URL=postgresql://user:pass@host/db
bash docker/build.sh --no-cache
```

**Q: How do I access the database?**
A: Connect with your database client to the URL in `.env`

**Q: Can multiple people access it?**
A: Yes, in production with Tailscale networking:

1. Configure `TS_AUTH_KEY`
2. Run `bash docker/run-prod.sh`
3. Access via VPN tunnel

**Q: How do I clean up old images?**
A: ```bash
bash docker/clean.sh --all --confirm

```

**Q: What if I need to modify the Dockerfile?**
A: Edit `docker/app.Dockerfile`, then rebuild:
```bash
bash docker/build.sh --no-cache
```
