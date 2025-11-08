# RPGAI Deployment Guide

## 🚀 Production Deployment Options

### Option 1: Docker Deployment (Recommended)

#### 1. Create Dockerfile

```dockerfile
# /Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY server/ ./server/

# Create media directory
RUN mkdir -p media

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/healthz')"

# Run application
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 2. Create docker-compose.yml

```yaml
version: '3.8'

services:
  rpgai:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - GOOGLE_APPLICATION_CREDENTIALS=/app/gcp-key.json
      - LOG_LEVEL=INFO
    volumes:
      - ./media:/app/media
      - ./npc_memory.db:/app/npc_memory.db
      - ./gcp-key.json:/app/gcp-key.json:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/healthz"]
      interval: 30s
      timeout: 10s
      retries: 3
```

#### 3. Deploy

```bash
# Build image
docker-compose build

# Start service
docker-compose up -d

# View logs
docker-compose logs -f

# Check health
curl http://localhost:8000/healthz
```

---

### Option 2: Cloud Platforms

#### Google Cloud Run

```bash
# Build and push
gcloud builds submit --tag gcr.io/PROJECT_ID/rpgai

# Deploy
gcloud run deploy rpgai \
  --image gcr.io/PROJECT_ID/rpgai \
  --platform managed \
  --region us-central1 \
  --set-env-vars GEMINI_API_KEY=$GEMINI_API_KEY \
  --allow-unauthenticated

# Get URL
gcloud run services describe rpgai --format='value(status.url)'
```

**Note:** WebSockets require Cloud Run with HTTP/2

#### AWS Elastic Beanstalk

```bash
# Install EB CLI
pip install awsebcli

# Initialize
eb init -p python-3.11 rpgai

# Create environment
eb create rpgai-prod \
  --instance_type t3.small \
  --envvars GEMINI_API_KEY=$GEMINI_API_KEY

# Deploy
eb deploy

# Open app
eb open
```

#### Heroku

```bash
# Create app
heroku create rpgai-prod

# Set environment
heroku config:set GEMINI_API_KEY=$GEMINI_API_KEY

# Deploy
git push heroku main

# Scale
heroku ps:scale web=2

# View logs
heroku logs --tail
```

---

### Option 3: VPS / Bare Metal

#### Ubuntu 22.04 Setup

```bash
# 1. Install dependencies
sudo apt update
sudo apt install -y python3.11 python3.11-venv nginx certbot

# 2. Create app user
sudo useradd -m -s /bin/bash rpgai
sudo su - rpgai

# 3. Clone and setup
cd /opt
git clone <your-repo> rpgai
cd rpgai
python3.11 -m venv venv
source venv/bin/activate
pip install -r server/requirements.txt

# 4. Configure environment
cp .env.example .env
nano .env  # Add your keys

# 5. Create systemd service
sudo nano /etc/systemd/system/rpgai.service
```

**rpgai.service:**
```ini
[Unit]
Description=RPGAI NPC Dialogue Service
After=network.target

