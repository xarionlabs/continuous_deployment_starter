# Security Best Practices and Guidelines

This document outlines the security considerations, best practices, and guidelines for the continuous deployment system. Security is implemented at multiple layers to provide comprehensive protection.

## Security Overview

The continuous deployment system implements a defense-in-depth security strategy with multiple layers of protection:

1. **Infrastructure Security**: Host-level security and network isolation
2. **Container Security**: Rootless containers and image security
3. **Application Security**: Secure coding practices and dependency management
4. **Data Security**: Encryption, secrets management, and access controls
5. **Operational Security**: Monitoring, logging, and incident response

## Infrastructure Security

### 1. Host Security

#### Operating System Hardening
```bash
# Regular system updates
sudo apt update && sudo apt upgrade -y

# Install security updates automatically
sudo apt install unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades

# Configure automatic security updates
echo 'APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Download-Upgradeable-Packages "1";
APT::Periodic::AutocleanInterval "7";
APT::Periodic::Unattended-Upgrade "1";' | sudo tee /etc/apt/apt.conf.d/20auto-upgrades
```

#### Firewall Configuration
```bash
# Configure UFW (Uncomplicated Firewall)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Advanced firewall rules for specific services
sudo ufw allow from 10.0.0.0/8 to any port 5432  # PostgreSQL from private networks only
sudo ufw allow from 172.16.0.0/12 to any port 6379  # Redis from private networks only
```

#### SSH Security
```bash
# SSH hardening configuration in /etc/ssh/sshd_config
Protocol 2
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2
AllowUsers deployment-user
```

### 2. Network Security

#### Network Segmentation
```yaml
# Docker network configuration for service isolation
networks:
  frontend:
    name: frontend-network
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
  backend:
    name: backend-network
    driver: bridge
    ipam:
      config:
        - subnet: 172.21.0.0/16
  database:
    name: database-network
    driver: bridge
    ipam:
      config:
        - subnet: 172.22.0.0/16
```

#### SSL/TLS Configuration
```nginx
# Nginx SSL configuration
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384;
ssl_prefer_server_ciphers on;
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 10m;
ssl_stapling on;
ssl_stapling_verify on;

# Security headers
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header X-Frame-Options DENY always;
add_header X-Content-Type-Options nosniff always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
```

## Container Security

### 1. Rootless Containers

#### Podman Rootless Configuration
```bash
# Enable rootless containers for deployment user
sudo usermod --add-subuids 100000-165535 --add-subgids 100000-165535 deployment-user

# Configure rootless Podman
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export DBUS_SESSION_BUS_ADDRESS="unix:path=${XDG_RUNTIME_DIR}/bus"

# Enable lingering for the deployment user
sudo loginctl enable-linger deployment-user
```

#### Container Runtime Security
```bash
# Run containers with security profiles
podman run --security-opt seccomp=unconfined \
           --security-opt apparmor=unconfined \
           --cap-drop ALL \
           --cap-add NET_BIND_SERVICE \
           --read-only \
           --tmpfs /tmp \
           myapp:latest
```

### 2. Image Security

#### Image Signing and Attestation
```bash
# Sign container images during build
docker buildx build --attest type=sbom \
                   --attest type=provenance \
                   --tag myapp:latest \
                   --push .

# Verify image signatures
cosign verify --key cosign.pub myapp:latest
```

#### Vulnerability Scanning
```yaml
# GitHub Actions vulnerability scanning
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: '${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ env.IMAGE_TAG }}'
    format: 'sarif'
    output: 'trivy-results.sarif'

- name: Upload Trivy scan results to GitHub Security tab
  uses: github/codeql-action/upload-sarif@v2
  with:
    sarif_file: 'trivy-results.sarif'
```

#### Base Image Security
```dockerfile
# Use minimal, security-focused base images
FROM cgr.dev/chainguard/node:latest AS builder
FROM cgr.dev/chainguard/nginx:latest AS runtime

# Or use official images with specific tags
FROM node:18-alpine AS builder
FROM nginx:1.24-alpine AS runtime

# Always specify exact versions
FROM postgres:15.4-alpine
FROM redis:7.2-alpine
```

