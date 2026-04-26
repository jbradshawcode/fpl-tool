# FPL Analysis Test Suite

Comprehensive unit tests for the FPL analysis tool.

## Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── domain/                  # Domain layer tests
│   ├── test_history.py     # Scoring calculations
│   └── test_calculations.py # Aggregation logic
├── services/               # Service layer tests
│   └── test_player_service.py # Player operations
└── infrastructure/         # Infrastructure tests
    └── test_api_client.py  # API mocking
```

## Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/domain/test_history.py

# Run specific test class
pytest tests/domain/test_history.py::TestCalculatePlayPoints

# Run with coverage
pytest --cov=domain --cov=services --cov=infrastructure

# Run only fast tests (exclude slow)
pytest -m "not slow"

# Run only integration tests
pytest -m integration
```

## Coverage Areas

### Domain Layer (`domain/`)
- **Scoring calculations**: Play points, attack points, clean sheets, GC penalties
- **Expected points integration**: Full calculation pipeline
- **Per-90 metrics**: Edge cases with zero minutes, red cards
- **Data aggregation**: Grouping and filtering operations

### Service Layer (`services/`)
- **Player filtering**: Price, team, search term combinations
- **Sorting**: Custom position sort, column sorting
- **Pagination**: Edge cases, boundary conditions
- **Pinned players**: Extraction and separation

### Infrastructure (`infrastructure/`)
- **API client**: Mocked external calls, error handling
- **Data loading**: File operations, caching

## Writing New Tests

### Test Naming Convention
```python
def test_<what_it_does>_<condition>():
    """Should <expected behavior> when <condition>."""
```

### Using Fixtures
```python
def test_my_function(sample_history_df, sample_scoring):
    # Use fixtures from conftest.py
    result = my_function(sample_history_df, sample_scoring)
    assert result > 0
```

### Adding Custom Fixtures
Add to `conftest.py`:
```python
@pytest.fixture
def my_custom_data():
    return pd.DataFrame({...})
```

## Key Fixtures

- `sample_scoring` - FPL scoring rules
- `sample_parameters` - Game parameters (thresholds)
- `sample_players_df` - Player metadata
- `sample_history_df` - Match history data
- `empty_history_df` - Empty dataframe for edge cases
- `players_for_pagination` - 25 players for pagination tests
- `players_for_filtering` - 5 players with varied attributes

## Continuous Development

When adding new features:
1. Write tests FIRST (TDD approach)
2. Run `pytest` to ensure tests fail (red)
3. Implement feature
4. Run `pytest` to ensure tests pass (green)
5. Refactor while keeping tests green
6. Commit with confidence!

## Edge Cases Covered

- Empty dataframes
- Zero minutes played
- Missing columns
- Boundary conditions (thresholds)
- Invalid/malformed data
- Extreme values

## Mocking External Calls

```python
from unittest.mock import patch

@patch("infrastructure.api_client.requests.get")
def test_api_call(mock_get):
    mock_get.return_value.json.return_value = {"data": []}
    result = fetch_data("endpoint")
    assert result == {"data": []}
```
