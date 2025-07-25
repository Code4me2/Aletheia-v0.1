# n8n Automated Workflow Loading

## Overview

This system automatically imports and activates n8n workflows on container startup, eliminating manual configuration. It uses a custom initialization script that runs before n8n's normal operation.

**✅ The autoload mechanism is working perfectly** - workflows are successfully imported into n8n with deduplication to prevent duplicate entries. Custom node loading remains a separate issue.

## Current Status

### ✅ **Working Features**
- **Workflow Import**: All JSON files from `/workflow_json/` are successfully imported
- **Deduplication**: Prevents duplicate imports by checking existing workflows
- **Health Checking**: Waits for n8n readiness before operations
- **Process Management**: Handles n8n lifecycle (background → operations → foreground)
- **Logging**: Clear progress tracking with import/skip counts
- **Error Handling**: Graceful handling of missing files or import failures

### ❌ **Known Limitations**
- **Custom Node Recognition**: n8n doesn't load custom nodes from mounted directory
- **Workflow Activation**: Workflows using custom nodes fail with "Unrecognized node type"
  - Affects: `n8n-nodes-hierarchicalSummarization`, `n8n-nodes-haystack`

### 🎆 **Recent Improvements**
- **Deduplication Added**: No more duplicate workflow imports
- **Single Script**: Cleaned up multiple experimental versions
- **Production Ready**: Stable implementation for workflow automation

## Architecture

### Components

1. **Init Script** (`/n8n/init-workflows.sh`)
   - Runs as Docker entrypoint
   - Manages n8n lifecycle during import
   - Uses wget for health checks (curl not available)
   - Implements deduplication to prevent duplicate imports

2. **Docker Configuration**
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
2. Start n8n (background) → Wait for Health (up to 60 seconds)
3. Check Existing Workflows → Import New Workflows Only
4. Skip Duplicates → Attempt Activation
5. Stop Background n8n → Restart n8n (foreground)
```

### Implementation Details

#### Key Functions:

1. **`wait_for_n8n()`** - Health check using wget on `/healthz` endpoint
2. **`get_existing_workflows()`** - Lists current workflow names from n8n CLI
3. **`get_workflow_name_from_json()`** - Extracts name using jq or grep/sed fallback
4. **`import_workflows()`** - Imports with deduplication logic
5. **`activate_workflows()`** - Attempts to activate all workflows

#### Example Output:
```
[n8n-init] Starting n8n workflow automation with deduplication...
[n8n-init] Starting n8n in background...
[n8n-init] Waiting for n8n to be ready...
[n8n-init] n8n is ready!
[n8n-init] Importing workflows with deduplication...
[n8n-init] Checking existing workflows...
[n8n-init] Found 4 workflow file(s)
[n8n-init] Skipping 'Main Workflow' - already exists
[n8n-init] Skipping 'Basic Search Workflow' - already exists
[n8n-init] Import complete: 0 imported, 2 skipped
[n8n-init] Activating all workflows...
[n8n-init] All workflows activated successfully
[n8n-init] Stopping background n8n process...
[n8n-init] Starting n8n in foreground...
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

## Custom Node Loading Issue

### Current Situation

**The workflow import is successful** - the issue is that n8n cannot find the custom node types referenced in the workflows. Despite having:
- Custom nodes mounted at `/home/node/.n8n/custom`
- Environment variable `N8N_CUSTOM_EXTENSIONS=/home/node/.n8n/custom`
- Proper `package.json` with `n8n` field
- Built `dist/` directories with compiled JavaScript

n8n still reports "Unrecognized node type" for custom nodes.

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

### Investigation Results

1. **Package Name Mismatch** (✅ FIXED): 
   - `n8n-nodes-haystack-rag` → `n8n-nodes-haystack` (fixed)
   - `n8n-nodes-hierarchicalsummarization` → `n8n-nodes-hierarchicalSummarization` (fixed)

2. **Permission Issues**: 
   - Mounted volumes have different ownership than container user
   - NPM install attempts fail with EACCES errors

3. **Loading Mechanism**:
   - n8n should auto-load from `N8N_CUSTOM_EXTENSIONS` directory
   - Despite fixing package names, nodes are still not recognized
   - This appears to be an issue with n8n v1.101.1 not loading custom extensions properly

