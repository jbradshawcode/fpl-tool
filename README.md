# FPL Expected Points Tool

A Flask web application for analyzing Fantasy Premier League player performance with expected points calculations.

## Overview

This tool provides comprehensive analysis of FPL player data including:

- **Expected Points Calculation**: Uses advanced metrics (xG, xA, defensive contributions) to calculate expected points per match
- **Player Rankings**: Filter and sort players by position, price, team, and performance metrics
- **Fixture Difficulty Adjustment**: Optionally adjust rankings based on upcoming fixture difficulty
- **Historical Analysis**: View actual vs expected points per 90 minutes
- **Web Interface**: Clean, responsive UI for easy exploration of player data

### Key Features

- Real-time data fetching from FPL API with daily caching
- Concurrent player history downloads for fast updates
- Position-specific analysis (GKP, DEF, MID, FWD)
- Customizable time periods and minutes thresholds
- Price and team filtering
- Pagination for large datasets

## Setup with uv

1. Install uv (if not already installed):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Install dependencies:
```bash
uv sync
```

3. Install development dependencies:
```bash
uv sync --dev
```

## Running

```bash
uv run python app.py
```

The app will open automatically at http://127.0.0.1:5002

## Development

- Format code: `uv run black .`
- Lint: `uv run ruff check .`
- Run tests: `uv run pytest`
