# GitHub Environments Configuration

This directory contains documentation for GitHub environment configurations required for the enhanced CI/CD pipeline.

## Required Environments

### 1. `staging`
- **Purpose**: Staging environment for testing deployments
- **Protection Rules**: None (automatic deployment)
- **Required Variables**:
  - `HOST`: Staging server hostname/IP
  - `USERNAME`: SSH username for staging server
- **Required Secrets**:
  - `KEY`: SSH private key for staging server
  - Additional secrets as needed by applications

### 2. `live`
- **Purpose**: Production environment
- **Protection Rules**: 
  - Required reviewers: At least 1 reviewer from administrators
  - Deployment branch: Only from `releases` branch
  - Wait timer: 0 minutes (approval required)
- **Required Variables**:
  - `HOST`: Production server hostname/IP
  - `USERNAME`: SSH username for production server
- **Required Secrets**:
  - `KEY`: SSH private key for production server
  - Additional secrets as needed by applications

### 3. `live-approval`
- **Purpose**: Approval gate for production deployments
- **Protection Rules**:
  - Required reviewers: At least 2 reviewers from administrators
  - Deployment branch: Only from `releases` branch
  - Wait timer: 0 minutes (approval required)
- **Required Variables**: None
- **Required Secrets**: None

## Setting Up Environments

1. Go to your repository settings
2. Navigate to "Environments"
3. Create each environment with the specified protection rules
4. Add the required variables and secrets for each environment
5. Configure reviewer lists with appropriate team members

## Security Considerations

- **Principle of Least Privilege**: Each environment only has access to secrets it needs
- **Separation of Concerns**: Staging and production environments are completely separate
- **Approval Process**: Production deployments require explicit approval
- **Audit Trail**: All deployments are logged and can be traced

## Deployment Flow

1. Code changes trigger build workflow
2. Successful builds deploy to staging automatically
3. Staging deployment triggers E2E tests
4. If staging tests pass, production deployment waits for approval
5. After approval, production deployment proceeds with additional safety checks
6. Post-deployment validation ensures services are healthy

## Rollback Process

If a deployment fails or issues are discovered:

1. Check the deployment logs for error details
2. Use the rollback information logged during deployment
3. Manually trigger a rollback using the previous deployment tag
4. Monitor services to ensure rollback is successful

## Monitoring and Alerting

- All deployments generate structured logs with timestamps
- Failed deployments automatically collect system state information
- Security scans run on all container images
- Dependency reviews are performed on pull requests