"""Flask web UI for Fantasy Premier League expected points analysis.

This module provides a simple localhost web interface to display player rankings
by position with their expected and actual points per 90 minutes.
"""

import json
import os
import webbrowser
from threading import Timer

import pandas as pd
from flask import Flask, render_template, request, jsonify, session

from fpl import calculations, history
from helpers.config import BOOTSTRAP_STATIC_ENDPOINT
from helpers.loading import initialise_data, search_players
from helpers.logger import setup_logger, get_logger
from helpers.update_guard import mark_updated, should_update


# Initialize logging
setup_logger()
logger = get_logger(__name__)

app = Flask(__name__)
app.secret_key = "fpl-secret-key-for-sessions"  # Required for session management


def open_browser():
    """Open the web browser to the Flask app URL."""
    webbrowser.open_new("http://127.0.0.1:5002/")


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
        players_df = pd.read_csv("data/players_data.csv", index_col="id")
        history_df = pd.read_csv("data/player_histories.csv")
        fdr_df = pd.read_csv("data/fixture_difficulty_ratings.csv")
        fdr_df["round"] = fdr_df["round"].astype(int)
        fdr_df["team_id"] = fdr_df["team_id"].astype(int)
        fdr_df["fixture_difficulty"] = fdr_df["fixture_difficulty"].astype(int)

        with open("data/scoring.json") as f:
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


def get_game_metadata(history_df: pd.DataFrame) -> dict:
    """Calculate game metadata like max games and remaining rounds."""
    max_games = int(history_df["round"].max()) if len(history_df) > 0 else 38
    total_rounds = 38
    return {
        "max_games": max_games,
        "remaining_games": total_rounds - max_games,
        "default_games": min(5, max_games),
    }


def parse_query_params(request, default_games: int, remaining_games: int) -> dict:
    """Parse and return all query parameters from request."""
    return {
        "selected_position": request.args.get("position", "", type=str),
        "page": request.args.get("page", 1, type=int),
        "mins_threshold": request.args.get("mins", 70, type=int),
        "time_period": request.args.get("games", default_games, type=int),
        "sort_by": request.args.get("sort", "expected_points", type=str),
        "sort_order": request.args.get("order", "desc", type=str),
        "selected_team": request.args.get("team", "", type=str),
        "price_max": request.args.get("price_max", None, type=float),
        "search_term": request.args.get("search", "", type=str),
        "adjust_difficulty": request.args.get("adjust_difficulty", "true", type=str)
        == "true",
        "horizon": min(request.args.get("horizon", 5, type=int), remaining_games),
    }


def get_position_names() -> dict:
    """Return mapping of position codes to display names."""
    return {
        "GKP": "Goalkeepers",
        "DEF": "Defenders",
        "MID": "Midfielders",
        "FWD": "Forwards",
    }


def fetch_player_data(
    players_df: pd.DataFrame,
    history_df: pd.DataFrame,
    fdr_df: pd.DataFrame,
    selected_position: str,
    mins_threshold: int,
    time_period: int,
    max_games: int,
    adjust_difficulty: bool,
    horizon: int,
) -> pd.DataFrame:
    """Fetch expected points data for selected position(s)."""
    fdr_arg = fdr_df if adjust_difficulty else None
    horizon_arg = horizon if adjust_difficulty else None

    if selected_position:
        return calculations.expected_points_per_90(
            history_df=history_df,
            players_df=players_df,
            position=selected_position,
            mins_threshold=mins_threshold / 100,
            time_period=time_period if time_period < max_games else None,
            fdr_df=fdr_arg,
            horizon=horizon_arg,
        )

    # Combine all positions
    dfs = [
        calculations.expected_points_per_90(
            history_df=history_df,
            players_df=players_df,
            position=pos,
            mins_threshold=mins_threshold / 100,
            time_period=time_period if time_period < max_games else None,
            fdr_df=fdr_arg,
            horizon=horizon_arg,
        )
        for pos in ["GKP", "DEF", "MID", "FWD"]
    ]
    return pd.concat(dfs, ignore_index=True)


def extract_pinned_players(df: pd.DataFrame, pinned_players: list) -> tuple:
    """Extract pinned players from dataframe and return both sets."""
    if not pinned_players or len(df) == 0 or "web_name" not in df.columns:
        return pd.DataFrame(), df

    pinned_df = df[df["web_name"].isin(pinned_players)].copy()
    remaining_df = df[~df["web_name"].isin(pinned_players)].copy()

    if len(pinned_df) > 0:
        logger.info(f"Extracted {len(pinned_df)} pinned players")

    return pinned_df, remaining_df


