#!/bin/bash
# Script to standardize file naming conventions to kebab-case

echo "🔄 Standardizing file names to kebab-case..."

# Function to convert to kebab-case
to_kebab_case() {
    echo "$1" | sed 's/\([A-Z]\)/-\1/g' | sed 's/^-//' | tr '[:upper:]' '[:lower:]'
}

# Keep these files uppercase as they are standard
KEEP_UPPERCASE=(
    "README.md"
    "LICENSE"
    "CHANGELOG.md"
    "CONTRIBUTING.md"
    "CODE_OF_CONDUCT.md"
    "SECURITY.md"
    "AUTHORS"
    "NOTICE"
    "CLAUDE.md"
    "Makefile"
    "Dockerfile"
)

# Function to check if file should keep uppercase
should_keep_uppercase() {
    local filename=$(basename "$1")
    for keep in "${KEEP_UPPERCASE[@]}"; do
        if [[ "$filename" == "$keep" ]]; then
            return 0
        fi
    done
    return 1
}

# Find files that need renaming
files_to_rename=()
while IFS= read -r file; do
    if ! should_keep_uppercase "$file"; then
        files_to_rename+=("$file")
    fi
done < <(find . -type f -name "*[A-Z]*" \
    -not -path "*/node_modules/*" \
    -not -path "*/.git/*" \
    -not -path "*/dist/*" \
    -not -path "*/.next/*" \
    -not -path "*/coverage/*" \
    -not -path "*/build/*" \
    | grep -E "\.(md|yml|yaml|json|js|ts|tsx|jsx|sh)$")

# Rename files
renamed_count=0
for file in "${files_to_rename[@]}"; do
    dir=$(dirname "$file")
    basename=$(basename "$file")
    
    # Convert basename to kebab-case
    new_basename=$(to_kebab_case "$basename")
    
    if [[ "$basename" != "$new_basename" ]]; then
        new_file="$dir/$new_basename"
        echo "📝 Renaming: $file → $new_file"
        git mv "$file" "$new_file" 2>/dev/null || mv "$file" "$new_file"
        ((renamed_count++))
    fi
done

echo "✅ Renamed $renamed_count files to kebab-case"

# Update imports and references
echo "🔍 Updating imports and references..."

# Update TypeScript/JavaScript imports
find . -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" \) \
    -not -path "*/node_modules/*" \
    -not -path "*/.git/*" \
    -not -path "*/dist/*" \
    -not -path "*/.next/*" \
    -exec sed -i.bak 's/Router\.ts/router\.ts/g' {} \;

find . -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" \) \
    -not -path "*/node_modules/*" \
    -not -path "*/.git/*" \
    -not -path "*/dist/*" \
    -not -path "*/.next/*" \
    -exec sed -i.bak 's/EventBus\.ts/event-bus\.ts/g' {} \;

find . -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" \) \
    -not -path "*/node_modules/*" \
    -not -path "*/.git/*" \
    -not -path "*/dist/*" \
    -not -path "*/.next/*" \
    -exec sed -i.bak 's/ServiceRegistry\.ts/service-registry\.ts/g' {} \;

# Clean up backup files
find . -name "*.bak" -type f -delete

echo "✅ File naming standardization complete!"