### 3. Container Runtime Security

#### Security Contexts
```yaml
# Docker Compose security configuration
services:
  app:
    image: myapp:latest
    security_opt:
      - no-new-privileges:true
      - seccomp:unconfined
    cap_drop:
      - ALL
    cap_add:
      - NET_BIND_SERVICE
    read_only: true
    tmpfs:
      - /tmp:noexec,nosuid,size=100m
    user: "1000:1000"
```

#### Resource Limits
```yaml
# Resource constraints for security
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '0.50'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
    ulimits:
      nproc: 65535
      nofile:
        soft: 20000
        hard: 40000
```

## Application Security

### 1. Secure Coding Practices

#### Environment Variable Security
```bash
# Secure environment variable handling
# Never commit secrets to version control
echo "SECRET_KEY=your-secret-here" >> .env
echo ".env" >> .gitignore

# Use GitHub secrets for sensitive data
# Reference in workflows as ${{ secrets.SECRET_NAME }}
```

#### Input Validation and Sanitization
```typescript
// TypeScript/JavaScript input validation
import { z } from 'zod';

const userSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8).max(100),
  age: z.number().min(18).max(120)
});

export function validateUser(input: unknown) {
  return userSchema.parse(input);
}
```

```python
# Python input validation
from pydantic import BaseModel, EmailStr, validator

class UserModel(BaseModel):
    email: EmailStr
    password: str
    age: int

    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        return v
```

#### Authentication and Authorization
```typescript
// JWT token security
import jwt from 'jsonwebtoken';

const JWT_SECRET = process.env.JWT_SECRET!;
const JWT_EXPIRES_IN = '1h';

export function generateToken(payload: any): string {
  return jwt.sign(payload, JWT_SECRET, {
    expiresIn: JWT_EXPIRES_IN,
    algorithm: 'HS256'
  });
}

export function verifyToken(token: string): any {
  return jwt.verify(token, JWT_SECRET, {
    algorithms: ['HS256']
  });
}
```

### 2. Dependency Security

#### Dependency Scanning
```bash
# Node.js dependency audit
npm audit --audit-level moderate
npm audit fix

# Python dependency scanning
pip-audit --desc --format=json
safety check --json
```

#### Package Lock Files
```bash
# Always commit lock files
git add package-lock.json  # Node.js
git add poetry.lock       # Python Poetry
git add requirements.txt  # Python pip

# Verify integrity during builds
npm ci --only=production
poetry install --no-dev
```

### 3. Database Security

#### Connection Security
```python
# Secure database connection
import ssl
from sqlalchemy import create_engine

# Use SSL/TLS for database connections
DATABASE_URL = f"postgresql://user:password@host:5432/dbname?sslmode=require&sslcert=client-cert.pem&sslkey=client-key.pem&sslrootcert=ca-cert.pem"

engine = create_engine(
    DATABASE_URL,
    connect_args={
        "sslmode": "require",
        "sslcert": "client-cert.pem",
        "sslkey": "client-key.pem",
        "sslrootcert": "ca-cert.pem"
    }
)
```

#### SQL Injection Prevention
```python
# Use parameterized queries
from sqlalchemy.text import text

# Safe query with parameters
query = text("SELECT * FROM users WHERE email = :email")
result = connection.execute(query, {"email": user_email})

# ORM usage (automatically parameterized)
user = session.query(User).filter(User.email == user_email).first()
```

```typescript
// TypeScript/Prisma ORM (safe by default)
const user = await prisma.user.findUnique({
  where: { email: userEmail },
  select: { id: true, email: true, name: true }
});
```

## Data Security

### 1. Secrets Management

#### GitHub Secrets
```yaml
# Use GitHub secrets in workflows
env:
  DATABASE_URL: ${{ secrets.DATABASE_URL }}
  JWT_SECRET: ${{ secrets.JWT_SECRET }}
  SHOPIFY_API_KEY: ${{ secrets.SHOPIFY_API_KEY }}
  SHOPIFY_API_SECRET: ${{ secrets.SHOPIFY_API_SECRET }}
```