def apply_filters(
    df: pd.DataFrame,
    price_max: float,
    selected_team: str,
    search_term: str,
    players_df: pd.DataFrame,
) -> pd.DataFrame:
    """Apply price, team, and search filters to player data."""
    # Price filter
    df = df[df["now_cost"] <= price_max]

    # Team filter
    if selected_team and "team_name" in df.columns:
        df = df[df["team_name"] == selected_team]

    # Search filter
    if search_term and search_term.strip():
        filtered_players = search_players(players_df, search_term)
        if "web_name" in df.columns and len(filtered_players) > 0:
            df = df[df["web_name"].isin(filtered_players["web_name"])]
        elif len(filtered_players) == 0:
            return pd.DataFrame()

    return df


def sort_players(df: pd.DataFrame, sort_by: str, sort_order: str) -> pd.DataFrame:
    """Sort players by specified column with custom position handling."""
    if len(df) == 0:
        return df

    ascending = sort_order == "asc"

    if sort_by not in df.columns:
        default_col = "web_name" if "web_name" in df.columns else df.columns[0]
        logger.warning(f"Sort column '{sort_by}' not found, using '{default_col}'")
        return df.sort_values(by=default_col, ascending=ascending).reset_index(
            drop=True
        )

    # Custom position sort
    if sort_by == "pos_abbr" and "pos_abbr" in df.columns:
        position_order = {"GKP": 0, "DEF": 1, "MID": 2, "FWD": 3}
        df["_sort_key"] = df["pos_abbr"].map(position_order)
        df = df.sort_values(by="_sort_key", ascending=ascending).reset_index(drop=True)
        df = df.drop(columns=["_sort_key"])
    else:
        df = df.sort_values(by=sort_by, ascending=ascending).reset_index(drop=True)

    logger.info(
        f"Sorting by {sort_by} ({'asc' if ascending else 'desc'}) - {len(df)} results"
    )
    return df


def paginate(df: pd.DataFrame, page: int, per_page: int = 10) -> tuple:
    """Calculate pagination and return page of players."""
    total_players = len(df)
    total_pages = max(1, (total_players + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))

    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_players = df.iloc[start_idx:end_idx].copy()
    page_players["rank"] = range(start_idx + 1, start_idx + len(page_players) + 1)

    return page_players, total_players, total_pages, page


def get_filter_bounds(df: pd.DataFrame) -> tuple:
    """Extract team list and price bounds for filter controls."""
    all_teams = (
        sorted(df["team_name"].dropna().unique().tolist())
        if "team_name" in df.columns
        else []
    )

    if len(df) > 0:
        price_min = round(float(df["now_cost"].min()), 1)
        price_max = round(float(df["now_cost"].max()), 1)
    else:
        price_min, price_max = 4.0, 15.0

    return all_teams, price_min, price_max


@app.route("/")
def index():
    """Main page displaying player rankings by position."""
    try:
        players_df, history_df, fdr_df, scoring = load_data()

        # Get game metadata and query parameters
        meta = get_game_metadata(history_df)
        params = parse_query_params(
            request, meta["default_games"], meta["remaining_games"]
        )
        position_names = get_position_names()

        # Fetch player data
        df = fetch_player_data(
            players_df,
            history_df,
            fdr_df,
            params["selected_position"],
            params["mins_threshold"],
            params["time_period"],
            meta["max_games"],
            params["adjust_difficulty"],
            params["horizon"],
        )
        df = format_player_data(df)

        # Get filter bounds from unfiltered data
        all_teams, global_price_min, global_price_max = get_filter_bounds(df)
        price_max = params["price_max"] if params["price_max"] else global_price_max

        # Extract and separate pinned players
        pinned_players = session.get("pinned_players", [])
        logger.info(f"Pinned players from session: {pinned_players}")
        pinned_df, df = extract_pinned_players(df, pinned_players)

        # Apply filters to non-pinned players
        df = apply_filters(
            df, price_max, params["selected_team"], params["search_term"], players_df
        )

        # Sort and combine
        df = sort_players(df, params["sort_by"], params["sort_order"])
        if len(pinned_df) > 0:
            pinned_df = sort_players(pinned_df, params["sort_by"], params["sort_order"])
            df = pd.concat([pinned_df, df], ignore_index=True)
            logger.info(
                f"Combined {len(pinned_df)} pinned players with {len(df) - len(pinned_df)} filtered results"
            )

        # Paginate
        page_players, total_players, total_pages, page = paginate(df, params["page"])

        # Build template context
        position_data = {
            "name": position_names.get(params["selected_position"], "All Players"),
            "code": params["selected_position"],
            "players": page_players.to_dict("records"),
            "total_players": total_players,
            "total_pages": total_pages,
            "current_page": page,
            "start_rank": (page - 1) * 10 + 1,
            "end_rank": min(page * 10, total_players),
        }

        return render_template(
            "index.html",
            position_data=position_data,
            all_positions=position_names,
            selected_position=params["selected_position"],
            page=page,
            mins_threshold=params["mins_threshold"],
            time_period=params["time_period"],
            max_games=meta["max_games"],
            remaining_games=meta["remaining_games"],
            sort_by=params["sort_by"],
            sort_order=params["sort_order"],
            all_teams=all_teams,
            selected_team=params["selected_team"],
            price_max=price_max,
            global_price_min=global_price_min,
            global_price_max=global_price_max,
            adjust_difficulty=params["adjust_difficulty"],
            horizon=params["horizon"],
            search_term=params["search_term"],
        )

    except Exception as e:
        logger.error(f"Error loading data: {e}")
        return f"Error loading data: {e}", 500


