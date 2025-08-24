# Aletheia Test Suite

Centralized testing directory for all Aletheia components.

## Structure

```
tests/
├── unit/                 # Unit tests for individual functions
│   ├── services/        # Service-specific unit tests
│   ├── components/      # Frontend component tests
│   ├── custom-nodes/    # n8n custom node tests
│   └── utils/          # Utility function tests
├── integration/         # Integration tests between services
│   ├── api/            # API endpoint tests
│   ├── database/       # Database integration tests
│   └── workflows/      # n8n workflow tests
├── e2e/                # End-to-end tests
│   ├── user-flows/     # Complete user journey tests
│   └── smoke/          # Quick smoke tests
├── fixtures/           # Test data and mocks
│   ├── data/          # Sample data files (moved from data/)
│   └── mocks/         # Mock responses
├── pacer/             # PACER/RECAP integration tests (Python)
└── manual/            # Manual testing scripts and docs
```

## Running Tests

```bash
# Run all tests
./dev test

# Run specific test suites
./dev test unit
./dev test integration
./dev test e2e

# Legacy commands (still supported)
cd tests/integration && node integration-test.js
cd tests/pacer && python test_real_cases.py
```

## Test Organization Guidelines

1. **Unit Tests**: Test individual functions/components in isolation
2. **Integration Tests**: Test service interactions and API contracts
3. **E2E Tests**: Test complete user workflows through the UI
4. **Fixtures**: Shared test data and mock responses
5. **Manual Tests**: Scripts for manual verification when automation isn't practical

## Migration Note

Tests are being consolidated from various locations:
- `court-processor/tests/` → `tests/unit/services/court-processor/`
- `services/lawyer-chat/e2e/` → `tests/e2e/lawyer-chat/`
- `services/lawyer-chat/src/**/__tests__/` → `tests/unit/services/lawyer-chat/`
- `n8n/custom-nodes/*/test/` → `tests/unit/custom-nodes/`