"""Flask web UI entry point for Fantasy Premier League expected points analysis.

This module serves as the minimal entry point. Route logic in routes/,
service orchestration in services/, domain logic in domain/.
"""

import os
from threading import Timer

import pandas as pd
from flask import Flask, render_template, request, jsonify, session

from infrastructure.logger import setup_logger, get_logger
from routes.utils import (
    open_browser,
    format_player_data,
    get_game_metadata,
    parse_query_params,
    get_position_names,
)
from services.data_service import load_fpl_data, fetch_players_for_analysis
from services.player_service import (
    extract_pinned_players,
    apply_all_filters,
    sort_by_column,
    paginate_results,
    get_filter_bounds,
)


# Initialize logging
setup_logger()
logger = get_logger(__name__)

# Flask app instance
app = Flask(__name__)
app.secret_key = "fpl-secret-key-for-sessions"


@app.route("/")
def index():
    """Main page displaying player rankings by position."""
    try:
        players_df, history_df, fdr_df = load_fpl_data()

        # Get game metadata and query parameters
        meta = get_game_metadata(history_df)
        params = parse_query_params(
            request, meta["default_games"], meta["remaining_games"]
        )
        position_names = get_position_names()

        # Fetch player data
        df = fetch_players_for_analysis(
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
        df = apply_all_filters(
            df, price_max, params["selected_team"], params["search_term"], players_df
        )

        # Sort and combine
        df = sort_by_column(df, params["sort_by"], params["sort_order"])
        if len(pinned_df) > 0:
            pinned_df = sort_by_column(
                pinned_df, params["sort_by"], params["sort_order"]
            )
            df = pd.concat([pinned_df, df], ignore_index=True)
            logger.info(
                f"Combined {len(pinned_df)} pinned players with {len(df) - len(pinned_df)} filtered results"
            )

        # Paginate
        page_players, total_players, total_pages, page = paginate_results(
            df, params["page"]
        )

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


@app.route("/api/pin-player", methods=["POST"])
def pin_player():
    """Save or unpin a player in the session."""
    try:
        data = request.get_json()
        player_name = data.get("player_name")
        action = data.get("action")

        if not player_name or action not in ["pin", "unpin"]:
            return jsonify({"success": False, "error": "Invalid request"})

        pinned = session.get("pinned_players", [])

        if action == "pin" and player_name not in pinned:
            pinned.append(player_name)
        elif action == "unpin" and player_name in pinned:
            pinned.remove(player_name)

        session["pinned_players"] = pinned
        logger.info(f"Updated pinned players: {pinned}")

        return jsonify({"success": True, "pinned_players": pinned})

    except Exception as e:
        logger.error(f"Error pinning player: {e}")
        return jsonify({"success": False, "error": str(e)})


if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        Timer(1.5, open_browser).start()
    app.run(debug=True, host="0.0.0.0", port=5002)
