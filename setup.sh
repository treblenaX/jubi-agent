#!/bin/bash

# Jubi Multi-Agent Provisioning Script
# Purpose: Automatically set up the multi-agent system by deploying blueprints.

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
FOX='\033[1;33m'
NC='\033[0m'

echo -e "${FOX}🦊 Initializing Jubi Multi-Agent Environment...${NC}"

# 1. Preflight Checks
if ! command -v openclaw &> /dev/null; then
    echo -e "${RED}Error: openclaw CLI not found. Please install it first.${NC}"
    exit 1
fi

if [ -z "$BRAVE_API_KEY" ]; then
    echo -e "${BLUE}⚠️  Warning: BRAVE_API_KEY is not set. Search capabilities will be limited.${NC}"
fi

# 2. Define the agents to provision
# Each entry is: "blueprint_dir:agent_name"
AGENTS=(" .agents/jubi:jubi" ".agents/jubi-coder:jubi-coder")

for entry in "${AGENTS[@]}"; do
    IFS=":" read -r dir name <<< "$entry"
    
    echo -e "${BLUE}▶  Deploying agent: $name${NC}"
    
    # Create the destination directory (local path for the agent)
    # In a production scenario, this might be a shared network path, 
    # but here we use a standard local path.
    DEST_DIR="$HOME/.openclaw/workspace-$name"
    mkdir -p "$DEST_DIR"
    
    # Register the agent with OpenClaw
    openclaw agents add "$name" --workspace "$DEST_DIR"
    
    # Deploy identity files as source files
    echo -e "${BLUE}   Deploying identity blueprints to $DEST_DIR...${NC}"
    cp "$dir/soul.md" "$DEST_DIR/_soul_source.md"
    cp "$dir/user.md" "$DEST_DIR/_user_source.md"
    cp "$dir/agents.md" "$DEST_DIR/_agents_source.md"
    
    # If a specific identity file exists (like identity.md or project-specific ones), 
    # we ensure they are included or handled.
    if [ -f "$dir/identity.md" ]; then
        cp "$dir/identity.md" "$DEST_DIR/_identity_source.md"
    fi

    # Generate the Bootstrap script for the agent
    echo -e "${BLUE}   Generating bootstrap instructions...${NC}"
    cat <<EOF > "$DEST_DIR/BOOTSTRAP.md"
# Bootstrap: $(date +%Y-%m-%d)
# Instructions for the first time you are activated.

You have been provisioned from a blueprint. To finalize your identity:
1. Merge the source files into your primary configuration files:
   - Merge \`_soul_source.md\` into \`SOUL.md\`
   - Merge \`_user_source.md\` into \`USER.md\`
   - Merge \`_agents_source.md\` into \`AGENTS.md\`
2. Delete all \`_source.md\` files.
3. Once complete, you will be fully initialized and ready to operate.

# Done.
EOF

    echo -e "${GREEN}✅ Agent $name successfully provisioned.${NC}"
done

echo -e "${FOX}🦊 Multi-agent environment successfully initialized!${NC}"
echo -e "${BLUE}To start the main coordinator, run your usual openclaw command for 'jubi'.${NC}"
