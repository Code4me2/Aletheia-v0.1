#!/usr/bin/env python3
"""
Analyze current error handling patterns in the pipeline
"""

import re
import ast

def analyze_error_handling(filepath):
    """Analyze error handling patterns in a Python file"""
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Patterns to look for
    patterns = {
        'broad_exceptions': r'except Exception as \w+:',
        'bare_exceptions': r'except:',
        'specific_exceptions': r'except \w+Error as \w+:',
        'error_logging': r'logger\.error\(',
        'warning_logging': r'logger\.warning\(',
        'silent_failures': r'except.*:\s*pass',
        'return_empty': r'except.*:\s*return\s*\{\}',
        'return_none': r'except.*:\s*return\s*None',
        'try_blocks': r'\btry:',
    }
    
    results = {}
    for pattern_name, pattern in patterns.items():
        matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
        results[pattern_name] = len(matches)
    
    # Find error handling context
    try_except_blocks = re.findall(
        r'try:.*?except.*?:.*?(?=\n(?:def|class|try:|$))',
        content,
        re.DOTALL
    )
    
    print("=== ERROR HANDLING ANALYSIS ===\n")
    print(f"File: {filepath}\n")
    
    print("Pattern Counts:")
    for pattern, count in results.items():
        print(f"  {pattern}: {count}")
    
    print(f"\nTotal try-except blocks: {len(try_except_blocks)}")
    
    # Analyze what types of errors are caught
    error_types = re.findall(r'except (\w+(?:Error|Exception)) as', content)
    print(f"\nSpecific error types caught:")
    for error_type in set(error_types):
        print(f"  - {error_type}")
    
    # Find functions with no error handling
    functions = re.findall(r'def (\w+)\(.*?\):', content)
    print(f"\nTotal functions: {len(functions)}")
    
    # Check for validation patterns
    validation_patterns = {
        'isinstance_checks': r'isinstance\(',
        'type_checks': r'type\(\w+\)',
        'none_checks': r'if.*is None:',
        'empty_checks': r'if not \w+:',
        'key_exists': r'\.get\(',
    }
    
    print("\nValidation Patterns:")
    for pattern_name, pattern in validation_patterns.items():
        count = len(re.findall(pattern, content))
        print(f"  {pattern_name}: {count}")
    
    return results

if __name__ == "__main__":
    # Analyze both versions
    print("Analyzing original pipeline...")
    original_results = analyze_error_handling("eleven_stage_pipeline_optimized.py")
    
    print("\n" + "="*50 + "\n")
    
    print("Analyzing cleaned pipeline...")
    cleaned_results = analyze_error_handling("eleven_stage_pipeline_cleaned.py")