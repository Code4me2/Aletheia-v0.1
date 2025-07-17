# FLP Integration Worktree

## Branch Information
- **Branch Name**: `feature/flp-integration-clean`
- **Worktree Name**: `flp-integration`
- **Purpose**: Clean implementation of Free Law Project API integration

## Port Configuration
This worktree uses the following isolated ports to avoid conflicts:

- **N8N**: 8083 (mapped from internal 5678)
- **Website**: 3003 (mapped from internal 3000)
- **PostgreSQL**: 5435 (mapped from internal 5432)

## Container Names
All containers in this worktree are prefixed with `flp-integration-`:
- `flp-integration-n8n`
- `flp-integration-postgres`
- `flp-integration-website`
- `flp-integration-court-processor`

## Database
- **Database Name**: `aletheia_flp_integration`
- **Database User**: `aletheia`
- **Database Password**: `aletheia123`

## Getting Started

1. Ensure you're in the correct worktree:
   ```bash
   cd /Users/vel/Desktop/coding/Aletheia-worktrees/flp-integration
   ```

2. Set up your FLP API key in the `.env` file:
   ```bash
   # Edit .env and add your actual FLP_API_KEY
   ```

3. Start the services:
   ```bash
   docker-compose up -d
   ```

4. Access the services:
   - N8N: http://localhost:8083
   - Website: http://localhost:3003
   - PostgreSQL: localhost:5435

## Development Notes
This worktree focuses on integrating with the Free Law Project API for enhanced court data collection and processing. The isolated environment ensures clean development without affecting other features.