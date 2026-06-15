# Run all tests
pip install -e ".[dev]" 2>$null
python -m pytest tests/ -v --tb=short 2>&1 | Select-String -NotMatch "passed|failed|ERRORS|test_" -NotMatch