[Service]
Type=simple
User=rpgai
WorkingDirectory=/opt/rpgai
Environment="PATH=/opt/rpgai/venv/bin"
EnvironmentFile=/opt/rpgai/.env
ExecStart=/opt/rpgai/venv/bin/uvicorn server.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# 6. Start service
sudo systemctl daemon-reload
sudo systemctl enable rpgai
sudo systemctl start rpgai
sudo systemctl status rpgai
```

#### Nginx Reverse Proxy

```nginx
# /etc/nginx/sites-available/rpgai
server {
    listen 80;
    server_name rpgai.yourdomain.com;

    # WebSocket support
    location /v1/chat.stream {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;  # 24 hours
    }

    # HTTP endpoints
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # Media files (if serving directly)
    location /media/ {
        alias /opt/rpgai/media/;
        expires 1h;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/rpgai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# Setup SSL
sudo certbot --nginx -d rpgai.yourdomain.com
```

---

## 🔒 Security Hardening

### 1. Environment Variables

```bash
# Use secrets manager instead of .env files
# AWS Secrets Manager
aws secretsmanager create-secret \
  --name rpgai/gemini-key \
  --secret-string $GEMINI_API_KEY

# GCP Secret Manager
gcloud secrets create gemini-key --data-file=- <<< "$GEMINI_API_KEY"

# Kubernetes Secrets
kubectl create secret generic rpgai-secrets \
  --from-literal=GEMINI_API_KEY=$GEMINI_API_KEY
```

### 2. CORS Configuration

Update `server/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://yourgame.com",
        "https://play.yourgame.com"
    ],  # Don't use "*" in production!
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

### 3. Rate Limiting

```bash
pip install slowapi
```

```python
# server/main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.websocket("/v1/chat.stream")
@limiter.limit("10/minute")  # 10 connections per minute per IP
async def chat_stream(websocket: WebSocket):
    ...
```

### 4. API Key Authentication (Optional)

```python
from fastapi import Header, HTTPException

async def verify_api_key(x_api_key: str = Header()):
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API Key")

@app.post("/v1/memory/write", dependencies=[Depends(verify_api_key)])
async def write_memory(...):
    ...
```

---

## 📊 Monitoring & Logging

### Application Logging

```python
# server/settings.py
import logging.config

LOGGING_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'default': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        },
        'json': {
            'class': 'pythonjsonlogger.jsonlogger.JsonFormatter'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default'
        },
        'file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/rpgai.log',
            'maxBytes': 10485760,  # 10MB
            'backupCount': 5,
            'formatter': 'json'
        }
    },
    'root': {
        'level': 'INFO',
        'handlers': ['console', 'file']
    }
}

logging.config.dictConfig(LOGGING_CONFIG)
```

### Health Monitoring

```bash
# Prometheus metrics
pip install prometheus-fastapi-instrumentator
```

```python
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()
Instrumentator().instrument(app).expose(app)
```

### Error Tracking

```bash
pip install sentry-sdk
```

```python
import sentry_sdk

sentry_sdk.init(
    dsn="your-sentry-dsn",
    traces_sample_rate=0.1,
    environment="production"
)
```

---

## 🔄 CI/CD Pipeline

### GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy RPGAI

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r server/requirements.txt
      - run: pytest tests/ -v

  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Cloud Run
        run: |
          gcloud auth configure-docker
          docker build -t gcr.io/${{ secrets.GCP_PROJECT }}/rpgai .
          docker push gcr.io/${{ secrets.GCP_PROJECT }}/rpgai
          gcloud run deploy rpgai \
            --image gcr.io/${{ secrets.GCP_PROJECT }}/rpgai \
            --platform managed \
            --region us-central1
```

---

## 📦 Database Backups

### SQLite Backups

```bash
# Cron job for daily backups
0 2 * * * /opt/rpgai/backup.sh

# backup.sh
#!/bin/bash
DATE=$(date +%Y%m%d)
sqlite3 /opt/rpgai/npc_memory.db ".backup '/opt/rpgai/backups/npc_memory_$DATE.db'"
find /opt/rpgai/backups -mtime +30 -delete  # Keep 30 days
```

### Cloud Storage Sync

```bash
# Sync to S3
aws s3 sync /opt/rpgai/backups s3://rpgai-backups/

# Sync to GCS
gsutil -m rsync -r /opt/rpgai/backups gs://rpgai-backups/
```

---

## 🔍 Performance Optimization

### 1. Database Indexing

Already implemented in `memory.py`:
```sql
CREATE INDEX idx_mem_query 
ON npc_memory(npc_id, player_id, salience DESC, ts DESC);
```

### 2. Response Caching

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_system_instruction():
    return SYSTEM_INSTRUCTION  # Cache static prompt
```

### 3. Connection Pooling

```python
# For PostgreSQL (if migrating from SQLite)
from databases import Database

database = Database("postgresql://user:pass@host/db")
```

### 4. Load Balancing

```nginx
upstream rpgai_backend {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
}

server {
    location / {
        proxy_pass http://rpgai_backend;
    }
}
```

---

## 📈 Scaling Strategies

### Horizontal Scaling

```bash
# Run multiple workers
uvicorn server.main:app --workers 4 --host 0.0.0.0

# Or use Gunicorn
gunicorn server.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Database Migration

For high traffic, migrate to PostgreSQL:

```python
# server/settings.py
DATABASE_URL = "postgresql://user:pass@localhost/rpgai"

# Use SQLAlchemy or asyncpg for async operations
```

### Caching Layer

```bash
# Redis for distributed memory
pip install redis aioredis
```

```python
import aioredis

redis = await aioredis.create_redis_pool('redis://localhost')

# Cache top memories
await redis.setex(f"mem:{npc_id}:{player_id}", 300, json.dumps(memories))
```

---

## 🛠️ Maintenance

### Regular Tasks

```bash
# Weekly: Clean old memories
sqlite3 npc_memory.db "DELETE FROM npc_memory WHERE ts < strftime('%s', 'now', '-90 days')"

# Daily: Rotate logs
logrotate /etc/logrotate.d/rpgai

# Monthly: Vacuum database
sqlite3 npc_memory.db "VACUUM"
```

### Update Strategy

```bash
# Zero-downtime deployment
1. Deploy new version to port 8001
2. Test: curl http://localhost:8001/healthz
3. Switch Nginx upstream
4. Stop old version
```

---

## 🚨 Troubleshooting Production Issues

### High Memory Usage

```bash
# Check process memory
ps aux | grep uvicorn

# Reduce workers
uvicorn server.main:app --workers 2

# Enable garbage collection logging
python -X showrefcount server/main.py
```

### Slow Responses

```bash
# Check Gemini API latency
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/healthz

# Enable query logging
LOG_LEVEL=DEBUG uvicorn server.main:app
```

### Database Locks

```bash
# Check for locks
sqlite3 npc_memory.db "PRAGMA busy_timeout = 5000"

# Or migrate to PostgreSQL for better concurrency
```

---

## ✅ Production Checklist

- [ ] Environment variables in secrets manager
- [ ] CORS restricted to game domains
- [ ] HTTPS/WSS enabled
- [ ] Rate limiting configured
- [ ] Database backups automated
- [ ] Logging to centralized system
- [ ] Error tracking (Sentry) enabled
- [ ] Health checks configured
- [ ] Load balancing setup
- [ ] Monitoring dashboards (Grafana)
- [ ] SSL certificates auto-renewed
- [ ] Firewall rules configured
- [ ] DDoS protection enabled
- [ ] API versioning strategy
- [ ] Rollback procedure documented

---

**For local development, see [`QUICKSTART.md`](./QUICKSTART.md)**  
**For architecture details, see [`PROJECT_STRUCTURE.md`](./PROJECT_STRUCTURE.md)**

