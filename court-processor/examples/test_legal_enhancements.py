"""
Example script to test legal document enhancements
"""
import asyncio
import json
from datetime import datetime

# Add parent directory to path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.unified_document_processor import UnifiedDocumentProcessor
from services.legal_document_enhancer import LegalDocumentEnhancer


async def test_transcript_enhancement():
    """Test transcript processing with legal enhancements"""
    print("Testing Transcript Enhancement...")
    
    # Sample transcript document
    transcript_doc = {
        'id': 12345,
        'court_id': 'test',
        'case_name': 'State v. Smith - Transcript',
        'type': 'transcript',
        'plain_text': """
UNITED STATES DISTRICT COURT
EASTERN DISTRICT OF CALIFORNIA

STATE v. SMITH
Case No. 2024-CR-00123

TRANSCRIPT OF PROCEEDINGS
January 15, 2024

THE COURT: Good morning, counsel. Are we ready to proceed?

MR. JONES: Good morning, Your Honor. The prosecution is ready.

MS. DAVIS: Good morning, Your Honor. The defense is ready.

THE COURT: Very well. Mr. Jones, you may call your first witness.

MR. JONES: The State calls Officer Williams to the stand.

(Witness sworn)

DIRECT EXAMINATION
BY MR. JONES:

Q. Officer Williams, were you on duty on December 1st, 2023?
A. Yes, I was.

Q. And did you respond to a call at 123 Main Street?
A. I did.

MS. DAVIS: Objection, Your Honor. Foundation.

THE COURT: Sustained. Lay a proper foundation, counsel.

MR. JONES: Let me rephrase. Officer Williams, what was your assignment on December 1st?
A. I was patrolling the downtown area in my squad car.

Q. Did you receive any calls during your patrol?
A. Yes, at approximately 2:30 PM, I received a dispatch call.

MS. DAVIS: Objection. Hearsay.

THE COURT: Overruled. The officer can testify to why he responded.

Q. What did the dispatch indicate?
A. There was a reported disturbance at 123 Main Street.

CROSS-EXAMINATION
BY MS. DAVIS:

Q. Officer Williams, you didn't actually see my client at the scene initially, did you?
A. No, not initially.

Q. In fact, he was already in custody when you arrived?
A. That's correct.

MS. DAVIS: No further questions.

THE COURT: Any redirect?

MR. JONES: No, Your Honor.

THE COURT: The witness may step down. Let's take a 15-minute recess.

(RECESS)
        """
    }
    
    # Process through pipeline
    processor = UnifiedDocumentProcessor()
    result = await processor.process_single_document(transcript_doc)
    
    # Display results
    if result.get('structured_elements'):
        print("\nEnhanced Transcript Elements:")
        print("-" * 50)
        
        elements = result['structured_elements'].get('structured_elements', [])
        for i, elem in enumerate(elements[:10]):  # Show first 10
            if elem.get('legal_metadata'):
                print(f"\nElement {i}:")
                print(f"Text: {elem['text'][:100]}...")
                print(f"Legal Metadata: {json.dumps(elem['legal_metadata'], indent=2)}")


async def test_opinion_enhancement():
    """Test opinion processing with legal enhancements"""
    print("\n\nTesting Opinion Enhancement...")
    
    # Sample opinion document
    opinion_doc = {
        'id': 67890,
        'court_id': 'ca9',
        'case_name': 'Smith v. Jones',
        'type': 'opinion',
        'plain_text': """
UNITED STATES COURT OF APPEALS
FOR THE NINTH CIRCUIT

JOHN SMITH, Plaintiff-Appellant,
v.
JANE JONES, Defendant-Appellee.

No. 23-12345

Appeal from the United States District Court
for the Northern District of California
D.C. No. 2022-cv-00123

PROCEDURAL HISTORY

This case comes before us on appeal from the district court's grant of 
summary judgment in favor of defendant Jane Jones. The plaintiff, John Smith,
filed this action alleging breach of contract and fraud arising from a 
business transaction in 2021.

STANDARD OF REVIEW

We review a district court's grant of summary judgment de novo. Anderson v. 
Liberty Lobby, Inc., 477 U.S. 242, 247 (1986). Summary judgment is appropriate
when there is no genuine dispute as to any material fact and the movant is 
entitled to judgment as a matter of law. Fed. R. Civ. P. 56(a).

FACTUAL BACKGROUND

In January 2021, Smith and Jones entered into a partnership agreement to 
develop a mobile application. Under the agreement, Smith would provide 
technical expertise while Jones would secure funding and manage business 
operations.

DISCUSSION

I. The Breach of Contract Claim

The district court properly granted summary judgment on Smith's breach of 
contract claim. To establish breach of contract under California law, a 
plaintiff must prove: (1) the existence of a contract, (2) plaintiff's 
performance, (3) defendant's breach, and (4) damages. See Oasis West Realty, 
LLC v. Goldman, 51 Cal. 4th 811, 821 (2011).

II. The Fraud Claim

Smith's fraud claim likewise fails. The elements of fraud in California are:
(1) misrepresentation, (2) knowledge of falsity, (3) intent to defraud,
(4) justifiable reliance, and (5) resulting damage. Lazar v. Superior Court,
12 Cal. 4th 631, 638 (1996).

CONCLUSION

For the foregoing reasons, we AFFIRM the district court's judgment.

AFFIRMED.
        """
    }
    
    # Process through pipeline
    processor = UnifiedDocumentProcessor()
    result = await processor.process_single_document(opinion_doc)
    
    # Display section analysis
    if result.get('structured_elements'):
        print("\nOpinion Sections Identified:")
        print("-" * 50)
        
        elements = result['structured_elements'].get('structured_elements', [])
        sections = {}
        
        for elem in elements:
            legal = elem.get('legal_metadata', {})
            if section := legal.get('section'):
                if section not in sections:
                    sections[section] = []
                sections[section].append(elem['text'][:100] + "...")
        
        for section, texts in sections.items():
            print(f"\n{section.upper()}:")
            for text in texts[:2]:  # Show first 2 of each section
                print(f"  - {text}")


