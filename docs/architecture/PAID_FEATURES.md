"""
CourtListener RECAP Fetch API Implementation
For retrieving IP documents from federal courts with cost optimization
"""

import asyncio
import aiohttp
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass
from enum import Enum
import re
import time
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RequestType(Enum):
    """RECAP Fetch request types"""
    DOCKET = 1
    DOCUMENT = 2
    ATTACHMENT_PAGE = 3


@dataclass
class Document:
    """Document metadata"""
    case_number: str
    document_number: int
    description: str
    date_filed: str
    pacer_doc_id: Optional[str] = None
    pacer_case_id: Optional[str] = None
    page_count: Optional[int] = None
    filepath_local: Optional[str] = None
    is_available_in_recap: bool = False
    estimated_cost: float = 0.0
    ip_relevance_score: int = 0


class CourtListenerClient:
    """
    Client for interacting with CourtListener's free and paid APIs
    """
    
    def __init__(self, api_token: str, pacer_username: str, pacer_password: str):
        self.api_token = api_token
        self.pacer_username = pacer_username
        self.pacer_password = pacer_password
        self.base_url = "https://www.courtlistener.com/api/rest/v4"
        self.headers = {
            "Authorization": f"Token {self.api_token}",
            "Content-Type": "application/json"
        }
        self.session = None
        self.total_cost = 0.0
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def search_cases(self, 
                          court: str = "txed",
                          judge: Optional[str] = None,
                          nature_of_suit: Optional[str] = None,
                          filed_after: Optional[str] = None,
                          filed_before: Optional[str] = None,
                          party_name: Optional[str] = None) -> List[Dict]:
        """
        Search for cases in CourtListener's free database
        """
        params = {
            "court": court,
            "order_by": "-date_filed"
        }
        
        if judge:
            params["assigned_to__name_last__icontains"] = judge
        if nature_of_suit:
            params["nature_of_suit"] = nature_of_suit
        if filed_after:
            params["date_filed__gte"] = filed_after
        if filed_before:
            params["date_filed__lte"] = filed_before
        if party_name:
            params["case_name__icontains"] = party_name
            
        results = []
        url = f"{self.base_url}/dockets/"
        
        while url:
            logger.info(f"Searching cases: {params}")
            async with self.session.get(url, headers=self.headers, params=params) as resp:
                if resp.status != 200:
                    logger.error(f"Search failed: {await resp.text()}")
                    break
                    
                data = await resp.json()
                results.extend(data.get("results", []))
                url = data.get("next")
                params = {}  # Clear params for pagination
                
        logger.info(f"Found {len(results)} cases")
        return results
    
    async def check_document_availability(self, pacer_doc_id: str) -> Tuple[bool, Optional[Dict]]:
        """
        Check if a document is already available in RECAP Archive (free)
        """
        url = f"{self.base_url}/recap-documents/"
        params = {"pacer_doc_id": pacer_doc_id}
        
        async with self.session.get(url, headers=self.headers, params=params) as resp:
            if resp.status != 200:
                return False, None
                
            data = await resp.json()
            if data.get("count", 0) > 0:
                doc = data["results"][0]
                return True, doc
                
        return False, None
    
    async def fetch_docket_via_recap(self,
                                   court: str,
                                   case_number: Optional[str] = None,
                                   pacer_case_id: Optional[str] = None,
                                   include_parties: bool = True,
                                   date_from: Optional[str] = None,
                                   date_to: Optional[str] = None) -> Dict:
        """
        Fetch a docket from PACER via RECAP fetch API (costs money)
        """
        if not case_number and not pacer_case_id:
            raise ValueError("Either case_number or pacer_case_id required")
            
        data = {
            "request_type": RequestType.DOCKET.value,
            "court": court,
            "pacer_username": self.pacer_username,
            "pacer_password": self.pacer_password,
            "show_parties_and_counsel": include_parties
        }
        
        if case_number:
            data["docket_number"] = case_number
        if pacer_case_id:
            data["pacer_case_id"] = pacer_case_id
        if date_from:
            data["date_from"] = date_from
        if date_to:
            data["date_to"] = date_to
            
        url = f"{self.base_url}/recap-fetch/"
        
        logger.info(f"Fetching docket: {case_number or pacer_case_id}")
        async with self.session.post(url, headers=self.headers, json=data) as resp:
            if resp.status != 201:
                error = await resp.text()
                logger.error(f"Docket fetch failed: {error}")
                raise Exception(f"Fetch failed: {error}")
                
            result = await resp.json()
            fetch_id = result["id"]
            
        # Poll for completion
        return await self._poll_fetch_completion(fetch_id)
    
    async def fetch_document_via_recap(self, recap_document_id: int) -> Dict:
        """
        Fetch a specific document from PACER via RECAP fetch API (costs money)
        """
        data = {
            "request_type": RequestType.DOCUMENT.value,
            "recap_document": recap_document_id,
            "pacer_username": self.pacer_username,
            "pacer_password": self.pacer_password
        }
        
        url = f"{self.base_url}/recap-fetch/"
        
        logger.info(f"Fetching document: {recap_document_id}")
        async with self.session.post(url, headers=self.headers, json=data) as resp:
            if resp.status != 201:
                error = await resp.text()
                logger.error(f"Document fetch failed: {error}")
                raise Exception(f"Fetch failed: {error}")
                
            result = await resp.json()
            fetch_id = result["id"]
            
        # Poll for completion
        return await self._poll_fetch_completion(fetch_id)
    
    async def _poll_fetch_completion(self, fetch_id: int, max_attempts: int = 60) -> Dict:
        """
        Poll for RECAP fetch completion
        """
        url = f"{self.base_url}/recap-fetch/{fetch_id}/"
        
        for attempt in range(max_attempts):
            async with self.session.get(url, headers=self.headers) as resp:
                if resp.status != 200:
                    raise Exception(f"Poll failed: {await resp.text()}")
                    
                data = await resp.json()
                status = data.get("status")
                
                if status == "SUCCESSFUL":
                    cost = data.get("cost", 0.0)
                    self.total_cost += cost
                    logger.info(f"Fetch completed. Cost: ${cost:.2f}")
                    return data
                elif status == "FAILED":
                    raise Exception(f"Fetch failed: {data.get('message')}")
                    
            # Wait before next poll
            await asyncio.sleep(2)
            
        raise Exception("Fetch timed out")
    
    async def download_free_document(self, filepath_local: str) -> bytes:
        """
        Download a document from RECAP Archive (free)
        """
        url = f"https://storage.courtlistener.com/{filepath_local}"
        
        logger.info(f"Downloading free document: {filepath_local}")
        async with self.session.get(url) as resp:
            if resp.status != 200:
                raise Exception(f"Download failed: {resp.status}")
                
            return await resp.read()


