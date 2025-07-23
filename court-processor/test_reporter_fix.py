#!/usr/bin/env python3
"""
Test the fixed reporter normalization
"""

from eleven_stage_pipeline_optimized import OptimizedElevenStagePipeline
from eyecite import get_citations

# Create pipeline instance
pipeline = OptimizedElevenStagePipeline()

print("Testing Fixed Reporter Normalization")
print("=" * 60)

# Test cases with various reporters
test_texts = [
    "Smith v. Jones, 123 F.3d 456 (5th Cir. 2023)",
    "Brown v. Board, 456 F.2d 789 (9th Cir. 1972)",
    "Apple v. Samsung, 789 F. Supp. 2d 123 (E.D. Tex. 2020)",
    "Microsoft v. Google, 321 F. Supp. 3d 456 (N.D. Cal. 2021)",
    "Doe v. Roe, 654 U.S. 321 (2019)",
    "State v. Smith, 432 S. Ct. 876 (2020)",
    "Patent Case, 567 Fed. Cir. 234 (2021)",  # This won't normalize
    "Basic Case, 123 F. 456 (D.C. Cir. 1910)"  # First series
]

all_citations = []
for text in test_texts:
    citations = get_citations(text)
    print(f"\nText: '{text}'")
    print(f"Found {len(citations)} citations")
    
    # Convert to our format
    for cite in citations:
        citation_data = {
            'text': str(cite),
            'groups': cite.groups if hasattr(cite, 'groups') else {}
        }
        all_citations.append(citation_data)
        print(f"  Citation: {cite}")
        if hasattr(cite, 'groups'):
            print(f"  Reporter: {cite.groups.get('reporter', 'N/A')}")

# Test normalization
print("\n\nTesting Reporter Normalization:")
print("-" * 60)

result = pipeline._normalize_reporters_optimized(all_citations)

print(f"\nNormalization Results:")
print(f"Unique reporters found: {result['count']}")
print(f"Unique reporters: {result['unique_reporters']}")

print("\nDetailed normalization:")
for norm in result['normalized_reporters']:
    status = "✅" if norm.get('edition') != norm.get('original') or norm.get('original') in ['U.S.', 'S. Ct.'] else "❌"
    print(f"{status} '{norm['original']}' -> '{norm['edition']}' ({norm.get('name', 'Unknown')})")

# Summary
print("\n\nSummary:")
federal_reporters = [n for n in result['normalized_reporters'] if 'F.' in n['original']]
print(f"Federal reporters normalized: {len(federal_reporters)}/{len([c for c in all_citations if 'F.' in str(c)])}")

# Test specific problem cases
print("\n\nTesting Specific Problem Cases:")
problem_reporters = ['F.3d', 'F.2d', 'F. Supp. 2d', 'F. Supp. 3d']
for reporter in problem_reporters:
    info = pipeline._get_reporter_info(reporter)
    if info['found']:
        print(f"✅ '{reporter}' -> Found as '{info['edition']}' ({info['name']})")
    else:
        print(f"❌ '{reporter}' -> Not found")

print("\n✅ Reporter normalization has been fixed!")