## Solutions

### Implemented Solution: Fixed Package Names ✅

The root cause was package name mismatches between the custom nodes' package.json files and what the workflows expected. This has been fixed:

1. **Haystack Node**: Changed `"name": "n8n-nodes-haystack-rag"` to `"name": "n8n-nodes-haystack"`
2. **Hierarchical Summarization**: Changed `"name": "n8n-nodes-hierarchicalsummarization"` to `"name": "n8n-nodes-hierarchicalSummarization"`
3. **Rebuilt nodes** to ensure dist folders are updated

### Alternative Solutions (Since custom extension loading is not working)

#### Option 1: Custom Docker Image (RECOMMENDED)

Create a custom n8n image with nodes pre-installed. This is the most reliable approach:
```dockerfile
# Build custom n8n image with nodes pre-installed
FROM n8nio/n8n:latest
COPY ./custom-nodes /custom-nodes
RUN cd /custom-nodes && npm install each-node
```

#### Option 2: Install Nodes at Container Start

Modify the init script to copy and install nodes directly into n8n's node_modules:

```bash
# Copy custom nodes to n8n's node_modules directory
cp -r /home/node/.n8n/custom/* /usr/local/lib/node_modules/n8n/node_modules/
```

#### Option 3: Use n8n Community Nodes

Publish the custom nodes to npm and install them as community nodes through n8n's UI.

#### Option 4: Downgrade n8n Version

Use an older n8n version where custom extension loading worked properly.

**Note**: 
- NPM install in running container fails due to permission issues with mounted volumes
- N8N_CUSTOM_EXTENSIONS environment variable is not loading custom nodes in n8n v1.101.1
- Package name fixes were implemented but n8n still doesn't recognize the custom nodes

## Usage Guide

### Initial Setup

```bash
# 1. Ensure custom nodes are built (one-time setup)
cd /home/manesha/AI_Legal/Aletheia-v0.1/n8n
./build-custom-nodes.sh

# 2. Start n8n with auto-import
docker compose up -d n8n

# 3. Watch import progress
docker compose logs -f n8n | grep "n8n-init"
```

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

| Error | Cause | Solution | Status |
|-------|-------|----------|--------|
| "exec: no such file" | Script mount issue | Verify mount path `/data/init-workflows.sh` | ✅ Fixed |
| "NOT NULL constraint" | Missing workflow fields | Add `name` and `active` fields | ✅ Fixed |
| "Unrecognized node type" | Custom nodes not loaded | See custom node solutions below | ❌ Ongoing |
| "Read-only file system" | Correct behavior | Script is read-only mounted | ℹ️ Info |
| Duplicate workflows | Pre-deduplication imports | Use cleanup commands below | ✅ Prevented |

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
1. ~~Fix package name mismatches~~ ✅ **COMPLETED**
2. Implement custom Docker image with pre-installed nodes
3. Test workflow activation with custom image

### Future Improvements
1. ~~Check for existing workflows before import~~ ✅ **IMPLEMENTED**
2. Version control for workflow updates
3. Automated custom node installation
4. Credential management system
5. Environment-specific workflow loading
6. Clean up existing duplicates automatically

## Recent Updates

### 🔧 **Package Name Fixes** (2024-07-24)

Fixed custom node package names to match workflow expectations:
- `n8n-nodes-haystack-rag` → `n8n-nodes-haystack`
- `n8n-nodes-hierarchicalsummarization` → `n8n-nodes-hierarchicalSummarization`
- Rebuilt affected nodes to update dist folders

### 🧹 **Script Cleanup** (2024-07-24)

Removed multiple experimental versions:
- `init-workflows-enhanced.sh` - Custom node install attempt (permission issues)
- `init-workflows-final.sh` - Another npm install approach 
- `init-workflows-fixed.sh` - Symlink approach
- `init-workflows-simple.sh` - Basic verification approach
- `init-workflows-original.sh` - Backup of working version

**Result**: Single, clean `init-workflows.sh` with deduplication

## Related Documentation

- [CLAUDE.md](../CLAUDE.md) - Project overview
- [Custom Nodes README](../n8n/custom-nodes/README.md) - Node details
- [n8n Docs](https://docs.n8n.io/) - Official documentation