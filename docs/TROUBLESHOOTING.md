# Troubleshooting Guide

This comprehensive troubleshooting guide covers common issues, debugging techniques, and solutions for the continuous deployment system.

## Table of Contents

1. [Build Issues](#build-issues)
2. [Deployment Issues](#deployment-issues)
3. [Service Runtime Issues](#service-runtime-issues)
4. [Container Issues](#container-issues)
5. [Network Issues](#network-issues)
6. [Database Issues](#database-issues)
7. [GitHub Actions Issues](#github-actions-issues)
8. [Security Issues](#security-issues)
9. [Performance Issues](#performance-issues)
10. [Monitoring and Debugging](#monitoring-and-debugging)

## Build Issues

### Application Build Failures

#### Docker Build Errors
```bash
# Check Docker daemon status
systemctl status docker

# Clean Docker cache
docker system prune -a --volumes

# Build with verbose output
docker build --no-cache --progress=plain -t myapp:latest .

# Check for syntax errors in Dockerfile
docker run --rm -i hadolint/hadolint < Dockerfile
```

#### Dependency Installation Failures
```bash
# Node.js dependency issues
rm -rf node_modules package-lock.json
npm install

# Python dependency issues
pip install --upgrade pip
pip install --no-cache-dir -r requirements.txt

# Clear pip cache
pip cache purge
```

#### Test Failures During Build
```bash
# Run tests locally with verbose output
docker run --rm -it --entrypoint=/app/entrypoints/entrypoint_test.sh myapp:latest

# Check test logs
docker logs $(docker ps -q --filter "ancestor=myapp:latest")

# Run specific test suites
npm test -- --verbose
pytest -v --tb=short
```

### GitHub Actions Build Issues

#### Workflow Not Triggering
```yaml
# Check workflow triggers in .github/workflows/build.yml
on:
  push:
    branches: [ "main" ]
  pull_request:
    branches: [ "main" ]
  workflow_dispatch:  # Allow manual triggers
```

#### Build Matrix Issues
```bash
# Check if applications are detected correctly
git diff --name-only HEAD~1 HEAD | grep -E '^(applications|utilities|release-tooling)/'

# Verify build matrix JSON
echo '${{ needs.find-changed-applications.outputs.applications }}' | jq '.'
```

## Deployment Issues

### Service Not Found Errors After Release

If you encounter "service not found" errors after a release, the issue is likely with Podman Quadlet not being able to parse the container configurations properly.

#### Debugging Quadlet Configuration
```bash
# Run Quadlet in dry-run mode
/usr/libexec/podman/quadlet --dryrun --user $XDG_CONFIG_HOME/containers/systemd/

# Check systemd unit files
ls -la $XDG_CONFIG_HOME/containers/systemd/
cat $XDG_CONFIG_HOME/containers/systemd/myapp.container

# Validate generated service files
systemctl --user daemon-reload
systemctl --user status myapp
```

#### Common Quadlet Issues
- Invalid container configuration syntax
- Missing required fields in `.container` files
- Incorrect file permissions on configuration files
- Missing dependencies between services

### SSH Connection Issues

#### Connection Failures
```bash
# Test SSH connection manually
ssh -i ~/.ssh/deploy_key user@server -v

# Check SSH key permissions
chmod 600 ~/.ssh/deploy_key
chmod 644 ~/.ssh/deploy_key.pub

# Verify SSH agent
ssh-add -l
ssh-add ~/.ssh/deploy_key
```

#### Authentication Issues
```bash
# Check SSH configuration
cat ~/.ssh/config

# Test with different authentication methods
ssh -o PreferredAuthentications=publickey user@server
ssh -o PreferredAuthentications=password user@server
```

### Environment Variable Issues

#### Missing Environment Variables
```bash
# Check environment variable loading
source /opt/deployment/.env
env | grep -E '(DB_|REDIS_|APP_)'

# Validate environment file format
cat /opt/deployment/.env | grep -v '^#' | grep -v '^$' | head -10
```

#### GitHub Secrets Not Available
```yaml
# Verify secrets are properly configured
env:
  TEST_SECRET: ${{ secrets.TEST_SECRET }}
steps:
  - name: Check secret availability
    run: |
      if [ -z "$TEST_SECRET" ]; then
        echo "Secret not available"
        exit 1
      fi
```

### Service Startup Issues

#### Service Dependencies
```bash
# Check service dependency chain
systemctl --user list-dependencies all-containers.target

# Start services in correct order
systemctl --user start postgres
systemctl --user start redis
systemctl --user start myapp
```

#### Resource Constraints
```bash
# Check resource usage
systemctl --user status myapp
journalctl --user -u myapp --since "1 hour ago"

# Monitor resource consumption
podman stats --no-stream
```

## Service Runtime Issues

### Container Startup Failures

#### Exit Code Analysis
```bash
# Check container exit codes
podman ps -a --format "table {{.Names}} {{.Status}} {{.ExitCode}}"

# Inspect container configuration
podman inspect myapp-container

# Check container logs
podman logs --tail 50 myapp-container
```

#### Common Exit Codes
- Exit code 0: Successful termination
- Exit code 1: General error
- Exit code 125: Docker daemon error
- Exit code 126: Container command not executable
- Exit code 127: Container command not found
- Exit code 137: SIGKILL (out of memory)

### Health Check Failures

#### Application Health Checks
```bash
# Test health endpoint directly
curl -f http://localhost:8080/health

# Check health check configuration
podman inspect myapp-container | jq '.[] | .Config.Healthcheck'

# Manual health check
docker exec myapp-container /app/health-check.sh
```

#### Database Health Checks
```bash
# PostgreSQL health check
psql -h localhost -U username -d database -c "SELECT 1;"

# Redis health check
redis-cli ping

# Check database connections
netstat -an | grep :5432
```

## Container Issues

### Image Pull Failures

#### Registry Authentication
```bash
# Login to GitHub Container Registry
echo $GITHUB_TOKEN | podman login ghcr.io -u username --password-stdin

# Check authentication
podman login --get-login ghcr.io

# Pull image manually
podman pull ghcr.io/owner/repo/app:latest
```

#### Image Not Found
```bash
# Check image availability
podman search ghcr.io/owner/repo/app

# List available tags
curl -H "Authorization: Bearer $GITHUB_TOKEN" \
  https://ghcr.io/v2/owner/repo/app/tags/list
```

### Volume Mount Issues

#### Permission Problems
```bash
# Check volume permissions
ls -la /opt/deployment/volumes/
sudo chown -R 1000:1000 /opt/deployment/volumes/myapp

# SELinux context issues (if applicable)
sudo setsebool -P container_manage_cgroup on
sudo semanage fcontext -a -t container_file_t "/opt/deployment/volumes(/.*)?"
sudo restorecon -R /opt/deployment/volumes/
```

#### Mount Point Issues
```bash
# Verify mount points
findmnt /opt/deployment/volumes/myapp

# Check disk space
df -h /opt/deployment/volumes/
```

### Network Issues

#### Container Networking
```bash
# List networks
podman network ls

# Inspect network configuration
podman network inspect myapp-network

# Test container connectivity
podman exec myapp-container ping postgres-container
```

#### Port Binding Issues
```bash
# Check port usage
netstat -tulpn | grep :8080
lsof -i :8080

# Test port connectivity
telnet localhost 8080
nc -zv localhost 8080
```

## Database Issues

### Connection Issues

#### PostgreSQL Connection Problems
```bash
# Check PostgreSQL status
systemctl --user status postgres

# Test connection
psql -h localhost -p 5432 -U username -d database

# Check connection pool
psql -c "SELECT * FROM pg_stat_activity;"
```

#### Common Connection Errors
- `FATAL: password authentication failed`: Check credentials
- `FATAL: database does not exist`: Verify database name
- `could not connect to server`: Check if PostgreSQL is running
- `timeout expired`: Check network connectivity

### Migration Issues

#### Database Migration Failures
```bash
# Check migration status
cd applications/app.pxy6.com/src
npx prisma migrate status

# Run migrations manually
npx prisma migrate deploy

# Reset database (development only)
npx prisma migrate reset
```

#### Migration Rollback
```bash
# Rollback to specific migration
npx prisma migrate resolve --rolled-back "migration_name"

# Check migration history
npx prisma migrate status
```

## GitHub Actions Issues

### Workflow Failures

#### Permission Issues
```yaml
# Check required permissions
permissions:
  contents: read
  packages: write
  actions: read
  security-events: write
```

#### Secret Access Issues
```bash
# Check if secrets are properly configured
echo "Secret length: ${#GITHUB_TOKEN}"
echo "First 4 chars: ${GITHUB_TOKEN:0:4}"

# Test secret in workflow
- name: Test secret
  run: |
    if [ -z "${{ secrets.GITHUB_TOKEN }}" ]; then
      echo "GITHUB_TOKEN not available"
      exit 1
    fi
```

### Action-Specific Issues

#### Docker Build Action Issues
```yaml
# Use specific action versions
- uses: docker/build-push-action@v4
  with:
    context: .
    push: true
    tags: myapp:latest
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

#### SSH Action Issues
```yaml
# Debug SSH action
- uses: appleboy/ssh-action@v0.1.5
  with:
    host: ${{ secrets.HOST }}
    username: ${{ secrets.USERNAME }}
    key: ${{ secrets.KEY }}
    debug: true
    script: |
      echo "Connected successfully"
      whoami
      pwd
```

## Security Issues

### Certificate Issues

#### SSL Certificate Problems
```bash
# Check certificate validity
openssl x509 -in /etc/ssl/certs/example.com.crt -text -noout

# Test SSL connection
openssl s_client -connect example.com:443

# Check certificate expiration
openssl x509 -in /etc/ssl/certs/example.com.crt -noout -dates
```

### Access Control Issues

#### Permission Denied Errors
```bash
# Check file permissions
ls -la /opt/deployment/
sudo chown -R deployment-user:deployment-user /opt/deployment/

# Check systemd user permissions
loginctl show-user deployment-user
```

#### SELinux Issues (if applicable)
```bash
# Check SELinux status
getenforce

# Check SELinux denials
sudo ausearch -m avc -ts recent

# Allow container operations
sudo setsebool -P container_manage_cgroup on
```

## Performance Issues

### Slow Application Response

#### Performance Monitoring
```bash
# Check application metrics
curl http://localhost:8080/metrics

# Monitor resource usage
top -p $(pgrep myapp)
htop

# Check disk I/O
iostat -x 1
```

#### Database Performance
```sql
-- Check slow queries
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;

-- Check database connections
SELECT * FROM pg_stat_activity;
```

### Memory Issues

#### Out of Memory Errors
```bash
# Check memory usage
free -h
cat /proc/meminfo

# Check container memory limits
podman stats --no-stream

# Check for memory leaks
valgrind --leak-check=full ./myapp
```

#### Swap Usage
```bash
# Check swap usage
swapon -s
cat /proc/swaps

# Monitor swap activity
vmstat 1
```

## Monitoring and Debugging

### Log Analysis

#### Application Logs
```bash
# View application logs
journalctl --user -u myapp -f

# Search logs for errors
journalctl --user -u myapp | grep -i error

# Export logs for analysis
journalctl --user -u myapp --since "24 hours ago" > app.log
```

#### System Logs
```bash
# Check system logs
sudo journalctl -f

# Check specific service logs
sudo journalctl -u docker -f
sudo journalctl -u ssh -f
```

### Debugging Tools

#### Container Debugging
```bash
# Enter container for debugging
podman exec -it myapp-container /bin/bash

# Run debugging tools in container
podman exec myapp-container ps aux
podman exec myapp-container netstat -tulpn
```

#### Network Debugging
```bash
# Check network connectivity
traceroute example.com
mtr example.com

# Check DNS resolution
nslookup example.com
dig example.com

# Test specific ports
telnet example.com 80
nc -zv example.com 80
```

### Performance Profiling

#### Application Profiling
```bash
# Node.js profiling
node --inspect myapp.js

# Python profiling
python -m cProfile myapp.py
```

#### System Profiling
```bash
# CPU profiling
perf top
perf record -g ./myapp

# Memory profiling
valgrind --tool=massif ./myapp
```

## Common Error Messages and Solutions

### Error: "Permission denied"
**Solution**: Check file permissions and ownership
```bash
sudo chown -R user:group /path/to/files
chmod 755 /path/to/executable
```

### Error: "Port already in use"
**Solution**: Find and stop the process using the port
```bash
lsof -i :8080
kill -9 PID
```

### Error: "No space left on device"
**Solution**: Clean up disk space
```bash
df -h
docker system prune -a
sudo apt autoremove
```

### Error: "Connection refused"
**Solution**: Check if service is running and accessible
```bash
systemctl status myservice
netstat -tulpn | grep :8080
```

## Emergency Procedures

### System Recovery

#### Service Recovery
```bash
# Stop all services
systemctl --user stop all-containers.target

# Clear problematic containers
podman rm -f $(podman ps -aq)

# Restart services
systemctl --user start all-containers.target
```

#### Database Recovery
```bash
# Stop database
systemctl --user stop postgres

# Check database integrity
pg_dump database > backup.sql

# Restore from backup
dropdb database
createdb database
psql database < backup.sql
```

### Rollback Procedures

#### Application Rollback
```bash
# Rollback to previous version
PREVIOUS_VERSION=$(git tag --sort=-version:refname | head -2 | tail -1)
git checkout $PREVIOUS_VERSION

# Redeploy previous version
./release-tooling/scripts/deploy_on_host.sh "all" "{}" "{}"
```

#### Configuration Rollback
```bash
# Restore configuration backup
cp /opt/deployment/backup/docker-compose.yml /opt/deployment/
systemctl --user restart myapp
```

## Getting Help

### Information to Collect

When seeking help, collect the following information:

1. **System Information**
   ```bash
   uname -a
   cat /etc/os-release
   podman version
   systemctl --version
   ```

2. **Error Messages**
   ```bash
   journalctl --user -u myapp --since "1 hour ago"
   ```

3. **Configuration**
   ```bash
   cat docker-compose.yml
   env | grep -v PASSWORD
   ```

4. **Resource Usage**
   ```bash
   free -h
   df -h
   podman stats --no-stream
   ```

### Support Channels

- Check the documentation: [docs/](.)
- Review existing issues: GitHub Issues
- Create new issue with collected information
- Consult with team members or security team for security-related issues

### Best Practices for Troubleshooting

1. **Start with the basics**: Check if services are running
2. **Check logs first**: Most issues are logged somewhere
3. **Isolate the problem**: Test individual components
4. **Document the issue**: Keep notes on what you've tried
5. **Test solutions**: Verify fixes work before deploying
6. **Update documentation**: Add new issues and solutions to this guide

## Related Documentation

- [Architecture Overview](docs/ARCHITECTURE.md) - System design and components
- [Security Guide](docs/SECURITY.md) - Security-related troubleshooting
- [Release Process](docs/RELEASE_PROCESS.md) - Deployment workflow troubleshooting
- [Local Testing](docs/LOCAL_TESTING.md) - Development and testing issues

Remember: When in doubt, start with the logs and work systematically through the troubleshooting steps. Most issues have been encountered before and documented either in this guide or in the system logs.