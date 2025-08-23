# Test Suite

Consolidated test directory for all Aletheia testing.

## Structure

```
tests/
├── unit/          # Unit tests (currently empty, to be populated)
├── integration/   # Integration tests (JS test files)
├── data/          # Test data files (PDFs, sample documents)
├── pacer/         # PACER/RECAP integration tests (Python)
└── manual/        # Manual testing utilities (HTML, shell scripts)
```

## Running Tests

### Integration Tests
```bash
cd tests/integration
node setup.js
node integration-test.js
```

### PACER Tests
```bash
cd tests/pacer
pip install -r requirements.txt
python test_real_cases.py
```

### Manual Tests
See `tests/manual/` for browser-based and shell test utilities.