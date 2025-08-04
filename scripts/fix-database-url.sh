#!/bin/bash

# Load environment variables
source .env

# URL encode the password
url_encode() {
    local string="${1}"
    local strlen=${#string}
    local encoded=""
    local pos c o

    for (( pos=0 ; pos<strlen ; pos++ )); do
        c=${string:$pos:1}
        case "$c" in
            [-_.~a-zA-Z0-9] ) o="${c}" ;;
            * ) printf -v o '%%%02x' "'$c"
        esac
        encoded+="${o}"
    done
    echo "${encoded}"
}

# Encode the password
ENCODED_PASSWORD=$(url_encode "$DB_PASSWORD")

echo "Original password: $DB_PASSWORD"
echo "Encoded password: $ENCODED_PASSWORD"
echo ""
echo "Add this to your .env file:"
echo "DATABASE_URL_ENCODED=postgresql://${DB_USER}:${ENCODED_PASSWORD}@db:5432/lawyerchat"