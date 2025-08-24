# Aletheia Documentation Map

## Essential Documentation (Start Here)

1. **[README.md](../README.md)** - Quick start and project overview
2. **[DEVELOPER_GUIDE.md](../DEVELOPER_GUIDE.md)** - Developer commands and workflow
3. **[CLAUDE.md](../CLAUDE.md)** - AI assistant context and project details

## Architecture & Configuration

- **[docs/SERVICE_DEPENDENCIES.md](./SERVICE_DEPENDENCIES.md)** - Service architecture diagram
- **[docs/PORT_CONFIGURATION.md](./PORT_CONFIGURATION.md)** - Port mappings and strategy
- **[backups/.env.template](../backups/.env.template)** - Environment configuration template

## Component Documentation

### Services
- **[services/lawyer-chat/](../services/lawyer-chat/README.md)** - Legal chat application
- **[services/ai-portal/](../services/ai-portal/README.md)** - AI services portal
- **[court-processor/](../court-processor/README.md)** - Court document processing

### n8n & Custom Nodes
- **[n8n/](../n8n/README.md)** - n8n workflow automation setup
- **[n8n/custom-nodes/](../n8n/custom-nodes/)** - Custom node documentation
  - Each node has its own README in its directory

### Frontend
- **[website/](../website/README.md)** - Frontend application

### Testing
- **[tests/](../tests/README.md)** - Test suite organization

## Operations

- **[docs/CHANGELOG_AUGUST_2025.md](./CHANGELOG_AUGUST_2025.md)** - Recent fixes and changes
- **[docs/SIMPLIFICATION_REPORT.md](./SIMPLIFICATION_REPORT.md)** - Completed simplifications and impact
- **[scripts/](../scripts/README.md)** - Deployment and utility scripts
- **[backups/](../backups/README.md)** - Backup procedures

## Guides

- **[docs/guides/](./guides/)** - Step-by-step guides
  - [Website Guide](./guides/website.md)
  - [n8n Guide](./guides/n8n.md)
  - [Court Processor Guide](./guides/court-processor.md)

## Development Resources

- **[docs/development/](./development/)** - Development documentation
  - [Contributing](./development/contributing.md)
  - [Project Improvements](./development/project-improvements.md)

## Archive

Historical documentation has been moved to:
- **[docs/archive/](./archive/)** - Old documentation for reference

## Documentation Standards

### File Locations
- **Root directory**: Only essential files (README, DEVELOPER_GUIDE, CLAUDE)
- **docs/**: Architecture, guides, and detailed documentation
- **Component directories**: Component-specific README only
- **docs/archive/**: Historical/deprecated documentation

### When to Create Documentation
1. **README.md**: One per component, keep it concise
2. **Guides**: For complex workflows requiring step-by-step instructions
3. **Architecture docs**: For system design and technical decisions
4. **Archive**: Move outdated docs here instead of deleting

### Documentation Principles
- Keep it current - update docs with code changes
- Be concise - avoid redundancy
- Use examples - show, don't just tell
- Link don't duplicate - reference other docs instead of copying

## Quick Reference

### For New Developers
1. Start with [README.md](../README.md)
2. Read [DEVELOPER_GUIDE.md](../DEVELOPER_GUIDE.md)
3. Review [SERVICE_DEPENDENCIES.md](./SERVICE_DEPENDENCIES.md)

### For Contributing
1. Read [Contributing Guide](./development/contributing.md)
2. Check [Project Improvements](./development/project-improvements.md)
3. Follow standards in this document

### For Deployment
1. Check [scripts/README.md](../scripts/README.md)
2. Review [PORT_CONFIGURATION.md](./PORT_CONFIGURATION.md)
3. Use `./dev` commands

## Maintenance

This map should be updated when:
- New components are added
- Documentation is reorganized
- Files are archived or removed