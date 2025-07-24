# n8n Automated Workflow Loading

## Overview

This system automatically imports and activates n8n workflows on container startup, eliminating manual configuration. It uses a custom initialization script that runs before n8n's normal operation.

**✅ The autoload mechanism is working perfectly** - workflows are successfully imported into n8n with deduplication to prevent duplicate entries. The only issue is that custom nodes aren't being loaded by n8n, preventing workflow activation.

## Current Status

### ✅ **Working**
- **Workflow Import**: All JSON files from `/workflow_json/` are successfully imported into n8n
- **Deduplication**: Script checks for existing workflows and skips duplicates (fixed!)
- **JSON Structure**: All workflow files have required fields (`name`, `active`, etc.)
- **Import Script**: The `init-workflows.sh` correctly waits for n8n and imports workflows
- **Standard Nodes**: Workflows using built-in n8n nodes would activate correctly
- **Health Checking**: System properly waits for n8n readiness before import
- **Logging**: Clear initialization progress tracking with import/skip counts

### ❌ **Not Working**
- **Custom Nodes**: n8n doesn't recognize any custom node types
- **Workflow Activation**: Workflows using custom nodes fail with "Unrecognized node type" errors
- **Node Discovery**: Custom nodes are mounted but not loaded by n8n

### ✅ **Fixed Issues**
- **Duplicate Imports**: ~~Multiple restarts create duplicate workflow entries~~ **FIXED**
- **Deduplication**: Import now checks for existing workflows and skips duplicates

## Architecture

### Components

1. **Init Script** (`/n8n/init-workflows.sh`)
   - Runs as Docker entrypoint
   - Manages n8n lifecycle during import
   - Uses wget for health checks (curl not available)
   - Implements deduplication to prevent duplicate imports

2. **Build Script** (`/n8n/build-custom-nodes.sh`)
   - Separate utility script (NOT an init script)
   - Builds TypeScript custom nodes to JavaScript
   - Run manually before first deployment
   - Not part of the automated workflow loading

3. **Docker Configuration**
   ```yaml
   n8n:
     entrypoint: ["/bin/sh", "/data/init-workflows.sh"]
     environment:
       - N8N_CUSTOM_EXTENSIONS=/home/node/.n8n/custom
     volumes:
       - ./workflow_json:/workflows:ro
       - ./n8n/init-workflows.sh:/data/init-workflows.sh:ro
       - ./n8n/custom-nodes:/home/node/.n8n/custom
   ```

3. **Workflow Storage** (`/workflow_json/`)
   - `main_workflow.json` - Main application workflow
   - `basic_search.json` - Haystack search workflow
   - `hierarchical-summarization-template.json` - Document processing

### Process Flow

```
1. Container Start → Init Script Execution
2. Start n8n (background) → Wait for Health
3. Check Existing Workflows → Import New Workflows Only
4. Skip Duplicates → Attempt Activation
5. Stop n8n → Restart n8n (foreground)
```

### Deduplication Logic

The script now includes three key functions for deduplication:

1. **`get_existing_workflows()`** - Lists all current workflow names
2. **`get_workflow_name_from_json()`** - Extracts workflow name from JSON file
3. **`import_workflows()`** - Checks if workflow exists before importing

Example output:
```
[n8n-init] Checking existing workflows...
[n8n-init] Skipping 'Main Workflow' - already exists
[n8n-init] Importing: new_workflow.json (name: 'New Workflow')
[n8n-init] Import complete: 1 imported, 3 skipped
```

## Implementation Details

### Workflow Requirements

```json
{
  "name": "Workflow Name",     // Required
  "active": false,              // Required
  "nodes": [...],               // Required
  "connections": {...}          // Required
}
```

### Node Naming Conventions

| Type | Format | Example |
|------|--------|---------|
| Standard | `n8n-nodes-base.nodeName` | `n8n-nodes-base.webhook` |
| LangChain | `@n8n/n8n-nodes-langchain.nodeName` | `@n8n/n8n-nodes-langchain.agent` |
| Custom | `n8n-nodes-package.nodeName` | `n8n-nodes-haystack.haystackSearch` |

### Files Being Imported

All files in `/workflow_json/`:
- ✅ Successfully imported (appears in n8n UI)
- ✅ Proper JSON structure recognized
- ❌ Cannot activate if using custom nodes

## Custom Node Problem

### Root Cause

**The workflow import is successful** - the issue is that n8n cannot find the custom node types referenced in the workflows. Custom nodes have the `n8n` field in `package.json` but n8n isn't loading them:

```json
{
  "n8n": {
    "n8nNodesApiVersion": 1,
    "nodes": ["dist/nodes/NodeName/NodeName.node.js"]
  }
}
```

### Affected Nodes

