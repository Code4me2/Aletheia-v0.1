#!/usr/bin/env python3
"""
Debug and fix reporter normalization issue
"""

from reporters_db import REPORTERS

print("Investigating Reporter Normalization Issue")
print("=" * 60)

# Test reporters that failed
test_reporters = ['F.3d', 'f.3d', 'Fed. Cir.']

print("\n1. Checking REPORTERS data structure:")
print(f"   Type: {type(REPORTERS)}")
print(f"   Length: {len(REPORTERS)}")

# Check what's actually in REPORTERS
print("\n2. Sample of REPORTERS keys:")
count = 0
for key in sorted(REPORTERS.keys()):
    if count < 10:
        print(f"   '{key}': {type(REPORTERS[key])}")
        count += 1

# Look for our test reporters
print("\n3. Searching for test reporters:")
for reporter in test_reporters:
    print(f"\n   Looking for '{reporter}':")
    
    # Direct lookup
    if reporter in REPORTERS:
        print(f"   ✅ Found directly")
        continue
    
    # Case variations
    found = False
    for key in REPORTERS.keys():
        if reporter.lower() == key.lower():
            print(f"   ✅ Found as '{key}' (case mismatch)")
            found = True
            break
        elif reporter.replace('.', '') == key.replace('.', ''):
            print(f"   ✅ Found as '{key}' (punctuation difference)")
            found = True
            break
    
    if not found:
        # Check if it's in variations
        for key, value_list in REPORTERS.items():
            if isinstance(value_list, list) and value_list:
                for item in value_list:
                    if isinstance(item, dict):
                        variations = item.get('variations', {})
                        if isinstance(variations, dict):
                            # Check edition variations
                            for edition, edition_vars in variations.items():
                                if isinstance(edition_vars, list) and reporter in edition_vars:
                                    print(f"   ✅ Found in variations of '{key}' edition '{edition}'")
                                    found = True
                                    break
                        elif isinstance(variations, list):
                            if reporter in variations:
                                print(f"   ✅ Found in variations of '{key}'")
                                found = True
                                break
                    if found:
                        break
                if found:
                    break
    
    if not found:
        print(f"   ❌ Not found")
        # Let's see what similar keys exist
        similar = [k for k in REPORTERS.keys() if reporter.lower()[:2] == k.lower()[:2]]
        if similar:
            print(f"   Similar keys: {similar[:5]}")

# Check specific reporters we expect
print("\n4. Looking for Federal Reporter 3d Series:")
federal_keys = [k for k in REPORTERS.keys() if 'F.' in k or 'Fed' in k]
print(f"   Federal reporter keys: {federal_keys[:10]}")

print("\n5. Checking data structure of a known reporter:")
if 'U.S.' in REPORTERS:
    us_data = REPORTERS['U.S.']
    print(f"   'U.S.' data type: {type(us_data)}")
    if isinstance(us_data, list) and us_data:
        print(f"   First item type: {type(us_data[0])}")
        if isinstance(us_data[0], dict):
            print(f"   Keys: {list(us_data[0].keys())[:10]}")
            if 'variations' in us_data[0]:
                print(f"   Variations type: {type(us_data[0]['variations'])}")

print("\n6. Creating improved normalization function:")

def normalize_reporter_improved(reporter: str) -> tuple[bool, str]:
    """Improved reporter normalization"""
    
    # Direct lookup
    if reporter in REPORTERS:
        return True, reporter
    
    # Case-insensitive lookup
    for key in REPORTERS.keys():
        if reporter.lower() == key.lower():
            return True, key
    
    # Remove spaces and periods for comparison
    reporter_normalized = reporter.replace('.', '').replace(' ', '').lower()
    
    for key in REPORTERS.keys():
        key_normalized = key.replace('.', '').replace(' ', '').lower()
        if reporter_normalized == key_normalized:
            return True, key
    
    # Check variations
    for key, value_list in REPORTERS.items():
        if isinstance(value_list, list):
            for item in value_list:
                if isinstance(item, dict):
                    variations = item.get('variations', {})
                    if isinstance(variations, dict):
                        for edition, edition_vars in variations.items():
                            if isinstance(edition_vars, list):
                                for var in edition_vars:
                                    if reporter.lower() == var.lower():
                                        return True, key
                                    if reporter.replace('.', '').replace(' ', '').lower() == var.replace('.', '').replace(' ', '').lower():
                                        return True, key
    
    return False, reporter

# Test improved function
print("\n7. Testing improved normalization:")
test_cases = ['F.3d', 'f.3d', 'U.S.', 'S. Ct.', 'Fed. Cir.', 'F.2d', 'F. Supp.', 'F. Supp. 2d']

for reporter in test_cases:
    found, normalized = normalize_reporter_improved(reporter)
    if found:
        print(f"   ✅ '{reporter}' -> '{normalized}'")
    else:
        print(f"   ❌ '{reporter}' -> Not found")