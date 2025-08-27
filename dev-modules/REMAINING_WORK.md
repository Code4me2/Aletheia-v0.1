# Remaining Work for Dev CLI Modularization

## Current Status
- **Phase 1**: ✅ Complete (Non-breaking improvements)
- **Phase 3**: 🚧 30% Complete (Modularization)

## Completed Modules
1. ✅ `dev-lib.sh` - Common functions library (200+ lines)
2. ✅ `dev-help.sh` - Help system (100+ lines)  
3. ✅ `dev-n8n.sh` - n8n module (942 lines, kept intact for branch merging)

## Remaining Modules to Extract

### 1. `dev-services.sh` (~400 lines)
**Commands to extract:**
- `up|start` - Start services
- `down|stop` - Stop services
- `restart` - Restart services
- `status|ps` - Show service status
- `logs` - Show service logs
- `shell|exec` - Open shell in container
- `services` - List available services

**Line ranges in original dev:**
- up/start: 311-458
- down/stop: 460-495
- restart: 497-510
- status: 512-599
- logs: (embedded in various places)
- shell: 601-624
- services: 2728-2735

### 2. `dev-db.sh` (~200 lines)
**Commands to extract:**
- `db schema` - Show database schema
- `db shell` - Open PostgreSQL shell
- `db backup` - Create database backup
- `db restore` - Restore from backup
- `db restore-court-data` - Restore court processor sample data

**Line ranges in original dev:**
- db commands: 1193-1329

### 3. `dev-utils.sh` (~600 lines)
**Commands to extract:**
- `setup` - Initial setup wizard
- `doctor` - System diagnostics
- `validate` - System validation
- `backup` - Backup database and configs
- `rebuild` - Rebuild services
- `clean` - Clean volumes (destructive)
- `cleanup` - Archive old files
- `reload-nginx` - Reload nginx config
- `seed-users` - Initialize demo users
- `verify-frontend` - Frontend verification

**Line ranges in original dev:**
- setup: 792-894
- doctor: 2463-2567
- validate: 568-695
- backup: 703-726
- rebuild: 2392-2461
- clean: 627-638
- cleanup: 640-695
- seed-users: 2257-2361

### 4. `dev-env.sh` (~100 lines)
**Commands to extract:**
- `env check` - Verify environment configuration
- `env list` - List all environment variables
- `ports` - Show port configuration

**Line ranges in original dev:**
- env commands: 2625-2652
- ports: 741-790

### 5. `dev-docs.sh` (~100 lines)
**Commands to extract:**
- `docs verify` - Check documentation accuracy
- `docs update` - Update docs from running system

**Line ranges in original dev:**
- docs commands: 896-1191

## Integration Tasks

### 1. Create New Main Script
```bash
#!/bin/bash
# Source all modules
source dev-modules/dev-lib.sh
source dev-modules/dev-help.sh
source dev-modules/dev-services.sh
source dev-modules/dev-db.sh
source dev-modules/dev-utils.sh
source dev-modules/dev-env.sh
source dev-modules/dev-docs.sh
source dev-modules/dev-n8n.sh

# Main command router
case "$1" in
    n8n) handle_n8n_command "${@:2}" ;;
    db) handle_db_command "${@:2}" ;;
    env) handle_env_command "${@:2}" ;;
    docs) handle_docs_command "${@:2}" ;;
    # ... etc
esac
```

### 2. Update Variable References
- Change `$2` to `$1` in extracted functions
- Change `$3` to `$2` in extracted functions
- Update `shift` commands appropriately

### 3. Testing Requirements
- [ ] Each module loads without errors
- [ ] All commands work as before
- [ ] No regression in functionality
- [ ] JSON output still works
- [ ] Exit codes are correct
- [ ] Help text is accurate

## Estimated Effort
- Module extraction: 2-3 hours
- Integration and testing: 1-2 hours
- Documentation: 30 minutes
- Total: ~4-5 hours

## Benefits After Completion
1. **Maintainability**: Each module focused on specific domain
2. **Testability**: Modules can be tested independently
3. **Collaboration**: Multiple developers can work on different modules
4. **n8n Branch Merge**: Easy to merge n8n changes with isolated module
5. **Extensibility**: New features can be added to specific modules

## Next Session Starting Point
1. Start with `dev-services.sh` extraction (most straightforward)
2. Test service commands work correctly
3. Continue with `dev-db.sh` and `dev-utils.sh`
4. Create main integration script
5. Comprehensive testing