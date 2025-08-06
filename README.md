# Aletheia-v0.1

A sophisticated web application that integrates workflow automation (n8n) with AI capabilities for processing and analyzing large-scale textual data, with a focus on judicial and legal document processing. Includes automated court opinion scraping and judge-based document organization.

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.8+ (for data import scripts)
- 8GB+ RAM recommended (Elasticsearch uses 2GB, PostgreSQL 2GB, other services 4GB)
- Modern web browser
- Ports available: See [Port Mapping Guide](docs/PORT_MAPPING_GUIDE.md) for flexible configuration
- (Optional) Ollama with DeepSeek model for AI features (not available for windows yet)

### 1. Clone the repository

```bash
git clone https://github.com/Code4me2/Aletheia-v0.1.git
cd Aletheia-v0.1
```

### 2. Configure environment variables

```bash
# Generate environment-specific configuration
./scripts/deploy.sh -e development up

# Or manually:
cp .env.example .env
# Note: Default values in .env work for local development
# Add API keys for optional features:
# - COURTLISTENER_API_TOKEN for court data import
# - NEXTAUTH_SECRET for production deployments
```

### 3. Start all services

```bash
# Using new deployment script (recommended)
./scripts/deploy.sh up

# Or traditional method:
docker-compose up -d

# With monitoring stack:
./scripts/deploy.sh -m up

# For production deployment:
./scripts/deploy.sh -e production -m -l -s up
```

### 4. Verify services are healthy

```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
# All services should show "(healthy)" status
```

### 5. Access the application

- **Web Interface**: http://localhost:8080
- **Lawyer-Chat**: http://localhost:8080/chat
- **n8n Workflows**: http://localhost:8080/n8n/

### 6. Import the basic workflow

1. Access n8n at http://localhost:8080/n8n/
2. Create your account if first time
3. Click menu (⋮) → Import from file
4. Select `workflow_json/web_UI_basic`
5. Activate the workflow

### 7. Test the AI Chat

Navigate to the "AI Chat" tab in the web interface and start chatting!

## Notes for WSL:

**\*WSL and docker can be finnicky when working together, here are some methods to check and fix common issues:**

1. before trying to start docker desktop, execute the following commands in sequence:

```powershell
wsl --shutdown
```

```powershell
wsl -d ubuntu
```

2. From your newly opened ubuntu (or other distribution) instance, execute this:

```bash
docker version
```

```bash
docker ps
```

If both of those processes return results that indicate docker is connected to your WSL instance, cd to your Aletheia-v0.1 clone and execute:

```bash
docker compose up -d
```

and follow the rest of the quickstart guide to test things out.
If bash don't recognize docker commands, go into the docker desktop dashboard --> settings --> resources --> advanced --> WSL integration, and select your WSL integration (if using ubuntu, it will show up ther as an option) then restart docker.

## Common Issues

When starting up with this project, there are a few common issues, especially given the early development phase.

1. **Inactive workflow**

- When using the developer (or production) interface, if the n8n workflow is not activated the workflow will not run. This means the webhook won't pick up any of the signals sent to it from the UI.

2. **Unresponsive webhook**

- When the webhook is not responsive, the easiest method to check is to use `curl` through the CLI:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"test": "data", "timestamp": "2025-06-09"}' \
  -v \
  http://localhost:8080/webhook/c188c31c-1c45-4118-9ece-5b6057ab5177
```

if the webhook test is listening, it should return a response from the default chat setup out of workflow_json 3. **No session ID**

- With the AI agent node in workflow_json/web_UI_basic, having the simple memory in place without a session ID halts the workflow, and can be temporarily fixed when testing with curl by removing the simple memory node, or by simply filling in any sequence of numbers as a fixed key value.

## Overview

Data Compose combines multiple technologies to create a powerful document processing platform:

- **n8n** workflow automation engine with custom AI nodes
- **DeepSeek R1 1.5B** AI model integration via Ollama
- **Court Opinion Scraper** for automated judicial document collection
- **Elasticsearch** and **Haystack-inspired** API for advanced document search and analysis
- Modern **Single Page Application** frontend
- **Lawyer Chat** - Enterprise-grade legal AI assistant application
- **Docker-based** microservices architecture with flexible deployment

## Data Integration Documentation

### 📚 Documentation Links

- **[CourtListener Integration](./court-processor/courtlistener_integration/README.md)** - Complete guide for CourtListener API integration
- **[Haystack/RAG System](./n8n/haystack-service/README.md)** - Document search and analysis with Elasticsearch
- **[Data Pipeline Overview](./docs/data-pipeline.md)** - Visual guide to data flow from sources to RAG

## Key Features

### 🤖 AI-Powered Chat Interface

- Real-time chat with DeepSeek R1 1.5B model
- Webhook-based communication
- Thinking process visibility
- Context-aware responses

### ⚖️ Court Opinion Processing

- Automated daily scraping of federal court opinions
- Judge-centric database organization
- PDF text extraction with OCR fallback
- Support for multiple courts (Tax Court, 9th Circuit, 1st Circuit, Federal Claims)
- Automatic judge name extraction from opinion text
- Full-text search across all opinions

### 📄 Document Processing (Haystack RAG Integration)

- **RAG-Only Implementation**: Streamlined for pure retrieval-augmented generation
- **Hybrid Search**: BM25 + 384-dimensional vector embeddings (BAAI/bge-small-en-v1.5)
- **FastAPI Service**: Running `haystack_service_rag.py` (RAG-only version)
- **5 Core Endpoints**: Health, Ingest, Search, Import, Get Document
- **Dual Mode Support**: Standalone or unified with PostgreSQL integration
- **Direct Elasticsearch**: Uses Elasticsearch client without full Haystack library

### 🔄 Workflow Automation

- Visual workflow creation with n8n
- Custom nodes for AI and document processing
- Pre-configured workflows included
- Webhook integration with action-based routing
- Unified webhook endpoint handling multiple request types
- YAKE keyword extraction for automatic key phrase identification

### 💼 Lawyer Chat Application

- Enterprise-grade legal AI assistant with Next.js 15.3
- Type-safe architecture with full TypeScript support
- Flexible deployment with configurable base paths (`/chat` subpath)
- Secure authentication with NextAuth and CSRF protection
- Real-time streaming responses with n8n webhook integration
- Document citation panel with PostgreSQL session storage
- Comprehensive test suite (unit, integration, E2E with Playwright)

### 🎨 Modern Web Interface

- Single Page Application (SPA)
- Responsive design
- Tab-based navigation
- Real-time updates

## Architecture

### System Overview

Aletheia-v0.1 is a microservices-based platform that combines workflow automation, AI capabilities, and legal document processing. The architecture is designed for scalability, modularity, and ease of deployment.

### Core Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                   User Access Layer                              │
├─────────────────┬─────────────────┬─────────────────┬──────────────────────────┤
│  Data Compose   │   Lawyer Chat   │   AI Portal     │   Direct n8n Access      │
│  localhost:8080 │ localhost:8080  │ localhost:8085  │  localhost:8080/n8n/     │
│     (Main)      │     /chat       │  (Landing Page) │   (Workflow Editor)      │
└────────┬────────┴────────┬────────┴────────┬────────┴──────────┬───────────────┘
         │                 │                 │                   │
         ▼                 ▼                 ▼                   ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              NGINX Reverse Proxy                                 │
│                               (Port 8080)                                        │
│  Routes: /           → website (static files)                                   │
│          /chat       → lawyer-chat:3000                                         │
│          /n8n/       → n8n:5678                                                 │
│          /webhook/   → n8n:5678                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
        ▼                             ▼                             ▼
┌───────────────┐           ┌─────────────────┐          ┌──────────────────┐
│ Static Website│           │   Lawyer Chat   │          │  n8n Workflows   │
│   (SPA)       │           │   (Next.js)     │          │  (Port 5678)     │
│ - Home        │           │ - AI Chat UI    │          │ - Automation     │
│ - AI Chat     │           │ - History       │          │ - Custom Nodes   │
│ - RAG Testing │           │ - Citations     │          │ - Webhooks       │
│ - Dashboard   │           │ - Auth          │          │ - Integrations   │
└───────────────┘           └────────┬────────┘          └────────┬─────────┘
                                     │                             │
                                     │      ┌──────────────────────┘
                                     ▼      ▼
                            ┌─────────────────────┐
                            │   PostgreSQL DB    │
                            │   (Port 5432)      │
                            ├───────────────────┤
                            │ Schemas:           │
                            │ - public (default) │
                            │ - court_data       │
                            │ Tables include:    │
                            │ - n8n workflow     │
                            │ - lawyer chat      │
                            │ - hierarchical sum │
                            └─────────────────────┘
```