async def test_custom_enhancement():
    """Test custom legal enhancement for specific use case"""
    print("\n\nTesting Custom Enhancement...")
    
    # Create custom enhancer for bankruptcy documents
    enhancer = LegalDocumentEnhancer()
    
    def enhance_bankruptcy(elements):
        """Custom bankruptcy enhancement"""
        for elem in elements:
            # Detect chapter references
            import re
            if match := re.search(r'Chapter (\d+)', elem.text):
                elem.metadata.legal['bankruptcy_chapter'] = int(match.group(1))
            
            # Detect creditor discussions
            if 'creditor' in elem.text.lower():
                elem.metadata.legal['discusses_creditors'] = True
                
                # Classify creditor type
                if 'secured' in elem.text.lower():
                    elem.metadata.legal['creditor_type'] = 'secured'
                elif 'unsecured' in elem.text.lower():
                    elem.metadata.legal['creditor_type'] = 'unsecured'
        
        return elements
    
    # Register custom enhancer
    enhancer.register_custom_enhancer('bankruptcy', enhance_bankruptcy)
    
    # Test with bankruptcy content
    from unstructured.partition.text import partition_text
    
    bankruptcy_text = """
    In re: ACME CORPORATION
    Debtor
    
    Chapter 11 Proceeding
    Case No. 24-12345
    
    MOTION FOR RELIEF FROM AUTOMATIC STAY
    
    Secured Creditor First National Bank hereby moves for relief from the 
    automatic stay to foreclose on the property located at 123 Main Street.
    
    The debtor filed for Chapter 11 bankruptcy protection on January 1, 2024.
    First National Bank holds a secured claim of $1,000,000 against the property.
    
    Unsecured creditors have filed proofs of claim totaling $500,000.
    """
    
    elements = partition_text(text=bankruptcy_text)
    enhanced = enhancer.enhance(elements, doc_type='bankruptcy')
    
    print("\nBankruptcy-Specific Enhancements:")
    print("-" * 50)
    for elem in enhanced:
        if elem.metadata.legal:
            print(f"\nText: {elem.text[:80]}...")
            print(f"Legal Metadata: {json.dumps(elem.metadata.legal, indent=2)}")


async def test_statistics():
    """Test document statistics extraction"""
    print("\n\nTesting Document Statistics...")
    
    # Process a document and extract statistics
    doc = {
        'id': 11111,
        'court_id': 'test',
        'case_name': 'Complex Case with Many Citations',
        'plain_text': """
        This case involves multiple legal issues. See Smith v. Jones, 123 F.3d 456 
        (9th Cir. 2020); Johnson v. State, 789 U.S. 012 (2019); Brown v. Board,
        347 U.S. 483 (1954).
        
        MR. SMITH: Objection, relevance.
        THE COURT: Overruled.
        
        MS. JONES: Objection, hearsay.
        THE COURT: Sustained.
        
        The court finds that the standard of review is de novo. We must consider
        the abuse of discretion standard for evidentiary rulings.
        """
    }
    
    processor = UnifiedDocumentProcessor()
    result = await processor.process_single_document(doc)
    
    # Extract statistics
    if result.get('structured_elements'):
        elements = result['structured_elements'].get('structured_elements', [])
        
        stats = {
            'total_citations': 0,
            'objections': 0,
            'rulings': 0,
            'legal_standards': []
        }
        
        for elem in elements:
            legal = elem.get('legal_metadata', {})
            
            if legal.get('citations'):
                stats['total_citations'] += len(legal['citations'])
            
            if legal.get('event') == 'objection':
                stats['objections'] += 1
            
            if legal.get('event') == 'ruling':
                stats['rulings'] += 1
            
            if legal.get('standard_type'):
                stats['legal_standards'].append(legal['standard_type'])
        
        print("\nDocument Statistics:")
        print("-" * 50)
        print(json.dumps(stats, indent=2))


async def main():
    """Run all tests"""
    await test_transcript_enhancement()
    await test_opinion_enhancement()
    await test_custom_enhancement()
    await test_statistics()


if __name__ == "__main__":
    asyncio.run(main())