| Node | Purpose | Error |
|------|---------|-------|
| `n8n-nodes-haystack` | Document search | Unrecognized node type |
| `n8n-nodes-hierarchicalSummarization` | Document processing | Unrecognized node type |
| `n8n-nodes-deepseek` | AI integration | Not used in workflows |
| `n8n-nodes-yake` | Keyword extraction | Not used in workflows |
| `n8n-nodes-citationchecker` | Citation validation | Not used in workflows |
| `n8n-nodes-bitnet` | BitNet AI | Not used in workflows |

### Why It's Failing

1. **Missing NPM Installation**: Nodes are mounted but not installed as packages
2. **Path Resolution**: n8n may expect nodes in different locations
3. **Version Mismatch**: Possible n8n version compatibility issues

## Solutions

### Option 1: Install Nodes in Container (Recommended)

```bash
# Enter container
docker compose exec n8n /bin/sh

# Install each custom node
cd /home/node/.n8n
npm install ./custom/n8n-nodes-haystack
npm install ./custom/n8n-nodes-hierarchicalSummarization

# Restart n8n
exit
docker compose restart n8n
```

### Option 2: Use Community Nodes

1. Package nodes properly with npm
2. Publish to npm registry
3. Install via n8n UI or CLI

### Option 3: Debug Loading

```bash
# Check n8n's node discovery
docker compose exec n8n ls -la ~/.n8n/nodes/

# View loading errors
docker compose logs n8n | grep -i "load"

# Test node require
docker compose exec n8n node -e "console.log(require.resolve('n8n-nodes-haystack'))"
```

## Usage Guide

### Initial Setup

```bash
# 1. Build custom nodes (one-time setup, not part of automation)
cd /home/manesha/AI_Legal/Aletheia-v0.1/n8n
./build-custom-nodes.sh

# 2. Start n8n with auto-import (init-workflows.sh runs automatically)
docker compose up -d n8n

# 3. Watch import progress
docker compose logs -f n8n | grep "n8n-init"
```

**Note**: Only one init script (`init-workflows.sh`) is used. The `build-custom-nodes.sh` is a separate utility for building TypeScript nodes, not part of the automated workflow loading process.

### Adding New Workflows

1. Add JSON file to `./workflow_json/`
2. Ensure required fields are present
3. Restart container: `docker compose restart n8n`

### Monitoring

```bash
# List imported workflows
docker compose exec n8n n8n list:workflow

# Check activation status
docker compose logs n8n | grep "Activation"
```

## Troubleshooting

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "exec: no such file" | Script mount issue | Verify mount path `/data/init-workflows.sh` |
| "NOT NULL constraint" | Missing workflow fields | Add `name` and `active` fields |
| "Unrecognized node type" | Custom nodes not loaded | Install nodes via npm in container |
| "Read-only file system" | Correct behavior | Script is read-only mounted |
| Duplicate workflows | Imported before deduplication fix | Manually clean up old duplicates |

### Quick Fixes

```bash
# Check for duplicate workflows
docker compose exec n8n n8n list:workflow | cut -d'|' -f2 | sort | uniq -c | sort -nr

# Remove duplicate workflows (keep one, delete others)
docker compose exec n8n n8n delete:workflow --id=WORKFLOW_ID

# Manually activate workflow
docker compose exec n8n n8n update:workflow --id=WORKFLOW_ID --active=true

# Clear all data and start fresh (nuclear option)
docker compose down n8n
docker volume rm aletheia-v01_n8n_data
docker compose up -d n8n

# Verify deduplication is working
docker compose logs n8n | grep "Import complete"
```

## Next Steps

### Immediate
1. Install custom nodes properly in n8n container
2. Test workflow activation after node installation
3. ~~Add deduplication logic to import script~~ ✅ **COMPLETED**

### Future Improvements
1. ~~Check for existing workflows before import~~ ✅ **IMPLEMENTED**
2. Version control for workflow updates
3. Automated custom node installation
4. Credential management system
5. Environment-specific workflow loading
6. Clean up existing duplicates automatically

## Script Cleanup Summary

### ✅ **Removed** (cleaned up unnecessary files):
- `init-workflows.sh.backup` (no longer needed)
- `init-workflows-dedup.sh` (was redundant)

### ✅ **Kept** (essential scripts):
- `init-workflows.sh` - The main workflow automation script with deduplication
- `build-custom-nodes.sh` - The utility script for building custom nodes

The setup is now clean and simple with only the necessary scripts, each serving a distinct purpose.

## Related Documentation

- [CLAUDE.md](../CLAUDE.md) - Project overview
- [Custom Nodes README](../n8n/custom-nodes/README.md) - Node details
- [n8n Docs](https://docs.n8n.io/) - Official documentation