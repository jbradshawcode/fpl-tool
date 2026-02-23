"""Flask web UI for Fantasy Premier League expected points analysis.

This module provides a simple localhost web interface to display player rankings
by position with their expected and actual points per 90 minutes.
"""

import json
import webbrowser
from pathlib import Path
from threading import Timer

import pandas as pd
from flask import Flask, render_template, request

from fpl import calculations, history
from helpers.config import BOOTSTRAP_STATIC_ENDPOINT
from helpers.loading import initialise_data
from helpers.logger import setup_logger, get_logger
from helpers.update_guard import mark_updated, should_update


# Initialize logging
setup_logger()
logger = get_logger(__name__)

app = Flask(__name__)


def open_browser():
    """Open the web browser to the Flask app URL."""
    webbrowser.open_new('http://127.0.0.1:5002/')


def load_data():
    """Load and prepare FPL data with expected points calculations."""
    # Fetch/update histories
    if should_update():
        data = initialise_data(endpoint=BOOTSTRAP_STATIC_ENDPOINT)
        players_df, history_df, scoring = (
            data["players_df"],
            data["history_df"],
            data["scoring"],
        )
        mark_updated()
    else:
        logger.info("Loading data from local files...")
        players_df = pd.read_csv("data/players_data.csv", index_col='id')
        history_df = pd.read_csv("data/player_histories.csv")

        with Path("data/scoring.json").open() as f:
            scoring = json.load(f)

    # Calculate expected points
    history_df = history.calculate_expected_points(
        history_df=history_df,
        players_df=players_df,
        scoring=scoring,
    )

    return players_df, history_df, scoring


def format_player_data(df: pd.DataFrame) -> pd.DataFrame:
    """Format DataFrame for display with proper rounding and conversions."""
    df = df.copy()
    df["actual_points"] = df["actual_points"].round(2)
    df["expected_points"] = df["expected_points"].round(2)
    df["actual_points_per_90"] = df["actual_points_per_90"].round(2)
    df["expected_points_per_90"] = df["expected_points_per_90"].round(2)
    df["now_cost"] = df["now_cost"] / 10  # convert to millions
    df["percentage_of_mins_played"] = (df["percentage_of_mins_played"] * 100).round(2)
    return df


@app.route('/')
def index():
    """Main page displaying player rankings by position."""
    try:
        players_df, history_df, scoring = load_data()
        
        # Calculate max games available
        max_games = int(history_df['round'].max()) if len(history_df) > 0 else 38
        
        # Default to 5 games or max if less than 5 available
        default_games = min(5, max_games)
        
        # Get position, page, mins_threshold, time_period, and sort from query parameters
        selected_position = request.args.get('position', 'GKP', type=str)
        page = request.args.get('page', 1, type=int)
        mins_threshold = request.args.get('mins', 70, type=int)  # Default 70%
        time_period = request.args.get('games', default_games, type=int)  # Default to 5 or max
        sort_by = request.args.get('sort', 'expected_points', type=str)  # Default sort by xP
        sort_order = request.args.get('order', 'desc', type=str)  # Default descending
        per_page = 10
        
        position_names = {
            "GKP": "Goalkeepers",
            "DEF": "Defenders", 
            "MID": "Midfielders",
            "FWD": "Forwards"
        }
        
        # Get all players for selected position with mins threshold and time period
        df = calculations.expected_points_per_90(
            history_df=history_df,
            players_df=players_df,
            position=selected_position,
            mins_threshold=mins_threshold / 100,  # Convert percentage to decimal
            time_period=time_period if time_period < max_games else None,  # None = all games
        )
        
        df = format_player_data(df)
        
        # Apply user's sorting choice
        ascending = (sort_order == 'asc')
        df = df.sort_values(by=sort_by, ascending=ascending).reset_index(drop=True)
        
        # Calculate pagination
        total_players = len(df)
        total_pages = max(1, (total_players + per_page - 1) // per_page)  # Ceiling division, min 1
        
        # Ensure page is within valid range
        page = max(1, min(page, total_pages))
        
        # Get players for current page
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_players = df.iloc[start_idx:end_idx].copy()
        
        # Add simple 1,2,3,4,5... rank for display (just the row number)
        page_players['rank'] = range(start_idx + 1, start_idx + len(page_players) + 1)
        
        # Prepare data for template
        position_data = {
            'name': position_names[selected_position],
            'code': selected_position,
            'players': page_players.to_dict('records'),
            'total_players': total_players,
            'total_pages': total_pages,
            'current_page': page,
            'start_rank': start_idx + 1,
            'end_rank': min(end_idx, total_players)
        }
        
        return render_template(
            'index.html',
            position_data=position_data,
            all_positions=position_names,
            selected_position=selected_position,
            page=page,
            mins_threshold=mins_threshold,
            time_period=time_period,
            max_games=max_games,
            sort_by=sort_by,
            sort_order=sort_order
        )
    
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return f"Error loading data: {e}", 500


if __name__ == '__main__':
    # Open browser only once (not when Flask reloader restarts)
    import os
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        Timer(1.5, open_browser).start()
    app.run(debug=True, host='0.0.0.0', port=5002)
