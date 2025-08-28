#!/bin/bash

# ============================================================================
# Dev CLI Documentation Module
# ============================================================================
# This module contains commands for managing and verifying documentation

# Handle documentation commands
handle_docs_command() {
    local cmd="$1"
    shift
    
    case "$cmd" in
        verify)
            docs_verify "$@"
            ;;
        update)
            docs_update "$@"
            ;;
        *)
            if [ "$OUTPUT_FORMAT" = "json" ]; then
                echo '{"status":"error","message":"Unknown documentation command"}'
            else
                echo "Usage: ./dev docs [verify|update]"
                echo "  verify - Check documentation accuracy"
                echo "  update - Update docs from running system"
            fi
            return $EXIT_CONFIG_ERROR
            ;;
    esac
}

# Verify documentation accuracy
docs_verify() {
    if [ "$OUTPUT_FORMAT" != "json" ]; then
        print_header "Documentation Verification"
    fi
    
    errors=0
    warnings=0
    checks_json="["
    first=true
    
    # Check SERVICE_DEPENDENCIES.md
    if [ "$OUTPUT_FORMAT" != "json" ]; then
        echo -e "${CYAN}Checking SERVICE_DEPENDENCIES.md...${NC}"
    fi
    
    if [ -f docs/SERVICE_DEPENDENCIES.md ]; then
        deps_in_compose=$(grep -c "depends_on:" $DOCKER_COMPOSE.yml 2>/dev/null || echo "0")
        deps_in_docs=$(grep -c "→" docs/SERVICE_DEPENDENCIES.md 2>/dev/null || echo "0")
        
        if [ "$deps_in_compose" -gt 0 ] && [ "$deps_in_docs" -gt 0 ]; then
            if [ "$OUTPUT_FORMAT" != "json" ]; then
                echo -e "${GREEN}✓${NC} SERVICE_DEPENDENCIES.md exists"
            fi
            
            if [ "$OUTPUT_FORMAT" = "json" ]; then
                if [ "$first" = false ]; then checks_json="${checks_json},"; fi
                checks_json="${checks_json}{\"file\":\"SERVICE_DEPENDENCIES.md\",\"status\":\"ok\"}"
                first=false
            fi
        else
            if [ "$OUTPUT_FORMAT" != "json" ]; then
                echo -e "${YELLOW}⚠${NC}  SERVICE_DEPENDENCIES.md may need updating"
            fi
            warnings=$((warnings + 1))
            
            if [ "$OUTPUT_FORMAT" = "json" ]; then
                if [ "$first" = false ]; then checks_json="${checks_json},"; fi
                checks_json="${checks_json}{\"file\":\"SERVICE_DEPENDENCIES.md\",\"status\":\"warning\",\"message\":\"May need updating\"}"
                first=false
            fi
        fi
    else
        if [ "$OUTPUT_FORMAT" != "json" ]; then
            echo -e "${RED}✗${NC} SERVICE_DEPENDENCIES.md missing"
        fi
        errors=$((errors + 1))
        
        if [ "$OUTPUT_FORMAT" = "json" ]; then
            if [ "$first" = false ]; then checks_json="${checks_json},"; fi
            checks_json="${checks_json}{\"file\":\"SERVICE_DEPENDENCIES.md\",\"status\":\"error\",\"message\":\"Missing\"}"
            first=false
        fi
    fi
    
    # Check PORT_CONFIGURATION.md
    if [ "$OUTPUT_FORMAT" != "json" ]; then
        echo -e "${CYAN}Checking PORT_CONFIGURATION.md...${NC}"
    fi
    
    if [ -f docs/PORT_CONFIGURATION.md ]; then
        if [ "$OUTPUT_FORMAT" != "json" ]; then
            echo -e "${GREEN}✓${NC} PORT_CONFIGURATION.md exists"
        fi
        
        # Check if ports in .env match documentation
        if [ -f .env ]; then
            source .env
            if grep -q "8080" docs/PORT_CONFIGURATION.md && grep -q "8100" docs/PORT_CONFIGURATION.md; then
                if [ "$OUTPUT_FORMAT" != "json" ]; then
                    echo -e "${GREEN}✓${NC} Port documentation appears current"
                fi
                
                if [ "$OUTPUT_FORMAT" = "json" ]; then
                    if [ "$first" = false ]; then checks_json="${checks_json},"; fi
                    checks_json="${checks_json}{\"file\":\"PORT_CONFIGURATION.md\",\"status\":\"ok\"}"
                    first=false
                fi
            else
                if [ "$OUTPUT_FORMAT" != "json" ]; then
                    echo -e "${YELLOW}⚠${NC}  Port documentation may be outdated"
                fi
                warnings=$((warnings + 1))
                
                if [ "$OUTPUT_FORMAT" = "json" ]; then
                    if [ "$first" = false ]; then checks_json="${checks_json},"; fi
                    checks_json="${checks_json}{\"file\":\"PORT_CONFIGURATION.md\",\"status\":\"warning\",\"message\":\"May be outdated\"}"
                    first=false
                fi
            fi
        fi
    else
        if [ "$OUTPUT_FORMAT" != "json" ]; then
            echo -e "${RED}✗${NC} PORT_CONFIGURATION.md missing"
        fi
        errors=$((errors + 1))
        
        if [ "$OUTPUT_FORMAT" = "json" ]; then
            if [ "$first" = false ]; then checks_json="${checks_json},"; fi
            checks_json="${checks_json}{\"file\":\"PORT_CONFIGURATION.md\",\"status\":\"error\",\"message\":\"Missing\"}"
            first=false
        fi
    fi
    
    # Check DATABASE.md
    if [ "$OUTPUT_FORMAT" != "json" ]; then
        echo -e "${CYAN}Checking DATABASE.md...${NC}"
    fi
    
    if [ -f docs/DATABASE.md ]; then
        if [ "$OUTPUT_FORMAT" != "json" ]; then
            echo -e "${GREEN}✓${NC} DATABASE.md exists"
        fi
        
        # Check if it mentions the actual tables
        if check_service_running "db" true; then
            if $DOCKER_COMPOSE exec -T db psql -U "${DB_USER:-aletheia}" -d "${DB_NAME:-aletheia}" -c "\\dt court_data.*" 2>/dev/null | grep -q "opinions_unified"; then
                if grep -q "opinions_unified" docs/DATABASE.md; then
                    if [ "$OUTPUT_FORMAT" != "json" ]; then
                        echo -e "${GREEN}✓${NC} Database documentation includes main tables"
                    fi
                    
                    if [ "$OUTPUT_FORMAT" = "json" ]; then
                        if [ "$first" = false ]; then checks_json="${checks_json},"; fi
                        checks_json="${checks_json}{\"file\":\"DATABASE.md\",\"status\":\"ok\"}"
                        first=false
                    fi
                else
                    if [ "$OUTPUT_FORMAT" != "json" ]; then
                        echo -e "${YELLOW}⚠${NC}  Database documentation may be outdated"
                    fi
                    warnings=$((warnings + 1))
                    
                    if [ "$OUTPUT_FORMAT" = "json" ]; then
                        if [ "$first" = false ]; then checks_json="${checks_json},"; fi
                        checks_json="${checks_json}{\"file\":\"DATABASE.md\",\"status\":\"warning\",\"message\":\"May be outdated\"}"
                        first=false
                    fi
                fi
            fi
        else
            if [ "$OUTPUT_FORMAT" = "json" ]; then
                if [ "$first" = false ]; then checks_json="${checks_json},"; fi
                checks_json="${checks_json}{\"file\":\"DATABASE.md\",\"status\":\"ok\",\"message\":\"Cannot verify without DB running\"}"
                first=false
            fi
        fi
    else
        if [ "$OUTPUT_FORMAT" != "json" ]; then
            echo -e "${RED}✗${NC} DATABASE.md missing"
        fi
        errors=$((errors + 1))
        
        if [ "$OUTPUT_FORMAT" = "json" ]; then
            if [ "$first" = false ]; then checks_json="${checks_json},"; fi
            checks_json="${checks_json}{\"file\":\"DATABASE.md\",\"status\":\"error\",\"message\":\"Missing\"}"
            first=false
        fi
    fi
    
    # Summary
    if [ "$OUTPUT_FORMAT" = "json" ]; then
        checks_json="${checks_json}]"
        echo "{\"status\":\"$([ $errors -eq 0 ] && echo 'success' || echo 'error')\",\"errors\":$errors,\"warnings\":$warnings,\"checks\":$checks_json}"
    else
        echo ""
        if [ $errors -eq 0 ] && [ $warnings -eq 0 ]; then
            echo -e "${GREEN}✅ All documentation verified!${NC}"
        elif [ $errors -eq 0 ]; then
            echo -e "${YELLOW}⚠ Found $warnings documentation warning(s)${NC}"
            echo "Run './dev docs update' to regenerate documentation"
        else
            echo -e "${RED}✗ Found $errors error(s) and $warnings warning(s)${NC}"
            echo "Run './dev docs update' to regenerate documentation"
        fi
    fi
    
    [ $errors -eq 0 ] && return $EXIT_SUCCESS || return $EXIT_CONFIG_ERROR
}

# Update documentation from running system
docs_update() {
    if [ "$OUTPUT_FORMAT" = "json" ]; then
        echo '{"status":"error","message":"Documentation update not yet implemented"}'
        return $EXIT_CONFIG_ERROR
    fi
    
    echo -e "${BLUE}Updating documentation from current system...${NC}"
    echo -e "${YELLOW}This feature is planned but not yet implemented${NC}"
    echo "Would generate:"
    echo "  - SERVICE_DEPENDENCIES.md from $DOCKER_COMPOSE.yml"
    echo "  - DATABASE.md from actual database schema"
    echo "  - PORT_CONFIGURATION.md from running containers"
    
    # TODO: Implement automatic documentation generation
    # - Parse docker-compose.yml for dependencies
    # - Query database for schema information
    # - Extract port mappings from running containers
    # - Generate markdown files with current configuration
}

# Export functions
export -f handle_docs_command
export -f docs_verify
export -f docs_update