#### Podman Secrets
```bash
# Create Podman secrets
echo "database-password" | podman secret create db-password -
echo "jwt-secret-key" | podman secret create jwt-secret -

# Use secrets in containers
podman run --secret db-password,type=env,target=DATABASE_PASSWORD myapp:latest
```

#### Runtime Secret Injection
```python
# Python secret management
import os
from pathlib import Path

def get_secret(secret_name: str) -> str:
    """Get secret from environment or file"""
    # Try environment variable first
    env_value = os.environ.get(secret_name)
    if env_value:
        return env_value
    
    # Try secret file
    secret_file = Path(f"/run/secrets/{secret_name}")
    if secret_file.exists():
        return secret_file.read_text().strip()
    
    raise ValueError(f"Secret {secret_name} not found")

# Usage
DATABASE_PASSWORD = get_secret("DATABASE_PASSWORD")
```

### 2. Encryption

#### Data at Rest
```sql
-- PostgreSQL encryption
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    encrypted_data BYTEA  -- Store encrypted data
);

-- Use application-level encryption
INSERT INTO users (email, encrypted_data) 
VALUES ('user@example.com', pgp_sym_encrypt('sensitive data', 'encryption_key'));
```

#### Data in Transit
```nginx
# Nginx SSL configuration
server {
    listen 443 ssl http2;
    server_name example.com;
    
    ssl_certificate /etc/ssl/certs/example.com.pem;
    ssl_certificate_key /etc/ssl/private/example.com.key;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}
```

### 3. Data Protection

#### Data Minimization
```typescript
// Only collect necessary data
interface UserProfile {
  id: string;
  email: string;
  name: string;
  // Don't store sensitive data unnecessarily
  // preferences: UserPreferences;
}

// Implement data retention policies
async function cleanupOldData() {
  const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);
  
  await prisma.auditLog.deleteMany({
    where: {
      createdAt: {
        lt: thirtyDaysAgo
      }
    }
  });
}
```

#### Access Controls
```yaml
# Database access controls
services:
  postgres:
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: myapp_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    networks:
      - database
    # Only expose to internal network
    ports: []
```

## Operational Security

### 1. Monitoring and Logging

#### Security Event Logging
```python
# Python security logging
import logging
from datetime import datetime

security_logger = logging.getLogger('security')
security_logger.setLevel(logging.INFO)

# Configure structured logging
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

handler = logging.StreamHandler()
handler.setFormatter(formatter)
security_logger.addHandler(handler)

# Log security events
def log_security_event(event_type: str, user_id: str, details: dict):
    security_logger.info(
        f"Security event: {event_type}",
        extra={
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat(),
            'details': details
        }
    )

# Usage
log_security_event('login_failed', user_id, {'ip': request.remote_addr})
```

#### System Monitoring
```bash
# Monitor system security events
sudo journalctl -u ssh -f  # SSH login attempts
sudo journalctl -u podman -f  # Container events
sudo tail -f /var/log/auth.log  # Authentication logs
```

### 2. Incident Response

#### Security Incident Workflow
```yaml
# GitHub Actions security workflow
name: Security Incident Response

on:
  repository_dispatch:
    types: [security-incident]

jobs:
  incident-response:
    runs-on: ubuntu-latest
    steps:
      - name: Assess Incident
        run: |
          echo "Incident type: ${{ github.event.client_payload.type }}"
          echo "Severity: ${{ github.event.client_payload.severity }}"
      
      - name: Immediate Actions
        run: |
          # Rotate secrets if necessary
          if [ "${{ github.event.client_payload.type }}" == "credential-leak" ]; then
            echo "Rotating compromised credentials..."
            # Trigger secret rotation workflow
          fi
      
      - name: Notify Team
        uses: 8398a7/action-slack@v3
        with:
          status: custom
          custom_payload: |
            {
              text: "Security incident detected: ${{ github.event.client_payload.type }}"
            }
```

