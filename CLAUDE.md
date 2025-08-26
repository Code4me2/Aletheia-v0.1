# AI Assistant Instructions for Aletheia

This file contains specific instructions for AI assistants (Claude, GPT, etc.) working with the Aletheia codebase.

## Project Context

Aletheia is an AI-powered legal document processing platform. The main documentation is in [README.md](README.md).

## Automatic Setup Features

When running `./dev up`:
- **Database Initialization**: Automatically creates Prisma schema for lawyer-chat if needed
- **User Seeding**: Automatically seeds demo users if database is empty
  - Demo User: demo@reichmanjorgensen.com / demo123
  - Admin User: admin@reichmanjorgensen.com / admin123
- **Court Data Restore**: Automatically restores 485 court documents if database is empty

To manually seed/reset users: `./dev seed-users`

## Important Guidelines

### 1. Use the dev CLI
- **ALWAYS** use `./dev` for all operations (not `make`, `npm`, or `docker-compose` directly)
- Run `./dev help` to see available commands
- The dev CLI handles environment variables and proper service orchestration

### 2. Code Modifications
- **PREFER** editing existing files over creating new ones
- **NEVER** create documentation files unless explicitly requested
- **ALWAYS** check current branch and Docker status before making assumptions
- When modifying services, verify port configurations in `.env`

### 3. Documentation References
- **README.md** is the single source of truth for project documentation
- Check `docs/` folder for detailed architecture and guides
- Service-specific documentation is in each service's directory

### 4. Key Technical Details

#### Ports (from environment variables)
- Main Web: `${WEB_PORT:-8080}`
- n8n: `${N8N_PORT:-8100}`
- AI Portal: `${AI_PORTAL_PORT:-8102}`
- Court Processor: `${COURT_PROCESSOR_PORT:-8104}`
- PostgreSQL: `${POSTGRES_PORT:-8200}`
- Redis: `${REDIS_PORT:-8201}`

#### Critical IDs
- n8n Webhook ID: `c188c31c-1c45-4118-9ece-5b6057ab5177`
- Compose Project: `aletheia_development`

#### Database
- Default connection: `postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT}/${DB_NAME}`
- In Docker: host is `db`, port is `5432`
- From host: host is `localhost`, port is `${POSTGRES_PORT:-8200}`

### 5. Common Tasks

#### Check service status
```bash
./dev status
./dev health
./dev validate
```

#### View logs
```bash
./dev logs [service-name]
```

#### Database operations
```bash
./dev db schema    # View schema
./dev db shell     # PostgreSQL shell
./dev db backup    # Create backup
```

#### Documentation verification
```bash
./dev docs verify  # Check documentation accuracy
./dev docs update  # Update SERVICE_DEPENDENCIES.md
```

### 6. Testing Changes
- Always run `./dev validate` after making changes
- Check health with `./dev health`
- Review logs if services fail: `./dev logs [service]`

### 7. Git Workflow
- Check branch: `git branch --show-current`
- Commit incrementally with clear messages
- Never commit `.env` files or secrets

## Recent Context (August 2025)

### Completed Work
- Simplified codebase from 2.3GB to 1.5GB
- Consolidated documentation to README.md as single source of truth
- Removed hardcoded credentials from dev CLI
- Fixed port configurations to use environment variables
- Added comprehensive validation and documentation commands

### Known State
- Custom n8n nodes work from `dist/` folders (node_modules not needed)
- Lawyer Chat has Document Context feature working
- Court Processor API auto-starts on container launch
- All health checks are properly configured

## Best Practices

1. **Bandwidth Efficiency**: Prioritize lower bandwidth solutions
2. **Incremental Changes**: Make small, testable changes
3. **Verify First**: Always check current state before modifying
4. **Document Sparingly**: Only update docs when functionality changes
5. **Test Thoroughly**: Use `./dev validate` after changes

## DO NOT

- Create new README files in subdirectories
- Add comments to code unless requested
- Use hardcoded ports or credentials
- Create example or template files without explicit request
- Assume documentation is accurate without checking