### Service Communication Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           AI Processing Pipeline                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

    User Input                   n8n Workflows              AI Services
        │                            │                          │
        ▼                            ▼                          ▼
┌───────────────┐          ┌─────────────────┐       ┌──────────────────┐
│  Web UI       │ webhook  │  n8n Engine     │       │  DeepSeek Node   │
│  - Chat       ├─────────▶│  - Router       ├──────▶│  (Ollama)        │
│  - Forms      │          │  - Logic        │       └──────────────────┘
└───────────────┘          │  - Transform    │       ┌──────────────────┐
                           │                 ├──────▶│  BitNet Node     │
                           └─────────────────┘       │  (Local LLM)     │
                                     │               └──────────────────┘
                                     │               ┌──────────────────┐
                                     └──────────────▶│  Haystack Node   │
                                                     │  (RAG Search)    │
                                                     └──────────────────┘
```

### Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          Document Processing Pipeline                            │
└─────────────────────────────────────────────────────────────────────────────────┘

    Court Websites              Processing               Storage & Search
         │                          │                          │
         ▼                          ▼                          ▼
┌──────────────────┐      ┌──────────────────┐      ┌────────────────────┐
│ Court Processor  │      │ PDF Processor    │      │ PostgreSQL         │
│ - Scraping       ├─────▶│ - Text Extract   ├─────▶│ - court_data       │
│ - Scheduling     │      │ - OCR            │      │ - Metadata         │
└──────────────────┘      └──────────────────┘      └─────────┬──────────┘
                                                               │
                          ┌──────────────────┐                 │
                          │ Hierarchical Sum │◀────────────────┘
                          │ - Chunking       │
                          │ - Summarization  │
                          └────────┬─────────┘
                                   │
                          ┌────────▼─────────┐       ┌────────────────────┐
                          │ Haystack Service │      │ Elasticsearch      │
                          │ - Embeddings     ├─────▶│ - Vector Search    │
                          │ - API            │      │ - Full Text        │
                          └──────────────────┘      └────────────────────┘
```

### Network Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            Docker Networks                                       │
├──────────────────────────────────┬──────────────────────────────────────────────┤
│         Frontend Network         │           Backend Network                     │
│         (User-facing)            │           (Internal Services)                │
├──────────────────────────────────┼──────────────────────────────────────────────┤
│  • web (nginx proxy + static)    │  • db (postgresql database)                  │
│  • lawyer-chat                   │  • n8n (connected to both networks)         │
│  • ai-portal                     │  • court-processor                          │
│  • ai-portal-nginx               │  • elasticsearch (optional)                 │
│                                  │  • haystack-service (optional)             │
└──────────────────────────────────┴──────────────────────────────────────────────┘
```

### Security Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           Security Layers                                        │
└─────────────────────────────────────────────────────────────────────────────────┘

    External Access              Gateway               Internal Services
         │                          │                        │
         ▼                          ▼                        ▼
┌──────────────────┐      ┌──────────────────┐    ┌────────────────────┐
│  HTTPS/SSL       │      │  NGINX           │    │ Service Isolation  │
│  (Production)    ├─────▶│  - Rate Limiting ├───▶│ - Docker Networks  │
│                  │      │  - Headers       │    │ - Non-root Users   │
└──────────────────┘      │  - CORS          │    └────────────────────┘
                          └──────────────────┘    ┌────────────────────┐
┌──────────────────┐              │               │ Authentication     │
│  NextAuth        │              │               │ - JWT Tokens       │
│  - Sessions      ├──────────────┘               │ - API Keys         │
│  - CSRF          │                              │ - Webhook Secrets  │
└──────────────────┘                              └────────────────────┘
```

### Deployment Options

