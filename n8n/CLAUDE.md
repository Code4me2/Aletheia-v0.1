This project is a targeted addition to an existing architecture, being orchestrated via n8n. The Haystack+Elasticsearch integration is now fully implemented and operational.

## Current Status (Updated: July 24, 2025)

### Custom Nodes Implementation
- **6 Custom Nodes Built and Deployed**:
  - `n8n-nodes-haystack` - RAG and document search (8 operations, 7 functional)
  - `n8n-nodes-hierarchicalSummarization` - Document hierarchy processing
  - `n8n-nodes-citationchecker` - Legal citation verification
  - `n8n-nodes-deepseek` - DeepSeek R1 AI integration
  - `n8n-nodes-yake` - Keyword extraction
  - `n8n-nodes-bitnet` - BitNet AI processing

### Infrastructure
- **Custom Docker Image**: `Dockerfile.n8n` builds n8n with embedded custom nodes
- **Workflow Autoload**: `init-workflows.sh` automatically imports and activates workflows on startup
- **Database Persistence**: Separated database storage to `/data` volume
- **Fixed Node Types**: Workflows updated from `n8n-nodes-[name].[node]` to `[node]` format

### Services
- **Service**: Running `haystack_service_rag.py` (RAG-only version) with 7 implemented endpoints
- **Documentation**: Updated in `HAYSTACK_SETUP.md` and `haystack_readme.md`
- **Archived Files**: Old planning documents moved to `archived-docs/`
- **Known Issue**: The "Batch Hierarchy" operation in the n8n node has no corresponding endpoint in the service
- **Service Files**:
  - `haystack_service.py` - Full service with hierarchical summarization support
  - `haystack_service_rag.py` - Simplified RAG-only service (currently active)

The recommended steps for working with the integration are:

## Working with the Haystack Integration

Here are the key steps for using or modifying the Haystack integration:

---

### ✅ Step 1: **Finalize and Build Your Custom Node**

- Ensure your custom node is located in `custom-nodes/` inside your project root (`./custom-nodes/your-node-name`).
- Follow the `n8n-node-starter` structure: each node should have a `node.ts` and an optional `credentials.ts`, and be registered in `package.json`.
- Run:

  ```bash
  cd custom-nodes/your-node-name
  npm install
  npm run build
  ```

- This should generate a `dist/` directory with the compiled node code.

---

### ✅ Step 2: **Build and Deploy with Custom Docker Image**

- The project now uses a custom Docker image (`Dockerfile.n8n`) that:
  - Embeds all custom nodes directly in the image
  - Copies nodes to `/home/node/.n8n/custom/`
  - Fixes permission issues and removes pnpm requirements
  - Separates database storage to `/data` volume

- Build and deploy:
  ```bash
  docker-compose build n8n
  docker-compose up -d n8n
  ```

---

### ✅ Step 3: **Update Node Folder to Use Built Files Only**

- Inside `./custom-nodes`, make sure only the `dist` output is being used by n8n, or that the `dist` folder is at the root of each custom node folder.
- If needed, flatten the structure like this:

  ```
  custom-nodes/
    haystack-node/
      dist/
        YourHaystackNode.js
        ...
  ```

  n8n expects either:
  - `custom-nodes/dist/YourNode.js`, or
  - `custom-nodes/haystack-node/dist/YourNode.js`

  You may need to adjust your build or move files accordingly so they are directly accessible within the mount.

---

### ✅ Step 4: **Restart n8n Container to Load Node**

Run the following:

```bash
docker-compose restart n8n
```

- This will cause n8n to scan the `custom` folder and dynamically register any valid `.js` node files it finds.

---

### ✅ Step 5: **Verify Node in n8n Editor**

- Navigate to: [http://localhost:5678/](http://localhost:5678/) (direct n8n access)
- Or via proxy: [http://localhost:8080/n8n/](http://localhost:8080/n8n/)
- Workflows are automatically imported on startup
- Custom nodes should appear in the node palette

**Current Status**: 
- Standard node workflows activate automatically
- Custom node workflows may need manual save in UI to resolve node types

---

## Summary

The complete n8n integration includes:

### Custom Nodes (All Functional)
- **Haystack Search**: 8 operations for document management (7 functional, 1 without backend)
- **Hierarchical Summarization**: Document hierarchy processing
- **Citation Checker**: Legal citation verification
- **DeepSeek (DSR1)**: AI text generation via Ollama
- **YAKE**: Keyword extraction
- **BitNet**: AI processing with summary capabilities

### Infrastructure
- Custom Docker image with embedded nodes
- Automatic workflow import on startup
- Database persistence across restarts
- Fixed workflow node type references

### Documentation
- `N8N_WORKFLOW_AUTOLOAD_IMPLEMENTATION.md` - Complete technical documentation
- `HAYSTACK_SETUP.md` - Haystack service setup
- `haystack_readme.md` - Haystack integration guide

**Known Issues**: 
- The "Batch Hierarchy" operation in Haystack node has no service endpoint
- Custom nodes may show as `[node].undefined` until manually saved in UI
