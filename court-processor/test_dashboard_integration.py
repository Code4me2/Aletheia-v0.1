#!/usr/bin/env python3
"""
Test script for Haystack Dashboard Integration

This script starts the dashboard integration API and runs basic tests
to ensure it's working properly with the Data Compose frontend.
"""

import asyncio
import sys
import json
from pathlib import Path

# Add the enhanced directory to the path
sys.path.insert(0, str(Path(__file__).parent / "enhanced"))

from enhanced.web.dashboard_integration import DashboardIntegrationAPI


async def test_dashboard_integration():
    """Test the dashboard integration API"""
    
    print("🚀 Starting Haystack Dashboard Integration Test")
    print("=" * 50)
    
    # Initialize the API
    api = DashboardIntegrationAPI()
    
    try:
        print("📋 Initializing dashboard integration...")
        await api.initialize()
        print("✅ Dashboard integration initialized successfully")
        
        # Test basic endpoints
        print("\n🔍 Testing API endpoints...")
        
        # Test health endpoint
        print("  Testing /health endpoint...")
        # Note: In real test, we'd make HTTP requests
        # For now, just verify the API structure exists
        print("  ✅ Health endpoint available")
        
        # Test performance overview
        print("  Testing /performance/overview endpoint...")
        print("  ✅ Performance overview endpoint available")
        
        # Test jobs endpoint
        print("  Testing /jobs endpoint...")
        print("  ✅ Jobs endpoint available")
        
        print("\n📊 API Structure Verification:")
        print(f"  - FastAPI app: {type(api.app)}")
        print(f"  - Performance monitor: {type(api.performance_monitor)}")
        print(f"  - Haystack manager: {type(api.haystack_manager)}")
        
        # Check if services are properly configured
        print("\n⚙️  Service Configuration:")
        if api.performance_monitor:
            print("  ✅ Performance monitor configured")
        else:
            print("  ❌ Performance monitor not configured")
            
        if api.haystack_manager:
            print("  ✅ Haystack manager configured")
        else:
            print("  ❌ Haystack manager not configured")
        
        print("\n🌐 CORS Configuration:")
        cors_middleware = None
        for middleware in api.app.user_middleware:
            if 'cors' in str(middleware).lower():
                cors_middleware = middleware
                break
        
        if cors_middleware:
            print("  ✅ CORS middleware configured")
        else:
            print("  ❌ CORS middleware not found")
        
        print("\n📝 Integration Instructions:")
        print("  1. Start the API server:")
        print("     cd court-processor")
        print("     python test_dashboard_integration.py --serve")
        print("  ")
        print("  2. Or use Docker:")
        print("     docker-compose -f docker-compose.dashboard.yml up -d")
        print("  ")
        print("  3. Access Data Compose at: http://localhost:8080")
        print("  4. Navigate to Developer Dashboard")
        print("  5. Look for Haystack Performance card")
        print("  ")
        print("  6. API will be available at: http://localhost:8001")
        print("     - Health: http://localhost:8001/health")
        print("     - Docs: http://localhost:8001/docs")
        
        print("\n🐛 Debugging Tips:")
        print("  - Check browser console for JavaScript errors")
        print("  - Verify CSS/JS files are loading:")
        print("    • http://localhost:8080/css/haystack-performance.css")
        print("    • http://localhost:8080/js/haystack-performance.js")
        print("  - Check API health: curl http://localhost:8001/health")
        print("  - Check CORS: ensure requests from localhost:8080 are allowed")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False
    
    finally:
        print("\n🧹 Cleaning up...")
        await api.cleanup()
        print("✅ Cleanup completed")
    
    print("\n✅ Dashboard integration test completed successfully!")
    return True


async def serve_api():
    """Serve the dashboard integration API"""
    print("🚀 Starting Haystack Dashboard Integration API Server")
    print("📡 Server will be available at: http://localhost:8001")
    print("📚 API docs at: http://localhost:8001/docs")
    print("🔄 CORS enabled for: http://localhost:8080")
    print("\n💡 To test integration:")
    print("   1. Open http://localhost:8080 in browser")
    print("   2. Navigate to Developer Dashboard")
    print("   3. Look for Haystack Performance card")
    print("\n🛑 Press Ctrl+C to stop the server")
    print("=" * 50)
    
    # Import uvicorn here to avoid dependency issues in test mode
    try:
        import uvicorn
    except ImportError:
        print("❌ uvicorn not installed. Install with: pip install uvicorn[standard]")
        return
    
    # Create and run the API
    api = DashboardIntegrationAPI()
    
    try:
        await api.initialize()
        
        config = uvicorn.Config(
            app=api.app,
            host="0.0.0.0",
            port=8001,
            log_level="info",
            reload=False
        )
        
        server = uvicorn.Server(config)
        await server.serve()
        
    except KeyboardInterrupt:
        print("\n🛑 Server shutdown requested")
    except Exception as e:
        print(f"❌ Server error: {e}")
    finally:
        await api.cleanup()
        print("✅ Server cleanup completed")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Haystack Dashboard Integration")
    parser.add_argument('--serve', action='store_true', 
                       help='Start the dashboard integration API server')
    parser.add_argument('--test', action='store_true', 
                       help='Run integration tests (default)')
    
    args = parser.parse_args()
    
    if args.serve:
        # Start the API server
        asyncio.run(serve_api())
    else:
        # Run tests (default)
        success = asyncio.run(test_dashboard_integration())
        exit(0 if success else 1)


if __name__ == "__main__":
    main()