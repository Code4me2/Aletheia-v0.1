# Aletheia CLI Tools

This directory contains the CLI tool discovery system for the Aletheia project.

## Architecture

We use a **hybrid approach** for CLI tools:

1. **Service-local CLIs**: Each service maintains its own CLI tool in its directory
2. **Discovery tool**: The `dev` script helps find and run service CLIs

## Usage

### Discover Available CLIs
```bash
./cli/dev list
```

### Run a Service CLI
```bash
# Run Haystack CLI
./cli/dev run haystack --help

# Or run directly from service directory
cd n8n/haystack-service
./cli --help
```

### View Service Documentation
```bash
./cli/dev docs haystack
```

## Service CLI Locations

| Service | CLI Location | Documentation |
|---------|--------------|---------------|
| Haystack | `n8n/haystack-service/cli` | `n8n/haystack-service/CLI.md` |
| Court Processor | `court-processor/cli` | `court-processor/CLI.md` |
| Lawyer Chat | `services/lawyer-chat/cli` | `services/lawyer-chat/CLI.md` |
| AI Portal | `services/ai-portal/cli` | `services/ai-portal/CLI.md` |

## Creating a New Service CLI

1. Create an executable `cli` file in your service directory
2. Add documentation as `CLI.md` in the same directory
3. Register it in `cli/dev` by adding to `SERVICE_CLIS`

See `./cli/dev create` for a template.

## Philosophy

This hybrid approach provides:
- **Isolation**: Service tools stay with their code
- **Discoverability**: Central tool shows what's available
- **Flexibility**: Run CLIs directly or through discovery tool
- **Maintainability**: Service owners control their tools