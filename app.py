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
        players_df, history_df, fdr_df, scoring = (
            data["players_df"],
            data["history_df"],
            data["fdr_df"],
            data["scoring"],
        )
        mark_updated()
    else:
        logger.info("Loading data from local files...")
        players_df = pd.read_csv("data/players_data.csv", index_col='id')
        history_df = pd.read_csv("data/player_histories.csv")
        fdr_df = pd.read_csv("data/fixture_difficulty_ratings.csv")
        fdr_df["round"] = fdr_df["round"].astype(int)
        fdr_df["team_id"] = fdr_df["team_id"].astype(int)
        fdr_df["fixture_difficulty"] = fdr_df["fixture_difficulty"].astype(int)

        with Path("data/scoring.json").open() as f:
            scoring = json.load(f)

    # Calculate expected points
    history_df = history.calculate_expected_points(
        history_df=history_df,
        players_df=players_df,
        scoring=scoring,
    )

    return players_df, history_df, fdr_df, scoring


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
        players_df, history_df, fdr_df, scoring = load_data()
        
        # Calculate max games available
        max_games = int(history_df['round'].max()) if len(history_df) > 0 else 38
        
        # Default to 5 games or max if less than 5 available
        default_games = min(5, max_games)
        
        # Get query parameters
        selected_position = request.args.get('position', '', type=str)
        page = request.args.get('page', 1, type=int)
        mins_threshold = request.args.get('mins', 70, type=int)
        time_period = request.args.get('games', default_games, type=int)
        sort_by = request.args.get('sort', 'expected_points', type=str)
        sort_order = request.args.get('order', 'desc', type=str)
        selected_team = request.args.get('team', '', type=str)
        price_max = request.args.get('price_max', None, type=float)
        adjust_difficulty = request.args.get('adjust_difficulty', 'true', type=str) == 'true'
        horizon = request.args.get('horizon', 5, type=int)
        per_page = 10
        
        position_names = {
            "GKP": "Goalkeepers",
            "DEF": "Defenders", 
            "MID": "Midfielders",
            "FWD": "Forwards"
        }

        fdr_arg = fdr_df if adjust_difficulty else None
        horizon_arg = horizon if adjust_difficulty else None
        
        # Get all players for selected position (or all positions) with mins threshold and time period
        if selected_position:
            df = calculations.expected_points_per_90(
                history_df=history_df,
                players_df=players_df,
                position=selected_position,
                mins_threshold=mins_threshold / 100,
                time_period=time_period if time_period < max_games else None,
                fdr_df=fdr_arg,
                horizon=horizon_arg,
            )
        else:
            # Combine all positions
            dfs = []
            for pos in ["GKP", "DEF", "MID", "FWD"]:
                dfs.append(calculations.expected_points_per_90(
                    history_df=history_df,
                    players_df=players_df,
                    position=pos,
                    mins_threshold=mins_threshold / 100,
                    time_period=time_period if time_period < max_games else None,
                    fdr_df=fdr_arg,
                    horizon=horizon_arg,
                ))
            df = pd.concat(dfs, ignore_index=True)

        df = format_player_data(df)

        # Derive team list and price bounds from the full position dataset (before filtering)
        # so the controls always reflect the full range for the current position
        all_teams = sorted(df['team_name'].dropna().unique().tolist()) if 'team_name' in df.columns else []
        global_price_min = round(float(df['now_cost'].min()), 1) if len(df) > 0 else 4.0
        global_price_max = round(float(df['now_cost'].max()), 1) if len(df) > 0 else 15.0

        # Default price_max to the position maximum if not provided
        if price_max is None:
            price_max = global_price_max

        # Apply price filter
        df = df[df['now_cost'] <= price_max]

        # Apply team filter
        if selected_team and 'team_name' in df.columns:
            df = df[df['team_name'] == selected_team]

        # Apply sorting
        ascending = (sort_order == 'asc')
        df = df.sort_values(by=sort_by, ascending=ascending).reset_index(drop=True)
        
        # Calculate pagination
        total_players = len(df)
        total_pages = max(1, (total_players + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))
        
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        page_players = df.iloc[start_idx:end_idx].copy()
        page_players['rank'] = range(start_idx + 1, start_idx + len(page_players) + 1)
        
        position_data = {
            'name': position_names.get(selected_position, 'All Players'),
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
            sort_order=sort_order,
            all_teams=all_teams,
            selected_team=selected_team,
            price_max=price_max,
            global_price_min=global_price_min,
            global_price_max=global_price_max,
            adjust_difficulty=adjust_difficulty,
            horizon=horizon,
        )
    
    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return f"Error loading data: {e}", 500


if __name__ == '__main__':
    import os
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        Timer(1.5, open_browser).start()
    app.run(debug=True, host='0.0.0.0', port=5002)
