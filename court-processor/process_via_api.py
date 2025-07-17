#!/usr/bin/env python3
"""
Process fetched RECAP data through our existing pipeline APIs
"""
import asyncio
import aiohttp
import json
from pathlib import Path
from datetime import datetime

async def process_test_data():
    """Process fetched data using our RECAP API"""
    print("=== Processing Test Data via RECAP API ===")
    print(f"Started at: {datetime.now()}\n")
    
    # API endpoints
    RECAP_API = "http://localhost:8091"
    UNIFIED_API = "http://localhost:8090"
    
    # Load test data
    data_dir = Path("test_data/recap")
    
    try:
        with open(data_dir / "specific_test_cases.json", 'r') as f:
            test_cases = json.load(f)
    except FileNotFoundError:
        print("❌ No test data found. Run fetch_test_data.py first!")
        return
    
    async with aiohttp.ClientSession() as session:
        # Check API health
        print("1. Checking API health...")
        try:
            async with session.get(f"{RECAP_API}/") as resp:
                if resp.status == 200:
                    print("✓ RECAP API is running")
                else:
                    print("❌ RECAP API not responding")
                    return
        except:
            print("❌ RECAP API not running. Start with: python recap_api.py")
            return
        
        # Process each test case
        results = {}
        
        for case_type, case_data in test_cases.items():
            if not case_data:
                continue
                
            print(f"\n2. Processing {case_type}...")
            print(f"   Case: {case_data['docket']['case_name'][:60]}...")
            
            # Process docket through RECAP API
            try:
                async with session.post(
                    f"{RECAP_API}/recap/process-docket",
                    json={
                        "docket_id": case_data['docket']['id'],
                        "include_documents": True
                    }
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        results[case_type] = result
                        
                        print(f"   ✓ Processed successfully")
                        print(f"     Documents: {result.get('documents_processed', 0)}/{result.get('documents_found', 0)}")
                        print(f"     Is IP Case: {result.get('is_ip_case', False)}")
                        
                        if result.get('errors'):
                            print(f"     ⚠️  Errors: {len(result['errors'])}")
                    else:
                        print(f"   ❌ Failed: {resp.status}")
                        
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        # Get processing statistics
        print("\n3. Getting processing statistics...")
        try:
            async with session.get(f"{RECAP_API}/recap/stats") as resp:
                if resp.status == 200:
                    stats = await resp.json()
                    print("\n📊 Processing Statistics:")
                    for key, value in stats['stats'].items():
                        print(f"   {key}: {value}")
        except Exception as e:
            print(f"   ❌ Error getting stats: {e}")
    
    print(f"\n✓ Processing completed at: {datetime.now()}")
    
    # Save results
    with open(data_dir / "processing_results.json", 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"✓ Results saved to: {data_dir / 'processing_results.json'}")


async def batch_process_ip_cases():
    """Use the batch IP cases endpoint"""
    print("\n=== Batch Processing IP Cases ===")
    
    RECAP_API = "http://localhost:8091"
    
    async with aiohttp.ClientSession() as session:
        print("Processing last 30 days of IP cases...")
        
        try:
            async with session.post(
                f"{RECAP_API}/recap/ip-cases-batch",
                json={
                    "start_date": "2024-10-15",
                    "courts": ["txed", "deld"],
                    "transcripts_only": False
                }
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print("\n✓ Batch processing complete!")
                    print(f"  Stats: {json.dumps(result['stats'], indent=2)}")
                else:
                    print(f"❌ Failed: {resp.status}")
                    
        except Exception as e:
            print(f"❌ Error: {e}")


def verify_database():
    """Show SQL queries to verify data in PostgreSQL"""
    print("\n=== Database Verification Queries ===")
    print("\nRun these queries in PostgreSQL to verify the processed data:\n")
    
    queries = [
        ("Count RECAP documents", """
SELECT COUNT(*) as total_recap_docs 
FROM court_data.opinions_unified 
WHERE source = 'recap';
"""),
        
        ("RECAP documents by type", """
SELECT type, COUNT(*) as count 
FROM court_data.opinions_unified 
WHERE source = 'recap' 
GROUP BY type 
ORDER BY count DESC;
"""),
        
        ("Transcripts with speaker data", """
SELECT case_name, court_id, date_filed,
       jsonb_array_length(structured_elements->'structured_elements') as element_count
FROM court_data.opinions_unified
WHERE source = 'recap' 
  AND type = 'transcript'
LIMIT 5;
"""),
        
        ("IP cases by court", """
SELECT court_id, 
       nature_of_suit,
       COUNT(*) as case_count
FROM court_data.opinions_unified
WHERE source = 'recap'
  AND nature_of_suit IN ('820', '830', '835', '840')
GROUP BY court_id, nature_of_suit
ORDER BY case_count DESC;
"""),
        
        ("Recent processing activity", """
SELECT DATE(created_at) as process_date,
       COUNT(*) as docs_processed,
       COUNT(DISTINCT court_id) as courts
FROM court_data.opinions_unified
WHERE source = 'recap'
  AND created_at > NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY process_date DESC;
""")
    ]
    
    for title, query in queries:
        print(f"-- {title}")
        print(query)
    
    print("\n💡 To connect to the database:")
    print("docker exec -it unified-processor psql -U $DB_USER -d $DB_NAME")


if __name__ == "__main__":
    print("Choose processing method:")
    print("1. Process specific test cases")
    print("2. Batch process IP cases")
    print("3. Show database verification queries")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        asyncio.run(process_test_data())
    elif choice == "2":
        asyncio.run(batch_process_ip_cases())
    elif choice == "3":
        verify_database()
    else:
        print("Invalid choice")
    
    print("\n✓ Done! The data should now be in PostgreSQL.")