#### Rollback Procedures
```bash
# Emergency rollback script
#!/bin/bash
PREVIOUS_VERSION="${1:-$(git tag --sort=-version:refname | head -2 | tail -1)}"

echo "Rolling back to version: $PREVIOUS_VERSION"

# Stop current services
systemctl --user stop all-containers.target

# Restore previous configuration
git checkout $PREVIOUS_VERSION

# Redeploy with previous version
./release-tooling/scripts/deploy_on_host.sh "all" "{}" "{}"

# Verify rollback
./scripts/health-check.sh
```

### 3. Compliance and Auditing

#### Audit Trail
```sql
-- Audit table for tracking changes
CREATE TABLE audit_log (
    id SERIAL PRIMARY KEY,
    user_id UUID,
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(100),
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Trigger function for audit logging
CREATE OR REPLACE FUNCTION audit_trigger() RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO audit_log (user_id, action, resource_type, resource_id, old_values, new_values)
    VALUES (
        current_setting('myapp.user_id')::UUID,
        TG_OP,
        TG_TABLE_NAME,
        NEW.id,
        CASE WHEN TG_OP = 'DELETE' THEN row_to_json(OLD) ELSE NULL END,
        CASE WHEN TG_OP = 'DELETE' THEN NULL ELSE row_to_json(NEW) END
    );
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
```

#### Compliance Checks
```python
# Automated compliance checking
import asyncio
from typing import List, Dict

async def check_security_compliance() -> Dict[str, bool]:
    """Run security compliance checks"""
    checks = {
        'ssl_certificates_valid': await check_ssl_certificates(),
        'secrets_rotation_current': await check_secrets_rotation(),
        'dependencies_updated': await check_dependency_vulnerabilities(),
        'access_logs_enabled': await check_access_logging(),
        'backup_strategy_active': await check_backup_strategy(),
    }
    return checks

async def generate_compliance_report():
    """Generate compliance report"""
    results = await check_security_compliance()
    
    report = {
        'timestamp': datetime.utcnow().isoformat(),
        'compliance_status': all(results.values()),
        'checks': results,
        'recommendations': []
    }
    
    # Add recommendations for failed checks
    for check, passed in results.items():
        if not passed:
            report['recommendations'].append(f"Address {check} compliance issue")
    
    return report
```

## Security Testing

### 1. Automated Security Testing

#### Static Analysis Security Testing (SAST)
```yaml
# GitHub Actions SAST workflow
name: Security Analysis

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  security-analysis:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Run CodeQL Analysis
        uses: github/codeql-action/analyze@v2
        with:
          languages: javascript, python
          
      - name: Run Bandit Security Linter
        run: |
          pip install bandit
          bandit -r . -f json -o bandit-results.json
          
      - name: Run ESLint Security Plugin
        run: |
          npm install eslint-plugin-security
          npx eslint --ext .js,.ts . --format json --output-file eslint-results.json
```

#### Dynamic Application Security Testing (DAST)
```bash
# OWASP ZAP integration
#!/bin/bash
# Run OWASP ZAP against deployed application

docker run -t owasp/zap2docker-stable zap-baseline.py \
  -t https://staging.example.com \
  -J zap-report.json \
  -r zap-report.html

# Check for high-severity vulnerabilities
if grep -q "High" zap-report.json; then
  echo "High severity vulnerabilities found!"
  exit 1
fi
```

### 2. Penetration Testing

#### Manual Security Testing
```bash
# Security testing checklist
echo "Security Testing Checklist:"
echo "1. Authentication bypass attempts"
echo "2. SQL injection testing"
echo "3. Cross-site scripting (XSS) testing"
echo "4. Cross-site request forgery (CSRF) testing"
echo "5. Access control testing"
echo "6. File upload security testing"
echo "7. Session management testing"
echo "8. Input validation testing"
```