#### 1. **Single Host Deployment** (Default)

```yaml
# Standard deployment on a single server
docker-compose up -d
```

#### 2. **Multi-Host Deployment** (Swarm)

```yaml
# Distributed deployment across multiple servers
docker stack deploy -c docker-compose.swarm.yml aletheia
```

#### 3. **Development Deployment**

```yaml
# Local development with hot-reload
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Port Mapping

**New Flexible Port System**: The project now uses an advanced port mapping system that automatically manages ports across different environments. See the [Port Mapping Guide](docs/PORT_MAPPING_GUIDE.md) for complete details.

#### Quick Overview

```bash
# View current environment's port mappings
./scripts/deploy.sh ports

# Deploy with specific environment
./scripts/deploy.sh -e staging up
./scripts/deploy.sh -e production -m -l -s up
```

#### Default Development Ports

| Service         | Port  | Access URL                          |
|-----------------|-------|-------------------------------------|
| Web Interface   | 8080  | http://localhost:8080               |
| n8n             | 8100  | http://localhost:8080/n8n/          |
| Lawyer Chat     | 8101  | http://localhost:8080/chat/         |
| AI Portal       | 8102  | http://localhost:8080/portal/       |
| API Gateway     | 8081  | http://localhost:8081               |
| PostgreSQL      | 8200  | postgresql://localhost:8200         |
| Redis           | 8201  | redis://localhost:8201              |
| Elasticsearch   | 8202  | http://localhost:8202               |
| Prometheus      | 8300  | http://localhost:8300               |
| Grafana         | 8301  | http://localhost:8301               |

### Additional Services (When Enabled)

The monitoring stack and additional services are automatically configured with environment-appropriate ports:

```bash
# Enable monitoring stack
./scripts/deploy.sh -m up

# Enable load balancer
./scripts/deploy.sh -l up

# Full production deployment
./scripts/deploy.sh -e production -m -l -s up
```

Services include:
- **Prometheus**: Metrics collection
- **Grafana**: Visualization dashboards
- **Loki**: Log aggregation
- **HAProxy**: Load balancing
- **Consul**: Service discovery

### Key Architectural Decisions

1. **Microservices Architecture**
   - Each component runs in its own container
   - Services communicate via Docker networks
   - Easy to scale individual components

2. **Reverse Proxy Pattern**
   - NGINX handles all external requests
   - Provides unified access point
   - Enables path-based routing

3. **Webhook-Based Communication**
   - Loose coupling between UI and backend
   - n8n acts as central message router
   - Enables complex workflow automation

4. **Database Segregation**
   - Separate schemas for different services
   - Shared PostgreSQL instance
   - Clear data boundaries

5. **Optional Components**
   - Haystack/Elasticsearch can be disabled
   - AI services are pluggable
   - Modular architecture for flexibility

## Project Structure

```
Aletheia-v0.1/
├── docker-compose.yml         # Main Docker configuration
├── docker-compose.swarm.yml   # Docker Swarm configuration (scaling)
├── .env.example              # Environment template
├── nginx/
│   └── conf.d/
│       └── default.conf      # NGINX reverse proxy config
├── website/                  # Frontend Single Page Application
│   ├── index.html           # Main entry point
│   ├── css/
│   │   └── app.css         # Unified design system
│   ├── js/
│   │   ├── app.js          # Application framework
│   │   └── config.js       # Webhook configuration
│   └── favicon.ico
├── workflow_json/           # n8n workflow exports
│   └── web_UI_basic        # Basic AI chat workflow
├── court-processor/        # Court opinion scraper
│   ├── processor.py       # Main scraping logic
│   ├── pdf_processor.py   # PDF text extraction
│   └── config/courts.yaml # Court configurations
├── court-data/            # Scraped court data
│   ├── pdfs/             # Downloaded PDF files
│   └── logs/             # Processing logs
├── lawyer-chat/           # Enterprise legal AI assistant
│   ├── src/
│   │   ├── app/          # Next.js App Router
│   │   ├── components/   # React components
│   │   ├── lib/          # Type-safe utilities
│   │   ├── types/        # TypeScript definitions
│   │   └── hooks/        # Custom React hooks
│   ├── prisma/           # Database schema
│   └── scripts/          # Utility scripts
└── n8n/                    # n8n extensions and configuration
    ├── custom-nodes/       # Custom node implementations
    │   ├── n8n-nodes-deepseek/     # DeepSeek AI integration
    │   ├── n8n-nodes-haystack/     # Document search integration (7 implemented endpoints)
    │   ├── n8n-nodes-hierarchicalSummarization/  # PostgreSQL document processing
    │   ├── n8n-nodes-bitnet/       # BitNet LLM inference
    │   ├── n8n-nodes-yake/         # YAKE keyword extraction
    │   ├── test-utils/             # Shared testing utilities for all nodes
    │   └── run-all-node-tests.js   # Master test runner
    ├── docker-compose.haystack.yml # Haystack services config
    ├── haystack-service/          # Haystack API implementation
    │   ├── haystack_service.py    # Full service with hierarchy support
    │   └── haystack_service_rag.py # RAG-only service (currently active)
    └── local-files/              # Persistent storage
```

## Configuration

### Path Configuration (New!)

The application now supports flexible deployment at any base path through environment variables:

#### Setting the Base Path

1. **Docker Compose** (Recommended):

   ```yaml
   services:
     legal-chat:
       environment:
         - BASE_PATH=/legal-chat # Deploy at /legal-chat
   ```

2. **Development**:

   ```bash
   BASE_PATH=/legal-chat npm run dev
   ```

3. **Production Build**:
   ```bash
   BASE_PATH=/legal-chat npm run build
   BASE_PATH=/legal-chat npm start
   ```

#### Type-Safe Path System

The lawyer-chat application includes a robust type-safe path configuration system:

- **Automatic path prefixing** - All paths automatically include the BASE_PATH
- **Type-safe API calls** - Full TypeScript support for all endpoints
- **Runtime validation** - All API responses are validated
- **Zero hardcoded paths** - Complete flexibility for deployment

Example usage in code:

```typescript
import { buildApiUrl, apiClient } from '@/lib/paths';