@app.route("/api/players")
def api_players():
    """API endpoint for filtered player data (AJAX)."""
    try:
        players_df, history_df, fdr_df, scoring = load_data()

        # Get query parameters (same as main route)
        selected_position = request.args.get("position", "", type=str)
        mins_threshold = request.args.get("mins", 70, type=int)
        time_period = request.args.get("games", 5, type=int)
        sort_by = request.args.get("sort", "expected_points", type=str)
        sort_order = request.args.get("order", "desc", type=str)
        selected_team = request.args.get("team", "", type=str)
        price_max = request.args.get("price_max", None, type=float)
        search_term = request.args.get("search", "", type=str)
        adjust_difficulty = (
            request.args.get("adjust_difficulty", "true", type=str) == "true"
        )
        horizon = request.args.get("horizon", 5, type=int)

        # Calculate max games available
        max_games = int(history_df["round"].max()) if len(history_df) > 0 else 38
        total_rounds = 38
        remaining_games = total_rounds - max_games
        horizon = min(horizon, remaining_games)

        fdr_arg = fdr_df if adjust_difficulty else None
        horizon_arg = horizon if adjust_difficulty else None

        # Get player data (same logic as main route)
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
            all_dfs = []
            for pos in ["GKP", "DEF", "MID", "FWD"]:
                all_dfs.append(
                    calculations.expected_points_per_90(
                        history_df=history_df,
                        players_df=players_df,
                        position=pos,
                        mins_threshold=mins_threshold / 100,
                        time_period=time_period if time_period < max_games else None,
                        fdr_df=fdr_arg,
                        horizon=horizon_arg,
                    )
                )
            df = pd.concat(all_dfs, ignore_index=True)

        # Apply search filter BEFORE formatting
        if search_term and search_term.strip():
            logger.info(
                f"API: Searching for '{search_term}' in DataFrame with {len(df)} rows"
            )
            filtered_players = search_players(players_df, search_term)
            logger.info(f"API: Search found {len(filtered_players)} matches")

            if "web_name" in df.columns and len(filtered_players) > 0:
                original_len = len(df)
                df = df[df["web_name"].isin(filtered_players["web_name"])]
                logger.info(
                    f"API: Filtered DataFrame from {original_len} to {len(df)} rows"
                )
            elif len(filtered_players) == 0:
                logger.info("API: No search matches found, returning empty result")
                # Return empty result immediately without formatting
                return jsonify({"players": [], "total_players": 0, "success": True})

        # Format data for display (same as main route)
        df = format_player_data(df)

        # Apply team filter
        if selected_team and "team_name" in df.columns:
            df = df[df["team_name"] == selected_team]

        # Apply price filter
        if price_max is not None and len(df) > 0 and "now_cost" in df.columns:
            df = df[df["now_cost"] <= price_max]

        # Apply sorting
        ascending = sort_order == "asc"
        if len(df) > 0 and sort_by in df.columns:
            df = df.sort_values(by=sort_by, ascending=ascending).reset_index(drop=True)
        elif len(df) > 0:
            default_sort_col = "web_name" if "web_name" in df.columns else df.columns[0]
            df = df.sort_values(by=default_sort_col, ascending=ascending).reset_index(
                drop=True
            )

        # Return JSON response
        logger.info(f"API: Returning {len(df)} players in response")
        return jsonify(
            {
                "players": df.to_dict("records"),
                "total_players": len(df),
                "success": True,
            }
        )

    except Exception as e:
        logger.error(f"Error in API: {e}")
        return jsonify(
            {"players": [], "total_players": 0, "success": False, "error": str(e)}
        )


@app.route("/api/pin-player", methods=["POST"])
def pin_player():
    """Save or unpin a player in the session."""
    try:
        data = request.get_json()
        player_name = data.get("player_name")
        action = data.get("action")  # 'pin' or 'unpin'

        if not player_name or action not in ["pin", "unpin"]:
            return jsonify({"success": False, "error": "Invalid request"})

        # Get current pinned players from session
        pinned = session.get("pinned_players", [])

        if action == "pin" and player_name not in pinned:
            pinned.append(player_name)
        elif action == "unpin" and player_name in pinned:
            pinned.remove(player_name)

        # Save to session
        session["pinned_players"] = pinned
        logger.info(f"Updated pinned players: {pinned}")

        return jsonify({"success": True, "pinned_players": pinned})

    except Exception as e:
        logger.error(f"Error pinning player: {e}")
        return jsonify({"success": False, "error": str(e)})


if __name__ == "__main__":
    import os

    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        Timer(1.5, open_browser).start()
    app.run(debug=True, host="0.0.0.0", port=5002)
