# Git Hooks

This directory contains git hooks and installation scripts for the repository's pre-commit quality assurance system.

## Quick Start

To install the pre-commit hooks:

```bash
./scripts/install-hooks.sh
```

## What's Included

### Pre-commit Hook (`scripts/pre-commit`)

A comprehensive pre-commit hook that automatically runs quality checks based on which files are being committed:

#### 🔧 app.pxy6.com Checks
When files in `applications/app.pxy6.com/` are modified, the hook runs:
- **TypeScript type checking** (`npm run typecheck`)
- **ESLint linting** (`npm run lint`)
- **Jest tests** (`npm run test`)
- **Build process** (`npm run build`)

#### 🐳 Docker Build Tests
When any `Dockerfile` is modified, the hook:
- Tests Docker build for each modified Dockerfile
- Prevents commits if Docker builds fail
- Helps catch Docker build issues early

#### 📝 YAML Validation
When any `.yaml` or `.yml` files are modified, the hook:
- Validates YAML syntax using Docker with `mikefarah/yq`
- Prevents commits with invalid YAML syntax
- Helps catch configuration errors early
- No local dependencies required

### Installation Script (`scripts/install-hooks.sh`)

A helper script that:
- Installs the pre-commit hook from this directory
- Creates backups of existing hooks
- Makes hooks executable
- Provides usage instructions

## Usage

### Normal Operation
The hooks run automatically on every commit:
```bash
git add .
git commit -m "Your commit message"
# Hooks run automatically here
```

### Skip Hooks (Not Recommended)
If you need to skip hooks in an emergency:
```bash
git commit --no-verify -m "Emergency commit"
```

### Manual Hook Testing
You can manually test the hook without committing:
```bash
# Test the hook on currently staged files
.git/hooks/pre-commit
```

## Troubleshooting

### Common Issues

#### app.pxy6.com Checks Failing
```bash
# Navigate to the app directory
cd applications/app.pxy6.com/src

# Run individual checks to identify issues
npm run typecheck  # TypeScript errors
npm run lint       # ESLint errors
npm run test       # Test failures
npm run build      # Build errors
```

#### Docker Build Failures
```bash
# Navigate to the application directory
cd applications/your-app/

# Run Docker build to see detailed error
docker build .
```

#### YAML Validation Failures
```bash
# Check specific YAML file syntax
docker run --rm -v "$(pwd):/workdir" mikefarah/yq eval "." "/workdir/your-file.yaml"
```

### Performance Optimization

The hooks are designed to be fast and only run checks for modified files:
- Only runs app.pxy6.com checks when those files are modified
- Only tests Docker builds for modified Dockerfiles
- Only validates modified YAML files
- Uses existing node_modules when available

### Hook Management

#### Updating Hooks
1. Edit `scripts/pre-commit`
2. Run `./scripts/install-hooks.sh` to update the installed hook

#### Removing Hooks
```bash
rm .git/hooks/pre-commit
```

#### Checking Hook Status
```bash
ls -la .git/hooks/pre-commit
```

## Development

### Adding New Checks

To add new checks to the pre-commit hook:

1. Edit `scripts/pre-commit`
2. Add your check logic following the existing patterns
3. Test the hook manually
4. Run `./scripts/install-hooks.sh` to update the installed hook

### Example Check Pattern

```bash
# Check for specific file types
SPECIFIC_FILES=$(git diff --cached --name-only | grep -E "\.ext$" || true)

if [ -n "$SPECIFIC_FILES" ]; then
    echo "🔍 Checking specific files..."
    
    for file in $SPECIFIC_FILES; do
        if [ -f "$file" ]; then
            echo "Checking $file..."
            
            # Your check logic here
            if your_check_command "$file"; then
                echo "✅ $file passed"
            else
                echo "❌ $file failed"
                exit 1
            fi
        fi
    done
    
    echo "🎉 All specific files passed!"
else
    echo "No specific files modified, skipping checks."
fi
```

## Integration with CI/CD

The pre-commit hooks complement the CI/CD pipeline by:
- Catching issues early in the development process
- Reducing failed CI builds
- Maintaining code quality standards
- Ensuring consistent formatting and linting

The same checks that run in the hooks also run in the GitHub Actions workflows, providing multiple layers of quality assurance.

## Best Practices

1. **Always run hooks**: Don't skip hooks unless absolutely necessary
2. **Fix issues locally**: Address hook failures before pushing
3. **Keep hooks fast**: Only run necessary checks for modified files
4. **Test hook changes**: Always test hook modifications manually
5. **Document new checks**: Update this README when adding new checks

## Compatibility

The hooks are designed to work with:
- Git worktrees (like this repository setup)
- Docker Desktop or Podman
- Node.js applications
- Python applications
- Any YAML configuration files

## Support

If you encounter issues with the git hooks:
1. Check the troubleshooting section above
2. Ensure Docker is running (for Docker and YAML checks)
3. Ensure Node.js and npm are installed (for app.pxy6.com checks)
4. Check that the hook is executable: `ls -la .git/hooks/pre-commit`