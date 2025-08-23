#!/bin/bash
# Simple script to copy a directory to n8n for processing

if [ $# -eq 0 ]; then
    echo "Usage: ./upload-docs.sh /path/to/your/documents [batch-name]"
    echo "Example: ./upload-docs.sh ~/Documents/legal-case case-2024"
    exit 1
fi

SOURCE_DIR="$1"
BATCH_NAME="${2:-$(basename "$SOURCE_DIR")}"
TARGET_DIR="n8n/local-files/uploads/$BATCH_NAME"

# Check if source exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "Error: Directory '$SOURCE_DIR' not found"
    exit 1
fi

# Create target directory (may need sudo due to Docker ownership)
if ! mkdir -p "$TARGET_DIR" 2>/dev/null; then
    echo "Need sudo access to create directory (Docker-owned folder)"
    sudo mkdir -p "$TARGET_DIR"
    sudo chmod 777 "$TARGET_DIR"
fi

# Copy only .txt files
echo "Copying .txt files to $TARGET_DIR..."
if ! find "$SOURCE_DIR" -name "*.txt" -type f -exec cp {} "$TARGET_DIR/" \; 2>/dev/null; then
    echo "Using sudo to copy files..."
    find "$SOURCE_DIR" -name "*.txt" -type f -exec sudo cp {} "$TARGET_DIR/" \;
fi

COUNT=$(find "$TARGET_DIR" -name "*.txt" -type f | wc -l)
echo "✓ Copied $COUNT .txt files"
echo "✓ Ready for processing with batch name: $BATCH_NAME"
echo ""
echo "Now go to the web interface and enter: $BATCH_NAME"