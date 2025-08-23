# Documentation Consolidation Plan

## Current State Analysis

The project currently has **211 markdown files** which creates confusion for developers. Here's a proposed consolidation plan that preserves all information while making it more accessible.

## Documentation Categories

### 1. Essential Docs (Keep in Root)
These files should remain in the root directory for immediate visibility:

- `README.md` - Main project overview
- `DEVELOPER_ONBOARDING.md` - Quick start for new developers (newly created)
- `CONTRIBUTING.md` - Contribution guidelines
- `.env.example` - Environment template

### 2. Recently Active Docs (Keep but Organize)
These were modified in 2025 and contain current information:

- `CLAUDE.md` - Project-specific AI instructions
- `DEVICE_SPECIFIC_SETUP.md` - Hardware-specific configurations
- `COURT_PROCESSOR_INTEGRATION.md` - Active integration docs
- `DOCKER_SETUP_GUIDE.md` - Docker configuration guide

### 3. Redundant/Old Docs (Candidates for Archive)
These appear to be outdated or redundant:

#### Multiple README files across directories:
- 28 README.md files scattered throughout
- Many contain overlapping information
- Some reference deprecated features

#### Historical/Planning Docs:
- `HAYSTACK_MIGRATION_SUMMARY.md`
- `CI_CD_IMPLEMENTATION_SUMMARY.md`
- `DOCKER_CLEANUP_PLAN.md`
- `DOCKER_OPTIMIZATION_PLAN.md`
- Various "_COMPLETE_2024.md" files

#### Duplicate Configuration Guides:
- Multiple port configuration docs
- Several Docker setup variations
- Redundant integration guides

## Proposed Structure

```
Aletheia-v0.1/
├── README.md                        # Main overview
├── DEVELOPER_ONBOARDING.md          # Quick start guide
├── CONTRIBUTING.md                  # How to contribute
├── TROUBLESHOOTING.md              # Common issues & solutions
├── .env.example                     # Environment template
│
├── docs/                           
│   ├── setup/                      # Setup & configuration
│   │   ├── docker.md               # Docker setup
│   │   ├── environment.md          # Environment variables
│   │   └── ports.md                # Port configuration
│   │
│   ├── services/                   # Service documentation
│   │   ├── nginx.md                # Nginx configuration
│   │   ├── lawyer-chat.md          # Lawyer chat service
│   │   ├── court-processor.md      # Court processor
│   │   └── n8n.md                  # n8n workflows
│   │
│   ├── development/                # Development guides
│   │   ├── local-setup.md          # Local development
│   │   ├── testing.md              # Testing procedures
│   │   └── debugging.md            # Debugging tips
│   │
│   └── archive/                    # Historical docs
│       └── [old planning docs]
│
└── services/
    ├── lawyer-chat/README.md       # Service-specific docs
    ├── ai-portal/README.md
    └── [etc...]
```

## Consolidation Actions (Safe Approach)

### Phase 1: Create New Structure (Non-Destructive)
1. Create `docs/` directory structure
2. Create consolidated documents by combining information
3. Add clear navigation in main README

### Phase 2: Deprecation Notices
1. Add deprecation notices to old docs pointing to new locations
2. Update all internal references
3. Test all documentation links

### Phase 3: Archive (After Validation)
1. Move deprecated docs to `docs/archive/`
2. Maintain git history for all moves
3. Create redirect map for external references

## Documentation Standards Going Forward

### For New Documentation:
1. **No duplicate information** - Link to existing docs instead
2. **Clear ownership** - Each doc should have a "Last Updated" and "Owner" field
3. **Searchable titles** - Use descriptive, grep-friendly names
4. **Single source of truth** - One topic, one location

### For Existing Documentation:
1. **Regular reviews** - Quarterly documentation audits
2. **Deprecation process** - Clear warnings before removal
3. **Version tracking** - Document which version of Aletheia the docs apply to

## Quick Wins (Immediate, Non-Breaking)

1. **Create TROUBLESHOOTING.md** - Consolidate all "Common Issues" sections
2. **Update main README.md** - Add clear navigation to all important docs
3. **Add Documentation Index** - Create searchable index of all docs
4. **Validation Script** - Already created as `scripts/validate-setup.sh`

## Notes for Implementation

- **DO NOT** delete any files without team consensus
- **DO NOT** move files that are referenced in scripts or code
- **DO** preserve git history when moving files (use `git mv`)
- **DO** test all links after any reorganization
- **DO** communicate changes clearly in commit messages

## Metrics for Success

- New developer can get running in < 30 minutes
- All common issues have documented solutions
- No duplicate information across docs
- Clear path from problem → solution in documentation

---

*This is a proposal - no files have been moved or deleted. Review and adjust before implementation.*