#### Automated Penetration Testing
```python
# Basic security testing script
import requests
import subprocess

def test_sql_injection(url: str, param: str):
    """Test for SQL injection vulnerabilities"""
    payloads = [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "' UNION SELECT * FROM users --"
    ]
    
    for payload in payloads:
        response = requests.get(url, params={param: payload})
        if "error" in response.text.lower() or "sql" in response.text.lower():
            print(f"Potential SQL injection vulnerability: {payload}")

def test_xss(url: str, param: str):
    """Test for XSS vulnerabilities"""
    payloads = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert('XSS')>",
        "javascript:alert('XSS')"
    ]
    
    for payload in payloads:
        response = requests.get(url, params={param: payload})
        if payload in response.text:
            print(f"Potential XSS vulnerability: {payload}")
```

## Security Checklists

### 1. Pre-Deployment Security Checklist

- [ ] All secrets are stored in GitHub Secrets or Podman secrets
- [ ] Container images are scanned for vulnerabilities
- [ ] Dependencies are up to date and audited
- [ ] SSL/TLS certificates are valid and properly configured
- [ ] Database connections use encryption
- [ ] Access controls are properly configured
- [ ] Logging and monitoring are enabled
- [ ] Backup and recovery procedures are tested
- [ ] Security tests pass in CI/CD pipeline

### 2. Post-Deployment Security Checklist

- [ ] Services are running with correct security contexts
- [ ] Network segmentation is properly configured
- [ ] Firewall rules are active and correct
- [ ] Monitoring and alerting are functional
- [ ] Audit logs are being generated
- [ ] Security headers are present in HTTP responses
- [ ] Unauthorized access attempts are blocked
- [ ] Performance baselines are established

### 3. Regular Security Maintenance

#### Weekly Tasks
- [ ] Review security logs for anomalies
- [ ] Check for new vulnerability disclosures
- [ ] Verify backup integrity
- [ ] Test alerting mechanisms

#### Monthly Tasks
- [ ] Update and patch all systems
- [ ] Review and rotate secrets
- [ ] Conduct security scans
- [ ] Review access control lists

#### Quarterly Tasks
- [ ] Conduct penetration testing
- [ ] Review and update security policies
- [ ] Security training for team members
- [ ] Disaster recovery testing

## Incident Response Procedures

### 1. Security Incident Classification

#### Severity Levels
- **Critical**: Data breach, system compromise, service outage
- **High**: Unauthorized access, privilege escalation
- **Medium**: Suspicious activity, policy violations
- **Low**: Security tool alerts, informational events

### 2. Response Procedures

#### Immediate Response (0-1 hour)
1. **Assess** the situation and determine severity
2. **Contain** the threat (isolate affected systems)
3. **Preserve** evidence (logs, snapshots)
4. **Notify** stakeholders and security team

#### Short-term Response (1-24 hours)
1. **Investigate** the incident thoroughly
2. **Remediate** immediate security gaps
3. **Restore** services safely
4. **Document** findings and actions taken

#### Long-term Response (1-7 days)
1. **Analyze** root cause
2. **Implement** permanent fixes
3. **Update** security policies and procedures
4. **Conduct** post-incident review

### 3. Communication Plan

#### Internal Communication
- Security team notification: Immediate
- Management notification: Within 1 hour
- Development team notification: Within 2 hours
- All staff notification: Within 24 hours

#### External Communication
- Customer notification: As required by law/policy
- Regulatory notification: As required by law
- Public disclosure: As determined by legal counsel

## Related Documentation

- [Architecture Overview](ARCHITECTURE.md) - System design and components
- [Release Process](RELEASE_PROCESS.md) - Deployment workflow and security
- [Local Testing](LOCAL_TESTING.md) - Secure development practices
- [Troubleshooting](TROUBLESHOOTING.md) - Security-related troubleshooting

## Conclusion

Security is a continuous process that requires ongoing attention and improvement. This document provides a comprehensive framework for implementing and maintaining security in the continuous deployment system. Regular review and updates of these practices are essential to maintain a strong security posture.

Remember that security is everyone's responsibility, and the best security practices are those that are consistently followed by the entire team. Stay informed about new threats and vulnerabilities, and be proactive in implementing security measures.

For specific security questions or incidents, consult with your security team or escalate according to your organization's incident response procedures.