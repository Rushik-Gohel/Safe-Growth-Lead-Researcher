# Deployment Guide

This guide covers deploying the Safe-Growth Lead Researcher application using Docker.

## 🚀 Quick Start

### Prerequisites

- Docker Engine 20.10+ and Docker Compose 2.0+
- Valid API keys (Google Gemini, Tavily, LangSmith)
- At least 2GB RAM available
- Port 8501 available (only UI is exposed externally)

### Deployment Steps

1. **Clone and Configure**
```bash
git clone <repository-url>
cd safe-growth-researcher
cp .env.example .env
```

2. **Edit `.env` file with your API keys**
```bash
nano .env  # or use your preferred editor
```

Required keys:
- `GOOGLE_API_KEY` - Your Google Gemini API key
- `TAVILY_API_KEY` - Your Tavily Search API key (optional)
- `LANGCHAIN_API_KEY` - Your LangSmith API key (optional)

3. **Build and Start Services**
```bash
# Build images
docker-compose build

# Start services in detached mode
docker-compose up -d

# View logs
docker-compose logs -f
```

4. **Verify Deployment**
```bash
# Check service health
docker-compose ps

# Test UI health endpoint (publicly accessible)
curl http://localhost:8501/_stcore/health

# Test API health endpoint (only from within Docker network)
docker-compose exec ui curl http://api:8000/health
```

5. **Access Application**
- Streamlit UI: http://localhost:8501 (Public)
- FastAPI Backend: Internal only (not exposed externally for security)

**Note**: The API backend is only accessible within the Docker network. External users can only access the application through the Streamlit UI.

## 🔧 Production Configuration

### Security Enhancements

The Dockerfiles and docker-compose configuration include several security improvements:

1. **Non-root User**: Both containers run as user `appuser` (UID 1000)
2. **No Volume Mounts**: Source code is baked into images (commented out in docker-compose.yml)
3. **Minimal Base Image**: Using `python:3.11-slim` for smaller attack surface
4. **Security Guardrails**: Input validation and prompt injection detection enabled by default
5. **API Backend Isolation**: FastAPI backend is NOT exposed externally - only accessible within Docker network
   - External users can only access the application through the Streamlit UI (port 8501)
   - API port 8000 is only accessible to other containers in the same network
   - This prevents direct API access and potential abuse

### Resource Limits

Default resource limits per service:
- **CPU Limit**: 1.0 core
- **Memory Limit**: 1GB
- **CPU Reservation**: 0.5 core
- **Memory Reservation**: 512MB

Adjust in `docker-compose.yml` under `deploy.resources` if needed.

### Environment Variables

All configuration is managed through environment variables. Key settings:

#### Rate Limits (Gemini 1.5 Flash Tier 1)
```env
GEMINI_RPM=15              # Requests per minute
GEMINI_TPM=1000000         # Tokens per minute
GEMINI_TPD=1500            # Requests per day
```

#### Caching Configuration
```env
ENABLE_CACHING=true
CACHE_TTL=3600             # Default cache TTL (1 hour)
WORKFLOW_CACHE_TTL=3600    # Workflow results
LINKEDIN_CACHE_TTL=3600    # LinkedIn profiles
SEARCH_CACHE_TTL=1800      # Search results (30 min)
```

#### Security Settings
```env
ENABLE_GUARDRAILS=true
MAX_INPUT_LENGTH=1000
```

## 🔍 Monitoring

### Health Checks

Both services include health checks:
- **Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Retries**: 3
- **Start Period**: 40 seconds

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f ui

# Last 100 lines
docker-compose logs --tail=100
```

### Service Status

```bash
# Check running containers
docker-compose ps

# View resource usage
docker stats safe-growth-api safe-growth-ui
```

## 🛠️ Maintenance

### Update Application

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Restart Services

```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart api
docker-compose restart ui
```

### Stop Services

```bash
# Stop services (keeps containers)
docker-compose stop

# Stop and remove containers
docker-compose down

# Stop and remove containers + volumes
docker-compose down -v
```

### Clean Up

```bash
# Remove unused images
docker image prune -a

# Remove all stopped containers
docker container prune

# Full cleanup (careful!)
docker system prune -a --volumes
```

## 🐛 Troubleshooting

### Container Won't Start

1. Check logs:
```bash
docker-compose logs api
docker-compose logs ui
```

2. Verify environment variables:
```bash
docker-compose config
```

3. Check port conflicts:
```bash
lsof -i :8000
lsof -i :8501
```

### API Key Issues

1. Verify `.env` file exists and contains valid keys
2. Check environment variables in container:
```bash
docker-compose exec api env | grep API_KEY
```

3. Restart services after updating `.env`:
```bash
docker-compose restart
```

### Memory Issues

If containers are killed due to OOM:

1. Increase memory limits in `docker-compose.yml`
2. Check system resources:
```bash
docker stats
free -h
```

### Network Issues

1. Check network connectivity:
```bash
docker network ls
docker network inspect safe-growth-network
```

2. Test inter-service communication:
```bash
docker-compose exec ui curl http://api:8000/health
```

## 📊 Performance Optimization

### For Development

Uncomment volume mounts in `docker-compose.yml` for hot-reloading:
```yaml
volumes:
  - ./src:/app/src
```

### For Production

1. Keep volume mounts commented out
2. Rebuild images after code changes
3. Use `--no-cache` flag for clean builds
4. Consider using multi-stage builds for smaller images

### Scaling

To run multiple UI instances:
```bash
docker-compose up -d --scale ui=3
```

Note: You'll need to configure a load balancer for multiple instances.

## 🔐 Security Best Practices

1. **Never commit `.env` file** - It contains sensitive API keys
2. **Use secrets management** - Consider Docker secrets or external vaults
3. **Regular updates** - Keep base images and dependencies updated
4. **Network isolation** - Use Docker networks to isolate services
5. **HTTPS in production** - Use reverse proxy (nginx/traefik) with SSL
6. **Monitor logs** - Set up log aggregation and alerting

## 🌐 Production Deployment Options

### Cloud Platforms

#### AWS ECS/Fargate
```bash
# Push images to ECR
docker tag safe-growth-api:latest <account>.dkr.ecr.<region>.amazonaws.com/safe-growth-api:latest
docker push <account>.dkr.ecr.<region>.amazonaws.com/safe-growth-api:latest
```

#### Google Cloud Run
```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/<project-id>/safe-growth-api
gcloud run deploy safe-growth-api --image gcr.io/<project-id>/safe-growth-api
```

#### Azure Container Instances
```bash
# Push to ACR
az acr build --registry <registry-name> --image safe-growth-api:latest .
az container create --resource-group <rg> --name safe-growth-api --image <registry>.azurecr.io/safe-growth-api:latest
```

### Kubernetes

See `k8s/` directory for Kubernetes manifests (if available).

## 📞 Support

For issues and questions:
- GitHub Issues: [Create an issue](https://github.com/yourusername/safe-growth-researcher/issues)
- Documentation: [ARCHITECTURE.md](ARCHITECTURE.md)
- README: [README.md](README.md)

---

**Built with ❤️ for Safe-Growth**