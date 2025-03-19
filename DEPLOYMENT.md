# Continuous Deployment Architecture

This document provides an architectural overview of the continuous deployment system and practical guides for common operations.

## System Architecture

The deployment system follows a modern microservices architecture with the following key components:

### Infrastructure Components
1. **Container Registry**: GitHub Container Registry (ghcr.io) stores all container images
2. **Reverse Proxy**: Nginx handles external access and SSL termination
3. **Container Runtime**: Podman manages containers with systemd integration
4. **CI/CD Pipeline**: GitHub Actions orchestrates the entire deployment process

### Service Architecture
```
[External Access] → [Nginx Proxy] → [Service 1]
                          ↓
                    [Service 2]
                          ↓
                    [Service 3]
```

Each service runs in its own container, managed by Podman and systemd. Services communicate through internal networking, with Nginx handling external access.

## Common Problems and Solutions

### 1. Service Dependencies and Startup Order
**Problem**: Services failing because they start before their dependencies are ready.

**Solution**: 
- Use systemd quadlets with proper dependencies
- Implement meta-services for service groups
- Order service generation in reverse order (dependencies first)
```yaml
# Example service dependency
services:
  app:
    depends_on:
      - postgres
    networks:
      - internal
```

### 2. Secret Management
**Problem**: Inconsistent secret handling between environments and services.

**Solution**:
- Move all secrets to GitHub Actions secrets
- Use Podman's secret store instead of environment files
- Standardize secret naming conventions
```yaml
# Example secret usage
services:
  my-service:
    environment:
      - DB_PASSWORD=${DB_PASSWORD}  # From Podman secrets
```

### 3. Container Networking
**Problem**: Services unable to communicate due to network configuration issues.

**Solution**:
- Use consistent network naming
- Implement automatic network resolution
- Use bridge networking for better isolation
```yaml
networks:
  internal:
    external: true
    name: my-project-internal
```

### 4. Service Recovery
**Problem**: Services not recovering properly after failures.

**Solution**:
- Implement proper systemd service types
- Use one-shot services for migrations
- Configure automatic restart policies
```yaml
# Example systemd service configuration
[Unit]
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/bin/my-migration
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
```

### 5. Build and Cache Optimization
**Problem**: Slow builds and inefficient caching.

**Solution**:
- Use Docker Buildx for better caching
- Implement multi-stage builds
- Cache dependencies separately
```dockerfile
# Example optimized Dockerfile
FROM node:18 AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:18-slim
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules
```

## Adding New Secrets

### 1. Add Secret to GitHub
1. Go to your repository settings
2. Navigate to Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Add your secret with a descriptive name (e.g., `DB_PASSWORD`)

### 2. Access Secret in Deployment
Secrets are automatically available in GitHub Actions workflows and are injected into Podman's secret store during deployment.

Example of using a secret in a service:
```yaml
# docker-compose.yml
services:
  my-service:
    environment:
      - DB_PASSWORD=${DB_PASSWORD}
```

## Adding a New Service

### 1. Create Service Directory
```bash
mkdir -p services/05_my_new_service
```

### 2. Add Service Configuration
```yaml
# services/05_my_new_service/docker-compose.yml
version: '3.8'
services:
  my-service:
    image: ghcr.io/your-org/your-repo/my-service:${APP_VERSION}
    environment:
      - SERVICE_NAME=my-service
      - DB_HOST=postgres
    networks:
      - internal
    volumes:
      - ./data:/app/data

networks:
  internal:
    external: true
```

### 3. Add Environment Variables
```bash
# services/05_my_new_service/.env
SERVICE_NAME=my-service
DB_HOST=postgres
```

### 4. Add Service to Nginx Configuration
```nginx
# services/03_nginx-proxy/conf.d/my-service.conf
server {
    listen 80;
    server_name my-service.example.com;

    location / {
        proxy_pass http://my-service:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Making a Service Available via Nginx

### 1. Configure Service Port
Ensure your service exposes a port in its Dockerfile:
```dockerfile
EXPOSE 8080
```

### 2. Add Nginx Configuration
Create a new configuration file in `services/03_nginx-proxy/conf.d/`:
```nginx
server {
    listen 80;
    server_name your-service.example.com;

    # SSL configuration (recommended)
    listen 443 ssl;
    ssl_certificate /etc/nginx/ssl/your-cert.pem;
    ssl_certificate_key /etc/nginx/ssl/your-key.pem;

    location / {
        proxy_pass http://your-service:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. Update DNS
Add an A record pointing to your server's IP address:
```
your-service.example.com. IN A your-server-ip
```

## Service Communication

### Internal Communication
Services communicate through the internal network:
```yaml
# Example service configuration
services:
  my-service:
    networks:
      - internal
    environment:
      - DB_HOST=postgres  # Direct service name reference
```

### External Access
All external access is routed through Nginx:
```
[Client] → [Nginx] → [Service]
```

## Security Architecture

### Secret Management Flow
1. Secrets stored in GitHub Actions
2. Secrets injected into Podman secret store during deployment
3. Services access secrets through environment variables
4. Nginx handles SSL termination and security headers

### Network Security
- Internal services are isolated in a private network
- Only Nginx is exposed to the internet
- SSL/TLS encryption for all external traffic
- Rate limiting and security headers via Nginx

## Deployment Flow

1. **Code Push**
   - Push to main branch
   - GitHub Actions builds container
   - Image pushed to ghcr.io

2. **Deployment**
   - GitHub Actions deploys to server
   - Secrets are refreshed
   - Services are updated via systemd
   - Nginx configuration is reloaded

3. **Health Checks**
   - Services are monitored
   - Automatic recovery on failure
   - Health status reported to monitoring system

## Monitoring and Maintenance

### Health Monitoring
- Systemd service status
- Podman container health
- Nginx access logs
- Application logs

### Maintenance Tasks
1. Regular secret rotation
2. SSL certificate renewal
3. Container image updates
4. Security patches
5. Backup verification

## Troubleshooting

### Common Issues
1. **Service Not Accessible**
   - Check Nginx configuration
   - Verify DNS settings
   - Check service logs
   - Verify SSL certificates

2. **Secret Issues**
   - Verify GitHub secret exists
   - Check secret injection in logs
   - Verify environment variables

3. **Container Issues**
   - Check Podman logs
   - Verify systemd service status
   - Check container health

4. **Build Issues**
   - Check GitHub Actions logs
   - Verify build cache
   - Check image registry permissions

5. **Network Issues**
   - Verify network configuration
   - Check service dependencies
   - Verify DNS resolution 