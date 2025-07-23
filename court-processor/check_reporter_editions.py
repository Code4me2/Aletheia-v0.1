#!/usr/bin/env python3
"""
Check how Federal Reporter editions are stored
"""

from reporters_db import REPORTERS
import json

print("Checking Federal Reporter Structure")
print("=" * 60)

# Check the 'F.' reporter
if 'F.' in REPORTERS:
    f_data = REPORTERS['F.']
    print("\n'F.' Reporter Data:")
    print(f"Type: {type(f_data)}")
    
    if isinstance(f_data, list) and f_data:
        for i, item in enumerate(f_data):
            print(f"\nItem {i}:")
            if isinstance(item, dict):
                # Check editions
                if 'editions' in item:
                    editions = item['editions']
                    print(f"Editions found: {list(editions.keys())}")
                    
                    # Check if F.2d and F.3d are editions
                    for edition_key in ['F.2d', 'F.3d', 'F. 2d', 'F. 3d']:
                        if edition_key in editions:
                            print(f"\n✅ Found '{edition_key}' as an edition")
                            edition_data = editions[edition_key]
                            print(f"   Edition data: {json.dumps(edition_data, indent=2)[:200]}...")
                
                # Check variations
                if 'variations' in item:
                    variations = item['variations']
                    print(f"\nVariations type: {type(variations)}")
                    if isinstance(variations, dict):
                        # Check if F.2d, F.3d are in variations
                        for var_key, var_value in variations.items():
                            if isinstance(var_value, list):
                                if 'F.2d' in var_value or 'F.3d' in var_value:
                                    print(f"Found F.2d/F.3d in variations for '{var_key}': {var_value}")

print("\n\nCreating correct normalization logic:")

def normalize_federal_reporter(reporter: str) -> tuple[bool, str, str]:
    """
    Normalize federal reporter citations
    Returns: (found, base_reporter, edition)
    """
    
    # Check if it's a federal reporter variant
    if reporter.startswith('F.') or reporter.startswith('f.'):
        # It's a Federal Reporter - base key is 'F.'
        parts = reporter.split('.')
        if len(parts) >= 2:
            edition_marker = parts[1].strip()
            if edition_marker in ['2d', '3d', 'Supp']:
                edition = f"F.{edition_marker}"
                return True, 'F.', edition
            elif edition_marker.startswith('Supp'):
                # Handle 'F. Supp. 2d' etc
                full_reporter = reporter.replace(' ', '')
                if 'Supp.2d' in full_reporter or 'Supp2d' in full_reporter:
                    return True, 'F. Supp.', 'F. Supp. 2d'
                else:
                    return True, 'F. Supp.', 'F. Supp.'
    
    # Direct lookup for other reporters
    if reporter in REPORTERS:
        return True, reporter, reporter
    
    return False, reporter, reporter

# Test the logic
print("\nTesting Federal Reporter normalization:")
test_reporters = ['F.', 'F.2d', 'F.3d', 'f.3d', 'F. Supp.', 'F. Supp. 2d', 'Fed. Cir.']

for reporter in test_reporters:
    found, base, edition = normalize_federal_reporter(reporter)
    if found:
        print(f"✅ '{reporter}' -> base: '{base}', edition: '{edition}'")
    else:
        print(f"❌ '{reporter}' -> Not a federal reporter")

# Now let's create the complete solution
print("\n\nComplete Reporter Normalization Solution:")

def get_reporter_info(reporter: str) -> dict:
    """Get complete reporter information including editions"""
    
    # Normalize spaces and case
    reporter_clean = reporter.strip()
    
    # Handle Federal Reporter series
    if reporter_clean.lower().startswith('f.'):
        base_key = 'F.'
        if base_key in REPORTERS:
            reporter_data = REPORTERS[base_key]
            if isinstance(reporter_data, list) and reporter_data:
                base_info = reporter_data[0]
                
                # Determine edition
                if '3d' in reporter_clean or '3d' in reporter_clean:
                    edition = 'F.3d'
                elif '2d' in reporter_clean or '2d' in reporter_clean:
                    edition = 'F.2d'
                else:
                    edition = 'F.'
                
                return {
                    'found': True,
                    'base_reporter': base_key,
                    'edition': edition,
                    'name': base_info.get('name', ''),
                    'cite_type': base_info.get('cite_type', 'federal')
                }
    
    # Handle Federal Supplement
    if 'supp' in reporter_clean.lower():
        if '2d' in reporter_clean.lower():
            base_key = 'F. Supp.'
            edition = 'F. Supp. 2d'
        elif '3d' in reporter_clean.lower():
            base_key = 'F. Supp.'
            edition = 'F. Supp. 3d'
        else:
            base_key = 'F. Supp.'
            edition = 'F. Supp.'
        
        if base_key in REPORTERS:
            return {
                'found': True,
                'base_reporter': base_key,
                'edition': edition,
                'name': 'Federal Supplement',
                'cite_type': 'federal'
            }
    
    # Direct lookup for other reporters
    if reporter_clean in REPORTERS:
        reporter_data = REPORTERS[reporter_clean]
        if isinstance(reporter_data, list) and reporter_data:
            base_info = reporter_data[0]
            return {
                'found': True,
                'base_reporter': reporter_clean,
                'edition': reporter_clean,
                'name': base_info.get('name', ''),
                'cite_type': base_info.get('cite_type', '')
            }
    
    # Case-insensitive lookup
    for key in REPORTERS.keys():
        if reporter_clean.lower() == key.lower():
            reporter_data = REPORTERS[key]
            if isinstance(reporter_data, list) and reporter_data:
                base_info = reporter_data[0]
                return {
                    'found': True,
                    'base_reporter': key,
                    'edition': key,
                    'name': base_info.get('name', ''),
                    'cite_type': base_info.get('cite_type', '')
                }
    
    return {
        'found': False,
        'base_reporter': reporter_clean,
        'edition': reporter_clean,
        'name': '',
        'cite_type': ''
    }

# Final test
print("\nFinal test with complete solution:")
final_test = ['F.3d', 'F.2d', 'U.S.', 'S. Ct.', 'F. Supp. 2d', 'Fed. Cir.', 'Cal. App.']

for reporter in final_test:
    info = get_reporter_info(reporter)
    if info['found']:
        print(f"✅ '{reporter}' -> {info['edition']} ({info['name']})")
    else:
        print(f"❌ '{reporter}' -> Not found")