// All paths are automatically prefixed
const response = await apiClient.get<Chat[]>('/api/chats');
```

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# Project Configuration
COMPOSE_PROJECT_NAME=aletheia

# Database
DB_USER=your_db_user
DB_PASSWORD=your_secure_password
DB_NAME=your_db_name

# n8n
N8N_ENCRYPTION_KEY=your_encryption_key

# Service Ports (to avoid conflicts)
WEB_PORT=8080
N8N_PORT=5678
AI_PORTAL_PORT=8085
ELASTICSEARCH_PORT=9200
HAYSTACK_PORT=8000
```

**Note**: The "placeholder-looking" values (e.g., `your_db_user`, `your_secure_password_here`) are the actual working credentials for local development. For production deployment, generate strong credentials using the provided scripts.

### Database Schema

Aletheia uses PostgreSQL with multiple schemas for different components. The main schema is `court_data` which stores court opinions and judicial data.

For detailed database schema documentation including tables, views, functions, and usage examples, see [docs/DATABASE.md](docs/DATABASE.md).

**Quick Overview:**

- **judges** - Judge information and court affiliations
- **opinions** - Court opinions with full text and metadata
- **processing_log** - Tracking and statistics for data processing
- **judge_stats** (view) - Aggregated statistics per judge

## Development

### Creating Custom n8n Nodes

The DeepSeek node serves as an excellent template for creating new custom nodes. Here's how to create your own:

#### 1. **Node Structure Setup**

Create a new folder in `n8n/custom-nodes/` following this structure:

```
n8n-nodes-yournode/
├── nodes/
│   └── YourNode/
│       └── YourNode.node.ts    # Main node implementation
├── credentials/                 # Optional: for authenticated services
│   └── YourNodeApi.credentials.ts
├── package.json                # Node dependencies and metadata
├── tsconfig.json              # TypeScript configuration
├── gulpfile.js                # Build configuration
└── index.ts                   # Module entry point
```

#### 2. **Node Implementation Template**

Based on the DeepSeek implementation, here's a template for `YourNode.node.ts`:

```typescript
import {
  IExecuteFunctions,
  INodeExecutionData,
  INodeType,
  INodeTypeDescription,
  NodeOperationError,
} from 'n8n-workflow';

export class YourNode implements INodeType {
  description: INodeTypeDescription = {
    displayName: 'Your Node Name',
    name: 'yourNode',
    icon: 'file:youricon.svg', // Add icon to nodes/YourNode/
    group: ['transform'],
    version: 1,
    description: 'Description of what your node does',
    defaults: {
      name: 'Your Node',
    },
    inputs: ['main'],
    outputs: ['main'],
    properties: [
      // Node properties (fields shown in UI)
      {
        displayName: 'Operation',
        name: 'operation',
        type: 'options',
        options: [
          {
            name: 'Process',
            value: 'process',
            description: 'Process data',
          },
        ],
        default: 'process',
        noDataExpression: true,
      },
      // Add more properties as needed
    ],
  };

  async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
    const items = this.getInputData();
    const returnData: INodeExecutionData[] = [];

    for (let i = 0; i < items.length; i++) {
      try {
        // Get parameters from UI
        const operation = this.getNodeParameter('operation', i) as string;

        // Process your data here
        const result = await this.processData(items[i].json, operation);

        returnData.push({
          json: result,
          pairedItem: { item: i },
        });
      } catch (error) {
        if (this.continueOnFail()) {
          returnData.push({
            json: { error: error.message },
            pairedItem: { item: i },
          });
          continue;
        }
        throw new NodeOperationError(this.getNode(), error, { itemIndex: i });
      }
    }

    return [returnData];
  }

  // Helper methods
  private async processData(input: any, operation: string): Promise<any> {
    // Your processing logic here
    return { processed: input, operation };
  }
}
```

#### 3. **Package Configuration**

Create `package.json`:

```json
{
  "name": "n8n-nodes-yournode",
  "version": "0.1.0",
  "description": "Your node description",
  "keywords": ["n8n-community-node-package"],
  "license": "MIT",
  "homepage": "",
  "author": {
    "name": "Your Name",
    "email": "your@email.com"
  },
  "repository": {
    "type": "git",
    "url": "git+https://github.com/yourusername/n8n-nodes-yournode.git"
  },
  "main": "index.js",
  "scripts": {
    "build": "tsc && gulp build:icons",
    "dev": "tsc --watch",
    "format": "prettier nodes credentials --write",
    "lint": "eslint nodes credentials package.json",
    "lintfix": "eslint nodes credentials package.json --fix"
  },
  "files": ["dist"],
  "n8n": {
    "n8nNodesApiVersion": 1,
    "nodes": ["dist/nodes/YourNode/YourNode.node.js"]
  },
  "devDependencies": {
    "@types/node": "^16.11.26",
    "@typescript-eslint/parser": "^5.29.0",
    "eslint": "^8.17.0",
    "eslint-plugin-n8n-nodes-base": "^1.11.0",
    "gulp": "^4.0.2",
    "n8n-workflow": "^1.0.0",
    "prettier": "^2.7.1",
    "typescript": "^4.9.5"
  }
}
```

#### 4. **Building and Testing**

```bash
# Navigate to your node directory
cd n8n/custom-nodes/n8n-nodes-yournode

# Install dependencies
npm install

# Build the node
npm run build

# For development (watch mode)
npm run dev

# Link to n8n for testing
npm link
cd ~/.n8n/custom
npm link n8n-nodes-yournode

# Restart n8n to load your node
docker-compose restart n8n
```

#### 5. **Testing Your Node**

The project includes a comprehensive testing framework with shared utilities for all custom nodes:

```bash
# Test a specific node
cd n8n/custom-nodes/n8n-nodes-yournode
npm test

# Test all nodes
cd n8n/custom-nodes
node run-all-node-tests.js

# Test specific operations
npm run test:unit        # Unit tests only
npm run test:integration # Integration tests
npm run test:quick       # Quick structure validation
```

**Test Structure**:

```
n8n-nodes-yournode/
└── test/
    ├── run-tests.js      # Node test runner
    ├── unit/             # Unit tests
    │   ├── test-node-structure.js
    │   └── test-config.js
    └── integration/      # Integration tests
        └── test-api.js
```

**Using Shared Test Utilities**:

