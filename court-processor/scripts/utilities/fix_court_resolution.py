#!/usr/bin/env python3
"""
Quick fix for court resolution to handle opinion documents properly
"""

# Find the line in _enhance_court_info_validated around line 547-548
# Change from:
#     download_url = metadata.get('download_url', '')
#     if 'supremecourt.ohio.gov' in download_url:
# To:
#     download_url = metadata.get('download_url') or ''
#     if download_url and 'supremecourt.ohio.gov' in download_url:

# Also add generic court_id extraction for opinions after line 560:
#     # 3. Check for generic court_id field (works for CourtListener data)
#     if not court_hint:
#         court_hint = metadata.get('court_id') or metadata.get('court')
#         if court_hint:
#             extraction_method = 'opinion_metadata'

import fileinput
import sys

def fix_court_resolution():
    """Apply fixes to the pipeline file"""
    
    fixes_applied = 0
    
    # Read the file and apply fixes
    with open('eleven_stage_pipeline_robust_complete.py', 'r') as f:
        lines = f.readlines()
    
    # Fix 1: Handle None download_url
    for i, line in enumerate(lines):
        if "download_url = metadata.get('download_url', '')" in line:
            lines[i] = "            download_url = metadata.get('download_url') or ''\n"
            fixes_applied += 1
            print(f"Fixed download_url handling at line {i+1}")
        
        elif "'supremecourt.ohio.gov' in download_url:" in line:
            lines[i] = "            if download_url and 'supremecourt.ohio.gov' in download_url:\n"
            fixes_applied += 1
            print(f"Fixed download_url check at line {i+1}")
    
    # Fix 2: Add generic court_id extraction for opinions
    for i, line in enumerate(lines):
        if "# 3. Note: In production, would check cluster API here" in line:
            # Insert new code before this comment
            insert_lines = [
                "            # 3. Check for generic court_id field (works for CourtListener data)\n",
                "            if not court_hint:\n",
                "                court_hint = metadata.get('court_id') or metadata.get('court')\n",
                "                if court_hint:\n",
                "                    extraction_method = 'opinion_metadata'\n",
                "            \n",
                "            # 4. Note: In production, would check cluster API here\n"
            ]
            lines[i] = "".join(insert_lines)
            # Remove the original line since we replaced it
            fixes_applied += 1
            print(f"Added generic court_id extraction at line {i+1}")
            break
    
    # Write the fixed file
    with open('eleven_stage_pipeline_robust_complete.py', 'w') as f:
        f.writelines(lines)
    
    print(f"\nTotal fixes applied: {fixes_applied}")

if __name__ == "__main__":
    fix_court_resolution()