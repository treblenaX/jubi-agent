#!/bin/bash

# Jubi Setup Script
# Purpose: Initialize the Jubi agent workspace for immediate use.

set -e

# Colors for friendly output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
FOX='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${FOX}🦊 Jubi is arriving...${NC}"

# 1. Check for core directories
if [ ! -d "memory" ]; then
    echo -e "${BLUE}  -> Creating the 'memory/' directory for Jubi's growing mind...${NC}"
    mkdir -p memory
fi

# 2. Ensure basic Markdown files exist (safety check)
REQUIRED_FILES=("IDENTITY.md" "SOUL.md" "USER.md" "AGENTS.md")
for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${BLUE}  -> Warning: $file is missing. You might want to check your persona files.${NC}"
    fi
done

# 3. Initialize a basic MEMORY.md if it doesn't exist
if [ ! -f "MEMORY.md" ]; then
    echo -e "${BLUE}  -> Creating initial MEMORY.md...${NC}"
    cat <<EOF > MEMORY.md
# MEMORY.md - Durable Facts and Decisions

<!-- This file holds long-term, durable facts and decisions made during sessions. -->
EOF
fi

# 4. Finalizing
echo -e "${GREEN}✅ Jubi is fully configured and ready for adventure!${NC}"
echo -e "${FOX}🦊 To begin, launch your OpenClaw session in this directory.${NC}"
