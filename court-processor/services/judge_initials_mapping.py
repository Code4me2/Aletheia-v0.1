#!/usr/bin/env python3
"""
Judge initials to full name mapping for common federal judges
"""

# Common Texas Eastern District judges
JUDGE_INITIALS_MAP = {
    # Eastern District of Texas
    'RG': {'name': 'Rodney Gilstrap', 'full_name': 'Rodney Gilstrap', 'court': 'txed', 'title': 'Chief Judge'},
    'AM': {'name': 'Amos Mazzant', 'full_name': 'Amos L. Mazzant III', 'court': 'txed', 'title': 'District Judge'},
    'RP': {'name': 'Roy Payne', 'full_name': 'Robert W. Payne', 'court': 'txed', 'title': 'Magistrate Judge'},
    'RSW': {'name': 'Robert Schroeder', 'full_name': 'Robert W. Schroeder III', 'court': 'txed', 'title': 'District Judge'},
    'JDC': {'name': 'J. Campbell Barker', 'full_name': 'J. Campbell Barker', 'court': 'txed', 'title': 'District Judge'},
    
    # Northern District of Texas  
    'BH': {'name': 'Barbara Lynn', 'full_name': 'Barbara M.G. Lynn', 'court': 'txnd', 'title': 'Chief Judge'},
    'DF': {'name': 'David Fitzwater', 'full_name': 'Sidney A. Fitzwater', 'court': 'txnd', 'title': 'District Judge'},
    'EK': {'name': 'Ed Kinkeade', 'full_name': 'Ed Kinkeade', 'court': 'txnd', 'title': 'District Judge'},
    
    # Southern District of Texas
    'LHR': {'name': 'Lee Rosenthal', 'full_name': 'Lee H. Rosenthal', 'court': 'txsd', 'title': 'Chief Judge'},
    'AH': {'name': 'Alfred Bennett', 'full_name': 'Alfred H. Bennett', 'court': 'txsd', 'title': 'District Judge'},
    'KBE': {'name': 'Keith Ellison', 'full_name': 'Keith P. Ellison', 'court': 'txsd', 'title': 'District Judge'},
    
    # Western District of Texas
    'AMA': {'name': 'Alan Albright', 'full_name': 'Alan D. Albright', 'court': 'txwd', 'title': 'District Judge'},
    'DA': {'name': 'David Ezra', 'full_name': 'David A. Ezra', 'court': 'txwd', 'title': 'District Judge'},
    'XR': {'name': 'Xavier Rodriguez', 'full_name': 'Xavier Rodriguez', 'court': 'txwd', 'title': 'District Judge'},
}

def get_judge_from_initials(initials: str, court_id: str = None) -> dict:
    """
    Get judge information from initials
    
    Args:
        initials: Judge initials (e.g., 'RG')
        court_id: Optional court ID to help with disambiguation
        
    Returns:
        Dict with judge information or None
    """
    if initials in JUDGE_INITIALS_MAP:
        judge_info = JUDGE_INITIALS_MAP[initials].copy()
        
        # Verify court matches if provided
        if court_id and judge_info.get('court') != court_id:
            # Initials might be ambiguous across courts
            return None
            
        return judge_info
    
    return None

def get_all_initials_for_court(court_id: str) -> dict:
    """Get all judge initials for a specific court"""
    judges = {}
    for initials, info in JUDGE_INITIALS_MAP.items():
        if info.get('court') == court_id:
            judges[initials] = info
    return judges

# Add more mappings as needed
# This could be loaded from a JSON file or database in production