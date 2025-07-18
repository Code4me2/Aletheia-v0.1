#!/bin/bash

# Generate a secure password without problematic characters for URLs
# Uses only alphanumeric and underscore characters
generate_safe_password() {
    local length=${1:-32}
    # Use only alphanumeric characters and underscores
    LC_ALL=C tr -dc 'A-Za-z0-9_' < /dev/urandom | head -c "$length"
}

NEW_PASSWORD=$(generate_safe_password 32)
echo "Generated new safe password: $NEW_PASSWORD"
echo ""
echo "To update your .env file, run:"
echo "sed -i.backup 's/DB_PASSWORD=.*/DB_PASSWORD=$NEW_PASSWORD/' .env"