- `test-utils/common/test-runner.js` - Unified test execution
- `test-utils/common/node-validator.js` - Node structure validation
- `test-utils/common/env-loader.js` - Environment configuration
- `test-utils/common/api-tester.js` - API endpoint testing

See `n8n/custom-nodes/TEST_CONSOLIDATION.md` for detailed testing documentation.

#### 6. **Best Practices from DeepSeek Node**

1. **Error Handling**: Always wrap API calls in try-catch blocks
2. **Logging**: Use console.log for debugging during development
3. **Input Validation**: Validate user inputs before processing
4. **Response Parsing**: Handle different response formats gracefully
5. **Type Safety**: Use TypeScript interfaces for data structures
6. **UI Properties**: Provide sensible defaults and clear descriptions
7. **Advanced Options**: Hide complex settings under "Additional Fields"
8. **Testing**: Write comprehensive tests using the shared utilities

### AI Agent Integration Patterns

The project demonstrates advanced patterns for integrating custom AI nodes with n8n's AI Agent system, as shown in the BitNet and Hierarchical Summarization implementations.

#### Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│  Chat Trigger   │────▶│    AI Agent     │────▶│    Response      │
│  (User Input)   │     │ (Conversational) │     │   (To User)      │
└─────────────────┘     └────────┬────────┘     └──────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    │                         │
          ┌─────────▼──────────┐    ┌────────▼────────┐
          │  BitNet Chat Model  │    │     Memory      │
          │ (Language Model)    │    │  (Chat Context) │
          └────────────────────┘    └─────────────────┘
```

#### Creating AI Agent Compatible Nodes

To create custom nodes that work with n8n's AI Agent system:

1. **Implement the Supply Data Interface**:

   ```typescript
   async supplyData(this: ISupplyDataFunctions): Promise<any> {
     return {
       invoke: async (params: { messages, options }) => {
         // Process messages and return response
         return { text: response, content: response };
       }
     };
   }
   ```

2. **Configure Output Type**:

   ```typescript
   outputs: [NodeConnectionType.AiLanguageModel],
   outputNames: ['Model']
   ```

3. **Dual Mode Support**:
   - **Standalone Mode**: Traditional execute() method for direct use
   - **Sub-node Mode**: supplyData() method for AI Agent integration

#### Integration Examples

**1. Chat with BitNet Model**:

```
[Chat Trigger] → [Conversational Agent] → [Response]
                         ↓
                   [BitNet Chat Model]
```

**2. Document Processing Pipeline**:

```
[Document] → [Hierarchical Summarization] → [Summary]
                        ↓
                  [BitNet Chat Model]
```

**3. Advanced Workflow with Tools**:

```
[Chat Trigger] → [Tools Agent] → [Response]
                      ↓
                [BitNet Model]
                      ↓
                [Web Search Tool]
                      ↓
                [Calculator Tool]
```

#### Key Considerations

1. **Message Format**: AI Agents use standardized message format with roles (system, user, assistant)
2. **Options Handling**: Support temperature, max tokens, and other generation parameters
3. **Error Propagation**: Gracefully handle and report errors to the AI Agent
4. **Performance**: Efficient processing for real-time chat applications
5. **Context Management**: Work with memory nodes for conversation continuity

### Frontend Development

The frontend uses a modular architecture for easy extension:

```javascript
// Add new sections to the SPA
window.app.addSection('newsection', 'New Feature', 'icon-class', '<h2>Content</h2>', {
  onShow: () => initialize(),
});
```

### UI Features & Hidden Functionality

#### App Menu Cabinet

The application includes a slide-out menu system that provides quick access to additional features:

- **Access**: Click the menu icon or use `window.app.toggleAppMenu()`
- **Keyboard Support**: Press `Escape` to close the menu
- **Auto-close**: Clicks outside the menu will automatically close it

#### History Management

The Hierarchical Summarization feature includes advanced history capabilities:

- **History Drawer**: Collapsible sidebar showing all previous summarizations
- **Quick Actions**:
  - Plus (+) button for new summarization without opening history
  - Right-click on history items to delete
  - Auto-switch to form view when active item is deleted
- **Context Menus**: Right-click functionality for additional options

#### Chat Interface Modes

The AI chat system supports multiple operational modes:

- **Local Mode**: Direct connection to local AI services (DeepSeek via Ollama)
- **Public Mode**: Connection to cloud-based AI services
- **Mode Switching**: Available through UI controls or programmatically

#### Keyboard Navigation

Comprehensive keyboard shortcuts throughout the application:

**Hierarchical Summarization Visualization**:

- `←` Navigate to parent (toward final summary)
- `→` Navigate to children (toward source documents)
- `↑` Previous sibling at same level
- `↓` Next sibling at same level
- `Home` Jump to final summary
- `End` Jump to first source document
- `Ctrl+/` Open search dialog

**General Navigation**:

- `Escape` Close modals, drawers, and menus
- `Tab` Navigate between sections
- `Enter` Activate selected items

#### Advanced Visualization Features

The document hierarchy visualization includes:

- **Minimap**: Interactive overview of entire document tree
- **Search Functionality**: Full-text search with highlighting
- **Quick Jump**: Dropdown navigation with node previews
- **URL Bookmarking**: Direct links to specific nodes via URL hash
- **Real-time Updates**: Visual indicators for processing status

#### Developer Console Features

Hidden debugging and development features accessible via browser console:

- `window.app.debug()` - Enable debug mode with verbose logging
- `window.app.sections` - View all registered sections
- `window.app.config` - Access runtime configuration
- `window.testConnection()` - Test webhook connectivity

#### CSS Theme Customization

The application uses CSS custom properties for easy theming:

```css
/* Override in browser dev tools or custom CSS */
:root {
  --primary-color: #2c3e50;
  --secondary-color: #3498db;
  --accent-color: #e74c3c;
  --background-color: #f8f9fa;
  --text-color: #333333;
}
```

## Configuration

### Environment Variables

```bash
# Database
DB_USER=your_username
DB_PASSWORD=your_secure_password
DB_NAME=your_database_name

