# Scripts Directory

Most functionality has been consolidated into the main `/dev` CLI tool.

## Remaining Scripts

### Critical Infrastructure
- `init-databases.sh` - PostgreSQL initialization (used by Docker during container startup)

### Deployment & Operations  
- `deploy.sh` - Production/staging deployment with environment management
- `enable-n8n-execution-tracking.sh` - n8n webhook tracking patch
- `force-reimport-workflows.sh` - Force reimport of n8n workflows

## Using the Dev CLI

For most development tasks, use the `/dev` command instead:

```bash
# Common operations
./dev up        # Start services
./dev status    # Check status
./dev health    # Run health checks
./dev validate  # Validate setup
./dev backup    # Backup database
./dev help      # See all commands
```

## Archived Scripts

The following scripts have been archived to `.archive/scripts/` as their functionality is now in `/dev`:
- health-check.sh → `./dev health`
- validate-setup.sh → `./dev validate`
- generate-credentials.sh → `./dev setup`
- dev-helper.sh → merged into `/dev`
- setup-dev.sh → `./dev setup`
- port-config.sh → `./dev ports`