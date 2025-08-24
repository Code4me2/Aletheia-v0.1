# Backups Directory

This directory contains backup files and templates for the Aletheia project.

## Important Security Notice

**NEVER commit files containing real credentials, passwords, or API keys.**

## Files

- `.env.template` - Template for environment configuration (safe to commit)
- Database backups - SQL dumps for restoration

## Usage

1. Copy `.env.template` to create your `.env` file:
   ```bash
   cp backups/.env.template .env
   ```

2. Fill in your actual credentials in the `.env` file

3. Never commit the `.env` file with real values

## Best Practices

- Use strong, unique passwords
- Rotate credentials regularly
- Use secret management tools in production
- Keep backups encrypted and secure