# n8n
N8N_ENCRYPTION_KEY=your_encryption_key
```

### Webhook Configuration

Update `website/js/config.js` with your webhook ID:

```javascript
const CONFIG = {
  WEBHOOK_ID: 'c188c31c-1c45-4118-9ece-5b6057ab5177',
  WEBHOOK_URL: `${window.location.protocol}//${window.location.host}/webhook/c188c31c-1c45-4118-9ece-5b6057ab5177`,
};
```

## Advanced Features

### Haystack Integration (Optional)

The Haystack integration provides document processing with hierarchical analysis and search capabilities. It's designed for legal document processing with a 4-level hierarchy system.

#### Key Features:

- **Hierarchical Document Processing**: 4-level document hierarchy with parent-child relationships
- **Advanced Search**: Hybrid search combining BM25 and 384-dimensional vector embeddings
- **Direct Elasticsearch Integration**: Uses Elasticsearch directly without full Haystack framework
- **Development Server**: FastAPI service with auto-reload (not production-ready)
- **7 Implemented API Endpoints**:
  - `POST /import_from_node` - Import documents from n8n workflow nodes
  - `POST /search` - Hybrid search with BM25 and vector embeddings
  - `POST /hierarchy` - Get document parent-child relationships
  - `GET /health` - Service health check
  - `GET /get_final_summary/{workflow_id}` - Retrieve workflow's final summary
  - `GET /get_complete_tree/{workflow_id}` - Get full document hierarchy tree
  - `GET /get_document_with_context/{document_id}` - Get document with navigation context

#### Starting Haystack Services:

```bash
# Start with Haystack services
docker-compose -f docker-compose.yml -f n8n/docker-compose.haystack.yml up -d

# Or use the convenience script (recommended)
cd n8n && ./start_haystack_services.sh
```

#### Using in n8n Workflows:

1. **Add Haystack Search node** to your workflow
2. **Configure operation** (one of 7 available operations)
3. **Connect to other nodes** for document processing pipelines

Example workflow pattern:

```
PostgreSQL Query → Haystack Import → Search/Navigate Documents
```

**Important Note**: The Haystack n8n node defines 8 operations, but the service only implements 7 endpoints. The "Batch Hierarchy" operation exists in the node UI but lacks a corresponding endpoint in the service and will fail if used.

#### API Endpoints:

- **Haystack API Docs**: http://localhost:8000/docs
- **Elasticsearch**: http://localhost:9200
- **Health Check**: http://localhost:8000/health

#### Example Usage:

```bash
# Ingest document with hierarchy
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '[{
    "content": "Legal document text",
    "metadata": {"source": "case.pdf"},
    "document_type": "source_document",
    "hierarchy_level": 0
  }]'

# Search with hybrid mode (BM25 + vectors)
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "legal precedent", "use_hybrid": true, "top_k": 10}'

# Get documents ready for processing
curl -X POST http://localhost:8000/get_by_stage \
  -H "Content-Type: application/json" \
  -d '{"stage_type": "ready_summarize", "hierarchy_level": 1}'
```

For detailed documentation, see `n8n/HAYSTACK_README.md`

### Court Opinion Processing

The court processor automatically scrapes federal court opinions and organizes them by judge:

#### Quick Start:

```bash
# Initialize court processor database
docker-compose exec db psql -U postgres -d postgres -f /court-processor/scripts/init_db.sql

# Manual scrape
docker-compose exec court-processor python processor.py --court tax

# Check results
docker-compose exec db psql -U your_db_user -d your_db_name -c "SELECT * FROM court_data.judge_stats;"
```

#### Supported Courts:

- **tax**: US Tax Court (✅ Fully implemented)
- **ca9**: Ninth Circuit Court of Appeals (⚠️ Configuration exists, implementation pending)
- **ca1**: First Circuit Court of Appeals (⚠️ Configuration exists, implementation pending)
- **uscfc**: US Court of Federal Claims (⚠️ Configuration exists, implementation pending)

**Note**: Currently, only the Tax Court scraper is fully implemented. Other courts have configuration entries but require additional development.

#### Features:

- Automatic judge name extraction from PDF text
- Daily scheduled scraping via cron
- Full-text search across all opinions
- Judge-based statistics and analytics

For detailed documentation, see `court-processor/README.md`

### YAKE Keyword Extraction

The YAKE (Yet Another Keyword Extractor) node provides automatic keyword and key phrase extraction from documents:

#### Features:

- **Language-agnostic**: Works with multiple languages
- **Unsupervised**: No training data required
- **Statistical approach**: Uses word co-occurrence and frequency
- **Configurable**: Adjust window size, deduplication threshold, and max keywords

#### Usage in n8n:

1. Add YAKE node to your workflow
2. Connect document input
3. Configure extraction parameters:
   - Language (auto-detect or specify)
   - Max keywords to extract
   - N-gram size (1-3 words)
   - Deduplication threshold
4. Output: Ranked list of keywords with confidence scores

#### Example Use Cases:

- Document tagging and categorization
- Search engine optimization
- Content summarization
- Legal document analysis for key terms

## Monitoring & Developer Tools

### Monitoring Infrastructure

Aletheia-v0.1 includes comprehensive monitoring capabilities for production deployments.

**Note**: The project includes two separate monitoring configurations:

1. **Production Monitoring** (`docker-compose.production.yml`): General application monitoring with Prometheus, Grafana, and Loki
2. **Haystack Monitoring** (`monitoring/docker-compose.monitoring.yml`): Specialized monitoring for Haystack/Elasticsearch services

⚠️ **Important**: These stacks share Prometheus port 9090. Run only one at a time or reconfigure ports to avoid conflicts.

#### Prometheus Metrics Export

The Haystack service includes a Prometheus exporter (`n8n/monitoring/haystack_exporter.py`) that provides:

- **Search Performance Metrics**: Latency tracking by search type (hybrid, vector, BM25)
- **Document Processing Metrics**: Ingestion rates and processing times
- **Elasticsearch Health**: Cluster status and node availability
- **Error Tracking**: Categorized error counts by operation type

#### Grafana Dashboards

Pre-configured dashboards for visualizing:

- RAG performance metrics
- Service health status
- Query response times
- Document processing throughput

#### Alert Rules

Prometheus alerting for:

- Service downtime
- High error rates
- Performance degradation
- Resource exhaustion

### Developer Tools

#### Workflow Analysis Scripts

Located in the root directory:

- **`analyze_workflow.py`**: Analyzes n8n workflow JSON for optimization opportunities
- **`connection_analyzer.py`**: Debugs service connectivity issues
- **`workflow_validator.py`**: Validates workflow configurations
- **`simplify_workflow.py`**: Simplifies complex workflow structures

#### Testing Infrastructure

- **Parallel Testing**: `docker-compose.parallel-test.yml` for concurrent test execution
- **Performance Benchmarking**: `benchmark_rag_performance.py` for RAG system testing
- **Integration Tests**: Comprehensive test suites for all services

#### Deployment Utilities

Located in `scripts/` directory:

- **`standardize-names.sh`**: Converts filenames to kebab-case across the project
- **`rollback.sh`**: Advanced deployment rollback with version management
- **`wait-for-health.sh`**: Dynamic health check polling for services
- **`health-check.sh`**: Comprehensive multi-service health verification

#### Database Management

- **`scripts/init-databases.sh`**: Database initialization and schema setup
- **Migration Scripts**: Automated database migration tools

### Hidden Utilities

#### Energy Monitoring (BitNet)

- **`scripts/monitor_energy.py`**: Tracks power consumption during AI inference
- Useful for optimizing deployment costs and environmental impact

#### Service Monitoring

- **`monitor_server.sh`**: Real-time monitoring of BitNet server
- Provides slot status, resource usage, and performance metrics

#### Test Runners

- **`n8n/custom-nodes/run-all-node-tests.js`**: Master test runner for all custom nodes
- **`run_tests.py`**: Python test orchestrator with coverage reporting

### Development Workflows

#### Local Development Setup

```bash
# Run development environment with hot-reload
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Run specific service tests
cd n8n/custom-nodes && node run-all-node-tests.js