class IPDocumentAnalyzer:
    """
    Analyze documents for IP relevance and prioritize downloads
    """
    
    # IP-related document patterns
    IP_PATTERNS = {
        "patent": {
            "high_priority": [
                (r"claim\s+construction", 50),
                (r"markman", 50),
                (r"verdict", 45),
                (r"final\s+judgment", 45),
                (r"infringement\s+contention", 40),
                (r"invalidity\s+contention", 40),
                (r"expert\s+report", 35),
                (r"complaint.*patent", 30),
                (r"answer.*patent", 25),
                (r"summary\s+judgment", 30),
            ],
            "medium_priority": [
                (r"protective\s+order", 20),
                (r"discovery", 15),
                (r"motion.*dismiss", 20),
                (r"response.*motion", 15),
                (r"reply.*motion", 15),
            ],
            "low_priority": [
                (r"notice\s+of\s+appearance", -10),
                (r"pro\s+hac\s+vice", -10),
                (r"certificate\s+of\s+service", -10),
                (r"extension\s+of\s+time", -5),
            ]
        }
    }
    
    @classmethod
    def score_document(cls, description: str) -> int:
        """
        Score a document based on IP relevance
        """
        score = 0
        desc_lower = description.lower()
        
        # Check all pattern categories
        for category in ["high_priority", "medium_priority", "low_priority"]:
            for pattern, points in cls.IP_PATTERNS["patent"][category]:
                if re.search(pattern, desc_lower):
                    score += points
                    
        return max(0, score)
    
    @classmethod
    def is_ip_document(cls, description: str) -> bool:
        """
        Check if document is IP-related
        """
        return cls.score_document(description) > 0


