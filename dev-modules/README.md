# Dev CLI Modules

This directory contains modular components of the ./dev CLI script.

## Structure

- `dev-lib.sh` - Common functions library (check_db_ready, check_service_running, etc.)
- `dev-n8n.sh` - All n8n-related commands and subcommands
- `dev-db.sh` - Database-related commands (schema, shell, backup)
- `dev-services.sh` - Service management (up, down, restart, status, logs)
- `dev-utils.sh` - Utility commands (cleanup, backup, rebuild, validate)
- `dev-help.sh` - Help and documentation commands

## Usage

The main `dev` script sources these modules and routes commands to the appropriate handlers.

## Benefits

1. **Maintainability** - Each module is focused on a specific domain
2. **Testability** - Individual modules can be tested independently
3. **Extensibility** - New features can be added to specific modules
4. **Collaboration** - Multiple developers can work on different modules
5. **Performance** - Only required modules need to be loaded (future optimization)