# Analyze workflow performance
python analyze_workflow.py workflow_json/web_UI_basic

# Check service connections
python connection_analyzer.py
```

#### Performance Analysis

```bash
# Benchmark RAG performance
python benchmark_rag_performance.py

# Monitor resource usage
./monitor_server.sh

# Track energy consumption
python scripts/monitor_energy.py
```

#### Debugging Tools

```bash
# Debug service connectivity
python connection_analyzer.py --verbose

# Validate workflow structure
python workflow_validator.py workflow.json

# Check health of all services
./scripts/health-check.sh
```

## Troubleshooting

### Common Issues

1. **Services showing as unhealthy**:
   - Elasticsearch may crash after extended use (memory issues)
   - Haystack becomes unhealthy when Elasticsearch dies
   - Solution: Restart all services (see Clean Restart below)

2. **Browser hanging/not loading**:
   - Usually indicates services need restart
   - Clear browser cache and cookies for localhost
   - Try incognito/private browsing mode

3. **"Connection refused" errors**:
   - Services may need 30-60 seconds to fully start
   - Elasticsearch takes longest to initialize
   - Wait and retry, or check logs

4. **n8n workflow not responding**:
   - Ensure workflow is activated (toggle switch in n8n)
   - Check webhook URL matches in `website/js/config.js`
   - Verify with curl test (see below)

5. **Port conflicts**:
   - Ensure ports 8080, 5678, 9200, 8000 are free
   - Check with: `lsof -i :8080` (repeat for each port)
   - Kill conflicting processes or change ports in docker-compose.yml

6. **Network errors**:
   - If you see "Network aletheia_backend Resource is still in use"
   - Run: `docker network prune` (after stopping all containers)

### Clean Restart Procedure

```bash
# Stop everything properly
docker-compose down
cd n8n && docker-compose -f docker-compose.haystack.yml down && cd ..

# Remove any stuck networks (if needed)
docker network prune

# Start fresh
docker-compose up -d
cd n8n && ./start_haystack_services.sh

# Wait for services to be healthy (check every 10 seconds)
watch docker ps
```

### Service Health Checks

```bash
# Check all service statuses at once
docker ps --format "table {{.Names}}\t{{.Status}}"

# Individual health checks
curl http://localhost:8080/                    # Web interface
curl http://localhost:8080/n8n/healthz         # n8n
curl http://localhost:8000/health              # Haystack
curl http://localhost:9200/_cluster/health     # Elasticsearch

# Test webhook (replace with your webhook ID)
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"test": "data", "timestamp": "2025-01-11"}' \
  http://localhost:8080/webhook/c188c31c-1c45-4118-9ece-5b6057ab5177
```

### Useful Commands

```bash
# View logs for debugging
docker-compose logs -f [service_name]
docker-compose logs -f elasticsearch-judicial  # Common culprit

# Restart individual service
docker-compose restart [service_name]

# Check resource usage
docker stats

# Run tests for custom nodes
cd n8n/custom-nodes
node run-all-node-tests.js
```

### Memory Issues (Elasticsearch)

If Elasticsearch keeps crashing:

```yaml
# Edit n8n/docker-compose.haystack.yml
environment:
  - 'ES_JAVA_OPTS=-Xms1g -Xmx1g' # Reduce from 2g if needed
```

## Data Management

### Docker Volumes

The application uses Docker volumes for persistent data storage:

- **PostgreSQL Database** (`postgres_data`): All application data including court documents, hierarchical summaries, and chat conversations
- **n8n Data** (`n8n_data`): Workflows, credentials, execution history, and node configurations
- **Elasticsearch Data** (`elasticsearch_data`): Search indices and document embeddings
- **Haystack Models** (`haystack_models`): AI model files

### Backup Procedures

```bash
# Database backup
docker exec aletheia-db-1 pg_dumpall -U your_db_user > backup_$(date +%Y%m%d).sql

# n8n backup
docker exec aletheia-n8n-1 tar czf - -C /home/node/.n8n . > n8n_backup_$(date +%Y%m%d).tar.gz

# Export n8n workflows regularly through the UI
# Navigate to Workflows → Settings → Download
```

### Data Safety Rules

- **Never remove volumes without backup**: `docker volume rm` deletes all data permanently
- **Never use** `docker system prune -a --volumes` without careful consideration
- **Always check volume mounts** before removing containers
- **Use safe migration scripts** for network or configuration changes

## CourtListener Data Import (Optional)

### Prerequisites

```bash
# Install Python dependencies
pip install -r court-processor/courtlistener_integration/requirements.txt