class SmartDocumentRetriever:
    """
    Intelligent document retrieval with cost optimization
    """
    
    def __init__(self, client: CourtListenerClient, budget: float = 100.0):
        self.client = client
        self.budget = budget
        self.spent = 0.0
        self.free_downloads = 0
        self.paid_downloads = 0
        self.cache = {}
        
    async def get_case_documents(self, case_data: Dict) -> List[Document]:
        """
        Extract document information from case data
        """
        documents = []
        docket_entries = case_data.get("docket_entries", [])
        
        for entry in docket_entries:
            # Check each document in the entry
            for doc in entry.get("recap_documents", []):
                document = Document(
                    case_number=case_data.get("docket_number", ""),
                    document_number=entry.get("entry_number", 0),
                    description=doc.get("description", "") or entry.get("description", ""),
                    date_filed=entry.get("date_filed", ""),
                    pacer_doc_id=doc.get("pacer_doc_id"),
                    pacer_case_id=case_data.get("pacer_case_id"),
                    page_count=doc.get("page_count"),
                    filepath_local=doc.get("filepath_local"),
                    is_available_in_recap=bool(doc.get("filepath_local")),
                    ip_relevance_score=IPDocumentAnalyzer.score_document(
                        doc.get("description", "") or entry.get("description", "")
                    )
                )
                
                # Estimate cost if not free
                if not document.is_available_in_recap:
                    pages = document.page_count or 10  # Assume 10 pages if unknown
                    document.estimated_cost = min(pages * 0.10, 3.00)  # $3 cap for most docs
                    
                documents.append(document)
                
        return documents
    
    async def retrieve_documents(self, documents: List[Document]) -> Dict[str, List[Document]]:
        """
        Retrieve documents intelligently within budget
        """
        # Separate free and paid documents
        free_docs = [d for d in documents if d.is_available_in_recap]
        paid_docs = [d for d in documents if not d.is_available_in_recap]
        
        # Sort paid documents by relevance score
        paid_docs.sort(key=lambda x: x.ip_relevance_score, reverse=True)
        
        downloaded = []
        skipped = []
        
        # Download all free IP-relevant documents
        for doc in free_docs:
            if doc.ip_relevance_score > 0:
                try:
                    content = await self.client.download_free_document(doc.filepath_local)
                    doc.content = content
                    downloaded.append(doc)
                    self.free_downloads += 1
                    logger.info(f"Downloaded free document: {doc.description}")
                except Exception as e:
                    logger.error(f"Failed to download free document: {e}")
                    
        # Download paid documents within budget
        for doc in paid_docs:
            if doc.ip_relevance_score <= 0:
                continue
                
            if self.spent + doc.estimated_cost > self.budget:
                skipped.append(doc)
                continue
                
            try:
                # Find the recap document ID
                if doc.pacer_doc_id:
                    # Search for existing recap document
                    url = f"{self.client.base_url}/recap-documents/"
                    params = {"pacer_doc_id": doc.pacer_doc_id}
                    
                    async with self.client.session.get(
                        url, headers=self.client.headers, params=params
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("count", 0) > 0:
                                recap_doc_id = data["results"][0]["id"]
                                
                                # Fetch via RECAP
                                result = await self.client.fetch_document_via_recap(recap_doc_id)
                                
                                # Update tracking
                                actual_cost = result.get("cost", 0.0)
                                self.spent += actual_cost
                                self.paid_downloads += 1
                                
                                doc.content = result
                                downloaded.append(doc)
                                logger.info(f"Downloaded paid document: {doc.description} (${actual_cost:.2f})")
                                
            except Exception as e:
                logger.error(f"Failed to download paid document: {e}")
                skipped.append(doc)
                
        return {
            "downloaded": downloaded,
            "skipped": skipped,
            "stats": {
                "free_downloads": self.free_downloads,
                "paid_downloads": self.paid_downloads,
                "total_spent": self.spent,
                "budget_remaining": self.budget - self.spent
            }
        }


class IPCaseSearcher:
    """
    Search strategies for finding IP cases
    """
    
    # Nature of Suit codes for IP cases
    IP_NATURE_CODES = {
        "820": "Copyright",
        "830": "Patent",
        "840": "Trademark",
        "890": "Other Statutory"
    }
    
    def __init__(self, client: CourtListenerClient):
        self.client = client
        
    async def search_by_judge(self, 
                            judge_name: str = "Gilstrap",
                            court: str = "txed",
                            filed_after: str = None) -> List[Dict]:
        """
        Search for cases by judge with IP filters
        """
        all_cases = []
        
        # Search each IP nature of suit
        for code, description in self.IP_NATURE_CODES.items():
            logger.info(f"Searching {description} cases for Judge {judge_name}")
            
            cases = await self.client.search_cases(
                court=court,
                judge=judge_name,
                nature_of_suit=code,
                filed_after=filed_after
            )
            
            all_cases.extend(cases)
            
        return all_cases
    
    async def search_by_party(self,
                            party_name: str,
                            court: str = "txed") -> List[Dict]:
        """
        Search for cases by party name
        """
        return await self.client.search_cases(
            court=court,
            party_name=party_name
        )
    
    async def search_recent_ip_cases(self,
                                   court: str = "txed",
                                   days_back: int = 30) -> List[Dict]:
        """
        Search for recent IP cases
        """
        filed_after = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        
        all_cases = []
        for code in self.IP_NATURE_CODES:
            cases = await self.client.search_cases(
                court=court,
                nature_of_suit=code,
                filed_after=filed_after
            )
            all_cases.extend(cases)
            
        return all_cases


async def main():
    """
    Example usage of the IP document retrieval system
    """
    # Load credentials from environment
    api_token = os.getenv("COURTLISTENER_API_TOKEN")
    pacer_username = os.getenv("PACER_USERNAME")
    pacer_password = os.getenv("PACER_PASSWORD")
    
    if not all([api_token, pacer_username, pacer_password]):
        logger.error("Missing required credentials. Set environment variables:")
        logger.error("COURTLISTENER_API_TOKEN, PACER_USERNAME, PACER_PASSWORD")
        return
    
    async with CourtListenerClient(api_token, pacer_username, pacer_password) as client:
        # Initialize components
        searcher = IPCaseSearcher(client)
        retriever = SmartDocumentRetriever(client, budget=50.0)  # $50 budget
        
        # Search for recent Gilstrap patent cases
        logger.info("Searching for Judge Gilstrap's recent patent cases...")
        cases = await searcher.search_by_judge(
            judge_name="Gilstrap",
            court="txed",
            filed_after="2024-01-01"
        )
        
        logger.info(f"Found {len(cases)} cases")
        
        # Process first 5 cases as example
        for case in cases[:5]:
            logger.info(f"\nProcessing case: {case['docket_number']} - {case['case_name']}")
            
            # Check if we need to fetch full docket
            if not case.get("docket_entries"):
                logger.info("Fetching full docket from PACER...")
                try:
                    docket = await client.fetch_docket_via_recap(
                        court="txed",
                        case_number=case["docket_number"]
                    )
                    case.update(docket)
                except Exception as e:
                    logger.error(f"Failed to fetch docket: {e}")
                    continue
            
            # Get documents
            documents = await retriever.get_case_documents(case)
            logger.info(f"Found {len(documents)} documents")
            
            # Filter for IP documents
            ip_documents = [d for d in documents if d.ip_relevance_score > 0]
            logger.info(f"Found {len(ip_documents)} IP-relevant documents")
            
            # Retrieve documents
            results = await retriever.retrieve_documents(ip_documents)
            
            logger.info(f"Downloaded: {len(results['downloaded'])} documents")
            logger.info(f"Skipped: {len(results['skipped'])} documents")
            logger.info(f"Stats: {results['stats']}")
            
            # Save documents (implement your storage logic here)
            for doc in results['downloaded']:
                filename = f"{doc.case_number}_{doc.document_number}_{doc.pacer_doc_id}.pdf"
                # Save doc.content to file
                logger.info(f"Would save: {filename}")
        
        # Final summary
        logger.info(f"\n=== Final Summary ===")
        logger.info(f"Total cost: ${client.total_cost:.2f}")
        logger.info(f"Free downloads: {retriever.free_downloads}")
        logger.info(f"Paid downloads: {retriever.paid_downloads}")


if __name__ == "__main__":
    asyncio.run(main())
