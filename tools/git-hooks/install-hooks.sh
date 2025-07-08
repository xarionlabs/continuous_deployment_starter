#!/bin/bash

# Pre-commit hooks installation script
# This script installs and configures pre-commit hooks for the repository

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🔧 Installing pre-commit hooks...${NC}"

# Get the repository root directory
REPO_ROOT=$(git rev-parse --show-toplevel)
SCRIPT_DIR="$REPO_ROOT/scripts"
GIT_HOOKS_DIR=$(git rev-parse --git-dir)/hooks

echo "Repository root: $REPO_ROOT"
echo "Git hooks directory: $GIT_HOOKS_DIR"

# Ensure git hooks directory exists
mkdir -p "$GIT_HOOKS_DIR"

# Check if pre-commit hook already exists
if [ -f "$GIT_HOOKS_DIR/pre-commit" ]; then
    echo -e "${YELLOW}⚠️  Pre-commit hook already exists. Creating backup...${NC}"
    cp "$GIT_HOOKS_DIR/pre-commit" "$GIT_HOOKS_DIR/pre-commit.backup.$(date +%Y%m%d_%H%M%S)"
    echo -e "${GREEN}✅ Backup created${NC}"
fi

# Copy the pre-commit hook
if [ -f "$SCRIPT_DIR/pre-commit" ]; then
    echo -e "${GREEN}📋 Installing pre-commit hook from scripts/pre-commit...${NC}"
    cp "$SCRIPT_DIR/pre-commit" "$GIT_HOOKS_DIR/pre-commit"
else
    echo -e "${YELLOW}⚠️  scripts/pre-commit not found. Using the existing comprehensive hook...${NC}"
    # The hook is already in place, so we just need to ensure it's executable
fi

# Make the hook executable
chmod +x "$GIT_HOOKS_DIR/pre-commit"

echo -e "${GREEN}✅ Pre-commit hook installed successfully!${NC}"
echo ""
echo -e "${GREEN}🔍 Hook Features:${NC}"
echo "  • app.pxy6.com checks (TypeScript, ESLint, Jest, build) when files are modified"
echo "  • Docker build tests when any Dockerfile is modified"
echo "  • YAML validation when any .yaml/.yml files are modified"
echo ""
echo -e "${GREEN}💡 Usage:${NC}"
echo "  • The hook runs automatically on every commit"
echo "  • All checks must pass for the commit to succeed"
echo "  • To skip hooks (not recommended): git commit --no-verify"
echo ""
echo -e "${GREEN}🛠️  Troubleshooting:${NC}"
echo "  • If hooks fail, fix the issues and commit again"
echo "  • For Docker build failures, run: cd <app_dir> && docker build ."
echo "  • For YAML validation failures, check syntax with: docker run --rm -v \"\$(pwd):/workdir\" mikefarah/yq eval \".\" \"/workdir/<file>\""
echo ""
echo -e "${GREEN}🎉 Installation complete!${NC}"