# Add API key to .env
echo "COURTLISTENER_API_TOKEN=your_api_key_here" >> .env
```

### Quick Start Import

```bash
# 1. Initialize database schema
docker exec -i aletheia-db-1 psql -U $DB_USER -d $DB_NAME < court-processor/scripts/init_courtlistener_schema.sql

# 2. Download recent court data (example: Texas Eastern District, last 30 days)
python court-processor/courtlistener_integration/bulk_download.py \
  --court txed --days 30 --output-dir /tmp/courtlistener

# 3. Load to PostgreSQL
python court-processor/courtlistener_integration/load_to_postgres.py \
  --input-dir /tmp/courtlistener/txed

# 4. Index in Haystack for search
python court-processor/courtlistener_integration/ingest_to_haystack.py \
  --haystack-url http://localhost:8000 --limit 100
```

### Available Courts

- `ded` - District of Delaware
- `txed` - Eastern District of Texas
- `cand` - Northern District of California
- `cafc` - Court of Appeals for the Federal Circuit
- `cacd` - Central District of California
- `nysd` - Southern District of New York

For detailed instructions, see [CourtListener Integration Guide](./court-processor/courtlistener_integration/README.md)

## Production Deployment

### Security Considerations

1. **Generate Strong Credentials**:

   ```bash
   # Generate secure passwords
   DB_PASSWORD=$(openssl rand -base64 32)
   N8N_ENCRYPTION_KEY=$(openssl rand -hex 32)
   NEXTAUTH_SECRET=$(openssl rand -base64 32)
   ```

2. **Network Security**:
   - Use `COMPOSE_PROJECT_NAME=aletheia` for consistent network isolation
   - Backend network should be internal-only in production
   - Implement SSL/TLS for all external endpoints

3. **Container Security**:
   - All containers run with non-root users (except court-processor due to cron requirements)
   - Read-only filesystems where possible
   - Resource limits configured for all services

### Database Initialization

For new deployments, the database requires initialization:

```sql
-- Create service-specific databases
CREATE DATABASE lawyerchat;
GRANT ALL PRIVILEGES ON DATABASE lawyerchat TO your_db_user;

-- Create hierarchical summarization tables
CREATE TABLE IF NOT EXISTS hierarchical_summaries (
    id SERIAL PRIMARY KEY,
    workflow_id VARCHAR(255) NOT NULL,
    level INTEGER NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Deployment Environments

- **Staging**: Automated deployment on `develop` branch commits
- **Production**: Manual deployment via tagged releases
- **Environment Files**: `.env.staging` and `.env.production` (not in repository)

## CI/CD Pipeline

### Overview

Aletheia-v0.1 uses GitHub Actions for continuous integration and deployment, with comprehensive testing, security scanning, and automated deployments to staging and production environments.

### Continuous Integration

The CI pipeline (`.github/workflows/ci.yml`) runs on every push and pull request to `main` and `develop` branches:

1. **Linting & Formatting**: ESLint and Prettier checks
2. **JavaScript Tests**: Jest tests on Node.js 18 and 20
3. **Python Tests**: Pytest on Python 3.10 and 3.11
4. **Security Scanning**: Trivy vulnerability scanner and npm audit
5. **Docker Build Tests**: Validates all Docker images build correctly
6. **E2E Tests**: Playwright tests on Chromium and Firefox

### Deployment Pipeline

#### Staging Deployment

- **Trigger**: Push to `develop` branch
- **Workflow**: `.github/workflows/deploy-staging.yml`
- **Features**:
  - Automated tests before deployment
  - Docker image building and pushing to GitHub Container Registry
  - Health check verification
  - Slack notifications

#### Production Deployment

- **Trigger**: GitHub release or manual workflow dispatch
- **Workflow**: `.github/workflows/deploy-production.yml`
- **Features**:
  - Version format validation (v1.2.3)
  - Staging environment validation
  - Database backup before deployment
  - Blue-green deployment strategy
  - Automatic rollback on failure

### Key CI/CD Features

1. **Health Check Polling**: Dynamic service readiness checks replace hardcoded waits

   ```bash
   ./scripts/wait-for-health.sh <url> [timeout] [interval]
   ```

2. **Security Enhancements**:
   - All containers run as non-root users (except cron requirements)
   - Database credentials secured in container environment
   - Input validation for deployment parameters

3. **Rollback Capability**:

   ```bash
   ./scripts/rollback.sh [staging|production] [version]
   ```

4. **Environment Management**:
   - `.env.staging` - Staging configuration
   - `.env.production` - Production configuration (update placeholders)
   - Docker Compose overlays for each environment

### Deployment Scripts

- **`scripts/deploy.sh`**: Automated deployment with health checks
- **`scripts/rollback.sh`**: Version-specific rollback functionality
- **`scripts/wait-for-health.sh`**: Service health polling utility
- **`scripts/health-check.sh`**: Comprehensive health verification

### Setting Up CI/CD

1. **Configure GitHub Secrets**:

   ```
   STAGING_HOST, STAGING_USER, STAGING_SSH_KEY
   PRODUCTION_HOST, PRODUCTION_USER, PRODUCTION_SSH_KEY
   SLACK_WEBHOOK (optional)
   ```

2. **Update Environment Files**:
   - Replace all "CHANGE_THIS" placeholders in `.env.production`
   - Configure SMTP settings for notifications
   - Set monitoring endpoints

3. **Test Locally**:

   ```bash
   # Run tests
   npm test
   pytest

   # Test deployment script
   ./scripts/deploy.sh staging
   ```

### Monitoring & Observability

Production deployments include:

- Prometheus metrics collection
- Grafana dashboards
- Loki log aggregation
- Health check endpoints for all services

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests for your changes using the shared test utilities
4. Ensure all tests pass: `cd n8n/custom-nodes && node run-all-node-tests.js`
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [n8n](https://n8n.io/) - Workflow automation platform
- [DeepSeek](https://www.deepseek.com/) - AI model provider
- [Haystack](https://haystack.deepset.ai/) - Document processing framework
- [Ollama](https://ollama.ai/) - Local AI model hosting
