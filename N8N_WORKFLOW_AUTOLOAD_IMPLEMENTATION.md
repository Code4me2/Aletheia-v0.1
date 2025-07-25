# n8n Workflow Autoload Implementation

## Overview

This document explains the current implementation of n8n workflow autoloading with custom nodes in the Aletheia-v0.1 project. The system automatically imports workflows and custom nodes when the n8n container starts.

## Architecture Components

### 1. Custom Docker Image (`Dockerfile.n8n`)

The custom n8n Docker image is built on top of the official n8n:1.101.1 image with the following modifications:

```dockerfile
FROM n8nio/n8n:1.101.1
```

#### Key Features:
- **Custom Nodes Installation**: Copies all custom nodes directly into `/home/node/.n8n/custom/`
- **Database Separation**: Uses `/data` for persistent storage (database) to avoid conflicts with custom nodes
- **Permission Fix**: Removes pnpm requirement from deepseek node
- **Init Script**: Uses a custom initialization script as the entrypoint

#### Directory Structure:
```
/home/node/.n8n/
├── custom/                    # Custom nodes directory
│   ├── n8n-nodes-haystack/
│   ├── n8n-nodes-hierarchicalSummarization/
│   ├── n8n-nodes-citationchecker/
│   ├── n8n-nodes-deepseek/
│   ├── n8n-nodes-yake/
│   └── n8n-nodes-bitnet/
└── database.sqlite            # n8n database (copied from /data)

/data/                         # Persistent volume mount
└── database.sqlite            # Persistent database storage
```

### 2. Initialization Script (`init-workflows.sh`)

The initialization script handles the complete startup process:

#### Startup Flow:

1. **Database Management**:
   - Copies existing database from `/data` to `/home/node/.n8n/` if it exists
   - Sets up a trap to copy database back on exit for persistence

2. **n8n Startup Process**:
   - Starts n8n in background mode
   - Waits for n8n to be ready (checks `/healthz` endpoint)
   - Maximum 30 attempts with 2-second intervals

3. **Workflow Import**:
   - Checks for workflows in `/workflows` directory
   - Extracts workflow names from JSON files
   - Implements deduplication - skips workflows that already exist
   - Uses `n8n import:workflow` command for each new workflow

4. **Workflow Activation**:
   - Attempts to activate all workflows using `n8n update:workflow --all --active=true`
   - Continues even if some workflows fail to activate

5. **Final Startup**:
   - Kills background n8n process
   - Starts n8n in foreground mode for Docker container

#### Key Functions:

- `wait_for_n8n()`: Health check with retry logic
- `get_existing_workflows()`: Lists current workflows in database
- `get_workflow_name_from_json()`: Extracts workflow name from JSON (supports jq and grep/sed fallback)
- `import_workflows()`: Handles deduplication and import
- `activate_workflows()`: Bulk activation of all workflows
- `main()`: Orchestrates the entire process

### 3. Docker Compose Configuration

```yaml
n8n:
  build:
    context: .
    dockerfile: Dockerfile.n8n
  environment:
    - N8N_CUSTOM_EXTENSIONS=/home/node/.n8n/custom
    - N8N_USER_FOLDER=/data
  volumes:
    - n8n_data:/data                    # Persistent database storage
    - ./n8n/local-files:/files         # Local file access
    - ./workflow_json:/workflows:ro     # Workflow definitions (read-only)
```

### 4. Custom Nodes Structure

Each custom node follows the standard n8n node structure:

```
n8n-nodes-[name]/
├── package.json          # Node metadata and n8n configuration
├── index.js             # Entry point (references dist)
├── dist/                # Compiled JavaScript
│   ├── index.js        # Main export
│   └── nodes/
│       └── [NodeName]/
│           ├── [NodeName].node.js    # Node implementation
│           └── [icon].svg            # Node icon
└── node_modules/        # Dependencies (if needed)
```

## Workflow Import Process

### 1. Workflow Detection
- Scans `/workflows` directory for `*.json` files
- Each file should contain a valid n8n workflow export

### 2. Deduplication Logic
- Extracts workflow name from JSON
- Compares against existing workflows in database
- Only imports workflows with unique names

### 3. Import Mechanism
- Uses n8n CLI: `n8n import:workflow --input="[file]"`
- Imports are logged with success/failure status
- Failed imports don't stop the process

### 4. Activation
- Bulk activation attempt for all workflows
- Some workflows may fail if custom nodes aren't recognized
- Standard node workflows activate successfully

## Current Issues and Limitations

### 1. Custom Node Recognition
- Custom nodes are installed but may show as `[nodeName].undefined`
- This is likely due to n8n's node discovery mechanism
- Workflows with custom nodes may need manual intervention in UI

### 2. Database Persistence
- Database is copied between `/data` and `/home/node/.n8n/`
- This ensures persistence across container restarts
- Potential race condition if container stops abruptly

### 3. Workflow Updates
- Existing workflows are never updated
- To update a workflow, it must be deleted first
- No version control for workflows

## File Modifications During Setup

### 1. Fixed Workflow Node Types
- Original: `"type": "n8n-nodes-haystack.haystackSearch"`
- Fixed to: `"type": "haystackSearch"`
- Script: `fix-workflow-node-types.sh` (created during setup)

### 2. Package.json Modifications
- Removed pnpm preinstall script from deepseek node
- Prevents installation failures in Docker environment

## Success Indicators

1. **Container Health**: n8n container shows as "healthy"
2. **Workflow Import**: Logs show "Successfully imported" messages
3. **Standard Nodes**: "Test Standard Nodes Only" workflow activates
4. **Port Access**: n8n UI accessible at http://localhost:5678

## Troubleshooting Guide

### Problem: Custom nodes not recognized
**Solution**: Access n8n UI, open workflows, and save them to trigger node resolution

### Problem: Workflows not importing
**Check**: 
- Workflow files in `./workflow_json/` directory
- JSON files are valid n8n exports
- Workflow names are unique

### Problem: Database not persisting
**Check**:
- Volume `n8n_data` exists
- Proper permissions on `/data` directory
- Exit trap is executing

## Future Improvements

1. **Node Registration**: Implement proper n8n node package installation
2. **Workflow Versioning**: Add version tracking for workflow updates
3. **Error Recovery**: Better error handling for failed imports
4. **Health Monitoring**: Add custom health checks for node availability
5. **Dynamic Updates**: Support hot-reloading of workflows and nodes