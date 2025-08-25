#!/bin/bash
# Test API improvements within Docker environment

echo "=========================================="
echo "Testing Court Processor API Improvements"
echo "=========================================="

# Run the test script inside the court-processor container
docker-compose exec court-processor python test_api_improvements.py

# Check exit code
if [ $? -eq 0 ]; then
    echo ""
    echo "✅ All API improvement tests passed!"
else
    echo ""
    echo "❌ Some tests failed. Check the output above."
fi

# Optionally run a quick workflow test
echo ""
echo "=========================================="
echo "Running Quick Workflow Test"
echo "=========================================="

# Create a test configuration that uses the new features
cat > /tmp/test_config.py << EOF
import asyncio
from court_processor_orchestrator import CourtProcessorOrchestrator

async def test_workflow():
    config = {
        'ingestion': {
            'court_ids': ['txed'],  # Just E.D. Texas for quick test
            'document_types': ['opinions'],
            'max_per_court': 5,  # Small batch
            'lookback_days': 30,
            'nature_of_suit': ['830'],  # Patent cases only
            'search_type': 'r'  # RECAP search
        },
        'processing': {
            'batch_size': 5,
            'extract_pdfs': True,
            'validate_strict': False,
            'enable_judge_lookup': True,
            'enable_citation_validation': True
        }
    }
    
    orchestrator = CourtProcessorOrchestrator(config)
    results = await orchestrator.run_complete_workflow()
    
    print(f"\nWorkflow completed: {results.get('success')}")
    if results.get('success'):
        print(f"Documents ingested: {results['phases']['ingestion'].get('documents_ingested', 0)}")
        print(f"Documents processed: {results['phases']['processing'].get('summary', {}).get('total_processed', 0)}")
    
    return results

if __name__ == "__main__":
    asyncio.run(test_workflow())
EOF

# Copy test config to container and run
docker cp /tmp/test_config.py $(docker-compose ps -q court-processor):/app/test_config.py
docker-compose exec court-processor python test_config.py

# Clean up
rm /tmp/test_config.py

echo ""
echo "=========================================="
echo "Test Complete"
echo "==========================================">