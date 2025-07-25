#!/usr/bin/env python3
"""
Fix workflow JSON files by adding required fields.
This script adds the missing 'name' and 'active' fields to workflow JSON files.
"""

import json
import os
import sys
from pathlib import Path

def fix_workflow_json(filepath):
    """Add required fields to a workflow JSON file."""
    print(f"Processing: {filepath}")
    
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Check if required fields already exist
        if 'name' in data and 'active' in data:
            print(f"  ✓ Already has required fields")
            return True
        
        # Generate a name from the filename
        filename = Path(filepath).stem
        workflow_name = filename.replace('-', ' ').replace('_', ' ').title()
        
        # Add required fields if missing
        if 'name' not in data:
            data['name'] = workflow_name
            print(f"  + Added name: {workflow_name}")
        
        if 'active' not in data:
            data['active'] = False  # Default to inactive for safety
            print(f"  + Added active: False")
        
        # Ensure other common fields exist
        if 'settings' not in data:
            data['settings'] = {}
            print(f"  + Added empty settings")
        
        if 'tags' not in data:
            data['tags'] = []
            print(f"  + Added empty tags")
        
        # Write the fixed JSON back
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"  ✓ Fixed and saved")
        return True
        
    except json.JSONDecodeError as e:
        print(f"  ✗ Invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def main():
    """Fix all workflow JSON files in the current directory."""
    workflow_dir = Path.cwd()
    json_files = list(workflow_dir.glob("*.json"))
    
    if not json_files:
        print("No JSON files found in current directory")
        sys.exit(1)
    
    print(f"Found {len(json_files)} JSON files to process\n")
    
    success_count = 0
    for json_file in json_files:
        if fix_workflow_json(json_file):
            success_count += 1
        print()
    
    print(f"Summary: {success_count}/{len(json_files)} files processed successfully")
    
    # Verify the fixes
    print("\nVerifying fixes:")
    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
            print(f"  {json_file.name}: name='{data.get('name')}', active={data.get('active')}")
        except:
            print(f"  {json_file.name}: Failed to verify")

if __name__ == "__main__":
    main()